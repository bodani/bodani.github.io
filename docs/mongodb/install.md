# MongoDB 安装

## 简介

MongoDB 是一个基于分布式文件存储的开源数据库系统，属于 NoSQL 数据库，使用 JSON 风格的数据结构。

## 安装方式

[官网](https://www.mongodb.com/zh-cn/docs/v8.0/tutorial/install-mongodb-on-ubuntu)

### Ubuntu/Debian

```bash
#
sudo apt-get install gnupg curl
# 导入公钥
curl -fsSL https://www.mongodb.org/static/pgp/server-8.0.asc | \
   sudo gpg -o /usr/share/keyrings/mongodb-server-8.0.gpg \
   --dearmor

# 添加MongoDB APT源
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] https://repo.mongodb.org/apt/ubuntu noble/mongodb-org/8.0 multiverse" | \
   sudo tee /etc/apt/sources.list.d/mongodb-org-8.0.list

# 更新包列表并安装MongoDB
sudo apt-get update
# 安装指定版本
sudo apt-get install -y \
   mongodb-org=8.0.12 \
   mongodb-org-database=8.0.12 \
   mongodb-org-server=8.0.12 \
   mongodb-mongosh \
   mongodb-org-shell=8.0.12 \
   mongodb-org-mongos=8.0.12 \
   mongodb-org-tools=8.0.12 \
   mongodb-org-database-tools-extra=8.0.12
# 锁定版本, 避免 apt-get  升级
echo "mongodb-org hold" | sudo dpkg --set-selections
echo "mongodb-org-database hold" | sudo dpkg --set-selections
echo "mongodb-org-server hold" | sudo dpkg --set-selections
echo "mongodb-mongosh hold" | sudo dpkg --set-selections
echo "mongodb-org-mongos hold" | sudo dpkg --set-selections
echo "mongodb-org-cryptd hold" | sudo dpkg --set-selections
echo "mongodb-org-tools hold" | sudo dpkg --set-selections
echo "mongodb-org-database-tools-extra hold" | sudo dpkg --set-selections
```

数据目录 /var/lib/mongodb

日志目录 /var/log/mongodb

## 配置文件

/etc/mongod.conf

```
# network interfaces
net:
  # 监听端口
  port: 27017
  # 绑定所有IP
  bindIp: 0.0.0.0
```

## 验证安装

```bash
# 启动MongoDB服务
sudo systemctl start mongod
# 查看状态
sudo systemctl status mongod
# 设置开机自启动
sudo systemctl enable mongod

# 连接MongoDB
mongosh
```

## 生产配置

### 启用 TLS

创建自签名证书

```
# Creating self-signed CA cert and SAN cert for localhost
# aka mdbinstance01.mydevelopment.net
#=====================================================================================
#1. 创建根 CA 的私钥和自签名证书
openssl req -x509 -nodes -sha256 -days 3650 -newkey rsa:4096 \
 -keyout rootCA.key -out rootCA.crt -subj="/CN=ca.mydevelopment.net"
#2. 为服务器生成私钥和证书签名请求 (CSR)
openssl req -newkey rsa:4096 -keyout server.key -nodes \
 -out domain.csr -subj "/CN=server.mydevelopment.net"
#3. 使用根 CA 签名服务器证书，并添加 SAN（主题备用名称)
openssl req -x509 -nodes -CA rootCA.crt -CAkey rootCA.key -in domain.csr \
 -out mdbinstance01.mydevelopment.net.crt -days 3650 -nodes \
 -subj '/CN=<mdbinstance_mydevelopment_net>' -extensions san -config <( \
   echo '[req]'; \
   echo 'distinguished_name=req'; \
   echo '[san]'; \
   echo 'subjectAltName=DNS:localhost,DNS:mdbinstance01.mydevelopment.net')

cat rootCA.key rootCA.crt >rootCAcombined.pem
cat server.key mdbinstance01.mydevelopment.net.crt >serverCert.pem
```

配置

```
# network interfaces
net:
  port: 27017
  bindIp: 0.0.0.0  # Binds to all network interfaces - use only in secure networks
  tls:
    mode: requireTLS  # Forces all connections to use TLS
    certificateKeyFile: /path/to/serverCert.pem  # Server certificate with private key
    CAFile: /path/to/rootCAcombined.pem  # CA certificate with private key
```

### SCRAM 身份验证 (用户密码)

默认没有任何用户

#### 登录到实例。并创建超级用户

mongosh --port 27017

```
use admin
db.createUser(
  {
    user: "root",
    pwd: passwordPrompt(), // or cleartext password
    roles: [
      { role: "root", db: "admin" },
    ]
  }
)

```

#### 配置文件开启 SCRAM 认证

配置后需要重启，开始认证

```
security:
    authorization: enabled
```

也可以先配置开启认证后在启动服务。然后在没有任何用户的情况下会利用`本地主机例外`允许创建第一个用户。

#### 验证连接

```
mongosh --port 27017  --authenticationDatabase \
    "admin" -u "myUserAdmin" -p
```

#### 初始监控用户管理

```
db.createUser(
  {
    user: "user_exporter",
    pwd: passwordPrompt(), // or cleartext password
    roles: [
      { role: "clusterMonitor", db: "admin" },
      { role: "read", db: "local" }
    ]
  }
)

```
连接 
```
mongosh "mongodb://username:password@host1:27017,host2:27017,host3:27017/admin?replicaSet=rs0&authSource=admin"
```

如果有DNS，需要配合配置对应的DNS。