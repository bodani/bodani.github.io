# mysql-shell 管理组复制

## 安装
```
sudo apt-get install mysql-shell
```

创建超级用户
```
create user administrator@'%' identified with 'caching_sha2_password'  by 'password';
grant all PRIVILEGES on *.* to administrator@'%' WITH GRANT OPTION;
flush privileges;
show grants for administrator@'%';
```
## 创建集群
```
创建集群，第一个节点
mysqlsh -uadministrator -ppassword -h 10.10.2.11 

shell.options['dba.restartWaitTimeout']=300;
var cluster=dba.createCluster('YOURMGR',{disableClone:false});
加入节点 1 
dba.getCluster().addInstance('administrator:cluster_password@10.10.2.12:3306',{recoveryMethod:'clone'})
加入节点 2
dba.getCluster().addInstance('administrator:cluster_password@10.10.2.12:3306',{recoveryMethod:'clone'})
```
使用 mysqlsh 创建集群会自动创建组复制的相关用户，并不是使用的这个administrator 账号。


查看状态
```
dba.getCluster().status();
```

```
mysql router 
# 创建配置文件
mysqlrouter --bootstrap mysql_user@host:port  -d /etc/mysql/conf/router --name myrouter --force --user=mysql
```

```
# 启动router
cd /etc/mysql/conf/router && sh start.sh
```

```
https://github.com/rluisr/mysqlrouter_exporter
```
注意事项apparmor aa-teardown

```
# 验证
mysql -h xxx -P 6446 -pmysql_4U

mysql -h xxx -P 6447 -pmysql_4U
```

```
#mysqlsh 配置验证，修复
dba.checkInstanceConfiguration();
dba.configureInstance();
```

## 扩容节点
查看状态
```
dba.getCluster().status();
```
加入前验证集群
```
dba.checkInstanceConfiguration('user@10.10.2.13:3306');
```
加入前配置集群
```
dba.configureInstance('user@10.10.2.13:3306');
```
加入集群
```
dba.getCluster().addInstance('user@10.10.2.13:3306');
```
重新加入集群 
```
cluster.rejoinInstance() 
```

## 缩容
```
cluster.removeInstance("root@instanceWithOldUUID:3306", {force: true})
cluster.rescan()
```

## 指定主节点
```
cluster.setPrimaryInstance()
```

## 重启集群
当所有集群中的节点都处于关闭状态时
```
dba.rebootClusterFromCompleteOutage();
```

API

```
https://dev.mysql.com/doc/dev/mysqlsh-api-python/8.0/
```


## 脑裂场景

当集群中多数节点（半数或以上）失效时。

当集群中有部分节点出现UNREACHABLE状态，此时集群无法做出决策，，会出现以下局面，此时只剩下一个活跃节点，此节点只能提供查询，无法写入，执行写入操作会hang住。
`"status": "NO_QUORUM"`

```
js> cluster.status()
{
    "clusterName": "mycluster",
    "defaultReplicaSet": {
        "name": "default",
        "primary": "192.168.33.21:3306",
        "status": "NO_QUORUM",
        "statusText": "Cluster has no quorum as visible from '192.168.33.21:3306' and cannot process write transactions. 2 members are not active",
        "topology": {
            "192.168.33.21:3306": {
                "address": "192.168.33.21:3306",
                "mode": "R/W",
                "readReplicas": {},
                "role": "HA",
                "status": "ONLINE"
            },
            "192.168.33.22:3306": {
                "address": "192.168.33.22:3306",
                "mode": "R/O",
                "readReplicas": {},
                "role": "HA",
                "status": "UNREACHABLE"
            },
            "192.168.33.23:3306": {
                "address": "192.168.33.23:3306",
                "mode": "R/O",
                "readReplicas": {},
                "role": "HA",
                "status": "(MISSING)"
            }
        }
    }
}
```
修复这种状态，需要执行forceQuorumUsingPartitionOf指定当前活跃节点(如果是多个则选择primary node)，此时活跃节点可以提供读写操作，然后将其他节点加入此集群。

```
js> cluster.forceQuorumUsingPartitionOf('root@192.168.33.21:3306')
```

节点有哪状态

- ONLINE - 节点状态正常。
- OFFLINE - 实例在运行，但没有加入任何Cluster。
- RECOVERING - 实例已加入Cluster，正在同步数据。
- ERROR - 同步数据发生异常。
- UNREACHABLE - 与其他节点通讯中断，可能是网络问题，可能是节点crash。
- MISSING 节点已加入集群，但未启动group replication

集群有哪些状态

- OK – 所有节点处于online状态，有冗余节点。
- OK_PARTIAL – 有节点不可用，但仍有冗余节点。
- OK_NO_TOLERANCE – 有足够的online节点，但没有冗余，例如：两个节点的Cluster，其中一个挂了，集群就不可用了。
- NO_QUORUM – 有节点处于online状态，但达不到法定节点数，此状态下Cluster无法写入，只能读取。
- UNKNOWN – 不是online或recovering状态，尝试连接其他实例查看状态。
- UNAVAILABLE – 组内节点全是offline状态，但实例在运行，可能实例刚重启还没加入Cluster。


组复制信息持久化 存储位置 `mysqld-auto.cnf` 
<details>
  <summary>查看代码</summary>
``` json
mysql_static_variables": {
        "group_replication_ssl_mode": {
            "Value": "REQUIRED",
            "Metadata": {
                "Host": "",
                "User": "root",
                "Timestamp": 1726712162400774
            }
        },
        "group_replication_group_name": {
            "Value": "f5af33a9-68cb-11ef-8fbc-2a9c829ebee5",
            "Metadata": {
                "Host": "",
                "User": "root",
                "Timestamp": 1726712162386269
            }
        },
        "group_replication_group_seeds": {
            "Value": "helmbroker-my01-1:3306,helmbroker-my01-2:3306",
            "Metadata": {
                "Host": "",
                "User": "root",
                "Timestamp": 1726712217411206
            }
        },
        "group_replication_ip_allowlist": {
            "Value": "AUTOMATIC",
            "Metadata": {
                "Host": "",
                "User": "root",
                "Timestamp": 1726712162406505
            }
        },
        "group_replication_local_address": {
            "Value": "helmbroker-my01-0:3306",
            "Metadata": {
                "Host": "",
                "User": "root",
                "Timestamp": 1726712162402566
            }
        },
        "group_replication_member_weight": {
            "Value": "50",
            "Metadata": {
                "Host": "",
                "User": "root",
                "Timestamp": 1726712162410144
            }
        },
        "group_replication_start_on_boot": {
            "Value": "ON",
            "Metadata": {
                "Host": "",
                "User": "root",
                "Timestamp": 1726712162417423
            }
        },
        "group_replication_autorejoin_tries": {
            "Value": "3",
            "Metadata": {
                "Host": "",
                "User": "root",
                "Timestamp": 1726712162415523
            }
        },
        "group_replication_recovery_use_ssl": {
            "Value": "ON",
            "Metadata": {
                "Host": "",
                "User": "root",
                "Timestamp": 1726712162396737
            }
        },
        "group_replication_view_change_uuid": {
            "Value": "f5af3c16-68cb-11ef-8fbc-2a9c829ebee5",
            "Metadata": {
                "Host": "",
                "User": "root",
                "Timestamp": 1726712162389707
            }
        },
        "group_replication_exit_state_action": {
            "Value": "READ_ONLY",
            "Metadata": {
                "Host": "",
                "User": "root",
                "Timestamp": 1726712162408402
            }
        },
        "group_replication_communication_stack": {
            "Value": "MYSQL",
            "Metadata": {
                "Host": "",
                "User": "root",
                "Timestamp": 1726712162419318
            }
        },
        "group_replication_paxos_single_leader": {
            "Value": "OFF",
            "Metadata": {
                "Host": "",
                "User": "root",
                "Timestamp": 1726712162422954
            }
        },
        "group_replication_single_primary_mode": {
            "Value": "ON",
            "Metadata": {
                "Host": "",
                "User": "root",
                "Timestamp": 1726712162394640
            }
        },
        "group_replication_member_expel_timeout": {
            "Value": "5",
            "Metadata": {
                "Host": "",
                "User": "root",
                "Timestamp": 1726712162413567
            }
        },
        "group_replication_transaction_size_limit": {
            "Value": "150000000",
            "Metadata": {
                "Host": "",
                "User": "root",
                "Timestamp": 1726712162421121
            }
        },
        "group_replication_recovery_ssl_verify_server_cert": {
            "Value": "OFF",
            "Metadata": {
                "Host": "",
                "User": "root",
                "Timestamp": 1726712162398833
            }
        },
        "group_replication_enforce_update_everywhere_checks": {
            "Value": "OFF",
            "Metadata": {
                "Host": "",
                "User": "root",
                "Timestamp": 1726712162392318
            }
        }
    }
```
</details>



线上问题

```
dba.getCluster().status();
WARNING: Error connecting to Cluster: MYSQLSH 51004: Unable to find a primary member in the Cluster
Retrying getCluster() using a secondary member
WARNING: You are connected to an instance in state 'Read Only'
Write operations on the InnoDB cluster will not be allowed.

{
    "clusterName": "MXMGR", 
    "defaultReplicaSet": {
        "name": "default", 
        "primary": "helmbroker-lasm-mysql-base-demo-1:3306", 
        "ssl": "REQUIRED", 
        "status": "OK_NO_TOLERANCE_PARTIAL", 
        "statusText": "Cluster is NOT tolerant to any failures. 1 member is not active.", 
        "topology": {
            "helmbroker-lasm-mysql-base-demo-0:3306": {
                "address": "helmbroker-lasm-mysql-base-demo-0:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.34"
            }, 
            "helmbroker-lasm-mysql-base-demo-1:3306": {
                "address": "helmbroker-lasm-mysql-base-demo-1:3306", 
                "instanceErrors": [
                    "NOTE: group_replication is stopped."
                ], 
                "memberRole": "PRIMARY", 
                "memberState": "OFFLINE", 
                "mode": "n/a", 
                "readReplicas": {}, 
                "role": "HA", 
                "status": "UNREACHABLE", 
                "version": "8.0.34"
            }, 
            "helmbroker-lasm-mysql-base-demo-2:3306": {
                "address": "helmbroker-lasm-mysql-base-demo-2:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.34"
            }
        }, 
        "topologyMode": "Single-Primary"
    }, 
    "groupInformationSourceMember": "helmbroker-lasm-mysql-base-demo-2:3306"
}
```