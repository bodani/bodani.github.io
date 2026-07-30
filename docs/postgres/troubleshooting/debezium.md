# 利用debezium 实现数据变更捕获

整个实现以功能演示为目标，便于流程的梳理和理解。不适合正式生成环境使用。

## debezium的几种使用方式

- 单独部署 下游数据传输到cloud，官方目前不推荐
- 与kafka联合使用 下游数据传输到kafka
- 嵌入式 例如Flink使用的debezium作为数据的source connetor模块使用，将数据接入到Flink中

这里使用与kafka联合使用的方式，将源端数据库中的数据及变更导入到kafka中，来提供下游使用。

## mysql cdc

源端数据库为mysql， 利用Debezium 捕获mysql数据及变化，并实时导入到kafka中。

### Topology

````
                   +-------------+
                   |             |
                   |    MySQL    |
                   |             |
                   +------+------+
                          |
                          |
                          |
          +---------------v------------------+
          |                                  |
          |           Kafka Connect          |
          |  (Debezium, JDBC connectors)     |
          |                                  |
          +---------------+------------------+
````

### 启动服务

```shell
-- 启动zk
docker run -it --rm --name zookeeper -p 2181:2181 -p 2888:2888 -p 3888:3888 quay.io/debezium/zookeeper:1.9

-- 启动kafka
docker run -it --rm --name kafka -p 9092:9092 --link zookeeper:zookeeper quay.io/debezium/kafka:1.9

-- 启动mysql
docker run -it --rm --name mysql -p 3306:3306 -e MYSQL_ROOT_PASSWORD=debezium -e MYSQL_USER=mysqluser -e MYSQL_PASSWORD=mysqlpw quay.io/debezium/example-mysql:1.9
```

### 访问源数据库

```sql
-- 利用mysql client 登录mysql数据库
docker run -it --rm --name mysqlterm --link mysql --rm mysql:8.0 sh -c 'exec mysql -h"$MYSQL_PORT_3306_TCP_ADDR" -P"$MYSQL_PORT_3306_TCP_PORT" -uroot -p"$MYSQL_ENV_MYSQL_ROOT_PASSWORD"'
mysql> use inventory;
mysql> show tables;
+---------------------+
| Tables_in_inventory |
+---------------------+
| addresses           |
| customers           |
| geom                |
| orders              |
| products            |
| products_on_hand    |
+---------------------+
mysql> SELECT * FROM customers;
+------+------------+-----------+-----------------------+
| id   | first_name | last_name | email                 |
+------+------------+-----------+-----------------------+
| 1001 | Sally      | Thomas    | sally.thomas@acme.com |
| 1002 | George     | Bailey    | gbailey@foobar.com    |
| 1003 | Edward     | Walker    | ed@walker.com         |
| 1004 | Anne       | Kretchmar | annek@noanswer.org    |
+------+------------+-----------+-----------------------+
4 rows in set (0.00 sec)
```

###  启动kafka connect

```shell
启动
docker run -it --rm --name connect -p 8083:8083 -e GROUP_ID=1 -e CONFIG_STORAGE_TOPIC=my_connect_configs -e OFFSET_STORAGE_TOPIC=my_connect_offsets -e STATUS_STORAGE_TOPIC=my_connect_statuses --link zookeeper:zookeeper --link kafka:kafka --link mysql:mysql quay.io/debezium/connect:1.9
验证
curl -H "Accept:application/json" localhost:8083/
{"version":"3.2.0","commit":"cb8625948210849f"} 
```

### 注册 MySQL source connector

```shell
-- 注册
$ curl -i -X POST -H "Accept:application/json" -H "Content-Type:application/json" localhost:8083/connectors/ -d '{ "name": "inventory-connector", "config": { "connector.class": "io.debezium.connector.mysql.MySqlConnector", "tasks.max": "1", "database.hostname": "mysql", "database.port": "3306", "database.user": "debezium", "database.password": "dbz", "database.server.id": "184054", "database.server.name": "dbserver1", "database.include.list": "inventory", "database.history.kafka.bootstrap.servers": "kafka:9092", "database.history.kafka.topic": "dbhistory.inventory" } }'

-- 查看注册的connector 情况
$ curl -H "Accept:application/json" localhost:8083/connectors/
$ curl -H  "Content-Type:application/json" http://localhost:8083/connectors/inventory-connector | jq
$ curl -H  "Content-Type:application/json" http://localhost:8083/connectors/inventory-connector/status | jq
```

### 观察 change events

		这里可以对mysql数据进行dml操作，实时观察数据变更捕获情况

```shell
$ docker run -it --rm --name watcher --link zookeeper:zookeeper --link kafka:kafka quay.io/debezium/kafka:1.9 watch-topic -a -k dbserver1.inventory.customers
```

## postgres cdc

源端数据库为postgres， 利用Debezium 捕获postgres数据及变化，并实时导入到kafka中。

### Topology

````
                   +-------------+
                   |             |
                   |    MySQL    |
                   |             |
                   +------+------+
                          |
                          |
                          |
          +---------------v------------------+
          |                                  |
          |           Kafka Connect          |
          |  (Debezium, JDBC connectors)     |
          |                                  |
          +---------------+------------------+
````

### 配置文件准备

这里利用docker-compose 一键启动所有服务

- docker-compost-postgres.yaml
- register-postgres.json 

docker-compost-postgres.yaml

```
version: '2'
services:
  zookeeper:
    image: quay.io/debezium/zookeeper:${DEBEZIUM_VERSION}
    ports:
     - 2181:2181
     - 2888:2888
     - 3888:3888
  kafka:
    image: quay.io/debezium/kafka:${DEBEZIUM_VERSION}
    ports:
     - 9092:9092
    links:
     - zookeeper
    environment:
     - ZOOKEEPER_CONNECT=zookeeper:2181
  postgres:
    image: quay.io/debezium/example-postgres:${DEBEZIUM_VERSION}
    ports:
     - 5432:5432
    environment:
     - POSTGRES_USER=postgres
     - POSTGRES_PASSWORD=postgres
  connect:
    image: quay.io/debezium/connect:${DEBEZIUM_VERSION}
    ports:
     - 8083:8083
    links:
     - kafka
#     - postgres
    environment:
     - BOOTSTRAP_SERVERS=kafka:9092
     - GROUP_ID=1
     - CONFIG_STORAGE_TOPIC=my_connect_configs
     - OFFSET_STORAGE_TOPIC=my_connect_offsets
     - STATUS_STORAGE_TOPIC=my_connect_statuses
# For testing newer connector versions, unpack the connector archive into this
# directory and uncomment the lines below
#    volumes:
#     - ./debezium-connector-postgres:/kafka/connect/debezium-connector-postgres
```
      register-postgres.json

```
{
    "name": "inventory-connector",
    "config": {
        "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
        "tasks.max": "1",
        "database.hostname": "postgres",
        "database.port": "5432",
        "database.user": "postgres",
        "database.password": "postgres",
        "database.dbname" : "postgres",
        "database.server.name": "dbserver1",
        "schema.include.list": "inventory"
    }
}
```

### 开始测试

```
export DEBEZIUM_VERSION=1.9
# 一键启动所有服务
docker-compose -f docker-compose-postgres.yaml up

# Start Postgres connector
curl -i -X POST -H "Accept:application/json" -H  "Content-Type:application/json" http://localhost:8083/connectors/ -d @register-postgres.json

# Consume messages from a Debezium topic
docker-compose -f docker-compose-postgres.yaml exec kafka /kafka/bin/kafka-console-consumer.sh \
    --bootstrap-server kafka:9092 \
    --from-beginning \
    --property print.key=true \
    --topic dbserver1.inventory.customers

# Modify records in the database via Postgres client
docker-compose -f docker-compose-postgres.yaml exec postgres env PGOPTIONS="--search_path=inventory" bash -c 'psql -U $POSTGRES_USER postgres'

# Shut down the cluster
docker-compose -f docker-compose-postgres.yaml down

```

##  postgres sourcer connetor

区别与官方提供的pg docker 镜像

	官方中的pg镜像逻辑解码使用的是decoderbufs，wal2jon。对于pg版本10+ 更推荐使用 logical 。并利用pgoutput进行解析 

### 配置管理

pg

```
wal_level = logical
```

      拥有repication 权限访问数据库的用户，这里使用超级用户postgres	

docker-compose-postgres.yaml

加入kakfa-ui 访问IP:8080 

   ```
version: '2'
services:
  zookeeper:
    image: quay.io/debezium/zookeeper:${DEBEZIUM_VERSION}
    ports:
     - 2181:2181
     - 2888:2888
     - 3888:3888
  kafka:
    image: quay.io/debezium/kafka:${DEBEZIUM_VERSION}
    ports:
     - 9092:9092
    links:
     - zookeeper
    environment:
     - ZOOKEEPER_CONNECT=zookeeper:2181
  kafka-ui:
    image: provectuslabs/kafka-ui:latest 
    ports:
     - 8080:8080
    links:
     - kafka:kakfa
    environment:
     - KAFKA_CLUSTERS_0_NAME=mykafka
     - KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS=kafka:9092
  connect:
    image: quay.io/debezium/connect:${DEBEZIUM_VERSION}
    ports:
     - 8083:8083
    links:
     - kafka
    environment:
     - BOOTSTRAP_SERVERS=kafka:9092
     - GROUP_ID=1
     - CONFIG_STORAGE_TOPIC=my_connect_configs
     - OFFSET_STORAGE_TOPIC=my_connect_offsets
     - STATUS_STORAGE_TOPIC=my_connect_statuses
# For testing newer connector versions, unpack the connector archive into this
# directory and uncomment the lines below
#    volumes:
#     - ./debezium-connector-postgres:/kafka/connect/debezium-connector-postgres
   ```

register-postgres.json

```
{
    "name": "inventory-connector",
    "config": {
	    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
	    "database.hostname": "postgres",
	    "database.port": "5432",
	    "database.user": "postgres",
	    "database.password": "postgres",
	    "database.dbname": "postgres",
	    "database.server.name": "debezium",
	    "slot.name": "inventory_slot",
	    "table.include.list": "inventory.orders,inventory.products",
	    "publication.name": "dbz_inventory_connector",
	    "publication.autocreate.mode": "all_tables",
	    "plugin.name": "pgoutput",	
            "topic.creation.default.replication.factor": 3,
            "topic.creation.default.partitions": 10,
            "topic.creation.default.cleanup.policy": "delete",
            "topic.creation.default.compression.type": "lz4"
    }
}
```

配置文件说明

https://debezium.io/documentation/reference/1.9/connectors/postgresql.html#postgresql-required-configuration-properties

| 字段名称                    | 描述                                                         |
| --------------------------- | ------------------------------------------------------------ |
| connector.class             | connector的实现类，本文使用的是io.debezium.connector.postgresql.PostgresConnector，因为我们的数据库是PostgreSQL |
| database.hostname           | 数据库服务的IP或域名                                         |
| database.port               | 数据库服务的端口                                             |
| database.user               | 连接数据库的用户                                             |
| database.password           | 连接数据库的密码                                             |
| database.dbname             | 数据库名                                                     |
| database.server.name        | 每个被监控的表在Kafka都会对应一个topic，topic的命名规范是`<database.server.name>.<schema>.<table>` |
| slot.name                   | PostgreSQL的复制槽(Replication Slot)名称                     |
| table.include.list          | 如果设置了table.include.list，即在该list中的表才会被Debezium监控 |
| plugin.name                 | PostgreSQL服务端安装的解码插件名称，可以是decoderbufs, wal2json, wal2json_rds, wal2json_streaming, wal2json_rds_streaming 和  pgoutput。如果不指定该值，则默认使用decoderbufs。   本例子中使用了pgoutput，因为它是PostgreSQL 10+自带的解码器，而其他解码器都必须在PostgreSQL服务器安装插件。 |
| publication.name            | PostgreSQL端的WAL发布(publication)名称，每个Connector都应该在PostgreSQL有自己对应的publication，如果不指定该参数，那么publication的名称为dbz_publication |
| publication.autocreate.mode | 该值在plugin.name设置为pgoutput才会有效。有以下三个值：  **all_tables** - debezium会检查publication是否存在，如果publication不存在，connector则使用脚本CREATE  PUBLICATION <publication_name> FOR ALL  TABLES创建publication，即该发布者会监控所有表的变更情况。  **disabled** - connector不会检查有无publication存在，如果publication不存在，则在创建connector会报错.  **filtered** - 与all_tables不同的是，debezium会根据connector的配置中的table.include.list生成生成创建publication的脚本： `CREATE PUBLICATION <publication_name> FOR TABLE <tbl1, tbl2, tbl3>`。例如，本例子中，“table.include.list"值为"inventory.orders,inventory.products”，则publication只会监控这两个表的变更情况。 |

### 开始测试

```
export DEBEZIUM_VERSION=1.9
docker-compose -f docker-compose-postgres.yaml up

# Start Postgres connector
curl -i -X POST -H "Accept:application/json" -H  "Content-Type:application/json" http://localhost:8083/connectors/ -d @register-postgres.json

# Consume messages from a Debezium topic
docker-compose -f docker-compose-postgres.yaml exec kafka /kafka/bin/kafka-console-consumer.sh \
    --bootstrap-server kafka:9092 \
    --from-beginning \
    --property print.key=true \
    --topic dbserver1.inventory.orders
```

### 数据库验证

```
-- 数据库中执行
select * from pg_replication_slots where slot_name = 'inventory_slot';
   slot_name    |  plugin  | slot_type | datoid | database | temporary | active | active_pid | xmin | catalog_xmin | restart_lsn | confirmed_flush_lsn | wal_status | safe_wal_size | two_phase 
----------------+----------+-----------+--------+----------+-----------+--------+------------+------+--------------+-------------+---------------------+------------+---------------+-----------
 inventory_slot | pgoutput | logical   |  14486 | postgres | f         | t      |       3798 |      |          790 | 0/E7AAE90   | 0/E7AAEC8           | reserved   |               | f
(1 row)

select * from pg_publication;
  oid  |         pubname         | pubowner | puballtables | pubinsert | pubupdate | pubdelete | pubtruncate | pubviaroot 
-------+-------------------------+----------+--------------+-----------+-----------+-----------+-------------+------------
 49187 | dbz_inventory_connector |       10 | f            | t         | t         | t         | t           | f
(1 row)

```

## postgres sinker connetor 

### Topology

````
                   +-------------+
                   |             |
                   |   Postgres  |
                   |             |
                   +------+------+
                          |
                          |
                          |
          +---------------v------------------+
          |                                  |
          |           Kafka Connect          |
          |  (Debezium, JDBC connectors)     |
          |                                  |
          +---------------+------------------+
                          |
                          |
                          |
                   +-------------+
                   |             |
                   |   Postgres  |
                   |    citus    |
                   +------+------+

````

### docker  citus 

```
# run PostgreSQL with Citus on port 5500
docker run -d --name citus -p 5500:5432 -e POSTGRES_PASSWORD=mypassword citusdata/citus

# connect using psql within the Docker container
docker exec -it citus psql -U postgres

# set user postgres password 111111
alter user postgres with encrypted password '111111';

# or, connect using local psql
psql -U postgres -d postgres -h localhost -p 5500
```


plugin 下载地址，下载后解压到connetor 文件目录下并重新启动kafka connetor

https://www.confluent.io/hub/

https://d1i4a15mxbxib1.cloudfront.net/api/plugins/confluentinc/kafka-connect-jdbc/versions/10.5.1/confluentinc-kafka-connect-jdbc-10.5.1.zip

### 单张表 

####        配置 sink-postgres.json  

```
{
    "name": "test-jdbc-sink",
    "config": {
        "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
        "tasks.max": "1",
        "connection.url": "jdbc:postgresql://10.10.2.13:5432/test?user=postgres&password=111",
        "connection.user":"postgres",
	    "connection.password":"1111",
        "topics":"debezium.public.tablename",
        "dialect.name":"PostgreSqlDatabaseDialect",
        "table.name.format": "public.tablename",
        "auto.create":"true",
        "auto.evolve":"true",
        "insert.mode":"upsert",
     	"transforms": "unwrap",
        "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
        "transforms.unwrap.drop.tombstones": "false",
        "pk.fields":"id",
        "pk.mode":"record_key",
        "delete.enabled" : true
    }
}
```

说明:

```
name : connector 名称
connector.xxx : sink 数据库连接信息
topics : kafka中的topic
dialect.name: 方言
table.name.format : sink 端与topic 对应的表名称。 表名默认为topic
auto.create : 是否自动建表
insert.mode : insert upsert update
delete.enabled： 默认false 不支持删除和更新
pk.fields ： 主键 
pk.mode ： 主键类型
```

更多选项请参考 https://docs.confluent.io/kafka-connect-jdbc/current/sink-connector/sink_config_options.html

#### 注册 sink

```
curl -i -X POST -H "Accept:application/json" -H  "Content-Type:application/json" http://localhost:8083/connectors/ -d @sink-postgres.json
```

### 多表

		默认情况table.name.format 的值为 topics，

        topics的名称为 source connection 中定义的database.server.name+schema+tablename

       这样就会对source connection  在定义时有所要求。即下游的dbname 与 database.server.name 必须保持一致

       否则在创建sink connection 时将会出现如下错误

       `ERROR:  cross-database references are not implemented `

   通过如下方式解除这种非必要的绑定

    自定义topics、  table.name.format 。映射源表与目标表之间的对应关系。好处是非常的灵活，弊端每个表之间的关系都需要定义。

如果是源表与目标表名称完全一致或存在某种规律，比方加个前缀等。可通过如下方法批量处理、非常适合将数据库从一个库导到另一个库中的场景。

source connetor 端不需要修改    、只需要在 sink connetor 端做如下定义。截取topic的前缀

####      配置 sink-postgres-alltables.json 

```json
{
    "name": "test-jdbc-sink-alltables",
    "config": {
        "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
        "tasks.max": "1",
        "connection.url": "jdbc:postgresql://10.10.2.13:5432/test?user=postgres&password=111",
        "connection.user":"postgres",
	"connection.password":"1111",
        "topics.regex": "dbserver1.public(.*)",
        "transforms": "dropPrefix,unwrap",
        "transforms.dropPrefix.type":"org.apache.kafka.connect.transforms.RegexRouter",
        "transforms.dropPrefix.regex":"dbserver1.public(.*)",
        "transforms.dropPrefix.replacement":"$1",
        "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
        "transforms.unwrap.drop.tombstones": "false",
        "dialect.name":"PostgreSqlDatabaseDialect",
        "auto.create":"true",
        "insert.mode":"upsert",
        "pk.mode":"record_key",
        "delete.enabled" : "true"
    }
}
```

## Kafka Connect REST API

为了方便查看json 建议安装jq 

``` yum install epel-release jq -y ```

 官方文档

https://kafka.apache.org/documentation.html#connect_rest

### 获取 Connect 集群的基本信息

```sh
curl -s -X GET localhost:8083/ | jq
```

### 列出 Kafka Connect Worker 上安装的插件

```sh
# curl -s -X GET localhost:8083/connector-plugins | jq
```

### 创建一个连接器

```sh
curl -i -X POST -H "Accept:application/json" -H "Content-Type:application/json" 192.168.0.40:8083/connectors/ -d @inventory-connector.json
```

### 获取所有现有的连接器名称

```sh
# curl -s -X GET localhost:8083/connectors/ | jq
```

### 获取连接器的配置信息

```sh
# curl -s -X GET localhost:8083/connectors/inventory-connector | jq
```

### 获取连接器的状态信息

```sh
# curl -s -X GET localhost:8083/connectors/inventory-connector/status | jq
```

### 获取当前为连接器运行的任务列表

```sh
# curl -s -X GET localhost:8083/connectors/inventory-connector/tasks | jq
```

### 获取任务的当前状态

```sh
# curl -s -X GET localhost:8083/connectors/inventory-connector/tasks/0/status | jq
```

### 获取连接器使用的主题(topics)列表

```sh
# curl -s -X GET localhost:8083/connectors/oracle-scott-connector/topics | jq
```

### 清空连接器的活动主题(topics)列表

```
# curl -s -X PUT localhost:8083/connectors/oracle-scott-connector/topics/reset
```

### 暂停连接器任务

```
# curl -s -X PUT localhost:8083/connectors/inventory-connector/pause
```

### 恢复连接器任务

```
# curl -s -X PUT localhost:8083/connectors/inventory-connector/resume
```

### 删除连接器

```
# curl -s -X DELETE localhost:8083/connectors/inventory-connector
```

### 更新连接器

```
# curl -i -X PUT -H "Accept:application/json" -H "Content-Type:application/json" localhost:8083/connectors/inventory-connector/config -d @inventory-connector.json
```

### 重启连接器和任务(tasks)

- 语法

```
POST /connectors/{name}/restart?includeTasks=<true|false>&onlyFailed=<true|false>
# "includeTasks=true": 重新启动连接器实例和任务实例
# "includeTasks=false"(默认): 仅重新启动连接器实例
# "onlyFailed=true": 仅重新启动具有 FAILED 状态的实例
# "onlyFailed=false"(默认): 重新所有实例
```

- 示例

```
# curl -s -X POST localhost:8083/connectors/inventory-connector/restart
```

- 默认只重新启动连接器并不会重新启动其所有任务。因此，您也可以重新启动失败的单个任务，然后再次获取其状态：

```
# curl -s -X POST localhost:8083/connectors/inventory-connector/tasks/0/restart
# curl -s -X GET localhost:8083/connectors/inventory-connector/tasks/0/status | jq
```


