# 故障排查

本节包含了 PostgreSQL 常见问题排查与处理相关的文档。

快速定位和解决问题是 DBA 的核心能力，本章涵盖常见故障场景、诊断方法和处理方案。

## 文档列表

### 常见问题处理

- [auto vacuum 触发机制](auto_vacuum_trigger.md) - autovacuum/autoanalyze 触发条件分析
- [避免 needrestart 自动重启 PostgreSQL](avoid_restart.md) - 系统升级导致数据库意外重启
- [数据库 OOM 预防](oom.md) - 内存溢出预防与 OOM Killer 配置
- [客户端故障转移](libpg.md) - 应用侧多主机连接与故障转移

### SQL 诊断

- [Explain 执行计划](explain.md) - 执行计划解读与 SQL 调优基础

### 数据迁移与同步

- [DTS 数据迁移服务](dts.md) - 基于逻辑复制的在线数据迁移
- [利用 debezium 实现数据变更捕获](debezium.md) - Debezium CDC 实现流程

### 综合参考

- [工作中所使用的 Postgres](awsome-postgres.md) - PG 实际应用概览与 MVCC 等核心特性
