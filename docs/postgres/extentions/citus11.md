# 环境介绍

## 版本信息

 - centos7

- postgres 14.4

- citus 110-2

## 安装步骤

  - 安装

    ```
    略
    ```

- 配置

```
sudo pg_conftool 14 main set wal_level logical
sudo pg_conftool 14 main set listen_addresses '*'
sudo pg_conftool 14 main set shared_preload_libraries citus
```

```
sudo vi /etc/postgresql/14/main/pg_hba.conf
```

- 创建数据库免密码登录

  

  ```
  -- Edit .pgpass in the postgres user’s home directory, 
  hostname:port:database:username:password
  ```

  

## 节点信息

| nodenanme | IP          | role        |
| --------- | ----------- | ----------- |
| master01  | 10.10.20.11 | coordinator |
| worker01  | 10.10.2.12  | worker      |
| worker02  | 10.10.2.14  | worker      |
|           |             |             |



# 搭建集群

创建database&extension

在每个worker节点上执行

```
CREATE DATABASE newbie;
\c newbie
CREATE EXTENSION citus;
```

在master接节点上执行

```
CREATE DATABASE newbie;
\c newbie
CREATE EXTENSION citus;
SELECT citus_set_coordinator_host('10.10.2.11', 5432);
#添加worker节点
SELECT * from citus_add_node('10.10.2.12', 5432);
SELECT * from citus_add_node('10.10.2.14', 5432);
-- ... for all of them
```

查看集群节点

`````
SELECT * FROM citus_get_active_worker_nodes();
 node_name  | node_port 
------------+-----------
 10.10.2.12 |      5432
 10.10.2.14 |      5432
(2 rows)
`````

查看节点分表

```
select * from pg_dist_node;
 nodeid | groupid |  nodename  | nodeport | noderack | hasmetadata | isactive | noderole | nodecluster | metadatasynced | shouldhaveshards 
--------+---------+------------+----------+----------+-------------+----------+----------+-------------+----------------+------------------
      1 |       0 | 10.10.2.11 |     5432 | default  | t           | t        | primary  | default     | t              | f
      3 |       2 | 10.10.2.12 |     5432 | default  | t           | t        | primary  | default     | t              | t
      4 |       3 | 10.10.2.14 |     5432 | default  | t           | t        | primary  | default     | t              | t

```

# 表管理

## 表类型

- 本地表
- 参考表
- 分布表

### 本地表

与传统表使用方式一致，数据只存放在master节点

### 参考表

每个节点(master , worker)包含一份表的所有数据，对表的DML采用2pc。适用于存放业务元数据，便于与分布表联合查询使用

### 分布表

根据分布键（通常为表的指定列），将数据分布到每个worker节点中。每个worker节点包含表的部分数据内容

### 查看表信息

```
-- 包括参考表和分布表
select * from citus_tables ;

-- 包括所有类型的表及分布信息
select * from citus_shards ;

--- 查看库分布表size
SELECT logicalrelid AS name,
       pg_size_pretty(citus_table_size(logicalrelid)) AS size
  FROM pg_dist_partition where name = '$tablename';

--- 查看分布表分布在每个node上的size 
select table_name, nodename as node_name,round(sum(shard_size)*100.0/citus_table_size(table_name),2) percent, pg_size_pretty(sum(shard_size)) as table_size_node,pg_size_pretty(citus_table_size(table_name)) AS table_size from citus_shards where citus_table_type = 'distributed' group by nodename , table_name;

          table_name           | node_name  | percent | table_size_node | table_size
-------------------------------+------------+---------+-----------------+------------
mydistable | 10.10.2.12 |   32.60 | 1424 kB         | 4368 kB
mydistable | 10.10.2.14 |   60.81 | 2656 kB         | 4368 kB
(2 rows)

```

## 表管理

### 参考表创建

```
SELECT create_reference_table('tablename');
```

### 分布表创建

```istributed relations cannot have UNIQUE, EXCLUDE, or PRIMARY KEY constraints that do not include the partition column (with an equality operator if EXCLUDE)
SELECT create_distributed_table('tablename', 'column');
```

####   注意事项 

`distributed relations cannot have UNIQUE, EXCLUDE, or PRIMARY KEY constraints that do not include the partition column (with an equality operator if EXCLUDE)`

#### 亲和性

```
SELECT create_distributed_table('github_events', 'repo_id',
                                colocate_with => 'github_repo');
```

#### 更新表亲和性

```
SELECT update_distributed_table_colocation('A', colocate_with => 'B');
```

#### 分片数量

```
show citus.shard_count;
set citus.shard_count = 64;
```

#### 查看默认分布策略

````
SELECT * FROM pg_dist_rebalance_strategy;
````

#### 设置分布策略

```
SELECT citus_set_default_rebalance_strategy('by_disk_size');
```

#### 进度查看

```
SELECT * FROM get_rebalance_progress();
```

#### 删除本地数据

```
-- 在将普通表转化化为分布表或参考表后，清空本地数据，待测试
SELECT truncate_local_data_after_distributing_table('tablename')
```

### 恢复表为本地表

```
select undistribute_table('table_name')
select undistribute_table('table_name',cascade_via_foreign_keys=>true); # 危险操作，注意所有表关联关系
```



## 函数管理

### 自定义函数

```

CREATE OR REPLACE FUNCTION
  delete_campaign(company_id int, campaign_id int)
RETURNS void LANGUAGE plpgsql AS $fn$
BEGIN
  DELETE FROM campaigns
   WHERE id = $2 AND campaigns.company_id = $1;
  DELETE FROM ads
   WHERE ads.campaign_id = $2 AND ads.company_id = $1;
END;
$fn$;
```

### 自定义函数下推

```
SELECT create_distributed_function(
  'delete_campaign(int, int)', 'company_id',
  colocate_with := 'campaigns'
);
```

### 查看执行计划，查看全部的task

```
SET citus.explain_all_tasks = 1;
```

# 高级特性

## 重新分布

加入删除节点时，不停服数据迁移

```
rebalance_table_shards()  #所有
rebalance_table_shards('tabename') #一个表
```

## 租户隔离

大租户单独分配，独享worker资源

创建分配

```
-- 根据租户ID隔离的分片
-- 返回新的shard id。
SELECT isolate_tenant_to_new_shard('table_name', tenant_id);
SELECT isolate_tenant_to_new_shard('table_name', tenant_id，'CASCADE');
│ isolate_tenant_to_new_shard │
├─────────────────────────────┤
│ 102240 │
```

迁移分片

```
SELECT nodename, nodeport
  FROM citus_shards
 WHERE shardid = 102240;

--  列出可能持有该分片的可用工作节点
SELECT * FROM master_get_active_worker_nodes();

-- 将分片移动到你选择的WORK节点上
--（它也会移动任何用CASCADE选项创建的分片）。
SELECT citus_move_shard_placement(
  102240,
  'source_host', source_port,
  'dest_host', dest_port);
```

## 时序数据分表管理

```
-- 自动创建分区表
SELECT create_time_partitions(
  table_name         := 'github_events',
  partition_interval := '1 month',
  end_at             := now() + '12 months'
);
```

```
-- 查看分区表
SELECT partition
  FROM time_partitions
 WHERE parent_table = 'github_events'::regclass;
```



## 归档数据列存

```
--转化为列存
CALL alter_old_partitions_set_access_method(
  'github_columnar_events',
  '2015-01-01 06:00:00' /* older_than */,
  'columnar'
);
```

```
-- 查看表的存储方式
SELECT partition, access_method
  FROM time_partitions
 WHERE parent_table = 'github_columnar_events'::regclass;
```

# 读写分离

```
-- 加入数据库从节点
select * from citus_add_secondary_node('new-node', 12345, 'primary-node', 12345);
```



```
-- 开启读写分离
citus.use_secondary_nodes
    never: (default) All reads happen on primary nodes.
    always: Reads run against secondary nodes instead, and insert/update statements are disabled.
```

# 节点管理

## 节点查看

```
select * from pg_dist_node;
 nodeid | groupid |  nodename  | nodeport | noderack | hasmetadata | isactive | noderole | nodecluster | metadatasynced | shouldhaveshards 
--------+---------+------------+----------+----------+-------------+----------+----------+-------------+----------------+------------------
      1 |       0 | 10.10.2.11 |     5432 | default  | t           | t        | primary  | default     | t              | f
      3 |       2 | 10.10.2.12 |     5432 | default  | t           | t        | primary  | default     | t              | t
      4 |       3 | 10.10.2.14 |     5432 | default  | t           | t        | primary  | default     | t              | t

```

## 删除节点

```
-- 删除一个节点
SELECT * from citus_drain_node('10.0.0.1', 5432);
```

```
-- 删除多个节点
#在每个节点上执行
SELECT * FROM citus_set_node_property(node_hostname, node_port, 'shouldhaveshards', false);
#
SELECT * FROM rebalance_table_shards(drain_only := true);
```

## 更新节点 

```
select * from citus_update_node(123, 'new-address', 5432);
```

## 加入备用节点

```
select * from citus_add_inactive_node('new-node', 12345);
```

## 激活备用节点

```
select * from citus_activate_node('new-node', 12345);
```

# 集群健康管理

```
SELECT * FROM citus_check_cluster_node_health();
```

# 高可用管理

```
select * from citus_add_secondary_node('new-node', 12345, 'primary-node', 12345);
```

```
select * from citus_update_node(123, 'new-address', 5432);
```
