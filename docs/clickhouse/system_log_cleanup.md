# ClickHouse system 库膨胀治理指南

> 适用场景：ClickHouse 集群 `system` 库日志表无限膨胀，占用大量磁盘空间，需要清理并配置自动回收策略。

---

## 查看 Database / Table 大小

### 按 Database 汇总

```sql
SELECT
    database,
    formatReadableSize(sum(bytes_on_disk)) AS total_size,
    sum(rows) AS total_rows,
    countDistinct(table) AS table_count
FROM system.parts
WHERE active
GROUP BY database
ORDER BY sum(bytes_on_disk) DESC;
```

### 按 Database + Table 细分

```sql
SELECT
    database,
    table,
    formatReadableSize(sum(bytes_on_disk)) AS size,
    sum(rows) AS rows,
    max(modification_time) AS latest_modification
FROM system.parts
WHERE active
GROUP BY database, table
ORDER BY database, sum(bytes_on_disk) DESC;
```

### 查看压缩率等详细信息

```sql
SELECT
    database,
    table,
    formatReadableSize(sum(bytes_on_disk)) AS disk_size,
    formatReadableSize(sum(data_compressed_bytes)) AS compressed,
    formatReadableSize(sum(data_uncompressed_bytes)) AS uncompressed,
    round(sum(data_compressed_bytes) / sum(data_uncompressed_bytes), 2) AS compress_ratio
FROM system.parts
WHERE active
GROUP BY database, table
ORDER BY sum(bytes_on_disk) DESC;
```

### 查看磁盘整体使用情况

```sql
SELECT
    name,
    path,
    formatReadableSize(free_space) AS free,
    formatReadableSize(total_space) AS total
FROM system.disks;
```

---

## system 库为什么会膨胀

ClickHouse 内置了多张系统日志表，用于记录查询、性能指标、数据合并等诊断信息。这些表默认使用 **普通 `MergeTree` 引擎**（非复制表），**默认不配置 TTL**，数据会永久累积。

### 主要日志表说明

| 表名 | 用途 | 膨胀风险 |
|------|------|---------|
| `system.asynchronous_metric_log` | 异步系统指标（CPU、内存、磁盘 I/O 等） | **最高**，每秒采集一次，默认无 TTL |
| `system.metric_log` | 同步内部计数器（查询数、连接数等） | 高，每分钟写入 |
| `system.trace_log` | 采样堆栈追踪，用于性能剖析 | 中高，取决于采样率 |
| `system.query_log` | 所有执行过的 SQL 记录 | 中等 |
| `system.part_log` | MergeTree part 的增删改操作 | 低 |
| `system.processors_profile_log` | 查询执行计划处理器级性能 | 低 |

### 膨胀根因

1. **无 TTL**：`CREATE TABLE` 语句中没有 `TTL event_date + INTERVAL ...`，数据永久保留
2. **高频采集**：`asynchronous_metrics_update_period_s = 1`（每秒采集一次）
3. **多节点独立存储**：`system` 表是**本地表**，每个分片/副本各自存储，集群节点越多，总量越大

---

## 清理 system 库数据

> ⚠️ **重要**：`system` 表是**本地 MergeTree**，不是 `ReplicatedMergeTree`，**需要在每个节点分别执行**清理操作。

### 方式一：ALTER DELETE（轻量清理，不立即释放磁盘）

按时间条件删除旧数据，适合保留近期数据、删除远期数据的场景。

```sql
-- 保留最近 7 天，删除更早的数据
ALTER TABLE system.asynchronous_metric_log 
    DELETE WHERE event_date < today() - 7;

ALTER TABLE system.metric_log 
    DELETE WHERE event_date < today() - 7;

ALTER TABLE system.trace_log 
    DELETE WHERE event_date < today() - 3;

ALTER TABLE system.query_log 
    DELETE WHERE event_date < today() - 7;

ALTER TABLE system.part_log 
    DELETE WHERE event_date < today() - 7;

ALTER TABLE system.processors_profile_log 
    DELETE WHERE event_date < today() - 7;
```

**特点**：
- 异步执行，后台通过 mutation merge 逐步清理
- **不会立即释放磁盘空间**，旧 part 标记为 inactive，等后续 merge 才真正删除
- 大表上可能非常慢，甚至卡住（见常见问题排查）

### 方式二：TRUNCATE（立即清空，推荐）

直接清空整张表，**立即释放磁盘空间**，不影响业务数据。

```sql
TRUNCATE TABLE system.asynchronous_metric_log;
TRUNCATE TABLE system.trace_log;
TRUNCATE TABLE system.metric_log;
TRUNCATE TABLE system.query_log;
TRUNCATE TABLE system.part_log;
TRUNCATE TABLE system.processors_profile_log;
```

**特点**：
- 秒级完成，立即释放空间
- 只清空数据，**表结构保留**
- 不影响业务，只是丢失历史监控日志

### 方式三：DROP TABLE（极端情况）

当表被僵死的 mutation/merge 阻塞，TRUNCATE 也卡住时使用。

```sql
-- 强制删除整张表（包括数据和结构）
DROP TABLE system.asynchronous_metric_log SYNC;
```

**特点**：
- `SYNC` 表示同步等待，避免异步挂起
- `system` 表删除后，ClickHouse 会在**下一次写入时自动重建**表结构（最多延迟 1~60 秒）
- 重建后的表**不会自动带 TTL**，需要手动再执行 `ALTER TABLE ... MODIFY TTL`

---

## 设置 TTL 彻底修复

清理只是治标，**必须配置 TTL** 才能防止再次膨胀。

### 在线修改表 TTL（无需重启，立即生效）

清理完数据后，立即为每张表添加 TTL：

```sql
-- 异步指标日志：保留 7 天（最占空间，优先处理）
ALTER TABLE system.asynchronous_metric_log 
    MODIFY TTL event_date + INTERVAL 7 DAY;

-- 指标日志：保留 7 天
ALTER TABLE system.metric_log 
    MODIFY TTL event_date + INTERVAL 7 DAY;

-- 追踪日志：保留 3 天（如无性能剖析需求，可关闭）
ALTER TABLE system.trace_log 
    MODIFY TTL event_date + INTERVAL 3 DAY;

-- 查询日志：保留 7 天
ALTER TABLE system.query_log 
    MODIFY TTL event_date + INTERVAL 7 DAY;

-- Part 操作日志：保留 7 天
ALTER TABLE system.part_log 
    MODIFY TTL event_date + INTERVAL 7 DAY;

-- 处理器性能日志：保留 7 天
ALTER TABLE system.processors_profile_log 
    MODIFY TTL event_date + INTERVAL 7 DAY;
```

**验证 TTL 是否生效**：

```sql
SHOW CREATE TABLE system.asynchronous_metric_log;
-- 确认输出中包含：TTL event_date + INTERVAL 7 DAY
```

### 服务端配置文件永久生效（推荐）

在 `config.xml` 的 `<system_logs>` 段配置 TTL，这样：
- 新节点启动时自动创建带 TTL 的 system 表
- 节点重建/Pod 重启后配置不丢失

```xml
<system_logs>
    <asynchronous_metric_log>
        <ttl>event_date + INTERVAL 7 DAY</ttl>
    </asynchronous_metric_log>
    <metric_log>
        <ttl>event_date + INTERVAL 7 DAY</ttl>
    </metric_log>
    <trace_log>
        <ttl>event_date + INTERVAL 3 DAY</ttl>
    </trace_log>
    <query_log>
        <ttl>event_date + INTERVAL 7 DAY</ttl>
    </query_log>
    <part_log>
        <ttl>event_date + INTERVAL 7 DAY</ttl>
    </part_log>
    <processors_profile_log>
        <ttl>event_date + INTERVAL 7 DAY</ttl>
    </processors_profile_log>
</system_logs>
```

**Helm Chart 配置示例**（`values.yaml`）：

```yaml
clickhouse:
  config:
    system_logs:
      asynchronous_metric_log:
        ttl: "event_date + INTERVAL 7 DAY"
      metric_log:
        ttl: "event_date + INTERVAL 7 DAY"
      trace_log:
        ttl: "event_date + INTERVAL 3 DAY"
      query_log:
        ttl: "event_date + INTERVAL 7 DAY"
      part_log:
        ttl: "event_date + INTERVAL 7 DAY"
      processors_profile_log:
        ttl: "event_date + INTERVAL 7 DAY"
```

### 降低异步指标采集频率

如果 7 天 TTL 后数据增长仍然过快，可以降低采集频率。在 `config.xml` 中：

```xml
<!-- 默认 1 秒，建议调整为 10~60 秒 -->
<asynchronous_metrics_update_period_s>60</asynchronous_metrics_update_period_s>
```

### 直接关闭不需要的日志

如果某些日志在生产环境完全不需要，可以直接关闭：

```xml
<!-- 在 config.xml 中移除该日志表 -->
<trace_log remove="remove"/>
<processors_profile_log remove="remove"/>
```

---

## 常见问题排查

### ALTER / TRUNCATE 卡住怎么办

**第一步：查看 merge 状态**

```sql
SELECT 
    database,
    table,
    elapsed,
    progress,
    num_parts,
    is_mutation
FROM system.merges 
WHERE table = 'asynchronous_metric_log';
```

- `is_mutation = 1`：DELETE / TTL 触发的 mutation merge，可能非常慢
- `is_mutation = 0`：正常后台 merge，通常 1~2 分钟完成
- `progress = 0` 且 `elapsed` 很长（>10 分钟）：**僵死任务，需要处理**

**第二步：查看 mutation 队列**

```sql
SELECT 
    mutation_id,
    command,
    create_time,
    is_done
FROM system.mutations
WHERE table = 'asynchronous_metric_log'
ORDER BY create_time DESC;
```

**第三步：取消僵死 mutation**

```sql
-- 取消该表所有挂起的 mutation
KILL MUTATION WHERE database = 'system' AND table = 'asynchronous_metric_log';

-- 或逐个取消
KILL MUTATION WHERE mutation_id = 'mutation_xxxx.txt';
```

**第四步：停止 merge 后强制清理**

```sql
-- 停止该表的新 merge 调度
SYSTEM STOP MERGES system.asynchronous_metric_log;

-- 强制删除（清掉所有僵死任务和磁盘文件）
DROP TABLE system.asynchronous_metric_log SYNC;

-- 恢复 merge 调度
SYSTEM START MERGES system.asynchronous_metric_log;

-- 等 2-3 秒表自动重建后，加 TTL
ALTER TABLE system.asynchronous_metric_log 
    MODIFY TTL event_date + INTERVAL 7 DAY;
```

### 出现 "Read-only file system" 报错

这通常意味着：
- 磁盘已满（PVC 配额耗尽）
- 文件系统因 I/O 错误进入只读保护模式

**排查**：

```sql
-- 查看磁盘空间
SELECT name, formatReadableSize(free_space) AS free FROM system.disks;
```

**处理**：
- 如果是磁盘满，先通过 `TRUNCATE` 释放空间
- 如果是文件系统损坏，需要检查底层存储/PVC，必要时重启 Pod

### 修改 TTL 后空间没有立即释放

TTL 修改后，ClickHouse 不会立即扫描全表删除旧数据。过期数据会在以下时机被清理：
- 后台定期 merge 时
- 手动触发：`OPTIMIZE TABLE system.asynchronous_metric_log FINAL`

如果磁盘非常紧张，建议先 `TRUNCATE` 清空表，再加 TTL。

---

## 推荐治理流程（一键参考）

```sql
-- Step 1: 确认哪些表占用了空间
SELECT database, table, formatReadableSize(sum(bytes_on_disk)) AS size
FROM system.parts WHERE active GROUP BY database, table ORDER BY size DESC;

-- Step 2: 清理大表（每个节点都要执行）
TRUNCATE TABLE system.asynchronous_metric_log;
TRUNCATE TABLE system.trace_log;
TRUNCATE TABLE system.metric_log;

-- Step 3: 添加 TTL 防止再次膨胀
ALTER TABLE system.asynchronous_metric_log MODIFY TTL event_date + INTERVAL 7 DAY;
ALTER TABLE system.trace_log MODIFY TTL event_date + INTERVAL 3 DAY;
ALTER TABLE system.metric_log MODIFY TTL event_date + INTERVAL 7 DAY;
ALTER TABLE system.query_log MODIFY TTL event_date + INTERVAL 7 DAY;
ALTER TABLE system.part_log MODIFY TTL event_date + INTERVAL 7 DAY;
ALTER TABLE system.processors_profile_log MODIFY TTL event_date + INTERVAL 7 DAY;

-- Step 4: 验证
SHOW CREATE TABLE system.asynchronous_metric_log;
```

---

## 注意事项

1. **每个节点独立执行**：`system` 表是本地 `MergeTree`，不通过 ZooKeeper/Keeper 同步，集群中每个节点都需要单独清理和配置 TTL
2. **不影响业务数据**：`system` 表只存储监控诊断日志，清理或删除不会丢失业务数据
3. **DROP 后自动重建**：`system` 表被删除后，ClickHouse 会自动重建，无需手动 `CREATE TABLE`
4. **配置持久化**：在线 `ALTER` 修改的 TTL 只保存在当前节点，Pod 重建后可能丢失。建议在 `config.xml` 中配置 `<system_logs>` 实现持久化
5. **滚动重启策略**：如果在 `config.xml` 中修改了配置，需要逐个节点滚动重启，避免整个集群同时不可用