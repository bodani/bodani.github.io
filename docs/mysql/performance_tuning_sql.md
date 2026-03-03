# MySQL性能调优-SQL优化

## 概述

SQL优化是MySQL性能调优的关键环节，通过对SQL语句的优化可以显著提升数据库的查询性能。SQL优化主要关注三个方面：查询效率、资源使用和系统负载。本章将详细介绍各种实用的SQL优化技术和工具。

### SQL优化基本原则

1. 优先分析慢查询并优化高频率执行的SQL语句
2. 充分利用索引来避免全表扫描
3. 减少不必要的数据传输和计算
4. 定期审查和维护执行计划的有效性

## SQL性能分析工具

### Performance Schema 和 Sys 模式的查询

Performance Schema 和 sys 模式是MySQL内置的性能分析工具集，它们提供了对数据库内部运行状态的洞察。

```
CALL sys.ps_truncate_all_tables(false);  -- 清空 Performance Schema 表（保留结构）
```

以下是常用的性能分析查询：

```sql
-- 分析SQL执行历史记录 , 总时间最长的
SELECT * FROM sys.statement_analysis LIMIT 1\G;
```

```sql
-- 找出执行时间位于前5%的SQL语句
select * from sys.statements_with_runtimes_in_95th_percentile ;
```

```sql
-- 根据平均执行时间查看SQL
select * from performance_schema.events_statements_summary_by_digest order by avg_timer_wait desc limit 2\G;
```

```sql
-- 根据执行频次查看SQL
select * from performance_schema.events_statements_summary_by_digest order by count_star desc limit 2\G;
```

```sql
-- 按扫描行数降序查看SQL
select * from performance_schema.events_statements_summary_by_digest order by sum_rows_examined desc limit 2\G;
```

```sql
-- 按返回行数降序查看SQL
select * from performance_schema.events_statements_summary_by_digest order by sum_rows_sent desc limit 2\G;
```

### 性能诊断存储过程

MySQL sys 模式提供了多种便捷的存储过程帮助进行性能诊断：

#### 存储过程进行性能监控

```sql
-- ps_trace_thread 存储过程用于跟踪指定线程的执行情况
CALL sys.ps_trace_thread(thread_id, 'output_file', 1, 10);
-- 参数说明:
-- thread_id: 需要跟踪的线程ID
-- 'output_file': 输出结果文件位置
-- 1: 监控时间间隔（秒）
-- 10: 采集次数
```

##### 相关的性能监控功能

- `ps_trace_statement_digest`: 跟踪指定SQL摘要的详细执行情况
- `statement_performance_analyzer`: 对比SQL执行的性能分析报告
- `ps_statement_avg_latency_histogram`: 生成SQL平均延迟分布直方图

## 索引优化分析

### 索引使用状况分析

```sql
-- 检查可能存在全表扫描的表
select * from sys.schema_tables_with_full_table_scans;
```

```sql
-- 检查疑似未使用的索引（注意：短期观察可能会误判常用索引未使用）
select * from sys.schema_unused_indexes ;
```

```sql
-- 检查可能存在冗余的索引
select * from sys.schema_redundant_indexes ;
```

### 不可见索引技术

MySQL 8.0+ 支持创建不可见索引（Invisible Indexes），这是进行性能回滚的有力手段。

- **功能**：在不删除索引的情况下临时禁用
- **用途**：测试索引删除的潜在影响，避免删除错误造成性能下降
- **特点**：可随时恢复，无需经历创建索引的时间成本

## 索引设计优化技术

### 覆盖索引

覆盖索引是指索引中包含了查询所需的全部列，避免了访问数据页的过程，可极大提高查询性能。

```
-- 查看索引 'xxx' 由哪些列组成（按顺序），方便利用覆盖索引
SELECT COLUMN_NAME, SEQ_IN_INDEX
FROM information_schema.STATISTICS
WHERE INDEX_NAME = 'xxx'
ORDER BY SEQ_IN_INDEX
```

使用建议：

- 将SELECT语句中的字段包含在覆盖索引中
- 在多表JOIN查询中对连接字段建立联合覆盖索引
- 注意平衡覆盖字段的多少与索引大小的矛盾

### 延迟关联（Delayed Join）

对于大数据量的关联查询，延迟关联可以通过减少JOIN操作的数据量来提高性能。

```sql
-- 使用子查询缩小关联范围
SELECT * FROM table_a
WHERE id IN (
    SELECT id FROM table_b
    WHERE conditions_for_table_b
);
```

这种技术尤其是在分页查询中的应用非常有效：

- 先在小范围内完成过滤条件查询
- 然后进行表间关联
- 大幅减少关联过程中扫描的数据行数

### 多字段的联合索引设计

设计联合索引时，要考虑：

- 频繁一起查询的字段放在同一个索引中
- 根据区分度安排字段顺序（将选择性最高的字段放在前面）
- 遵守最左匹配原则：查询条件包含联合索引左侧的连续字段才可有效使用索引

### 索引创建最佳实践

1. **等值匹配查询**：字段区分度高的放前面
2. **范围查询+其他条件**：范围字段后面不放其他字段
3. **包含NULL值的列**：考虑是否允许NULL以及如何索引

## 锁相关信息查询

```
-- 检查当前数据锁状态（MySQL 5.7+ 和 8.0+）
select * from performance_schema.data_locks;
```

该查询可用于诊断死锁等问题，重点关注以下字段：

- `OBJECT_SCHEMA`, `OBJECT_NAME`: 被锁对象
- `LOCK_TYPE`: 锁类型
- `LOCK_MODE`: 锁模式
- `LOCK_STATUS`: 锁状态

## 统计与优化策略

### 直方图统计

在特定的列上建立直方图。默认的统计信息存在于表和索引中，列中原本并没有。
直方图主要用于优化器进行更精确的查询计划选择，特别是在数据分布不均匀时。

直方图优势：

- 提供更好的选择度估计
- 改善数据倾斜表上的查询计划选择
- 减少估算误差

### 查看和整理表空间

检查磁盘可释放空间的查询：

```sql
select table_name,
    round(data_length/1024/1024) as data_length_mb,
    round(data_free/1024/1024) as data_free_mb
from information_schema.tables
where round(data_free/1024/1024) > 10
order by data_free_mb desc
limit 10;
```

对结果集较大或者长期未优化导致大量数据碎片的表进行空间整理：

```sql
-- 使用 OPTIMIZE TABLE 整理表碎片
OPTIMIZE TABLE your_table_name;

-- 或者使用 mysqlcheck 进行批量表空间整理
mysqlcheck -o database_name --all-databases
```

## SQL编写和设计优化策略

### 避免全表扫描的技巧

1. **WHERE条件优化**：始终将选择性高的条件放在前面
2. **LIKE优化**：避免前置通配符（如 `%keyword`），应尽量使用后置通配符
3. **OR条件替换**：使用UNION替换OR（当OR的字段都有索引时）
4. **数值范围缩小**：使用LIMIT提前终止搜索

### JOIN优化技巧

1. **JOIN顺序**：从小结果集开始JOIN
2. **索引选择**：确保连接字段上都有合适的索引
3. **驱动表选择**：通过EXPLAIN确认优化器选择正确的驱动表

### 排序优化

1. 使用索引进行排序（ORDER BY子句字段与索引顺序一致）
2. 尽可能使用单一索引满足排序需求
3. 避免混合ASC和DESC排序（MySQL 8.0以前可能导致无法使用索引）

## SQL执行计划分析（EXPLAIN）

理解执行计划的各个字段可以帮助我们更好地优化SQL：

```sql
-- 分析SQL执行计划
EXPLAIN FORMAT=JSON SELECT * FROM your_table WHERE conditions;
```

重点关注：

- type: 显示连接类型（最好到最差：system、const、eq_reg、ref、range、index、ALL）
- rows: MySQL估计需要遍历的行数
- Extra: 包含额外信息（Using Index, Using Where, etc.）

### 常见性能陷阱

1. **隐式转换**: 字段类型不匹配可能导致索引失效
2. **函数包裹列**: 在查询字段上使用函数（如 `DATE(date_field)`）会使索引失效
3. **COUNT(\*)与COUNT(字段)**: 不同情况选择不同的写法以获得更好性能

## MySQL配置参数与SQL性能的关系

### 查询缓存（8.0已移除）：

虽然MySQL 8.0移除了查询缓存，但在早期版本中需考虑其对特定工作负载的益处或负面影响。

### 临时表相关参数：

- tmp_table_size 和 max_heap_table_size：控制内存临时表的最大大小
- 影响需要临时表处理（如GROUP BY, ORDER BY）的SQL性能

### 排序和联接参数：

- sort_buffer_size：每个会话分配的排序缓冲区大小
- join_buffer_size：联接操作时使用的缓冲区大小

### 其他相关配置：

根据业务特点适当调整这些参数可以进一步提升SQL执行效率。

### 附注

MySQL的优化是一个综合性的过程，不仅包括SQL语句本身，也涉及系统参数调优、表结构设计、索引策略等多个方面，需要整体协调实施。
