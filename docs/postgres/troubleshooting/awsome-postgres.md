# 工作中所使用的 Postgres

Postgres 实际应用概览，覆盖日常运维与架构中的常用能力。

## MVCC 多版本控制

一个绕不开的话题，主要是对抗表空间膨胀、解决垃圾回收问题，以及主从库之间从库查询冲突。

目前方法：每日低峰期定时 vacuum（gocron 定时任务）；根据 `pgstattuple` 对磁盘空间利用率进行分析，决定是否 `vacuum full` / `pg_repack`。

## 流复制

主从复制、读写分离的基础，五种同步方式。

## 逻辑订阅

大版本升级、数据并归、迁移。

## 执行计划调优

调节成本因子比例，如不同的磁盘类型比例有所区别。

## 参数调优

主机和服务相关参数。

## 分区表

采用 `pg_pathman`，根据业务数据量决定是否分区；`pg_pathman` 能够在不停服的前提下自动分区数据。

## 高可用

Patroni。

## 分表

Citus：注意亲和性、表之间的 join、DDL 等限制。

## 监控与日志

Prometheus 套件、自定义监控项；Filebeat / Elasticsearch / Kibana 日志收集。

## 统计

结合数据库自带统计信息及 `pg_stat_statements` 插件生成报表。

## 压测

`pgbench`、自定义 SQL。

## 备份恢复

wal-g 全量和实时增量。

## 连接池

pgbouncer，主要用于分表中各个服务之间。

## FDW

（待补充）
