# MySQL 活跃会话与性能分析指南

MySQL 性能排查中，快速定位当前活跃的事务和消耗资源的 SQL 是核心技能。本章介绍从简单的 `SHOW PROCESSLIST` 到基于 Performance Schema 的多维度性能分析方法，帮助运维和开发人员快速发现性能瓶颈。


> 前置要求：以下基于 Performance Schema 的查询需要在 MySQL 5.7+/8.0+ 中启用 `performance_schema = ON`（默认开启）。低版本或关闭状态下数据为空。

---

## 查看当前正在执行的 SQL

最基础的排查命令：

```
show procelist;
```

!!! tip
    这个方法经常看不到任何有用的信息。 
    
1. SQL 可能已经完成执行，但连接仍然空闲；
2. SHOW PROCESSLIST 看到的 `Info` 字段可能被截断（默认只显示前100个字符）；
3. 对于短 SQL（如主键点查），快照的瞬间可能已经执行完毕，导致遗漏。
4. 如果需要查看完整的 SQL，可以使用 `SHOW FULL PROCESSLIST`，但仍然存在快照问题。

因此在生产环境中，推荐结合 Performance Schema 的**历史统计视图**来弥补这一缺陷。

---

## SQL 性能分析（按总耗时排序）

以下查询从 `events_statements_summary_by_digest` 表中提取执行统计信息，**按累计执行时间倒序**，适用于识别系统中最消耗资源的大户 SQL。通常这些是需要优先优化的对象（比如加索引、改写逻辑、做缓存等）。

### 应用场景
- 整体性能突降，需要找到罪魁祸首 SQL。
- 定期巡检，确认 TOP 慢 SQL 清单。
- 对比优化前后的效果（通过耗时占比、执行次数等指标）。

### 查询字段说明
| 字段分组 | 指标 | 含义 |
|---|---|---|
| SQL 与元信息 | `SQL 模板` | 规范化（脱敏）后的 SQL 结构，同一类查询归并显示，长度限制为250字符 |
|  | `数据库` | 该 SQL 执行时的默认 Schema |
| 时间与频率 | `执行次数` / `总耗时(秒)` | 反映该类 SQL 的总体压力；**耗时占比%** 是识别重点 SQL 的黄金指标 |
| 执行行数 | `平均返回行` / `平均扫描行` | 两者差距大（扫描多返回少）通常意味着全表扫描、索引未命中或回表过多 |
| 效率指标 | `扫描效率%` | 返回行 ÷ 扫描行 × 100，比例越高说明索引利用率越好；若持续低于 10%，需要优化 |
| 资源消耗 | `内存临时表` / `磁盘临时表` | 磁盘临时表会写物理磁盘，性能最差；应检查 ORDER BY / GROUP BY 列是否有足够索引 |
| 索引情况 | `未用索引次数` / `无合适索引次数` | 数字 >0 即告警，需添加或调整索引 |
| 锁与时间 | `总锁等待(秒)` / `排序合并` | 锁等待高说明并发冲突严重；排序合并多代表 sort_buffer_size 不足 |
| 时效性 | `首次出现` / `最近出现` / `几分钟前` | 判断 SQL 是常驻还是近期新出现，协助定位是否是发布变更引入的新问题 |

```
-- ========================================
-- SQL 性能分析完整版
-- ========================================

SELECT 
    -- SQL 模板（脱敏，去掉具体值）
    LEFT(DIGEST_TEXT, 250) AS 'SQL模板',
    
    SCHEMA_NAME AS '数据库',
    COUNT_STAR AS '执行次数',
    
    -- ===== 时间分析 =====
    ROUND(SUM_TIMER_WAIT / 1000000000000, 3) AS '总耗时(秒)',
    ROUND(AVG_TIMER_WAIT / 1000000000000, 4) AS '平均耗时(秒)',
    ROUND(MIN_TIMER_WAIT / 1000000000000, 6) AS '最小耗时(秒)',
    ROUND(MAX_TIMER_WAIT / 1000000000000, 4) AS '最大耗时(秒)',
    
    -- 耗时占比估算
    ROUND(
        SUM_TIMER_WAIT * 100.0 / 
        (SELECT SUM(SUM_TIMER_WAIT) FROM performance_schema.events_statements_summary_by_digest WHERE SCHEMA_NAME IS NOT NULL),
        2
    ) AS '耗时占比%',
    
    -- ===== 行数分析 =====
    SUM_ROWS_SENT AS '总返回行',
    ROUND(SUM_ROWS_SENT / COUNT_STAR, 2) AS '平均返回行',
    SUM_ROWS_EXAMINED AS '总扫描行',
    ROUND(SUM_ROWS_EXAMINED / COUNT_STAR, 2) AS '平均扫描行',
    
    -- 扫描效率（返回/扫描比，越高越好）
    ROUND(
        CASE WHEN SUM_ROWS_EXAMINED > 0 
             THEN SUM_ROWS_SENT * 100.0 / SUM_ROWS_EXAMINED 
             ELSE 0 
        END, 
        2
    ) AS '扫描效率%',
    
    -- ===== 资源消耗 =====
    SUM_CREATED_TMP_TABLES AS '内存临时表',
    SUM_CREATED_TMP_DISK_TABLES AS '磁盘临时表',
    SUM_NO_INDEX_USED AS '未用索引次数',
    SUM_NO_GOOD_INDEX_USED AS '无合适索引次数',
    
    -- ===== 排序和锁 =====
    SUM_SORT_MERGE_PASSES AS '排序合并',
    SUM_LOCK_TIME / 1000000000000 AS '总锁等待(秒)',

    -- ===== 时间戳 =====
    FIRST_SEEN AS '首次出现',
    LAST_SEEN AS '最近出现',
    
    -- 距离现在多久
    TIMESTAMPDIFF(MINUTE, LAST_SEEN, NOW()) AS '几分钟前'

FROM performance_schema.events_statements_summary_by_digest

WHERE SCHEMA_NAME IS NOT NULL
  -- 过滤掉系统查询
  AND DIGEST_TEXT NOT LIKE '%SHOW%'
  AND DIGEST_TEXT NOT LIKE '%SELECT% FROM performance_schema%'
  AND DIGEST_TEXT NOT LIKE '%SELECT% FROM information_schema%'
  AND DIGEST_TEXT NOT LIKE '%mysql.%'
  -- 只显示有执行记录的
  AND COUNT_STAR > 0

ORDER BY SUM_TIMER_WAIT DESC
LIMIT 25;

```

---

## 高执行频率 SQL 分析（按执行次数排序）

虽然累计耗时长是常见的优化目标，但有些 SQL **单条执行时间很短，但执行次数极高**，对 CPU、连接池或缓存造成巨大压力。此查询按 **COUNT_STAR（执行次数）** 排序，专门暴露“积少成多”的隐患类 SQL。

### 关键观察维度
- `执行次数`极高且 `平均耗时`不低 → 可能适合做**结果集缓存**或使用中间汇总表。
- `平均返回行` = 1, `平均扫描行` 很大 → 每次都在走全表扫描的**点查小SQL**，加一条索引即可解决。
- `总锁等待(秒)` 与 `平均耗时` 比例失调 → 可能存在行锁竞争（如并发更新同一记录）或间隙锁导致等待。

```
-- ========================================
-- SQL 性能分析完整版（按高频排序）
-- ========================================

SELECT 
    -- SQL 模板（脱敏，去掉具体值）
    LEFT(DIGEST_TEXT, 250) AS 'SQL模板',
    
    SCHEMA_NAME AS '数据库',
    COUNT_STAR AS '执行次数',
    
    -- ===== 时间分析 =====
    ROUND(SUM_TIMER_WAIT / 1000000000000, 3) AS '总耗时(秒)',
    ROUND(AVG_TIMER_WAIT / 1000000000000, 4) AS '平均耗时(秒)',
    ROUND(MIN_TIMER_WAIT / 1000000000000, 6) AS '最小耗时(秒)',
    ROUND(MAX_TIMER_WAIT / 1000000000000, 4) AS '最大耗时(秒)',
    
    -- 耗时占比估算
    ROUND(
        SUM_TIMER_WAIT * 100.0 / 
        (SELECT SUM(SUM_TIMER_WAIT) FROM performance_schema.events_statements_summary_by_digest WHERE SCHEMA_NAME IS NOT NULL),
        2
    ) AS '耗时占比%',
    
    -- ===== 行数分析 =====
    SUM_ROWS_SENT AS '总返回行',
    ROUND(SUM_ROWS_SENT / COUNT_STAR, 2) AS '平均返回行',
    SUM_ROWS_EXAMINED AS '总扫描行',
    ROUND(SUM_ROWS_EXAMINED / COUNT_STAR, 2) AS '平均扫描行',
    
    -- 扫描效率（返回/扫描比，越高越好）
    ROUND(
        CASE WHEN SUM_ROWS_EXAMINED > 0 
             THEN SUM_ROWS_SENT * 100.0 / SUM_ROWS_EXAMINED 
             ELSE 0 
        END, 
        2
    ) AS '扫描效率%',
    
    -- ===== 资源消耗 =====
    SUM_CREATED_TMP_TABLES AS '内存临时表',
    SUM_CREATED_TMP_DISK_TABLES AS '磁盘临时表',
    SUM_NO_INDEX_USED AS '未用索引次数',
    SUM_NO_GOOD_INDEX_USED AS '无合适索引次数',
    
    -- ===== 排序和锁 =====
    SUM_SORT_MERGE_PASSES AS '排序合并',
    SUM_LOCK_TIME / 1000000000000 AS '总锁等待(秒)',

    -- ===== 时间戳 =====
    FIRST_SEEN AS '首次出现',
    LAST_SEEN AS '最近出现',
    
    -- 距离现在多久
    TIMESTAMPDIFF(MINUTE, LAST_SEEN, NOW()) AS '几分钟前'

FROM performance_schema.events_statements_summary_by_digest

WHERE SCHEMA_NAME IS NOT NULL
  -- 过滤掉系统查询
  AND DIGEST_TEXT NOT LIKE '%SHOW%'
  AND DIGEST_TEXT NOT LIKE '%SELECT% FROM performance_schema%'
  AND DIGEST_TEXT NOT LIKE '%SELECT% FROM information_schema%'
  AND DIGEST_TEXT NOT LIKE '%mysql.%'
  -- 只显示有执行记录的
  AND COUNT_STAR > 0

ORDER BY COUNT_STAR DESC
LIMIT 25;

```

---

## 近期活跃 SQL 分析（按最近出现时间）

与上面按累计量排序不同的是，这个查询聚焦 **"最近刚发生过什么"**，非常适合追踪**刚刚发生的故障或性能抖动**。它只筛选最近 **1 小时内**执行过的 SQL（可调整 `INTERVAL 1 HOUR`），按最后出现时间 `LAST_SEEN` 倒序排列。

### 使用技巧
- 配合问题发生的时刻（如监控告警点、业务反馈卡顿时间），可快速确认当时是哪类 SQL 在运行。
- 观察 `距今(秒)`：数值很小说明是持续活跃的 SQL，数值较大则可能已经间歇停止。
- **问题标记**字段做了简单自动诊断，看到 `⚠️` 标识应重点审查。

!!! note "扩展建议"
    在 8.0.30+ 中，MySQL 新增了 `events_statements_histogram_global` 和 `events_statements_histogram_by_digest`，可以提供执行耗时的直方图分析，适合更细粒度的延迟分布排查。

```
-- ========================================
-- 最近活跃的 SQL（按 LAST_SEEN 排序）
-- ========================================

SELECT 
    LEFT(DIGEST_TEXT, 200) AS 'SQL模板',
    SCHEMA_NAME AS '数据库',
    COUNT_STAR AS '累计执行次数',
    
    -- 耗时
    ROUND(AVG_TIMER_WAIT / 1000000000000, 4) AS '平均耗时(秒)',
    ROUND(MAX_TIMER_WAIT / 1000000000000, 4) AS '最大耗时(秒)',
    
    -- 行数效率
    ROUND(SUM_ROWS_EXAMINED / COUNT_STAR, 0) AS '平均扫描行',
    ROUND(
        CASE WHEN SUM_ROWS_EXAMINED > 0 
             THEN SUM_ROWS_SENT * 100.0 / SUM_ROWS_EXAMINED 
             ELSE 0 
        END, 
        2
    ) AS '效率%',
    
    -- 问题标记
    CASE 
        WHEN SUM_NO_INDEX_USED > 0 THEN '⚠️ 未用索引'
        WHEN SUM_CREATED_TMP_DISK_TABLES > 0 THEN '⚠️ 磁盘临时表'
        WHEN SUM_ROWS_EXAMINED / COUNT_STAR > 10000 THEN '⚠️ 扫描量大'
        ELSE '✅ 正常'
    END AS '问题标记',
    
    LAST_SEEN AS '最近出现',
    TIMESTAMPDIFF(SECOND, LAST_SEEN, NOW()) AS '距今(秒)'

FROM performance_schema.events_statements_summary_by_digest

WHERE SCHEMA_NAME IS NOT NULL
  AND LAST_SEEN > DATE_SUB(NOW(), INTERVAL 1 HOUR)  -- 只查最近1小时活跃的
  AND DIGEST_TEXT NOT LIKE '%performance_schema%'

ORDER BY LAST_SEEN DESC
LIMIT 30;

```

---

## 查看单条 SQL 的完整历史执行记录

前面的统计视图能告诉你 "SQL 长什么样" 以及 "表现如何"，但如果你需要深入追查某一条**具体 digest** 的历史执行序列（包括真实的 SQL 文本、某次执行的实际时间、执行过程中的错误信息等），则需要查询 `events_statements_history` 或 `events_statements_history_long`。

### 表差异
| 表名 | 保留方式 | 默认行数 |
|---|---|---|
| `events_statements_history` | 每个 Thread 各存10条，循环覆写 | 约线程数 × 10 |
| `events_statements_history_long` | 全局总计循环覆写 | 默认 10,000 行 (受 `performance_schema_events_statements_history_long_size` 控制) |

建议**在线程很多时**使用 `history_long`，否则单线程历史更容易在 `history` 表命中（减少覆写丢失）。

### 字段解析
- `完整SQL`：这里包含具体参数值（可能有敏感信息），仅做开发调试之用，严禁随意外泄。
- `估计执行时间`：Performance Schema 的时间戳单位是皮秒，此处将其推算到实际 UNIX 时间上，方便与业务告警时间进行关联。
- `SOURCE`：源码行号定位，MySQL 8.0 中较有用；社区版一般不需深究。

### 使用步骤
1. 先运行上述 "SQL 性能分析" 查询，找到需要关注的 SQL；
2. 同时拿到它的 `DIGEST`（该 SQL 的规范化签名哈希值，通常以十六进制呈现）；
3. 替换本查询最后一行 `'上面查到的digest值'` 后再次执行，即可看到这条 SQL 近一段时间的每一次执行情况明细。

```
-- ========================================
-- 查看某个 DIGEST 的具体执行历史
-- ========================================

-- 先用上面的查询找到感兴趣的 DIGEST，然后：

SELECT 
    THREAD_ID,
    EVENT_ID,
    SQL_TEXT AS '完整SQL',  -- 注意：这里可能有敏感数据
    CURRENT_SCHEMA,
    
    ROUND(TIMER_WAIT / 1000000000000, 4) AS '耗时(秒)',
    ROWS_SENT AS '返回行',
    ROWS_EXAMINED AS '扫描行',
    
    CREATED_TMP_TABLES AS '内存临时表',
    CREATED_TMP_DISK_TABLES AS '磁盘临时表',
    NO_INDEX_USED AS '未用索引',
    
    SOURCE,  -- 源代码位置，用于定位问题
    MESSAGE_TEXT AS '错误信息',
    
    FROM_UNIXTIME(
        (TIMER_START / 1000000000000) - 
        (SELECT VARIABLE_VALUE / 1000000 FROM performance_schema.global_status WHERE VARIABLE_NAME = 'UPTIME') +
        UNIX_TIMESTAMP()
    ) AS '估计执行时间'

FROM performance_schema.events_statements_history_long  -- 或者 events_statements_history

WHERE DIGEST = '上面查到的digest值'  -- 替换为实际的 digest hash

ORDER BY TIMER_START DESC
LIMIT 50;

```

### 性能分析思路总结

```text
排查流程（由粗到细）：

┌─────────────────┐
│ 1. SHOW PROCESSLIST │ ← 先扫视当前是否卡住（实时快照）
└────────┬────────┘
         │
┌────────▼────────┐
│ 2. 按耗时或执行次数分析  │ ← 从 summary_by_digest 找出大对象
│   (TOP 慢 SQL 或高频率 SQL)
└────────┬────────┘
         │
┌────────▼────────┐
│ 3. 关注扫描效率、     │ ← 判断是全表扫描、索引未命中、
│    临时表、锁等待、    │   临时表溢出还是锁争抢
│    耗时分布异常等     │
└────────┬────────┘
         │
┌────────▼────────┐
│ 4. 定位具体 Digest，  │ ← 从 events_statements_history 中看具体 SQL 文本
│    看单次执行历史     │     和每一次执行的上下文
└─────────────────┘
```

掌握上述四个层面的查询和分析能力，基本能覆盖生产环境中绝大多数的性能诊断和活跃 SQL 追查场景。建议将它们封装在 SQL 脚本或运维管理平台中，便于一键调取。

