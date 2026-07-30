# MySQL DBA 应该掌握的 100 条命令

下面整理了 100 条 MySQL DBA 常用命令，主要面向 MySQL 8.0 和 MySQL 8.4 LTS。部分命令在生产环境中具有修改或终止操作的风险，执行前应确认影响范围。

一、实例与版本信息

01
查看 MySQL 版本

```sql
SELECT VERSION();
```
用于确认数据库版本，例如 MySQL 5.7、8.0 或 8.4。很多参数、系统视图和 SQL 语法都与版本相关，因此排查问题前应先确认版本。

02
查看服务器基础信息

```sql
SELECT
  @@hostname          AS hostname,
  @@port              AS port,
  @@server_uuid       AS server_uuid,
  @@server_id         AS server_id,
  @@version           AS version;
```
在多实例、主从复制或 MGR 环境中，这条命令可以快速确认当前连接的是哪台服务器。

03
查看实例启动时间

```sql
SELECT
    NOW() AS now_time,
    FROM_UNIXTIME(UNIX_TIMESTAMP(NOW()) - CAST(VARIABLE_VALUE AS UNSIGNED)) AS startup_time,
    CAST(VARIABLE_VALUE AS UNSIGNED) AS uptime_seconds
FROM performance_schema.global_status
WHERE VARIABLE_NAME = 'Uptime';
```
可用于判断实例是否刚刚发生过重启。

04
查看数据库当前时间

```sql
SELECT NOW(), CURRENT_TIMESTAMP, UTC_TIMESTAMP();
```
排查日志时间、复制延迟和定时任务问题时，需要确认数据库本地时间和 UTC 时间是否一致。

05
查看系统时区

```sql
SELECT @@global.time_zone, @@session.time_zone, @@system_time_zone;
```
应用写入时间异常、定时任务提前或延后时，应首先检查时区设置。

06
查看数据库运行模式

```sql
SELECT @@global.sql_mode, @@session.sql_mode;
```
ONLY_FULL_GROUP_BY、STRICT_TRANS_TABLES、NO_ZERO_DATE 等模式会影响 SQL 执行行为。

07
查看字符集配置

```sql
SELECT
  @@character_set_server,
  @@character_set_database,
  @@character_set_connection,
  @@character_set_client,
  @@character_set_results;
```
用于排查乱码、字符转换和索引长度问题。

08
查看排序规则配置

```sql
SELECT
  @@collation_server,
  @@collation_database,
  @@collation_connection;
```
不同排序规则会影响字符串比较、排序和索引使用。

09
查看数据目录

```sql
SELECT @@datadir;
```
确认 MySQL 数据文件所在目录。

10
查看重要文件路径

```sql
SELECT
  @@log_error,
  @@pid_file,
  @@socket,
  @@tmpdir,
  @@secure_file_priv;
```
用于定位错误日志、PID 文件、Socket 文件、临时目录以及文件导入导出限制目录。

二、数据库与表对象

11
查看所有数据库

```sql
SHOW DATABASES;
```
12
查看当前数据库

```sql
SELECT DATABASE();
```
13
查看数据库创建语句

```sql
SHOW CREATE DATABASE db_name;
```
可以确认数据库字符集和排序规则。

14
查看数据库大小

```sql
SELECT
  table_schema,
  ROUND(SUM(data_length + index_length) / 1024 / 1024 / 1024, 2) AS size_gb
FROM information_schema.tables
GROUP BY table_schema
ORDER BY size_gb DESC;
```
15
查看指定数据库中的表

```sql
SHOW FULL TABLES FROM db_name;
```
除了普通表，还可以识别视图。

16
查看表结构

```sql
DESC db_name.table_name;
```
或：

```sql
SHOW COLUMNS FROM db_name.table_name;
```
17
查看完整建表语句

```sql
SHOW CREATE TABLE db_name.table_name\G
```
排查字段类型、索引、分区、字符集和存储引擎问题时，SHOW CREATE TABLE 比 DESC 更完整。

18
查看表状态

```sql
SHOW TABLE STATUS FROM db_name LIKE 'table_name'\G
```
可查看存储引擎、估算行数、数据大小、索引大小和自增值。

19
查看各表大小

```sql
SELECT
  table_schema,
  table_name,
  table_rows,
  ROUND(data_length / 1024 / 1024, 2) AS data_mb,
  ROUND(index_length / 1024 / 1024, 2) AS index_mb,
  ROUND((data_length + index_length) / 1024 / 1024, 2) AS total_mb
FROM information_schema.tables
WHERE table_schema = 'db_name'
ORDER BY data_length + index_length DESC;
```
20
查看非 InnoDB 表

```sql
SELECT
  table_schema,
  table_name,
  engine
FROM information_schema.tables
WHERE table_schema NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
AND engine <> 'InnoDB';
```
生产业务表通常建议统一使用 InnoDB。

三、连接与会话排查

21
查看当前连接

```sql
SHOW PROCESSLIST;
```
22
查看完整 SQL 的连接列表

```sql
SHOW FULL PROCESSLIST;
```
普通 SHOW PROCESSLIST 会截断 SQL 文本，排查长 SQL 时应使用 FULL。

23
通过系统表查看连接详情

```sql
SELECT
  id,
  user,
  host,
  db,
  command,
  time,
  state,
  info
FROM information_schema.processlist
ORDER BY time DESC;
```
24
查看当前连接数

```sql
SHOW GLOBAL STATUS LIKE 'Threads_connected';
```
25
查看正在运行的线程数

```sql
SHOW GLOBAL STATUS LIKE 'Threads_running';
```
Threads_connected 高不一定代表数据库繁忙，真正需要重点关注的是 Threads_running。

26
查看最大连接数

```sql
SHOW VARIABLES LIKE 'max_connections';
```
27
查看历史最大连接数

```sql
SHOW GLOBAL STATUS LIKE 'Max_used_connections';
```
28
查看连接使用率

```sql
SELECT
  VARIABLE_VALUE AS current_connections,
  @@max_connections AS max_connections,
  ROUND(VARIABLE_VALUE / @@max_connections * 100, 2) AS usage_percent
FROM performance_schema.global_status
WHERE VARIABLE_NAME = 'Threads_connected';
```
29
按用户统计连接数

```sql
SELECT
  user,
COUNT(*) AS connection_count
FROM information_schema.processlist
GROUP BY user
ORDER BY connection_count DESC;
```
30
按客户端地址统计连接数

```sql
SELECT
  SUBSTRING_INDEX(host, ':', 1) AS client_ip,
COUNT(*) AS connection_count
FROM information_schema.processlist
GROUP BY SUBSTRING_INDEX(host, ':', 1)
ORDER BY connection_count DESC;
```
31
查看长时间运行的会话

```sql
SELECT
  id,
  user,
  host,
  db,
  command,
  time,
  state,
  info
FROM information_schema.processlist
WHERE command <> 'Sleep'
AND time > 60
ORDER BY time DESC;
```
32
查看长时间空闲连接

```sql
SELECT
  id,
  user,
  host,
  db,
  time
FROM information_schema.processlist
WHERE command = 'Sleep'
AND time > 600
ORDER BY time DESC;
```
33
终止指定会话

```sql
KILL CONNECTION 12345;
```
该命令会断开整个连接，并回滚连接中的未提交事务。

34
只终止当前 SQL

```sql
KILL QUERY 12345;
```
只终止正在执行的语句，不主动断开客户端连接。

35
批量生成终止空闲连接命令

```sql
SELECT CONCAT('KILL CONNECTION ', id, ';')
FROM information_schema.processlist
WHERE command = 'Sleep'
AND time > 3600
AND user NOT IN ('system user', 'event_scheduler');
```
建议先生成命令并人工核对，不要直接拼接后自动执行。

四、事务、锁与阻塞

36
查看当前 InnoDB 事务

```sql
SELECT *
FROM information_schema.innodb_trx\G
```
37
查看运行时间最长的事务

```sql
SELECT
  trx_id,
  trx_mysql_thread_id,
  trx_state,
  trx_started,
  TIMESTAMPDIFF(SECOND, trx_started, NOW()) AS trx_seconds,
  trx_rows_locked,
  trx_rows_modified,
  trx_query
FROM information_schema.innodb_trx
ORDER BY trx_started;
```
38
查看超过 60 秒的事务

```sql
SELECT
  trx_id,
  trx_mysql_thread_id,
  trx_started,
  TIMESTAMPDIFF(SECOND, trx_started, NOW()) AS trx_seconds,
  trx_rows_locked,
  trx_rows_modified,
  trx_query
FROM information_schema.innodb_trx
WHERE trx_started < NOW() - INTERVAL 60 SECOND
ORDER BY trx_started;
```
39
查看锁等待关系

```sql
SELECT *
FROM performance_schema.data_lock_waits;
```
40
查看当前持有和等待的锁

```sql
SELECT *
FROM performance_schema.data_locks;
```
41
使用 sys 视图查看锁等待

```sql
SELECT *
FROM sys.innodb_lock_waits\G
```
该视图已经把阻塞会话、等待会话、SQL 和锁信息进行了关联，通常比直接查询 Performance Schema 更方便。

42
查看元数据锁

```sql
SELECT *
FROM performance_schema.metadata_locks
WHERE LOCK_STATUS = 'PENDING';
```
当 ALTER TABLE、TRUNCATE TABLE、DROP TABLE 长时间卡住时，应重点检查元数据锁。

43
查看元数据锁等待详情

```sql
SELECT
  ml.object_schema,
  ml.object_name,
  ml.lock_type,
  ml.lock_duration,
  ml.lock_status,
  t.processlist_id,
  t.processlist_user,
  t.processlist_host,
  t.processlist_time,
  t.processlist_info
FROM performance_schema.metadata_locks ml
JOIN performance_schema.threads t
ON ml.owner_thread_id = t.thread_id
WHERE ml.lock_status = 'PENDING';
```
44
查看未提交事务对应的连接

```sql
SELECT
  trx.trx_id,
  trx.trx_started,
  trx.trx_mysql_thread_id,
  p.user,
  p.host,
  p.db,
  p.command,
  p.time,
  p.state,
  p.info
FROM information_schema.innodb_trx trx
LEFT JOIN information_schema.processlist p
ON trx.trx_mysql_thread_id = p.id
ORDER BY trx.trx_started;
```
45
查看 InnoDB 引擎状态

```sql
SHOW ENGINE INNODB STATUS\G
```
这是排查死锁、事务、锁等待、Buffer Pool、I/O 和后台线程状态的核心命令。

46
查看最近一次死锁

```sql
SHOW ENGINE INNODB STATUS\G
```
在输出中搜索：

```text
LATEST DETECTED DEADLOCK
```
47
开启全部死锁日志记录

```sql
SET GLOBAL innodb_print_all_deadlocks = ON;
```
开启后，所有检测到的死锁都会写入 MySQL 错误日志。该参数会增加少量日志量。

48
查看事务隔离级别

```sql
SELECT
  @@global.transaction_isolation,
  @@session.transaction_isolation;
```
49
查看自动提交状态

```sql
SELECT @@global.autocommit, @@session.autocommit;
```
50
手工提交和回滚事务

```sql
COMMIT;

ROLLBACK;
```
生产中出现长事务时，经常不是 SQL 执行慢，而是应用开启事务后长时间没有提交。

五、SQL 性能分析

51
查看 SQL 执行计划

```sql
EXPLAIN
SELECT *
FROM db_name.table_name
WHERE id = 100;
```
52
查看 JSON 格式执行计划

```sql
EXPLAIN FORMAT=JSON
SELECT *
FROM db_name.table_name
WHERE id = 100;
```
JSON 格式可以看到成本估算、条件过滤和访问路径等详细信息。

53
查看实际执行计划

```sql
EXPLAIN ANALYZE
SELECT *
FROM db_name.table_name
WHERE id = 100;
```
EXPLAIN ANALYZE 会真正执行 SQL。对于更新、删除或资源消耗较大的 SQL，必须谨慎使用。

54
查看优化器执行轨迹

```sql
SET optimizer_trace = 'enabled=on';

SELECT *
FROM db_name.table_name
WHERE id = 100;

SELECT trace
FROM information_schema.optimizer_trace\G
```
适用于分析优化器为何选择某个索引或执行计划。

55
查看当前正在执行的 SQL

```sql
SELECT
  processlist_id,
  processlist_user,
  processlist_host,
  processlist_db,
  processlist_time,
  processlist_state,
  processlist_info
FROM performance_schema.threads
WHERE type = 'FOREGROUND'
AND processlist_command <> 'Sleep'
ORDER BY processlist_time DESC;
```
56
查看累计执行时间最高的 SQL

```sql
SELECT
  digest_text,
  count_star,
  ROUND(sum_timer_wait / 1000000000000, 2) AS total_seconds,
  ROUND(avg_timer_wait / 1000000000000, 6) AS avg_seconds,
  sum_rows_examined,
  sum_rows_sent
FROM performance_schema.events_statements_summary_by_digest
WHERE digest_text IS NOT NULL
ORDER BY sum_timer_wait DESC
LIMIT 20;
```
57
查看平均执行时间最高的 SQL

```sql
SELECT
  digest_text,
  count_star,
  ROUND(avg_timer_wait / 1000000000000, 6) AS avg_seconds,
  ROUND(max_timer_wait / 1000000000000, 6) AS max_seconds,
  sum_rows_examined,
  sum_rows_sent
FROM performance_schema.events_statements_summary_by_digest
WHERE count_star >= 10
ORDER BY avg_timer_wait DESC
LIMIT 20;
```
58
查看扫描行数最多的 SQL

```sql
SELECT
  digest_text,
  count_star,
  sum_rows_examined,
  sum_rows_sent,
  ROUND(sum_rows_examined / NULLIF(sum_rows_sent, 0), 2) AS examine_send_ratio
FROM performance_schema.events_statements_summary_by_digest
ORDER BY sum_rows_examined DESC
LIMIT 20;
```
59
查看未使用索引的 SQL

```sql
SELECT
  digest_text,
  count_star,
  sum_no_index_used,
  sum_no_good_index_used,
  sum_rows_examined
FROM performance_schema.events_statements_summary_by_digest
WHERE sum_no_index_used > 0
   OR sum_no_good_index_used > 0
ORDER BY sum_no_index_used DESC
LIMIT 20;
```
这里的“未使用索引”不一定代表 SQL 必须优化，小表全表扫描有时比走索引更合理。

60
查看产生临时表较多的 SQL

```sql
SELECT
  digest_text,
  count_star,
  sum_created_tmp_tables,
  sum_created_tmp_disk_tables
FROM performance_schema.events_statements_summary_by_digest
WHERE sum_created_tmp_tables > 0
ORDER BY sum_created_tmp_disk_tables DESC
LIMIT 20;
```
61
查看排序次数较多的 SQL

```sql
SELECT
  digest_text,
  count_star,
  sum_sort_rows,
  sum_sort_scan,
  sum_sort_range,
  sum_sort_merge_passes
FROM performance_schema.events_statements_summary_by_digest
WHERE sum_sort_rows > 0
ORDER BY sum_sort_rows DESC
LIMIT 20;
```
62
查看全表扫描较多的表

```sql
SELECT *
FROM sys.schema_tables_with_full_table_scans
ORDER BY rows_full_scanned DESC
LIMIT 20;
```
63
查看最耗时的 SQL

```sql
SELECT *
FROM sys.statement_analysis
ORDER BY total_latency DESC
LIMIT 20;
```
64
查看当前会话最近执行的 SQL

```sql
SELECT
  event_id,
  sql_text,
  rows_examined,
  rows_sent,
  timer_wait
FROM performance_schema.events_statements_history
WHERE thread_id = PS_CURRENT_THREAD_ID()
ORDER BY event_id DESC;
```
65
清空 SQL 摘要统计

```sql
TRUNCATE TABLE performance_schema.events_statements_summary_by_digest;
```
该操作不会清除业务数据，但会重置 SQL 聚合统计。执行前应确认是否还需要保留历史性能数据。

六、索引与表结构分析

66
查看表索引

```sql
SHOW INDEX FROM db_name.table_name;
```
67
查看索引列顺序

```sql
SELECT
  index_name,
  non_unique,
  seq_in_index,
  column_name,
  cardinality,
  nullable
FROM information_schema.statistics
WHERE table_schema = 'db_name'
AND table_name = 'table_name'
ORDER BY index_name, seq_in_index;
```
68
查看没有主键的表

```sql
SELECT
  t.table_schema,
  t.table_name
FROM information_schema.tables t
LEFT JOIN information_schema.table_constraints c
ON t.table_schema = c.table_schema
 AND t.table_name = c.table_name
 AND c.constraint_type = 'PRIMARY KEY'
WHERE t.table_type = 'BASE TABLE'
AND t.engine = 'InnoDB'
AND t.table_schema NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
AND c.constraint_name IS NULL;
```
69
查看重复或冗余索引

```sql
SELECT *
FROM sys.schema_redundant_indexes;
```
删除冗余索引前，应结合 SQL 使用情况和业务特征确认，不能仅凭系统视图直接删除。

70
查看未使用索引

```sql
SELECT *
FROM sys.schema_unused_indexes;
```
该视图的数据来源于实例启动后的统计。实例刚重启时，结果通常不具备参考价值。

71
查看表的索引使用情况

```sql
SELECT *
FROM sys.schema_index_statistics
WHERE table_schema = 'db_name'
AND table_name = 'table_name'
ORDER BY rows_selected DESC;
```
72
更新表统计信息

```sql
ANALYZE TABLE db_name.table_name;
```
当表数据发生大规模变化，执行计划明显异常时，可以考虑重新收集统计信息。

73
检查表

```sql
CHECK TABLE db_name.table_name;
```
74
优化表

```sql
OPTIMIZE TABLE db_name.table_name;
```
对于 InnoDB，通常会重建表。大表执行可能占用大量 I/O、临时空间，并造成元数据锁影响。

75
查看表碎片估算

```sql
SELECT
  table_schema,
  table_name,
  engine,
  ROUND(data_length / 1024 / 1024, 2) AS data_mb,
  ROUND(data_free / 1024 / 1024, 2) AS data_free_mb
FROM information_schema.tables
WHERE table_schema NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
AND data_free > 0
ORDER BY data_free DESC;
```
data_free 不能简单等同于真实可回收碎片，尤其在共享表空间和分区表环境中需要谨慎解释。

七、InnoDB 与内存状态

76
查看 Buffer Pool 大小

```sql
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';
```
77
查看 Buffer Pool 实例数量

```sql
SHOW VARIABLES LIKE 'innodb_buffer_pool_instances';
```
部分新版本中该参数的行为和可配置性可能发生变化，应结合实际版本确认。

78
查看 Buffer Pool 命中相关指标

```sql
SHOW GLOBAL STATUS
WHERE Variable_name IN (
'Innodb_buffer_pool_read_requests',
'Innodb_buffer_pool_reads'
);
```
逻辑读请求与物理读次数的比例可以用于估算 Buffer Pool 命中率。

79
计算 Buffer Pool 命中率

```sql
SELECT
  ROUND(
    (
1 -
      reads.variable_value /
      NULLIF(requests.variable_value, 0)
    ) * 100,
```
4

  ) AS buffer_pool_hit_percent

FROM performance_schema.global_status reads

JOIN performance_schema.global_status requests

WHERE reads.variable_name = 'Innodb_buffer_pool_reads'

AND requests.variable_name = 'Innodb_buffer_pool_read_requests';

命中率高并不代表数据库一定没有 I/O 问题，还需要结合工作集大小、随机读延迟和 SQL 访问模式判断。

80
查看脏页数量

```sql
SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_pages_dirty';
```
81
查看 Buffer Pool 页面状态

```sql
SHOW GLOBAL STATUS
WHERE Variable_name IN (
'Innodb_buffer_pool_pages_total',
'Innodb_buffer_pool_pages_free',
'Innodb_buffer_pool_pages_data',
'Innodb_buffer_pool_pages_dirty'
);
```
82
查看 InnoDB 日志相关参数

```sql
SHOW VARIABLES
WHERE Variable_name IN (
'innodb_redo_log_capacity',
'innodb_log_buffer_size',
'innodb_flush_log_at_trx_commit',
'sync_binlog'
);
```
innodb_flush_log_at_trx_commit 与 sync_binlog 直接影响事务持久性和写入性能。

83
查看 InnoDB 数据读写统计

```sql
SHOW GLOBAL STATUS
WHERE Variable_name IN (
'Innodb_data_reads',
'Innodb_data_writes',
'Innodb_data_read',
'Innodb_data_written',
'Innodb_os_log_written'
);
```
84
查看行操作统计

```sql
SHOW GLOBAL STATUS
WHERE Variable_name IN (
'Innodb_rows_read',
'Innodb_rows_inserted',
'Innodb_rows_updated',
'Innodb_rows_deleted'
);
```
85
查看临时表使用情况

```sql
SHOW GLOBAL STATUS
WHERE Variable_name IN (
'Created_tmp_tables',
'Created_tmp_disk_tables',
'Created_tmp_files'
);
```
磁盘临时表比例过高时，应检查 SQL、tmp_table_size、max_heap_table_size 和 TempTable 引擎配置。

八、日志与慢 SQL

86
查看慢查询日志配置

```sql
SHOW VARIABLES
WHERE Variable_name IN (
'slow_query_log',
'slow_query_log_file',
'long_query_time',
'log_queries_not_using_indexes',
'min_examined_row_limit'
);
```
87
动态开启慢查询日志

```sql
SET GLOBAL slow_query_log = ON;
```
88
设置慢查询阈值

```sql
SET GLOBAL long_query_time = 1;
```
该设置只对新连接生效。已有会话可能仍使用原来的会话级参数。

89
查看二进制日志配置

```sql
SHOW VARIABLES
WHERE Variable_name IN (
'log_bin',
'log_bin_basename',
'binlog_format',
'binlog_row_image',
'binlog_expire_logs_seconds'
);
```
90
查看当前二进制日志位置

```sql
SHOW MASTER STATUS;
```
在部分较新的 MySQL 版本中，推荐使用兼容的新命令：

```sql
SHOW BINARY LOG STATUS;
```
91
查看所有二进制日志文件

```sql
SHOW BINARY LOGS;
```
92
查看二进制日志事件

```sql
SHOW BINLOG EVENTS
IN 'mysql-bin.000001'
LIMIT 100;
```
对于 Row 格式的完整行数据解析，通常需要使用 mysqlbinlog。

93
使用 mysqlbinlog 解析日志

```bash
mysqlbinlog \
  --base64-output=DECODE-ROWS \
  -vv \
  mysql-bin.000001
```
94
按时间范围解析 Binlog

```bash
mysqlbinlog \
  --start-datetime='2026-07-16 10:00:00' \
  --stop-datetime='2026-07-16 11:00:00' \
  --base64-output=DECODE-ROWS \
  -vv \
  mysql-bin.000001
```
该命令常用于误操作恢复和数据审计。

九、主从复制与复制延迟

95
查看复制状态

传统术语环境：

```sql
SHOW SLAVE STATUS\G
```
MySQL 8.0 推荐使用：

```sql
SHOW REPLICA STATUS\G
```
重点关注以下字段：

```text
Replica_IO_Running
Replica_SQL_Running
Seconds_Behind_Source
Last_IO_Error
Last_SQL_Error
Retrieved_Gtid_Set
Executed_Gtid_Set
```
96
查看复制连接和应用线程

```sql
SELECT *
FROM performance_schema.replication_connection_status\G
SELECT *
FROM performance_schema.replication_applier_status\G
```
97
查看复制工作线程状态

```sql
SELECT
  channel_name,
  worker_id,
  thread_id,
  service_state,
  last_error_number,
  last_error_message,
  last_error_timestamp
FROM performance_schema.replication_applier_status_by_worker;
```
并行复制环境中，某一个 Worker 报错可能导致整个 SQL 线程停止。

98
停止和启动复制

```sql
STOP REPLICA;

START REPLICA;
```
只控制 I/O 线程或 SQL 线程：

```sql
STOP REPLICA IO_THREAD;

START REPLICA IO_THREAD;

STOP REPLICA SQL_THREAD;

START REPLICA SQL_THREAD;
```
99
查看 GTID 状态

```sql
SELECT
  @@global.gtid_executed,
  @@global.gtid_purged,
  @@global.enforce_gtid_consistency,
  @@global.gtid_mode;
```
GTID 环境中，恢复、搭建复制和主从切换都需要重点确认这几个值。

十、备份、权限与安全

100
使用 mysqldump 进行逻辑备份

```bash
mysqldump \
  -h 127.0.0.1 \
  -P 3306 \
  -u backup_user \
  -p \
  --single-transaction \
  --routines \
  --events \
  --triggers \
  --set-gtid-purged=OFF \
  --databases db_name \
  > db_name_$(date +%F).sql
```
其中：

•
--single-transaction：对 InnoDB 表执行一致性备份，避免长时间锁表；

•
--routines：备份存储过程和函数；

•
--events：备份 Event Scheduler 事件；

•
--triggers：备份触发器；

•
--set-gtid-purged=OFF：避免导出文件自动写入 GTID 相关语句。

恢复命令：

```bash
mysql \
  -h 127.0.0.1 \
  -P 3306 \
  -u root \
  -p \
  < db_name_2026-07-16.sql
```
在生产环境中，mysqldump 更适合中小规模数据库。对于数百 GB 或 TB 级数据库，应优先考虑 MySQL Enterprise Backup、Percona XtraBackup、存储快照或云数据库物理备份能力。

DBA 经常使用的权限检查命令

虽然前面已经列满 100 条，但权限排查同样是日常工作的高频场景，下面几条建议单独保留。

查看用户：

```sql
SELECT
  user,
  host,
  plugin,
  account_locked,
  password_expired
FROM mysql.user;
```
查看用户权限：

```sql
SHOW GRANTS FOR 'app_user'@'%';
```
创建用户：

```sql
CREATE USER 'app_user'@'10.%'
IDENTIFIED BY 'StrongPassword';
```
授权：

```sql
GRANT SELECT, INSERT, UPDATE, DELETE
ON db_name.*
TO 'app_user'@'10.%';
```
回收权限：

```sql
REVOKE DELETE
ON db_name.*
FROM 'app_user'@'10.%';
```
修改密码：

```sql
ALTER USER 'app_user'@'10.%'
IDENTIFIED BY 'NewStrongPassword';
```
锁定用户：

```sql
ALTER USER 'app_user'@'10.%' ACCOUNT LOCK;
```
解锁用户：

```sql
ALTER USER 'app_user'@'10.%' ACCOUNT UNLOCK;
```
删除用户：

```sql
DROP USER 'app_user'@'10.%';
```
## 总结

对于 MySQL DBA 来说，这 100 条命令真正需要形成的不是记忆，而是一套排查顺序。

当数据库出现故障时，可以按照下面的路径进行判断：

- 先确认实例、版本和连接对象是否正确；

- 检查连接数、运行线程和长时间会话；

- 检查事务、行锁、元数据锁和阻塞链；

- 分析当前 SQL、历史高负载 SQL 和执行计划；

- 检查 Buffer Pool、磁盘临时表、Redo 和 InnoDB I/O；

- 检查慢查询日志、错误日志和 Binlog；

- 在复制环境中检查 I/O 线程、SQL 线程、Worker 和 GTID；

- 最后再决定是否终止会话、重建索引、修改参数或重启实例。

很多线上事故之所以处理时间长，并不是因为 DBA 不会执行命令，而是一开始就把排查方向选错了。CPU 高只是现象，连接数高只是现象，复制延迟同样只是现象。真正有效的排查，始终要回到会话、事务、等待、SQL 和资源消耗之间的因果关系。