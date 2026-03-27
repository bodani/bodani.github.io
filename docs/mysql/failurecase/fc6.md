# 集群加入节点失败 - 实例已存在于另一个集群

## 故障描述

```
dba.getCluster().addInstance('helmbroker-mysql-0:3306')
ERROR: RuntimeError: The instance 'helmbroker-mysql-0:3306' is already part of another InnoDB Cluster
Cluster.addInstance: The instance 'helmbroker-mysql-0:3306' is already part of another InnoDB Cluster (RuntimeError)

mysqlsh51104:dbd.getCluster().removeInstance('helmbroker-mysql-0:3306')
ERROR: The instance helmbroker-mysql-0:3306 does not belong to the cluster.
ERROR: MYSQLSH 51104: Metadata for instance helmbroker-mysql-0:3306 not found
Cluster.removeInstance: Metadata for instance helmbroker-mysql-0:3306 not found (MYSQLSH 51104)
```

在被加入节点执行`stop group_replication;`后，重新加入：

```
dba.getCluster().addInstance('helmbroker-mysql-0:3306');
NOTE: A GTID set check of the MySQL instance at 'helmbroker-mysql-0:3306' determined that it is missing transactions that were purged from all cluster members.
Clone based recovery was selected because it seems to be safely usable.
```

## 分析

该实例 (`helmbroker-mysql-0`) 之前曾配置组复制元数据但未正确清理，因此 MySQL 集群管理工具认为它已经属于另一个 InnoDB Cluster。检查插件可见 group_replication 处于启用状态：

```sql
SELECT PLUGIN_NAME FROM INFORMATION_SCHEMA.PLUGINS WHERE PLUGIN_NAME LIKE '%repli%';
+-------------------+
| PLUGIN_NAME       |
+-------------------+
| group_replication |
+-------------------+
```

需通过 `STOP GROUP_REPLICATION;` 停止组复制使实例脱离原有状态才能成功加入当前集群。添加时显示`Clone based recovery was selected`表示因为 GTID 事务集存在缺失（被 purge 过），需要通过 Clone 协议同步最新数据。


## 解决方案

**步骤 1**: 在被加入的节点执行：

```sql
STOP GROUP_REPLICATION;
```

**步骤 2**: 在集群管理员节点重新添加实例：

```javascript
var clus = dba.getCluster();
clus.addInstance('helmbroker-mysql-0:3306');
```

等待 Clone 完成即可。（根据数据量，克隆可能需要几秒到数小时）