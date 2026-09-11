# 索引与高级特性

本节包含了 PostgreSQL 索引类型、索引优化、分区表等高级特性相关的文档。

索引是数据库性能优化的核心手段，合理使用不同类型的索引能够大幅提升查询效率。

## 文档列表

### 索引基础

- [数据库索引类型及使用场景](index01.md) - B-tree、Hash、GIN、GiST 等各类索引适用场景
- [索引失效与优化](index-invalid.md) - 索引失效场景分析与优化建议

### 特殊索引类型

- [Bloom 索引](index-bloom.md) - 布隆过滤器索引原理与使用
- [GIN 索引全文检索实例教程](gin_full_text_search_example.md) - GIN 倒排索引与全文搜索实战
- [PostgreSQL 中的假设索引](hypopg-index.md) - HypoPG 虚拟索引测试执行计划

### 高级特性

- [原生分区表](partition.md) - 范围、列表、哈希分区表使用
- [unlogged table](unlogged_table.md) - 非日志表特性与适用场景
- [模板数据库](template.md) - template0/template1 模板数据库使用
