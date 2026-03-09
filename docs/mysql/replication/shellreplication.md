# MySQL Shell 管理数据库主从复制

## 概述

本文介绍如何使用MySQL Shell (mysqlsh) 来管理MySQL主从复制环境。MySQL Shell是官方推荐的现代化管理工具，其AdminAPI让复制管理变得简单而高效。

## 安装MySQL Shell

版本要求 8.0.19+

在Ubuntu系统上：

```bash
sudo apt install mysql-shell
```

在CentOS/RHEL系统上：

```bash
sudo yum install mysql-shell
```

## mysql 配置

server-id 每个节点不同

```
# my.cnf
server-id = 4010
log_bin=on
enforce_gtid_consistency=on
gtid_mode=on

log_slave_updates=on

master_info_repository=table
relay_log_info_repository=table
slave_parallel_type=LOGICAL_CLOCK
slave_parallel_workers=4
```

## 初始化主从复制架构

### 启动MySQL Shell

连接到JavaScript模式：

```bash
mysqlsh
```

然后连接到计划做为主服务器的MySQL实例：

```javascript
\connect root@master_host:3306
```

### 验证实例配置

确认要加入复制的每个实例都符合要求：

```javascript
dba.checkInstanceConfiguration("root@master_host:3306");
dba.checkInstanceConfiguration("root@slave1_host:3306");
dba.checkInstanceConfiguration("root@slave2_host:3306");
```

### 配置实例

为所有实例进行基本配置：

```javascript
dba.configureLocalInstance("root@master_host:3306");
dba.configureLocalInstance("root@slave1_host:3306");
dba.configureLocalInstance("root@slave2_host:3306");
```

### 创建复制集

连接到主服务器并创建副本集：

```javascript
var rs = dba.createReplicaSet("production_rs");
```

确认副本集创建完成：

```javascript
rs.status();
```

### 添加从节点

将从服务器加入到复制集中：

```javascript
// 添加第一个从节点
rs.addInstance("root@slave1_host:3306", {
  recoveryMethod: "clone",
});

// 添加第二个从节点
rs.addInstance("root@slave2_host:3306", {
  recoveryMethod: "clone",
});
```

查看完整的复制集状态：

```javascript
rs.status();
```

## 配置 MySQL Router 路由

### 初始化Router配置

MySQL Router提供连接路由功能，可根据读写类型自动转发请求到合适的MySQL实例。

首先使用管理员账户连接到当前主节点初始化Router配置：

```bash
mysqlrouter --bootstrap root@master_host:3306 --user=mysqlrouter
```

按提示输入主节点的数据库管理员密码。该命令会在MySQL主节点上创建必要账户，并自动生成配置文件。

### 启动Router服务

使用以下任一命令启动服务：

```bash
# systemd方式（推荐）
sudo systemctl start mysqlrouter

# 传统服务方式
sudo /etc/init.d/mysqlrouter restart

# 或者直接运行
mysqlrouter -c /etc/mysqlrouter/mysqlrouter.conf
```

Router启动后，会监听以下端口：

- 6446/64460: 写入端口，所有写操作路由到主节点
- 6447/64470: 读取端口，读操作分散到各个从节点

### 验证Router路由

通过MySQL Shell连接不同端口验证路由器的负载均衡功能：

```javascript
// 连接到写入端口，确保请求被路由到主节点
var writeSession = mysql.getSession({
  host: "routerip_host",
  port: 6446,
  user: "user",
  password: "password",
});
writeSession.runSql("SELECT @@hostname, @@port, @@read_only");

// 连接到读取端口，请求被路由到一个从节点
var readSession = mysql.getSession({
  host: "routerip_host",
  port: 6447,
  user: "user",
  password: "password",
});
readSession.runSql("SELECT @@hostname, @@port, @@read_only");
```

```
// 连接到其中一个节点检查Router状态
\connect root@master_host:3306
var rs = dba.getReplicaSet();
rs.listRouters();
```

通过这种方式，应用只需要连接固定的Router端口（6446用于写入，6447用于读取），Router会自动将请求路由到合适的数据库节点。

## 管理操作

### 查看从节点状态

```javascript
var replicaset = dba.getReplicaSet();
replicaset.status();
```

### 切换主节点

在维护期间切换主节点：

```javascript
rs.setPrimaryInstance("root@slave1_host:3306");
```

## 故障处理

### 恢复故障节点

重新加入失败的从节点：

```javascript
rs.rejoinInstance("root@slave1_host:3306");
```

若上述操作失败，需要重新添加节点：

```javascript
rs.removeInstance("root@slave1_host:3306");
rs.addInstance("root@slave1_host:3306", {
  recoveryMethod: "clone",
});
```

## 常用命令总结

```javascript
// 获取当前复制集引用
var rs = dba.getReplicaSet();

// 查看状态
rs.status();
rs.status({ extended: 1 }); // 详细状态

// 添加节点
rs.addInstance("user@host:port", { recoveryMethod: "clone" });

// 移除节点
rs.removeInstance("user@host:port");

// 设置主节点
rs.setPrimaryInstance("user@host:port");

// 强制重连故障节点
rs.rejoinInstance("user@host:port");
```

## 故障排除

### 常见问题1：网络不通导致连接失败

- 检查防火墙配置，确保3306等必要端口开放
- 验证各实例的 bind-address 配置允许外部连接

### 常见问题2：克隆失败

- 确认克隆源和目标有足够的磁盘空间
- 检查网络带宽和稳定性

### 常见问题3：权限不足

- 验证用户具有REPLICATION CLIENT, REPLICATION SLAVE权限
- 检查克隆PLUGIN (CLONE_ADMIN) 权限
