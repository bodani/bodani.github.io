# 运维工具

本节包含了 PostgreSQL 运维管理常用工具和扩展相关的文档。

熟练使用各类运维工具能够显著提升 DBA 的工作效率，涵盖监控、诊断、压测、维护等多个方面。

## 文档列表

### 日常运维

- [DBA 日常](dba.md) - DBA 日常工作清单
- [数据库年龄](pgage.md) - 事务回卷与年龄监控
- [wal 日志数量计算](wal_count.md) - WAL 日志空间计算工具

### 监控诊断

- [Postgres 监控常用工具](monitor.md) - Zabbix 等监控方案
- [数据库监控指标](monitor_explain.md) - 关键监控指标说明
- [查看数据信息常用 sql 整理](monitor-sql.md) - 实用监控 SQL 集合
- [数据库实时运行信息查看](pg_activity.md) - top 式实时活动监控
- [pgwatch2 数据库指标监控查看](pgwatch2.md) - pgwatch2 监控工具
- [数据库视图之 pg_stat_activity](view_pg_stat_activity.md) - 活动会话视图详解
- [数据库视图之 pg_stat_bgwriter](view_pg_stat_bgwriter.md) - 后台写视图详解
- [pg_stat_statements 数据库统计信息](pg_stat_statements.md) - SQL 统计扩展
- [pg_stat_kcache](pg_stat_kcache.md) - 内核缓存统计扩展
- [pg_buffercache](pg_buffercache.md) - 共享缓冲区缓存查看

### 锁与并发

- [锁等待](lock_wait.md) - 锁等待场景分析与处理
- [锁机制](pg_lock.md) - 锁机制原理详解

### 性能测试

- [pgbench 压力测试](pgbench.md) - 基准测试工具使用
- [tpch AP 测试](tpch.md) - TPC-H 分析型性能测试

### 维护工具

- [pg_repack](pg_repack.md) - 在线表重组与膨胀处理
- [pg_rewind 时间线对齐](pg_rewind.md) - 主备时间线对齐工具
- [pgfincore](pgfincore.md) - 操作系统缓存管理
- [数据预加载](pg_prewarm.md) - 缓存预热
- [pgxnclient](pgxnclient.md) - PostgreSQL 扩展网络客户端

### 生态扩展

- [citus 数据库分库](pg_citus.md) - Citus 分库分表调研
- [postgis 安装](postgis.md) - PostGIS 空间数据库扩展
- [数据库日志分析](pg_elk.md) - ELK 日志分析架构
- [关于时序数据库的一个示例](timescaledb_demo01.md) - TimescaleDB 访问统计示例
