# pg_auto_failover 实践

## 一个简单的架构

citus同源postgres高可用方案

角色:

- 主节点 (master)
- 复制节点 (slave)
- 监控节点 (monitor)

## 集群搭建

### 环境说明

#### 软件版本

- postgresql 14.4
- pg_auto_failover 1.6.4
- centos 7

#### 网络环境

|     IP     |    软件     |
| :--------: | :---------: |
| 10.10.2.11 |   monitor   |
| 10.10.2.12 |   master    |
| 10.10.2.13 | replication |



### 从零开始建设

	没有任何历史包袱，包括数据库自身的搭建

	**手动安装**

     在所有的节点上执行

```
-- 数据库安装
sudo yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm
sudo yum install -y postgresql14-server
```

```
# install pg_auto_failover
curl https://install.citusdata.com/community/rpm.sh | sudo bash
yum install pg_auto_failover_14.x86_64 -y

# confirm installation
/usr/pgsql-14/bin/pg_autoctl --version
```

     创建monitor节点

```
--创建监控节点
su - postgres -c "/usr/pgsql-14/bin/pg_autoctl create monitor \
   --hostname node0 \
   --auth trust \
   --ssl-self-signed \
   --pgdata /var/lib/pgsql/14/data/ \
   --pgctl /usr/pgsql-14/bin/pg_ctl "

--启动监控节点服务
/usr/pgsql-14/bin/pg_autoctl -q show systemd --pgdata "/var/lib/pgsql/14/data" | tee /etc/systemd/system/pgautofailover.service

systemctl start pgautofailover

-- 查看node连接monitor 信息
/usr/pgsql-14/bin/pg_autoctl show uri --formation monitor --pgdata /var/lib/pgsql/14/data/

postgres://autoctl_node@node0:5432/pg_auto_failover?sslmode=require

```

		创建数据库主节点

```
-- 创建数据库节点
su - postgres -c "/usr/pgsql-14/bin/pg_autoctl create postgres \
    --hostname node1 \
    --name node1 \
    --pgctl /usr/pgsql-14/bin/pg_ctl \
    --pgdata /var/lib/pgsql/14/data/ \
    --auth trust \
    --ssl-self-signed \
    --monitor 'postgres://autoctl_node@node0:5432/pg_auto_failover?sslmode=require' \
    "
    
```

```
创建节点说明，在create postgres后，将在本地生成配置信息。具体可查看
su - postgres -c "/usr/pgsql-14/bin/pg_autoctl show file   --pgdata /var/lib/pgsql/14/data/"
```


```
-- systemd 管理服务
su - postgres -c "/usr/pgsql-14/bin/pg_autoctl -q show systemd --pgdata /var/lib/pgsql/14/data "  > /etc/systemd/system/pgautofailover.service
   
-- 启动服务
systemctl start pgautofailover
```

		创建数据库从节点

```
-- 在另一个节点创建从库
su - postgres -c "/usr/pgsql-14/bin/pg_autoctl create postgres \
    --hostname node2 \
    --name node2 \
    --pgctl /usr/pgsql-14/bin/pg_ctl \
    --pgdata /var/lib/pgsql/14/data/ \
    --auth trust \
    --ssl-self-signed \
    --monitor 'postgres://autoctl_node@node0:5432/pg_auto_failover?sslmode=require' \
    "
```

```
-- systemd 管理服务
su - postgres -c "/usr/pgsql-14/bin/pg_autoctl -q show systemd --pgdata /var/lib/pgsql/14/data "  > /etc/systemd/system/pgautofailover.service

-- 启动服务
system start pgautofailover
```



```
-- 在monitor节点查看状态
/usr/pgsql-14/bin/pg_autoctl   show state --pgdata /var/lib/pgsql/14/data/

  Name |  Node |  Host:Port |       TLI: LSN |   Connection |      Reported State |      Assigned State
-------+-------+------------+----------------+--------------+---------------------+--------------------
node1 |     1 | node1:5432 |   1: 0/500BD90 |   read-write |             primary |             primary
 node2 |   111 | node2:5432 |   1: 0/500BD90 |    read-only |           secondary |           secondary

```

```
-- 在监控点删除postgres
su - postgres -c "/usr/pgsql-14/bin/pg_autoctl drop node  --destroy --force --name node2 "
```

### 现有数据库接管

	不影响现有数据库业务，使其具有高可用能力

    与从零开始创建集群不同的是，在create postgres阶段，根据    --pgdata 目录所指定的 pg_controldata 来判断数据库数   据目录现有情况。包括是否需要初始化数据库，及现有数据库状态 

## 集群管理

### 状态查看

```
/usr/pgsql-14/bin/pg_autoctl   show state --pgdata /var/lib/pgsql/14/data/
```

### 手动switch

```
/usr/pgsql-14/bin/pg_autoctl  perform switchover --formation default --group 0  --pgdata /var/lib/pgsql/14/data/
```

### 自动failover

#### 节点失败

	- 主节点失败
	  When the primary node is unhealthy, and only when the secondary node is itself in good health, then the primary node is asked to transition to the DRAINING state, and the attached secondary is asked to transition to the state PREPARE_PROMOTION. In this state, the secondary is asked to catch-up with the WAL traffic from the primary, and then report success.
	
	The monitor then continues orchestrating the promotion of the standby: it stops the primary (implementing STONITH in order to prevent any data loss), and promotes the secondary into being a primary now.
	
	Depending on the exact situation that triggered the primary unhealthy, it’s possible that the secondary fails to catch-up with WAL from it, in that case after the PREPARE_PROMOTION_CATCHUP_TIMEOUT the standby reports success anyway, and the failover sequence continues from the monitor.
	
	When the keeper reports an acceptable WAL difference in the two nodes again, then the replication is upgraded back to being synchronous. While a secondary node is not in the SECONDARY state, secondary promotion is disabled.
	主机恢复后重新加入集群中，并且状态为secondary

```
- 备节点失败
When the secondary node is unhealthy, the monitor assigns to it the state CATCHINGUP, and assigns the state WAIT_PRIMARY to the primary node. When implementing the transition from PRIMARY to WAIT_PRIMARY, the keeper disables synchronous replication.
```

```
- 监控节点失败
Then the primary and secondary node just work as if you didn’t have setup pg_auto_failover in the first place, as the keeper fails to report local state from the nodes. Also, health checks are not performed. It means that no automated failover may happen, even if needed.
```

尽量避免监控节点与主节点同时失败的情况，如避免同机架，同机房，同一个网络分区。

#### 网络问题

### 维护模式

```
$ pg_autoctl enable maintenance
$ pg_autoctl disable maintenance
```

### 增减节点

	添加数据库节点

		 与前面加入从节点一致

     删除数据库节点

```
-- 在监控点删除postgres
su - postgres -c "/usr/pgsql-14/bin/pg_autoctl drop node  --destroy --force --name node3 --formation formation_name_003"
```

### 切换策略机制

```
 pgautofailover.health_check_max_retries | 2
 pgautofailover.health_check_period      | 20000
 pgautofailover.health_check_retry_delay | 2000
 pgautofailover.health_check_timeout     | 5000
```

## 多集群管理

### 多集群管理说明

	多集群这里的含义是一个monitor管理多套集群

	主要用到的两个概念

- formation

- group

  

**A formation is a logical set of PostgreSQL services that are managed together.**

**It is possible to operate many formations with a single monitor instance. Each formation has a group of Postgres nodes and the FSM orchestration implemented by the monitor applies separately to each group.**

通过说明可以知道，利用formation可以实现一个monitor管理多套集群。

 **A group consists of a PostgreSQL primary server and a secondary server setup with Hot Standby synchronous replication.**

**The notion of a formation that contains multiple groups in pg_auto_failover is useful when setting up and managing a whole Citus formation, where the coordinator nodes belong to group zero of the formation, and each Citus worker node becomes its own group and may have Postgres standby nodes.**

这里提供一个思路，一套citus集群在一个formation之下，citus中的多个主从节点通过group来区分。

### 具体实现案例

#### 	 利用formation 管理多套集群

```
-- 创建formation , 默认使用default
/usr/pgsql-14/bin/pg_autoctl create formation \
 --pgdata /var/lib/pgsql/14/data/ \
 --monitor 'postgres://autoctl_node@node0:5432/pg_auto_failover1?sslmode=require' \
 --formation formation_name_003 \
 --kind pgsql \
 --dbname pg_auto_failover
```

```
--查看 formation 信息
select * from pgautofailover.formation ;
    formationid     | kind  |      dbname       | opt_secondary | number_sync_standbys 
--------------------+-------+-------------------+---------------+----------------------
 default            | pgsql | postgres          | t             |                    0
 formation_name_003 | pgsql | postgres          | t             |                    0
(2 rows)
```

```
-- 在创建数据库节点时指定formation
su - postgres -c "/usr/pgsql-14/bin/pg_autoctl create postgres \
--hostname node3 \
--formation formation_name_003 \
--name node3 \
--pgctl /usr/pgsql-14/bin/pg_ctl \
--pgdata /var/lib/pgsql/14/data/ \
--auth trust \
--ssl-self-signed \
--monitor 'postgres://autoctl_node@node0:5432/pg_auto_failover?sslmode=require' \ 
"

注意事项: 
--hostname 本机host，
--formation 上面创建的formation ,
--name节点名称 ,
--monitor monitor节点连接信息
```

```
-- 查看数据库节点本地配置文件位置
su - postgres -c "/usr/pgsql-14/bin/pg_autoctl show file   --pgdata /var/lib/pgsql/14/data/"
```

```
-- 在monitor节点查看 数据库node节点注册情况
select formationid,nodeid ,groupid,nodename from pgautofailover.node;
    formationid     | nodeid | groupid | nodename 
--------------------+--------+---------+----------
 formation_name_003 |    120 |       0 | node3
 default            |      1 |       0 | node_1
 default            |    111 |       0 | node2
(3 rows)

```

#### 利用group 管理citus中的多集群

在创建pg节点时并没有参考用来指定group, 文档中有如下关于group的描述。

**in a pgsql formation, there can be only one group, with groupId 0**

**At the moment citus formation kinds are not managed in the Open Source version of pg_auto_failover.**

很遗憾，现开源版本并不支持 citus类型的formation。 类型为pgsql的formation中只支持为零的group。

用pgautofailover来管理citus 集群还是使用多个formaton 吧

## 监控节点高可用

```
-- 数据库的主从流复制 mon1主节点,mon2复制节点 
-- 在创建formation 及 postgres 节点时， 将-- monitor 参数指定为
postgres://mon1:5432,mon2:5432,mon3:5432/pg_auto_failover?target_session_attrs=read-write&sslmode=prefer
```

## 客户端高可用

```
$ psql -d "postgresql://host1,host2/dbname?target_session_attrs=read-write"
$ psql -d "postgresql://host1:port2,host2:port2/dbname?target_session_attrs=read-write"
$ psql -d "host=host1,host2 port=port1,port2 target_session_attrs=read-write"
```

## 常用命令

https://pg-auto-failover.readthedocs.io/en/master/ref/manual.html

## 安全及权限
