# 数据库设计

本节包含了 PostgreSQL 数据库设计相关的文档。

良好的数据库设计是高性能应用的基础，涵盖范式理论、数据类型选择、索引设计、高级特性应用等多个方面。

## 文档列表

- [数据库拓展](extention.md) - PipelineDB、RecDB 等拓展产品介绍
- [HyperLogLog](hll.md) - 高效去重统计方案
- [快速生成大量数据](insert01.md) - 测试数据生成与写入性能测试
- [物化视图](materialized.md) - 物化视图原理与使用
- [数据库三范式五约束](normal-form.md) - 数据库设计范式理论
- [数据库的 json 类型](pg_json.md) - JSON 与 JSONB 类型使用
- [pg_trgm 模糊查询](pg_trgm.md) - GIST/GIN 索引加速字符匹配
- [upsert 用法](upset.md) - INSERT ON CONFLICT 语法
- [WAL LSN 示例](wal_lsn.md) - WAL 日志位置相关操作示例
- [WAL 总大小](wal_size.md) - WAL 日志空间问题分析
