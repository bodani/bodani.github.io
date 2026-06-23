# MySQL 8.0 #innodb_temp 空间膨胀排查手册

> 适用场景：`#innodb_temp` 目录异常增大，磁盘空间告警
> 核心机制：MySQL 8.0 为每个会话分配独立的 `.ibt` 临时表空间文件，会话断开时才会截断回收

---

## 一、快速诊断流程（决策树）

```
#innodb_temp 过大？
  │
  ├─> 检查 INNODB_TEMP_TABLE_INFO
  │    │
  │    ├─ 有记录 → 当前存在活跃临时表，定位产生它的 SQL
  │    │
  │    └─ 无记录 → 临时表已删除，但 .ibt 文件空间未回收
  │         │
  │         └─> 检查 INNODB_SESSION_TEMP_TABLESPACES
  │              │
  │              ├─ 文件少且小 → 正常现象，空间可能被 ibtmp1 占用
  │              │
  │              └─ 文件多且大 → 大量会话持有膨胀的 .ibt 文件
  │                   │
  │                   └─> 检查 PROCESSLIST
  │                        │
  │                        ├─ COMMAND=Sleep → 空闲长连接，调超时或 Kill
  │                        │
  │                        └─ COMMAND=Query → 活跃查询，继续排查
  │                             │
  │                             ├─ STATE=converting HEAP to ondisk
  │                             │    → 内存临时表溢出，检查 temptable_max_ram
  │                             │
  │                             └─ 检查 events_statements_summary_by_digest
  │                                  → 定位产生磁盘临时表最多的 SQL
```

---

## 二、详细排查步骤

### Step 1：确认当前活跃临时表

```sql
SELECT * FROM information_schema.INNODB_TEMP_TABLE_INFO;
```

| 结果 | 含义 |
|------|------|
| Empty set | 当前没有活跃临时表，空间占用来自历史会话遗留的 `.ibt` 文件 |
| 有记录 | 存在正在使用的临时表，记录 `TABLE_ID` 和 `NAME` 继续追踪 |

---

### Step 2：检查会话临时表空间文件

```sql
SELECT 
    ID, SPACE, PATH, SIZE, STATE, PURPOSE,
    SIZE / 1024 / 1024 / 1024 AS size_gb
FROM information_schema.INNODB_SESSION_TEMP_TABLESPACES
ORDER BY SIZE DESC;
```

| 字段 | 说明 |
|------|------|
| `ID` | 会话 ID，对应 `PROCESSLIST.ID` |
| `SIZE` | 该会话 `.ibt` 文件当前大小 |
| `STATE` | `ACTIVE`（在用）/ `INACTIVE`（空闲但保留） |
| `PURPOSE` | `INTRINSIC`（优化器内部临时表）/ `USER`（用户显式临时表） |

**判断标准：**
- 文件数量 > 100 且单文件 > 100MB → 高并发 + 大临时表，需立即处理
- `PURPOSE = INTRINSIC` → 优化器自动产生，通常由复杂 SQL 触发
- `PURPOSE = USER` → 应用显式 `CREATE TEMPORARY TABLE`，检查是否未 `DROP`

---

### Step 3：关联会话状态

```sql
SELECT 
    p.ID, p.USER, p.HOST, p.DB, p.COMMAND, p.TIME, p.STATE, p.INFO,
    t.SIZE / 1024 / 1024 / 1024 AS temp_gb
FROM information_schema.PROCESSLIST p
JOIN information_schema.INNODB_SESSION_TEMP_TABLESPACES t ON p.ID = t.ID
ORDER BY p.TIME DESC;
```

| COMMAND | STATE | 诊断 | 处理 |
|---------|-------|------|------|
| `Sleep` | `NULL` | 空闲长连接，`.ibt` 文件膨胀后未释放 | 调小 `wait_timeout` 或 Kill |
| `Query` | `executing` | 正在执行查询，可能产生大临时表 | 检查执行时间，超长的 Kill |
| `Query` | `converting HEAP to ondisk` | 内存临时表溢出到磁盘 | 优化 SQL + 增大 `temptable_max_ram` |
| `Query` | `Waiting for table lock` / `Waiting for metadata lock` | 被锁阻塞 | 排查锁等待，Kill 阻塞源 |

---

### Step 4：检查锁等待（排除卡死）

```sql
-- 检查 InnoDB 行锁等待（MySQL 8.0 使用 performance_schema）
SELECT 
    r.OBJECT_SCHEMA, r.OBJECT_NAME, r.THREAD_ID AS waiting_thread,
    b.THREAD_ID AS blocking_thread, r.LOCK_TYPE AS waiting_lock,
    b.LOCK_TYPE AS blocking_lock, r.LOCK_STATUS AS waiting_status,
    b.LOCK_STATUS AS blocking_status
FROM performance_schema.data_lock_waits w
JOIN performance_schema.data_locks r ON r.ENGINE_LOCK_ID = w.REQUESTING_ENGINE_LOCK_ID
JOIN performance_schema.data_locks b ON b.ENGINE_LOCK_ID = w.BLOCKING_ENGINE_LOCK_ID;

-- 检查元数据锁（MDL）
SELECT * FROM performance_schema.metadata_locks 
WHERE LOCK_STATUS = 'PENDING';
```

- 有结果 → 查询被锁阻塞，定位阻塞源并 Kill
- 无结果 → 查询确实在执行（或资源等待），继续分析 SQL

---

### Step 5：定位产生磁盘临时表的 SQL（最关键）

```sql
SELECT 
    DIGEST_TEXT,
    COUNT_STAR,
    SUM_CREATED_TMP_TABLES,
    SUM_CREATED_TMP_DISK_TABLES,
    AVG_TIMER_WAIT / 1000000000000 AS avg_sec,
    MAX_TIMER_WAIT / 1000000000000 AS max_sec
FROM performance_schema.events_statements_summary_by_digest
WHERE SUM_CREATED_TMP_DISK_TABLES > 0
ORDER BY SUM_CREATED_TMP_DISK_TABLES DESC
LIMIT 10;
```

| 指标 | 含义 | 阈值 |
|------|------|------|
| `SUM_CREATED_TMP_DISK_TABLES` | 该 SQL 产生磁盘临时表的总次数 | > 1000 需关注 |
| `AVG_TIMER_WAIT` | 平均执行时间 | > 10s 需优化 |
| `MAX_TIMER_WAIT` | 最长执行时间 | > 300s 可能已卡死 |

---

### Step 6：检查内存临时表溢出情况

```sql
SELECT 
    THREAD_ID, EVENT_NAME,
    SUM_NUMBER_OF_BYTES_ALLOC / 1024 / 1024 / 1024 AS alloc_gb,
    CURRENT_NUMBER_OF_BYTES_USED / 1024 / 1024 AS used_mb
FROM performance_schema.memory_summary_by_thread_by_event_name
WHERE EVENT_NAME LIKE '%temptable%'
ORDER BY SUM_NUMBER_OF_BYTES_ALLOC DESC
LIMIT 10;
```

- `alloc_gb` 大但 `used_mb` 小 → 曾经大量分配但已释放，说明频繁溢出

---

## 三、常见根因与解决方案

### 场景 A：空闲长连接导致 `.ibt` 文件累积

**特征：**
- `PROCESSLIST.COMMAND = 'Sleep'`
- `TIME` 很大（几小时到几天）
- `INNODB_SESSION_TEMP_TABLESPACES` 文件多但当前无活跃查询

**解决：**
```sql
-- 临时释放：Kill 空闲超过 1 小时的连接
SELECT CONCAT('KILL ', ID, ';') 
FROM information_schema.PROCESSLIST
WHERE COMMAND = 'Sleep' AND TIME > 3600;

-- 长期预防：调小超时时间
SET GLOBAL wait_timeout = 300;
SET GLOBAL interactive_timeout = 300;

-- 连接池配置：定期回收连接（如 HikariCP maxLifetime=30min）
```

---

### 场景 B：大查询产生磁盘临时表

**特征：**
- `PROCESSLIST.COMMAND = 'Query'`
- `STATE = 'converting HEAP to ondisk'` 或 `executing`
- `events_statements_summary_by_digest` 某条 SQL 的 `SUM_CREATED_TMP_DISK_TABLES` 极高

**解决：**

1. **立即释放空间**：Kill 超时查询
   ```sql
   SELECT CONCAT('KILL ', ID, ';')
   FROM information_schema.PROCESSLIST
   WHERE TIME > 600 AND COMMAND = 'Query';
   ```

2. **优化 SQL**：避免窗口函数、大表 `DISTINCT`、`ORDER BY` 无索引字段
   - 窗口函数 `FIRST_VALUE() OVER` → 改用 `GROUP BY + MIN()`
   - 大表 `DISTINCT` → 先 `GROUP BY` 缩小数据量
   - 确保 `ORDER BY` / `GROUP BY` 字段有索引

3. **添加索引**：
   ```sql
   ALTER TABLE t_table 
   ADD INDEX idx_filter_group (filter_col, group_col);
   ```

4. **调整内存参数**：
   ```ini
   [mysqld]
   temptable_max_ram = 2G          # 默认 1G，内存充裕可调大
   temptable_max_mmap = 2G        # 8.0.16+，mmap 溢出缓冲
   internal_tmp_mem_storage_engine = TempTable  # 优先内存引擎
   ```

---

### 场景 C：用户显式临时表未清理

**特征：**
- `INNODB_TEMP_TABLESPACES.PURPOSE = 'USER'`
- `INNODB_TEMP_TABLE_INFO` 有记录

**解决：**
- 检查应用代码中 `CREATE TEMPORARY TABLE` 后是否有 `DROP TEMPORARY TABLE`
- 确保事务结束后及时清理

---

## 四、参数速查表

| 参数 | 默认值 | 作用 | 建议 |
|------|--------|------|------|
| `temptable_max_ram` | 1G | TempTable 引擎内存上限 | 内存充裕可调至 2-4G |
| `temptable_max_mmap` | 1G | TempTable mmap 溢出上限 | 与 RAM 保持一致 |
| `tmp_table_size` | 16M | MEMORY 引擎临时表上限 | 通常保持默认，优先用 TempTable |
| `max_heap_table_size` | 16M | MEMORY 引擎表上限 | 同上 |
| `wait_timeout` | 28800 | 非交互连接超时（秒） | 长连接场景建议 300-600 |
| `interactive_timeout` | 28800 | 交互连接超时（秒） | 与 wait_timeout 保持一致 |

---

## 五、监控脚本

```sql
-- 每日检查：#innodb_temp 总大小
SELECT 
    COUNT(*) AS session_count,
    ROUND(SUM(SIZE) / 1024 / 1024 / 1024, 2) AS total_gb,
    ROUND(MAX(SIZE) / 1024 / 1024 / 1024, 2) AS max_session_gb
FROM information_schema.INNODB_SESSION_TEMP_TABLESPACES
WHERE STATE = 'ACTIVE';

-- 每日检查：TOP 磁盘临时表 SQL
SELECT 
    LEFT(DIGEST_TEXT, 80) AS sql_preview,
    SUM_CREATED_TMP_DISK_TABLES AS disk_tmp_tables,
    ROUND(AVG_TIMER_WAIT / 1000000000000, 2) AS avg_sec
FROM performance_schema.events_statements_summary_by_digest
WHERE SUM_CREATED_TMP_DISK_TABLES > 0
ORDER BY SUM_CREATED_TMP_DISK_TABLES DESC
LIMIT 5;
```