# 性能优化

本节包含了 PostgreSQL 性能优化相关的文档。

性能优化是数据库运维的永恒话题，需要从参数配置、SQL 优化、存储设计、垃圾回收等多个维度综合考虑。

## 文档列表

### 优化方法论

- [数据库优化思考-性能优化](thinking_in_db_performance.md) - 性能优化本质与方法论
- [数据库优化思考 - 模块调优](thinking_in_db_tune.md) - 结合 PG 特点的场景化调优

### 参数配置

- [数据库参数](params.md) - 性能相关参数详解与调优工具

### 存储与更新优化

- [fillfactor 填充因子](fillfactor.md) - 页面填充因子与 HOT 更新
- [hot update](hotupdate.md) - Heap Only Tuple 更新机制

### SQL 与统计

- [高级 SQL](high_level_sql.md) - 分组集、排序集等高级 SQL 特性
- [方法和函数](FunctionsandOperators.md) - 条件表达式等函数使用
- [PostgreSQL 指标查看 & stat 统计信息](stat.md) - 统计信息视图使用

### 垃圾回收

- [vacuum 垃圾回收器](vacuum.md) - VACUUM 原理与空间管理
- [vacuum 限流](vacuum_limit.md) - 后台清理资源限制配置
