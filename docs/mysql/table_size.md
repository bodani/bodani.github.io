```
SELECT      table_name AS `表名`,     ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024 / 1024, 2) AS `表大小(GB)`,     ROUND(DATA_FREE / 1024 / 1024 / 1024, 2) AS `碎片/未释放空间(GB)` FROM information_schema.TABLES WHERE      table_name = 'live_data_file_increment_4_4'     AND table_schema = DATABASE();

SELECT EVENT_NAME, WORK_COMPLETED, WORK_ESTIMATED  FROM performance_schema.events_stages_current  WHERE EVENT_NAME LIKE '%alter%'

SHOW VARIABLES LIKE 'innodb_buffer_pool_size';
SHOW VARIABLES LIKE 'key_buffer_size';
SHOW VARIABLES LIKE 'max_connections'; -- 最大连接数（过高会导致线程内存累积）
SHOW VARIABLES LIKE 'tmp_table_size';  -- 内存临时表上限

SELECT (@@read_buffer_size + @@sort_buffer_size + @@join_buffer_size) / (1024 * 1024) AS per_thread_mb;

SELECT (@@read_buffer_size + @@sort_buffer_size + @@join_buffer_size) / (1024 * 1024) AS per_thread_mb;
SHOW GLOBAL STATUS LIKE 'Threads_running';       -- 活跃线程数
```

-- 显示占用最高的模块（如InnoDB缓冲池、临时表）

```
SELECT event_name, current_alloc
FROM sys.memory_global_by_current_bytes
LIMIT 20;
```

```各个模块的总内存
select sys.format_bytes(SUM(current_alloc)) FROM sys.x$memory_global_by_current_bytes;
```

各个模块的分别占用的内存

```
SELECT SUBSTRING_INDEX(event_name,'/', 2 ) AS
       code_area, sys.format_bytes(SUM(current_alloc))
       AS current_alloc
       FROM sys.x$memory_global_by_current_bytes
       GROUP BY SUBSTRING_INDEX(event_name,'/', 2 )
       ORDER BY SUM(current_alloc) DESC;
```

```
监控InnoDB缓冲池利用率：
SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_pages%';

SET GLOBAL innodb_buffer_pool_size =

连接占用的内存
https://mp.weixin.qq.com/s?__biz=MjM5NzAzMTY4NQ==&mid=2653939777&idx=1&sn=da6b97b8d302b0b910fa52147e0f6854&chksm=bd3b722b8a4cfb3d3e974909558b805ca7200ddaeeefc0b8b04a5562543202a0df40b7d4365e#rd

pmap -x $(pgrep mysqld) | grep -i "anon" | sort -nrk3

查看 database size

selectname,FILE_SIZE/1024/1024/1024as  GB from information_schema.INNODB_TABLESPACES wherename='test/t1';

SELECT
table_schema as '数据库',
sum(table_rows) as '记录数',
sum(truncate(data_length/1024/1024, 2)) as '数据容量(MB)',
sum(truncate(index_length/1024/1024, 2)) as '索引容量(MB)',
sum(truncate(DATA_FREE/1024/1024, 2)) as '碎片占用(MB)'
from information_schema.tables
group by table_schema
order by sum(data_length) desc, sum(index_length) desc;

查看 table size

SELECT table_name AS `表名`, ROUND((DATA_LENGTH) / 1024 / 1024 / 1024, 2) AS `表大小(GB)`, ROUND((INDEX_LENGTH) / 1024 / 1024 / 1024, 2) AS `索引大小(GB)`, ROUND(DATA_FREE / 1024 / 1024 / 1024, 2) AS `碎片/未释放空间(GB)` FROM information_schema.TABLES where table_schema = DATABASE();

查看 optimize table 事件

SELECT EVENT_NAME, WORK_COMPLETED, WORK_ESTIMATED FROM performance_schema.events_stages_current;

optimize table xx 后查看进度
SELECT EVENT_NAME, WORK_COMPLETED, WORK_ESTIMATED FROM performance_schema.events_stages_current WHERE EVENT_NAME LIKE 'stage/innodb/alter%';

SELECT \* FROM sys.innodb_lock_waits\G
```
