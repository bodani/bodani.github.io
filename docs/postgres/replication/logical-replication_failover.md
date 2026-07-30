# 逻辑复制故障转移

## 逻辑复制故障转移


 - 主库 10.10.2.11
 - 物理从库 10.10.2.12
 - 逻辑从库 10.10.2.13

#### 测试任务
 当主库发生故障，物理复制从库变为新主库。逻辑从库将订阅地址变更为新主库。

![logical_replication_failover](/images/logical_replication_failover.excalidraw.png)
#### 开始测试

环境搭建参考

 - [物理复制](/postgres/replication01/)
 - [逻辑复制](/postgres/logical-replication/)

状态查看 复制关系
```
 select * from pg_stat_replication ;
-[ RECORD 1 ]----+------------------------------
pid              | 2628
usesysid         | 24576
usename          | repuser
application_name | sub1
client_addr      | 10.10.2.13
client_hostname  | 
client_port      | 40230
backend_start    | 2022-11-23 05:46:59.50291+00
backend_xmin     | 
state            | streaming
sent_lsn         | 0/21000140
write_lsn        | 0/21000140
flush_lsn        | 0/21000140
replay_lsn       | 0/21000140
write_lag        | 
flush_lag        | 
replay_lag       | 
sync_priority    | 0
sync_state       | async
-[ RECORD 2 ]----+------------------------------
pid              | 2757
usesysid         | 24576
usename          | repuser
application_name | walreceiver
client_addr      | 10.10.2.12
client_hostname  | 
client_port      | 37698
backend_start    | 2022-11-23 06:05:19.818834+00
backend_xmin     | 
state            | streaming
sent_lsn         | 0/21000140
write_lsn        | 0/21000140
flush_lsn        | 0/21000140
replay_lsn       | 0/21000140
write_lag        | 
flush_lag        | 
replay_lag       | 
sync_priority    | 0
sync_state       | async
```

复制槽
```
select * from pg_replication_slots ;
 slot_name |  plugin  | slot_type | datoid | database | temporary | active | active_pid | xmin | catalog_xmin | restart_lsn | confirmed_flush_lsn 
-----------+----------+-----------+--------+----------+-----------+--------+------------+------+--------------+-------------+---------------------
 node14    |          | physical  |        |          | f         | f      |            |      |              | 0/1F0005B8  | 
 sub1      | pgoutput | logical   |  12953 | postgres | f         | t      |       2628 |      |          570 | 0/21000108  | 0/21000140
(2 rows)
```

逻辑订阅表
```
select * from pg_publication_tables ;
 pubname | schemaname | tablename 
---------+------------+-----------
 test01  | public     | test01
(1 row)
```

表数据
```
 select * from test01 ;
 id 
----
  1
  2
  3
  4
(4 rows)
```

#### 主从切换

关闭主库 

```
systemctl stop postgresql
```

拷贝逻辑复制槽, 将主库pg_replsolt目录下的逻辑复制槽拷贝到从库对应目录下. 注意对应的用户及用户组。
```
scp -r pg_replslot/sub1/ 10.10.2.12:$PGDATA/data/pg_replslot/
```

将从库升级为主库并重新启动加载slot
```
pg_ctl promote 
waiting for server to promote.... done
server promoted
```

```
systemctl stop postgresql
```

查看复制槽加载情况

```
select * from pg_replication_slots ;
 slot_name |  plugin  | slot_type | datoid | database | temporary | active | active_pid | xmin | catalog_xmin | restart_lsn | confirmed_flush_lsn 
-----------+----------+-----------+--------+----------+-----------+--------+------------+------+--------------+-------------+---------------------
 sub1      | pgoutput | logical   |  12953 | postgres | f         | f      |            |      |          570 | 0/210001B8  | 0/210001B8
(1 row)

```

此时复制关系,无数据
```
select * from pg_stat_replication ;
```

在逻辑复制从库查看订阅信息
```
select * from pg_subscription;
 subdbid | subname | subowner | subenabled |                              subconninfo                               | subslotname | subsynccommit | subpublications 
---------+---------+----------+------------+------------------------------------------------------------------------+-------------+---------------+-----------------
   12953 | sub1    |       10 | t          | host=10.10.2.11 port=5432 dbname=postgres user=repuser password=123456 | sub1        | off           | {test01}

```

修改订阅信息
```
postgres=# alter subscription sub1 connection 'host=10.10.2.12 port=5432 dbname=postgres user=repuser password=123456';
ALTER SUBSCRIPTION
postgres=# select * from pg_subscription;
 subdbid | subname | subowner | subenabled |                              subconninfo                               | subslotname | subsynccommit | subpublications 
---------+---------+----------+------------+------------------------------------------------------------------------+-------------+---------------+-----------------
   12953 | sub1    |       10 | t          | host=10.10.2.12 port=5432 dbname=postgres user=repuser password=123456 | sub1        | off           | {test01}
(1 row)

```

查看复制关系 10.10.2.12
```
select * from pg_stat_replication ;
-[ RECORD 1 ]----+------------------------------
pid              | 3938
usesysid         | 24576
usename          | repuser
application_name | sub1
client_addr      | 10.10.2.13
client_hostname  | 
client_port      | 42330
backend_start    | 2022-11-23 07:10:27.604722+00
backend_xmin     | 
state            | streaming
sent_lsn         | 0/210004F8
write_lsn        | 0/210004F8
flush_lsn        | 0/210004F8
replay_lsn       | 0/210004F8
write_lag        | 
flush_lag        | 
replay_lag       | 
sync_priority    | 0
sync_state       | async

```

新主库插入数据查看逻辑复制情况
```
insert INTO test01 values (5);
```

逻辑从库查看结果
```
select * from test01 
```


#### 自动化基础
 - 拷贝repslot 目录
 - 重启新从库加载 repslot

Postgres 11 版本后，新增加函数  pg_replication_slot_advance

#### patroni 自动 failover配置


