# 高可用方案

本节包含了 PostgreSQL 高可用架构相关的文档。

高可用是企业级数据库的核心需求，PostgreSQL 提供了多种高可用方案来保障业务连续性。

## 文档列表

- [咨询锁 adlock](adlock.md) - PostgreSQL 咨询锁使用
- [数据库高可用设计分析](ha_fd.md) - 高可用集群基本概念与架构分析
- [PG 高可用 Patroni](patroni.md) - Patroni 高可用方案部署
- [Patroni 高可用管理进阶](patroni02.md) - Patroni 主从同步策略与高级配置
- [pg_auto_failover 实践](pgautofailover.md) - Citus 同源高可用方案
- [基于 Repmgr 实现数据库高可用](repmgr.md) - Repmgr 安装与配置
- [repmgrd 介绍](repmgrd.md) - Repmgr 守护进程与自动故障转移
