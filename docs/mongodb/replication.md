# MongoDB 副本集

## 概述

MongoDB 复制集 (Replica Set) 是一组维护相同数据集合的 mongod 实例。副本集提供了冗余和高可用性，是生产环境中推荐的数据存储方式。

副本集（Replica Set）的设计初衷是“数据冗余和高可用”，而不是“读写分离负载均衡”

## 复制集架构

https://www.mongodb.com/zh-cn/docs/v8.0/tutorial/deploy-replica-set/

| 成员 | 主机名               |
| ---- | -------------------- |
| 0    | mongodb0.example.net |
| 1    | mongodb1.example.net |
| 2    | mongodb2.example.net |

### 节点角色

- **Primary（主节点）**：接收所有写操作
- **Secondary（从节点）**：从 Primary 节点复制数据
- **Arbiter（仲裁节点）**：参与选举但不保存数据

  一个副本集最多可以有 50 个节点，但只能有 7 个具有投票权的节点。

## 创建复制集

### 配置 DNS

避免因 IP 变化导致复制集配置失效，使用 DNS 名称或主机名配置复制集成员。

### 安装实例

参考 [安装 MongoDB](../install)

### 配置文件准备

每个节点都需要相应配置：

```yaml
# mongod.conf
net:
  port: 27017
  bindIp: 0.0.0.0
replication:
  replSetName: rs0
security:
  authorization: enabled
  keyFile: /etc/mongodb/conf/keyfile
  clusterAuthMode: keyFile
```

keyfile 为随机字符串。用于集群内通信验证,同一副本集保持相同 (openssl rand -base64 21 > keyfile)

```
sudo chmod 400  /etc/mongodb/conf/keyfile
sudo chown mongodb:mongodb /etc/mongodb/conf/keyfile
```

`配置后重启mongodb实例`

### 初始化复制集

```bash
# 连接到其中一个节点
mongo --port 27017

# 初始化复制集
rs.initiate()
```

### 添加成员

```bash
# 添加复制集成员
rs.add("mongodb1.example.net:27017")
rs.add("mongodb2.example.net:27017")

# 或添加仲裁节点
rs.addArb("arbiter-hostname:27017")
```

加入集群后将自动复制源主机的数据及账户

### 删除成员

```
rs.remove("mongod3.example.net")
```

## 成员配置

### 配置模板

```javascript
cfg = rs.conf();
cfg.members[0].priority = 2; // 设置优先级
cfg.members[1].priority = 1; // 设置优先级
cfg.members[2].priority = 0; // 非选举成员
// 心跳
cfg.settings.heartbeatTimeoutSecs = 10;
// 选举超时
cfg.settings.electionTimeoutMillis = 10000;
rs.reconfig(cfg);
```

### 成员属性

- `priority`: 0-1000，影响选举，0 表示不可选举
- `votes`: 0 或 1，影响投票权 没有投票权的成员的 votes 和 priority 都等于 0
- `hidden`: true 为隐藏节点，对客户端不可见 同时priority=0
- `slaveDelay`: 延迟复制（秒）

## 管理操作

### 查看复制集状态

```bash
# 查看复制集状态
rs.status()

# 查看复制集配置
rs.conf()

# 查看复制延迟
db.printSecondaryReplicationInfo
```

### oplog

oplog 保留策略，默认范围 990M - 50G。或 5% 的物理存储空间

### 故障转移

MongoDB 会在 Primary 节点失效时自动进行故障转移：

- 至少需要两个节点能相互通信
- 选举过程通常在 10-30 秒内完成
- 旧的 Primary 节点在恢复后会成为 Secondary 节点

## 读写关注级别

### 写关注 (Write Concern)

```javascript
// 默认写入，返回acknowledged
db.collection.insertOne({ x: 1 }, { writeConcern: { w: 1 } });

// 等待多数节点确认
db.collection.insertOne({ x: 1 }, { writeConcern: { w: "majority" } });

// 设置超时时间
db.collection.insertOne(
  { x: 1 },
  { writeConcern: { w: "majority", wtimeout: 5000 } },
);
```

[关于写关注](./write_concern.md)

### 读关注 (Read Concern)

数据的一致性/隔离级别是什么？

```javascript
// 最近数据
db.collection.find().readConcern("local");

// 已提交数据
db.collection.find().readConcern("available");

// 线性一致读
db.collection.find().readConcern("linearizable");
```

## 读偏好

从哪个节点读取数据

```

mongodb://myDatabaseUser:D1fficultP%40ssw0rd@db0.example.com,db1.example.com,db2.example.com/?replicaSet=myRepl&readConcernLevel=majority

```

## 复制延迟

### 监控延迟

```bash
# 查看延迟
db.printSlaveReplicationInfo()

# 获取延迟统计
db.adminCommand("replSetGetStatus")
```

### 优化复制

- 启用 WiredTiger 存储引擎
- 调整 oplog 大小
- 避免大体积更新

## 运维最佳实践

### 监控指标

- 复制延迟
- oplog 使用情况
- 节点健康状态
- 写操作性能

### 部署策略

- 将复制集节点部署在不同的可用区
- 使用专用网络进行复制通信
- 正确设置节点优先级以确保合适的节点成为 Primary
- 定期测试故障转移过程

### 重置集群

当集群故障，主节点不可用。多数节点故障的时候。强制重置集群

```
// 1. 获取当前配置
cfg = rs.conf()

// 2. 修改配置，移除 node3（id:0）
// 查看当前所有成员
cfg.members

// 3. 移除不可达节点
cfg.members = [
  {
    _id: 1,
    host: "node1:27017",
    priority: 1,
    votes: 1
  }
]

// 4. 强制重配置
rs.reconfig(cfg, {force: true})
```

# 安装 mgeneratejs

npm install -g mgeneratejs

# 创建模板文件 template.json

echo '{
"id": "$inc",
  "name": "$name",
"email": "$email",
  "age": "$age",
"timestamp": "$date",
  "data": {
    "field1": "$lorem",
"field2": "$bool",
    "field3": "$integer"
}
}' > template.json

# 生成数据并导入 (生成1M文档，约1GB)

mgeneratejs template.json -n 1000000 | mongoimport --db testdb --collection testdata
