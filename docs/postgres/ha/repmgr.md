# 基于Repmgr实现数据库高可用

# 安装环境

## 软件环境

- postgres 10
- repmgr 5.3.2
- centos7

## 网络环境

| IP地址           |      | 运行软件          |
| ---------------- | ---- | ----------------- |
| 10.10.2.12/node1 |      | repmgr,repmgrd,pg |
| 10.10.2.13/node2 |      | repmgr,repmgrd,pg |
| 10.10.2.14/node3 |      | repmgr,repmgrd,pg |

## 前期准备

- hosts 文件配置

  ```
  vi /etc/hosts # 
  10.10.2.12 node1
  10.10.2.13 node2
  10.10.2.14 node3
  ```

- 安装PG10

```
 $ yum install https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm
  $ yum update -y 
  $ yum install -y postgresql10-server postgresql10  postgresql10-contrib
  # 只有主库需要初始化
  $ sudo su postgres -c  "/usr/pgsql-10/bin/initdb  --data-checksums -D /var/lib/pgsql/10/data" 
```

- 安装repmgr

  ```
  $ yum install -y repmgr10.x86_64 
  ```

- 提升postgres 用户具有部分sudo 执行权限

  repmgr 需要非root用户管理

  ```
  vi /etc/sudoers.d/postgres # chmod 400 /etc/sudoers.d/postgres
  Defaults:postgres !requiretty
  postgres ALL = NOPASSWD: /usr/bin/systemctl stop postgresql-10, \
  /usr/bin/systemctl start postgresql-10, \
  /usr/bin/systemctl restart postgresql-10, \
  /usr/bin/systemctl reload postgresql-10
  ```

- ssh 免密互通

  配置ssh免密互通非必须，在执行switchover操作时需要 

  ```
  $ su - postgres
  $ ssh-keygen
  $ cat .ssh/id_rsa.pub >  .ssh/authorized_keys # 本机免密登录 
  # 将 .ssh 目录下authorized_keys，id_rsa，id_rsa.pub 拷贝到其他节点对应位置上，并赋值对应权限
  $ chmod 600 .ssh/authorized_keys
  $ chmod 600 .ssh/id_rsa
  $ chmod 644 .ssh/id_rsa.pub 
  # 用命令拷贝到其他节点 # 首次连接需要设置密码
  $ ssh-copy-id ${远端服务器} 
  $ ssh $远端服务器}
  ```

#### 配置

- PG 配置

  ```
  vi postgres.conf
  # 必须项
  max_wal_senders = 10
  max_replication_slots = 10 # 复制槽
  wal_level = 'logical' # replica 或 logical ，便于后期应用逻辑复制建议使用logical
  hot_standby = on # 从库在recovery状态下可读
  wal_log_hints = on # pg_rewind 依赖配置
  # 可选，建议开启项目。后期修改可能需要重启数据库
  archive_mode = always # 从库也可做归档
  archive_command = '/bin/true'
  archive_timeout = 300 # 单位秒 ，五分钟
  wal_keep_segments = 1024 # 保留wal文件个数， 如果设置slot 可忽略
  # 访问相关
  listen_addresses = '*'                  # 监听网卡
  port = 5432                             # 端口
  max_connections = 1000                  # 最大连接数
  superuser_reserved_connections = 3     #  超级用户预留
  ```

  ```
  vi pg_hba.conf #  确保本机repmgr 用户可访问
  host    replication   repmgr      127.0.0.1/32            trust
  host    replication   repmgr      0.0.0.0/0               trust
  
  local   repmgr        repmgr                              trust
  host    repmgr        repmgr      127.0.0.1/32            trust
  host    repmgr        repmgr      0.0.0.0/0               md5
  ```

  ```
  # 元数据信息存储设置
  postgres=# create user repmgr;
  CREATE ROLE
  postgres=# alter user repmgr with password 'xxxxx';
  ALTER ROLE
  postgres=# alter user repmgr replication ;
  ALTER ROLE
  postgres=# create database repmgr owner repmgr;
  CREATE DATABASE
  postgres=#\c repmgr
  repmgr=# create extension repmgr;
  CREATE EXTENSION
  repmgr=# GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA repmgr TO repmgr ;
  ```

- repmgr

  ```
  vi repmgr.conf # /etc/repmgr/10/repmgr.conf
  ## 必须项
  node_id=1
  node_name= node1
  conninfo ='host=node1 dbname=repmgr user=repmgr connect_timeout=2'
  data_directory = '/var/lib/pgsql/10/data'
  ## 可选项
  config_directory = # pg配置文件位置
  replication_user = repmgr # 默认为conninfo 中使用的user
  location = # 服务器所在物理位置，有助于判断当发生脑裂时网络互通逻辑
  use_replication_slots = true # 是否使用物理复制槽
  log_level = INFO # 日志等级
  log_file =  '/var/log/repmgr/repmgr.log' # 日志输出文件位置 ，结合lograte管理
  # 数据库yum 方式安装，使用systemd 管理时
  service_start_command   = 'sudo systemctl start postgresql-10'
  service_stop_command    = 'sudo systemctl stop postgresql-10'
  service_restart_command = 'sudo systemctl restart postgresql-10'
  service_reload_command  = 'sudo systemctl reload postgresql-10' 
  ```

## 注册主库

- 启动数据库

  ```
  # 启动数据库服务
  systemctl start postgresql-10
  # 设置开机自启
  systemctl enable postgresql-10
  ```

  ```
  # 连接测试 repmgr.conf 中的conninfo 连接串信息测试本地登录
  psql  'host=node1 dbname=repmgr user=repmgr connect_timeout=2'
  ```

- 注册

  ```
  $ su - postgres
  
  # 测试注册主节点
  $ /usr/pgsql-10/bin/repmgr -f /etc/repmgr/10/repmgr.conf primary register --dry-run -L debug
  INFO: connecting to primary database...
  DEBUG: connecting to: "user=repmgr dbname=repmgr host=node1 port=5432 connect_timeout=2 fallback_application_name=repmgr options=-csearch_path="
  INFO: "repmgr" extension is already installed
  
  # 正式注册主节点
  $ /usr/pgsql-10/bin/repmgr -f /etc/repmgr/10/repmgr.conf primary register 
  INFO: connecting to primary database...
  INFO: "repmgr" extension is already installed
  NOTICE: primary node record (ID: 2) registered
  
  # 查看节点信息
  $ /usr/pgsql-10/bin/repmgr -f /etc/repmgr/10/repmgr.conf cluster show
   ID | Name  | Role    | Status    | Upstream | Location | Priority | Timeline | Connection string                             
  ----+-------+---------+-----------+----------+----------+----------+----------+------------------------------------------------
   2  | node1 | primary | * running |          | default  | 100      | 2        | host=node1 port=5432 user=repmgr dbname=repmgr
  
  ```

- 在数据库中查看注册信息

  ```
  $ repmgr=# set search_path = "$user", public,repmgr;
  SET
  
  $ repmgr=# \d+ 
                              List of relations
   Schema |        Name        | Type  | Owner  |    Size    | Description 
  --------+--------------------+-------+--------+------------+-------------
   repmgr | events             | table | repmgr | 16 kB      | 
   repmgr | monitoring_history | table | repmgr | 0 bytes    | 
   repmgr | nodes              | table | repmgr | 16 kB      | 
   repmgr | replication_status | view  | repmgr | 0 bytes    | 
   repmgr | show_nodes         | view  | repmgr | 0 bytes    | 
   repmgr | voting_term        | table | repmgr | 8192 bytes | 
  (6 rows)
  
  $ SELECT * FROM repmgr.nodes;
  -[ RECORD 1 ]----+-----------------------------------------------
  node_id          | 2
  upstream_node_id | 
  active           | t
  node_name        | node1
  type             | primary
  location         | default
  priority         | 100
  conninfo         | host=node1 port=5432 user=repmgr dbname=repmgr
  repluser         | repmgr
  slot_name        | repmgr_slot_2
  config_file      | /etc/repmgr/10/repmgr.conf
  
  $ SELECT * FROM repmgr.show_nodes ;
  -[ RECORD 1 ]------+-----------------------------------------------
  node_id            | 2
  node_name          | node1
  active             | t
  upstream_node_id   | 
  upstream_node_name | 
  type               | primary
  priority           | 100
  conninfo           | host=node1 port=5432 user=repmgr dbname=repmgr
  ```

## 加入从库

加入node2 ，node3 两个节点

- 安装PG & repmgr

- 配置repmgr

- 从主节点clone

  ```
  # 试运行 连接信息 -U -h -d 为主库地址 , 是否使用复制槽 在 repmgr.conf 中指定
  $ /usr/pgsql-10/bin/repmgr -h node1 -U repmgr -d repmgr -f /etc/repmgr/10/repmgr.conf standby clone --dry-run
  
  # 正式运行
  $ /usr/pgsql-10/bin/repmgr -h node1 -U repmgr -d repmgr -f /etc/repmgr/10/repmgr.conf standby clone 
  # 可选参数
  -c, --fast-checkpoint 主库执行checkpoint
  --upstream-node-id  可用于级联复制
  ```

    ```
  # 启动数据库
  $ sudo systemctl start postgresql-10
  # 注册从节点
  $ /usr/pgsql-10/bin/repmgr -f /etc/repmgr/10/repmgr.conf standby register 
    ```

  

  ```
  # 登录主库查看 主从复制信息
  select * from pg_stat_replication ;
  -[ RECORD 1 ]----+------------------------------
  pid              | 12204
  usesysid         | 16384
  usename          | repmgr
  application_name | node3
  client_addr      | 10.10.2.13
  client_hostname  | 
  client_port      | 37412
  backend_start    | 2022-08-11 06:15:08.568251+00
  backend_xmin     | 
  state            | streaming
  sent_lsn         | 0/5000648
  write_lsn        | 0/5000648
  flush_lsn        | 0/5000648
  replay_lsn       | 0/5000648
  write_lag        | 
  flush_lag        | 
  replay_lag       | 
  sync_priority    | 0
  sync_state       | async
  ```

  ```
   select * from pg_replication_slots ;
  -[ RECORD 1 ]-------+--------------
  slot_name           | repmgr_slot_3
  plugin              | 
  slot_type           | physical
  datoid              | 
  database            | 
  temporary           | f
  active              | t
  active_pid          | 12386
  xmin                | 
  catalog_xmin        | 
  restart_lsn         | 0/7001158
  confirmed_flush_lsn | 
  ```

  ```
  /usr/pgsql-10/bin/repmgr -f /etc/repmgr/10/repmgr.conf cluster show
   ID | Name  | Role    | Status    | Upstream | Location | Priority | Timeline | Connection string                             
  ----+-------+---------+-----------+----------+----------+----------+----------+------------------------------------------------
   2  | node1 | primary | * running |          | default  | 100      | 2        | host=node1 port=5432 user=repmgr dbname=repmgr
   3  | node3 | standby |   running | node1    | default  | 100      | 2        | host=node2 user=repmgr dbname=repmgr          
  ```

## 主动switchover

```
# 在计划提升为主库的节点上执行
/usr/pgsql-10/bin/repmgr -f /etc/repmgr/10/repmgr.conf standby switchover --siblings-follow 

# 查看切换结果 
/usr/pgsql-10/bin/repmgr -f /etc/repmgr/10/repmgr.conf cluster show
 ID | Name  | Role    | Status    | Upstream | Location | Priority | Timeline | Connection string                                     
----+-------+---------+-----------+----------+----------+----------+----------+--------------------------------------------------------
 1  | node1 | primary | * running |          | default  | 100      | 4        | host=node1 port=5432 user=repmgr dbname=repmgr        
 2  | node2 | standby |   running | node1    | default  | 100      | 3        | host=node2 user=repmgr dbname=repmgr                  
 3  | node3 | standby |   running | node1    | default  | 100      | 4        | host=node3 dbname=repmgr user=repmgr connect_timeout=2
  
```

注意事项，1 原主库上的slot 仍然存在（后期测试几次发现会自动删除） 2 级联复制的情况下避免最下游节点提升主

## 修改级联关系

```
/usr/pgsql-10/bin/repmgr -f /etc/repmgr/10/repmgr.conf standby follow --upstream-node-id 1
```

## 被动switchover

模拟主节点故障

```
# node1 关闭
sudo systemctl stop postgresql-10

# node2 上查看集群状态
/usr/pgsql-10/bin/repmgr -f /etc/repmgr/10/repmgr.conf cluster show
 ID | Name  | Role    | Status        | Upstream | Location | Priority | Timeline | Connection string                                     
----+-------+---------+---------------+----------+----------+----------+----------+--------------------------------------------------------
 1  | node1 | primary | ? unreachable | ?        | default  | 100      |          | host=node1 port=5432 user=repmgr dbname=repmgr        
 2  | node2 | standby |   running     | ? node1  | default  | 100      | 4        | host=node2 user=repmgr dbname=repmgr                  
 3  | node3 | standby |   running     | ? node1  | default  | 100      | 4        | host=node3 dbname=repmgr user=repmgr connect_timeout=2

WARNING: following issues were detected
  - unable to connect to node "node1" (ID: 1)
  - node "node1" (ID: 1) is registered as an active primary but is unreachable
  - unable to connect to node "node2" (ID: 2)'s upstream node "node1" (ID: 1)
  - unable to determine if node "node2" (ID: 2) is attached to its upstream node "node1" (ID: 1)
  - unable to connect to node "node3" (ID: 3)'s upstream node "node1" (ID: 1)
  - unable to determine if node "node3" (ID: 3) is attached to its upstream node "node1" (ID: 1)

HINT: execute with --verbose option to see connection error messages
```

提升node2 节点为主节点

```
# 在node2 上执行
$ /usr/pgsql-10/bin/repmgr -f /etc/repmgr/10/repmgr.conf standby promote
WARNING: 1 sibling nodes found, but option "--siblings-follow" not specified
DETAIL: these nodes will remain attached to the current primary:
  node3 (node ID: 3)
NOTICE: promoting standby to primary
DETAIL: promoting server "node2" (ID: 2) using "/usr/pgsql-10/bin/pg_ctl  -w -D '/var/lib/pgsql/10/data' promote"
waiting for server to promote.... done
server promoted
NOTICE: waiting up to 60 seconds (parameter "promote_check_timeout") for promotion to complete
NOTICE: STANDBY PROMOTE successful
DETAIL: server "node2" (ID: 2) was successfully promoted to primary

# 查看集群状态
$ /usr/pgsql-10/bin/repmgr -f /etc/repmgr/10/repmgr.conf cluster show
 ID | Name  | Role    | Status    | Upstream | Location | Priority | Timeline | Connection string                                     
----+-------+---------+-----------+----------+----------+----------+----------+--------------------------------------------------------
 1  | node1 | primary | - failed  | ?        | default  | 100      |          | host=node1 port=5432 user=repmgr dbname=repmgr        
 2  | node2 | primary | * running |          | default  | 100      | 5        | host=node2 user=repmgr dbname=repmgr                  
 3  | node3 | standby |   running | ? node1  | default  | 100      | 4        | host=node3 dbname=repmgr user=repmgr connect_timeout=2

WARNING: following issues were detected
  - unable to connect to node &quot;node1&quot; (ID: 1)
  - unable to connect to node &quot;node3&quot; (ID: 3)&apos;s upstream node &quot;node1&quot; (ID: 1)
  - unable to determine if node &quot;node3&quot; (ID: 3) is attached to its upstream node &quot;node1&quot; (ID: 1)

HINT: execute with --verbose option to see connection error messages

# 如果原来集群中有其他从节点，主节点也指向故障节点node1 ， 在提升node2节点时同时将其他节点指向自己
$ /usr/pgsql-10/bin/repmgr -f /etc/repmgr/10/repmgr.conf standby promote --siblings-follow 
```

node3 重新指定主库为node2

```
# 在node3 上执行
$ /usr/pgsql-10/bin/repmgr -f /etc/repmgr/10/repmgr.conf standby follow
# 查看状态
$ /usr/pgsql-10/bin/repmgr -f /etc/repmgr/10/repmgr.conf cluster show
 ID | Name  | Role    | Status    | Upstream | Location | Priority | Timeline | Connection string                                     
----+-------+---------+-----------+----------+----------+----------+----------+--------------------------------------------------------
 1  | node1 | primary | - failed  | ?        | default  | 100      |          | host=node1 port=5432 user=repmgr dbname=repmgr        
 2  | node2 | primary | * running |          | default  | 100      | 5        | host=node2 user=repmgr dbname=repmgr                  
 3  | node3 | standby |   running | node2    | default  | 100      | 4        | host=node3 dbname=repmgr user=repmgr connect_timeout=2

WARNING: following issues were detected
  - unable to connect to node "node1" (ID: 1)

HINT: execute with --verbose option to see connection error messages
```

node1 重新加入集群

```
# 登录到原主node1 节点 ， 确保数据是关闭状态 
$ /usr/pgsql-10/bin/repmgr node rejoin -f /etc/repmgr/10/repmgr.conf -d 'host=node3 dbname=repmgr user=repmgr'  --force-rewind --config-files=postgresql.conf --verbose --dry-run
NOTICE: using provided configuration file "/etc/repmgr/10/repmgr.conf"
NOTICE: rejoin target is node "node3" (ID: 3)
INFO: replication slots in use, 3 free slots on node 9
INFO: replication connection to the rejoin target node was successful
INFO: local and rejoin target system identifiers match
DETAIL: system identifier is 7129425727714895616
INFO: prerequisites for using pg_rewind are met
INFO: temporary archive directory "/tmp/repmgr-config-archive-node1" created
INFO: file "postgresql.conf" would be copied to "/tmp/repmgr-config-archive-node1/postgresql.conf"
INFO: 1 files would have been copied to "/tmp/repmgr-config-archive-node1"
INFO: temporary archive directory "/tmp/repmgr-config-archive-node1" deleted
INFO: pg_rewind would now be executed
DETAIL: pg_rewind command is:
  /usr/pgsql-10/bin/pg_rewind -D '/var/lib/pgsql/10/data' --source-server='host=node3 dbname=repmgr user=repmgr connect_timeout=2'
INFO: prerequisites for executing NODE REJOIN are met

# 正式执行
$ /usr/pgsql-10/bin/repmgr node rejoin -f /etc/repmgr/10/repmgr.conf -d 'host=node3 dbname=repmgr user=repmgr'  --force-rewind --config-files=postgresql.conf --verbose
# 启动数据库
$ sudo systemctl start postgresql-10
# 查看结果
$ /usr/pgsql-10/bin/repmgr -f /etc/repmgr/10/repmgr.conf cluster show
```

node1 节点故障不可恢复情况

 ```
# 将node1 节点从集群中注销, 登录到其他任意节点
$ /usr/pgsql-10/bin/repmgr -f /etc/repmgr/10/repmgr.conf standby unregister --node-id
 ```

```
 $ repmgr -f /etc/repmgr/10/repmgr.conf cluster event
```

## 自动failover

修改配置

vi postgresql.conf
```
shared_preload_libraries = 'repmgr'
```

vi /etc/repmgr/10/repmgr.conf
```
failover=automatic
promote_command='/usr/pgsql-10/bin/repmgr standby promote -f /etc/repmgr/10/repmgr.conf --log-to-file'
follow_command='/usr/pgsql-10/bin/repmgr standby follow -f /etc/repmgr/10/repmgr.conf --log-to-file --upstream-node-id=%n'
log_file='/var/lib/pgsql/repmgrd.log'
monitoring_history=true #（启用监控参数）
monitor_interval_secs=5 #（定义监视数据间隔写入时间参数）
reconnect_attempts=10 #（故障转移之前，尝试重新连接主库次数（默认为6）参数）
reconnect_interval=5 #（每间隔5s尝试重新连接一次参数
```

重启 postgres

```
repmgr node service --action=restart
```

启动 repmgrd

```
systemctl start repmgr-10
systemctl enable repmgr-10
```

测试

略

主节点重新加入集群

```
# 全部原主节点保持关闭状态。 首先将执行pg_rewind ->   自动启动服务 - > 注册服务
 repmgr node rejoin -d 'host=node1 dbname=repmgr user=repmgr' --force-rewind --config-files=postgresql.conf,postgresql.auto.conf --verbose --dry-run
 repmgr node rejoin -d 'host=node1 dbname=repmgr user=repmgr' --force-rewind --config-files=postgresql.conf,postgresql.auto.conf --verbose
```

#### 自动failover 几点说明

为预防网络脑裂发生： repmgr 做了如下努力： 1 ，使用见证节点。主要应用于只有主从两个节点的场景， 将见证节点与主节点部署在同一个网络区间。 当主节点与见证节点同时不可见时，认为是网络错误，不发生切换。当见证节点可见，主节点不可见时，认为主节点失效，触发切换。

引入见证节点提高了维护成本。 

多IDC网络场景，方案2 ： 使用location 标记服务所在的位置。当与主节点location相同的节点都不可见时，认为是网络错误，不发生切换。如果集群中没有其他节点与主节点的location配置相同，则永远不发生切换。

举例： 三个IDC，三个pg服务。location分别设置为dc1（主节点），dc2（从节点），dc3（从节点）。 当dc1 节点发生故障时不会发生故障转移。 因为集群中location 为dc1的节点（只有一个）都不可见。

合理的设置应该为cd1(主节点) ,dc1(一个从)，dc2（另一个从）。 此时当dc1 发生以外时，可故障转移。

#### 注意事项： 当主节点网络问题。如网卡，网线故障。服务正常的情况下。集群也会发生故障转移。当网络恢复的时候发生脑裂。 主要问题。当主节点脱离集群时没有彻底关闭服务。repmgr不能管理pg服务,将其关闭。

可以如下设置，通过确定与从节点连接个数决定是否关闭当前服务。在command中关闭当前pg
```
#child_nodes_check_interval=5           # Interval (in seconds) to check for attached child nodes (standbys)
#child_nodes_connected_min_count=-1     # Minimum number of child nodes which must remain connected, otherwise
                                        # disconnection command will be triggered
#child_nodes_disconnect_min_count=-1    # Minimum number of disconnected child nodes required to execute disconnection command
                                        # (ignored if "child_nodes_connected_min_count" set)
#child_nodes_disconnect_timeout=30      # Interval between child node disconnection and disconnection command execution
child_nodes_disconnect_command='' 
```

#### location 修改

localtion 参数在高可用架构中为防止网络分区问题发挥重要作用。 发生故障转移后location 通常也需要重新设计。

修改 /etc/repmgr/10/repmgr.conf

生效
```
repmgr standby register --force
systemctl restart repmgr-10
```

查看
```
repmgr cluster show
或
select * from repmgr.nodes;
```

[修改location](https://repmgr.org/docs/current/repmgrd-basic-configuration.html#REPMGRD-RELOADING-CONFIGURATION)


