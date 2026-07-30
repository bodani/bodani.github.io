# 逻辑复制

## 逻辑复制

Postgres 10 版本开始， 在内核层面支持基于REDO流的逻辑复制。

控制粒度为表级别

物理复制相同都是基于wal 

可指定多个上游数据源

下游数据可读可写

可用于数据汇总，无停服数据迁移,大版本升级等。

## 基本概念

- 发布者（publication）， 上游数据
- 订阅者 (subscrition)， 下游数据
- 复制槽 (slot), 保存逻辑复制的信息

## 注意事项

- 数据库模式和DDL命令不会被复制
- 序列数据不被复制
- 分区表,需要发布子表 

## 常用方式总结

#### 发布端
- 逻辑复制的前提是将数据库 wal_level 参数设置成 logical；
- 源库上逻辑复制的用户必须具有 replicatoin 或 superuser 角色；
- 逻辑复制目前仅支持数据库表逻辑复制，其它对象例如函数、视图不支持；
- 逻辑复制支持DML(UPDATE、INSERT、DELETE)操作，TRUNCATE 和 DDL 操作不支持；
- 需要发布逻辑复制的表，须配置表的 REPLICA IDENTITY 特性；
-  一个数据库中可以有多个publication，通过 pg_publication 查看；
- 允许一次发布所有表，语法： CREATE PUBLICATION alltables FOR ALL TABLES;

#### 订阅端
- 订阅节点需要指定发布者的连接信息；
-  一个数据库中可以有多个订阅者；
- 可以使用enable/disable启用/暂停该订阅；
- 发布节点和订阅节点表的模式名、表名必须一致，订阅节点允许表有额外字段；
- 发布节点增加表名，订阅节点需要执行： ALTER SUBSCRIPTION sub1 REFRESH PUBLICATION

#### 复制标识

为了能够复制UPDATE和DELETE操作，被发布的表必须配置有一个“复制标识”。
这样在订阅者那一端才能标识对于更新或删除合适的行。默认情况下，复制标识就是主键（如果有主键）。也可以在复制标识上设置另一个唯一索引（有特定的额外要求）。如果表没有合适的键，那么可以设置成复制标识“full”，它表示整个行为键。

如果没有复制标识，订阅端的UPDATE和DELETE操作将发生错误。INSERT可以执行。

查看复制标识
```
select relreplident from pg_class where relname = ' xxx ';

d 默认
n 无
f 所有列
i 索引
```
修改复制标识
```
alter table xxx replica identity using index xx_idx;
```
#### 冲突

跳过冲突事务
```
pg_replication_origin_advance()
```
查看冲突时的位置
```
pg_replication_origin_status
```

## 简单实践

 将PG10中的一张表同步到PG12中

#### 发布者服务器配置

postgresql.conf
```
wal_level = logical
max_replication_slots = 10 # 每个slot 需要一个
max_wal_senders = 10 # 每个slot 需要一个
max_worker_processes = 128 
 
```
pg_hba.conf

```
host replication postgres 10.1.0.0/16 md5
```

#### 订阅者服务器配置

postgresql.conf
```
max_replication_slots = 10 # 每个slot 需要一个
max_logical_replication_workers = 10 # 每个slot 需要一个
max_worker_processes = 128
```

#### 在发布端创建发布

```
create publication test01 for table test01 ;
```

#### 在订阅端创建表结构

pg_dump --schema-only 
```
pg_dump -U s -t test01 pglogicaltestdb
```

#### 在订阅端创建订阅
```
create subscription sub1 connection 'host=10.1.7.55 port=25432 dbname=pglogicaltestdb password=123456' publication test01;
```

## 常用视图查看

#### 发布端视图

```
 select * from pg_stat_replication ;

 select * from pg_publication;

 select * from pg_publication_tables ;
```

#### 订阅端视图

```
 select * from pg_stat_subscription;

 select * from pg_subscription
```

## 应用案例 - 升级数据库版本


## 更多思考

多主方案， DBR

例子
https://cdn.modb.pro/db/48200


对DDL支持
https://github.com/enova/pgl_ddl_deploy
