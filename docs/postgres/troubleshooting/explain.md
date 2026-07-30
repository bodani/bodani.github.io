# Explain 执行计划

EXPLAIN 用于查看 PostgreSQL 优化器为语句选择的执行计划，是 SQL 调优的基础工具。

## 文法

```sql
EXPLAIN [ ( option [, ...] ) ] statement
EXPLAIN [ ANALYZE ] [ VERBOSE ] statement

-- option 可以是：
--   ANALYZE [ boolean ]
--   VERBOSE [ boolean ]
--   COSTS [ boolean ]
--   BUFFERS [ boolean ]
--   TIMING [ boolean ]
--   SUMMARY [ boolean ]
--   FORMAT { TEXT | XML | JSON | YAML }
```

## 注意事项

使用了 `ANALYZE` 选项时，语句会被实际执行。如执行 DML 时将对数据库进行实际操作。

避免污染数据的方式：

```sql
BEGIN;
EXPLAIN ANALYZE ...;
ROLLBACK;
```

## 一个例子

```sql
postgres=# explain analyze select * from tbl;
                                                    QUERY PLAN
------------------------------------------------------------------------------------------------------------------
 Seq Scan on tbl  (cost=0.00..144248.48 rows=10000048 width=8) (actual time=0.091..780.145 rows=10000000 loops=1)
 Planning time: 0.124 ms
 Execution time: 1046.394 ms
(3 rows)
```

- Seq Scan：顺序扫描
- cost：代价成本，启动成本..总成本
- actual：实际值

## cost 计算

cost 的计算依据数据库中的统计信息及成本因子。

- 统计信息：`select * from pg_stats;`
- 成本因子：

```ini
# - Planner Cost Constants -

#seq_page_cost = 1.0                    # measured on an arbitrary scale
random_page_cost = 1.1                  # same scale as above
#cpu_tuple_cost = 0.01                  # same scale as above
#cpu_index_tuple_cost = 0.005           # same scale as above
#cpu_operator_cost = 0.0025             # same scale as above
#parallel_tuple_cost = 0.1              # same scale as above
#parallel_setup_cost = 1000.0   # same scale as above
#min_parallel_table_scan_size = 8MB
#min_parallel_index_scan_size = 512kB
effective_cache_size = 666666
```

## 影响执行计划的参数设置

开关类：

```text
enable_bitmapscan
enable_gathermerge
enable_hashagg
enable_hashjoin
enable_indexonlyscan
enable_indexscan
enable_material
enable_mergejoin
enable_nestloop
enable_seqscan
enable_sort
enable_tidscan
```

关联类：

```text
from_collapse_limit
join_collapse_limit
geqo_threshold
```

设置方式：

- session：`set enable_bitmapscan = default;`
- 全局：`postgresql.conf`
- 用户级：`alter user postgres set enable_bitmapscan = off;`
- 数据库级别：`alter database postgres set enable_bitmapscan = off;`

查看方式：

- session：`show enable_bitmapscan;`
- 用户级别：`select * from pg_user;`

## 在日志中记录 explain 信息

通过 `auto_explain` 扩展可在日志中记录 explain 信息。

- [文档 官网](https://www.postgresql.org/docs/10/using-explain.html)
- [文档 中文](http://www.postgres.cn/docs/10/sql-explain.html)

## SQL 在线分析工具

- <https://explain.depesz.com>
- <https://explain.dalibo.com/>
