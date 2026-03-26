# mgr组复制数据在导入的时候被覆盖

## 模拟问题

数据从mgr集群01 全量导出后，导入到mgr集群02 中。 集群02故障，集群元数据被破坏，账号信息被破坏。 

均为模拟账户临时随机密码

集群01 信息:
```
10.2.14.1
administrator: LnoEJpgcgp
root: Gwy3fJaAl6
```

集群02 信息：
```
10.2.14.29
administrator: eTjXJnS9aj
root: M9BRRjnjeY
```
备份数据
```
mysqldump -u administrator  -pLnoEJpgcgp -h 10.2.14.1 --single-transaction --routines --triggers --events \
    --set-gtid-purged=OFF  --hex-blob \
    --default-character-set=utf8mb4 \
    --max-allowed-packet=1073741824 \
    --all-databases > /tmp/all_backup.sql
```

数据恢复
```
mysql -uadministrator -peTjXJnS9aj -h 10.2.14.29 < /tmp/all_backup.sql
```
##  故障现象

集群router ,和 mysql-shell 都出现问题。

但是集群用原账号仍然可访问使用。

在集群的主节点写入数据，可以正常复制到从节点。 集群主节点关闭后还可以自动切主。

router 日志
```
2026-03-25 06:56:57 metadata_cache WARNING [79cf3862a6c0] Failed fetching metadata from metadata server on helmbroker-mysql02-0:3306 - No result returned for v2_this_instance metadata query
2026-03-25 06:56:58 metadata_cache WARNING [79cf3862a6c0] Failed fetching metadata from metadata server on helmbroker-mysql02-1:3306 - No result returned for v2_this_instance metadata query
2026-03-25 06:56:58 metadata_cache WARNING [79cf3862a6c0] Failed fetching metadata from metadata server on helmbroker-mysql02-2:3306 - No result returned for v2_this_instance metadata query
```

mysql-shell 登录失败

```
mysqlsh -uroot -pM9BRRjnjeY  -h helmbroker-mysql02-0
MySQL Shell 8.0.34

Copyright (c) 2016, 2023, Oracle and/or its affiliates.
Oracle is a registered trademark of Oracle Corporation and/or its affiliates.
Other names may be trademarks of their respective owners.

Type '\help' or '\?' for help; '\quit' to exit.
WARNING: Using a password on the command line interface can be insecure.
Creating a session to 'root@helmbroker-mysql02-0'
MySQL Error 1045: Access denied for user 'root'@'10.0.1.182' (using password: YES)
```
mysql 可以登录
```
 mysql -uroot -pM9BRRjnjeY  -h helmbroker-mysql02-0
mysql: [Warning] Using a password on the command line interface can be insecure.
Welcome to the MySQL monitor.  Commands end with ; or \g.
Your MySQL connection id is 17919
Server version: 8.0.34 Source distribution

Copyright (c) 2000, 2023, Oracle and/or its affiliates.

Oracle is a registered trademark of Oracle Corporation and/or its
affiliates. Other names may be trademarks of their respective
owners.

Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

mysql> 
```
查看集群信息，显示为集群01 的配置信息
```
use mysql_innodb_cluster_metadata;
select address from v2_instances;
+---------------------------+
| address                   |
+---------------------------+
| helmbroker-mysql01-0:3306 |
| helmbroker-mysql01-1:3306 |
| helmbroker-mysql01-2:3306 |
+---------------------------+
3 rows in set (0.00 sec)
```

查看集群状态
```
use performance_schema;
select * from replication_group_members;
+---------------------------+--------------------------------------+----------------------+-------------+--------------+-------------+----------------+----------------------------+
| CHANNEL_NAME              | MEMBER_ID                            | MEMBER_HOST          | MEMBER_PORT | MEMBER_STATE | MEMBER_ROLE | MEMBER_VERSION | MEMBER_COMMUNICATION_STACK |
+---------------------------+--------------------------------------+----------------------+-------------+--------------+-------------+----------------+----------------------------+
| group_replication_applier | 0a4682f0-27f6-11f1-922b-6edd54b6912b | helmbroker-mysql02-2 |        3306 | ONLINE       | SECONDARY   | 8.0.34         | MySQL                      |
| group_replication_applier | e714a3cd-27f5-11f1-97fb-8a5efde9322f | helmbroker-mysql02-0 |        3306 | ONLINE       | PRIMARY     | 8.0.34         | MySQL                      |
| group_replication_applier | fb8e2088-27f5-11f1-9a5b-2a9d84d35262 | helmbroker-mysql02-1 |        3306 | ONLINE       | SECONDARY   | 8.0.34         | MySQL                      |
+---------------------------+--------------------------------------+----------------------+-------------+--------------+-------------+----------------+----------------------------+
3 rows in set (0.00 sec)
```

## 集群恢复

修改密码, 在主节点执行。可自动同步到其他节点
```
mysql -uroot -pM9BRRjnjeY  -h helmbroker-mysql02-0
alter user 'root'@'%' identified by 'M9BRRjnjeY';
```
验证
```
mysqlsh -uroot -pM9BRRjnjeY  -h helmbroker-mysql02-0
mysqlsh -uroot -pM9BRRjnjeY  -h helmbroker-mysql02-1
mysqlsh -uroot -pM9BRRjnjeY  -h helmbroker-mysql02-2
```
重启 , 注意顺序，先重启从节点，避免发生主从切换
```
mysql -uroot -pM9BRRjnjeY  -h helmbroker-mysql02-2
shutdown
mysql -uroot -pM9BRRjnjeY  -h helmbroker-mysql02-1
shutdown
mysql -uroot -pM9BRRjnjeY  -h helmbroker-mysql02-0
shutdown
```
重启后连入主节点
```
dba.getCluster();
Dba.getCluster: This function is not available through a session to a standalone instance (metadata exists, instance does not belong to that metadata, and GR is not active) (RuntimeError)
 MySQL  helmbroker-mysql02-1:33060+ ssl  JS > dba.rebootClusterFromCompleteOutage();
Dba.rebootClusterFromCompleteOutage: This function is not available through a session to a standalone instance (metadata exists, instance does not belong to that metadata, and GR is not active) (RuntimeError)
```

重建集群
```
mysqlsh -uroot -pM9BRRjnjeY  -h helmbroker-mysql02-0 

dba.createCluster('MXMGR');
dba.getCluster().addInstance('');
```
重启 router 

## 分析

原有账号权限体系及组复制集群信息在内存中。在没有重启的情况下仍然可以滑翔，继续运行。但是router和 mysqlshell 需要验证组复制的元数据，出现故障。

恢复流程:

1. root 账号，这个很重要。事故现场的钥匙

2. 确认主节点

3. 逐个重启实例，保存内存与磁盘数据一致,最后重启主库。 这个时候主从还会自动切换的。

4. 利用mysqlsh 重建集群，连接到原来的主节点创建集群 。


