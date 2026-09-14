# 运维脚本

本节包含了 ClickHouse 运维常用的 Python 脚本工具。

## 脚本列表

- [cleanup_replicas.py](cleanup_replicas.py) - 清理 ClickHouse 集群中残留的 replica 节点（ZK 里 active=0 的残留节点）
- [generate_create_sql.py](generate_create_sql.py) - 从健康 ClickHouse 节点批量导出 Replicated*MergeTree 表的 CREATE TABLE 语句（含 UUID）
- [create_replicas.sql](create_replicas.sql) - 副本表创建 SQL 示例