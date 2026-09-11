# 维护管理

本节包含了 PostgreSQL 数据库日常维护和高级特性相关的文档。

数据库维护是保障长期稳定运行的关键，涵盖日志管理、分区表、WAL 归档、在线 DDL 等运维核心内容。

## 文档列表

### 架构设计

- [数据库优化思考 - 结构设计](thinking_in_db_fd.md) - 数据库结构设计方法论

### 日志与归档

- [数据库日志](log.md) - pg_log、WAL、clog 三种日志介绍
- [archive wal 归档](archive.md) - WAL 日志归档配置与原理

### 分区表

- [分区表](partition.md) - 原生分区表功能与使用
- [pg_pathman 分区表](pg_pathman.md) - pg_pathman 高性能分区扩展

### 高级特性

- [外部表](foreign_table.md) - Foreign Tables 跨数据源访问
- [pg_rewrite - 在线表重写](pg_rewrite.md) - 不中断业务的表定义变更

### 安装部署

- [kylin 系统 postgresql 编译安装](compile_kylin.md) - 麒麟操作系统源码编译安装