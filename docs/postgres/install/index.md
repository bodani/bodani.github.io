# 安装与基础配置

本节包含了 PostgreSQL 安装部署和基础配置相关的文档。

正确的安装和基础配置是数据库稳定运行的前提，涵盖多种安装方式、核心进程理解、存储管理等内容。

## 文档列表

### 安装部署

- [安装 PostgreSQL](install01.md) - 基于官方源的标准安装方式
- [数据库安装 Postgres12 Ubuntu18](install02.md) - Ubuntu 环境下 PG12 安装
- [postgres 12](postgres12.md) - PG12 安装与启动
- [安装与配置](install.md) - 安装配置概览

### 核心机制

- [Background Writer 进程](bgwriter.md) - 后台写进程原理与作用
- [checkpoint 检查点](checkpoint.md) - 检查点机制与崩溃恢复
- [TOAST 技术](toast.md) - 大字段存储技术
- [cluster 聚簇表](cluster.md) - 聚簇表存储与性能测试

### 存储管理

- [tablespace 表空间](tablespace.md) - 表空间管理与注意事项
- [表空间膨胀](pgstattuple.md) - 表膨胀检测与处理

### 日常运维

- [数据库日常管理](daily_management.md) - 日常运维工作清单
- [删除数据](delete.md) - 数据清理与归档
- [howto 系列](postgresql-howto.md) - EXPLAIN ANALYZE 等实用技巧
