# 网络穿透

## 背景

一个类似于花生壳的服务。将一个内网服务暴露在公网中提供访问。

## 前提条件

-  拥有公网IP的服务器。比如 xx云服务器

## 准备 

下载安装包 
```
wget https://github.com/fatedier/frp/releases/download/v0.38.0/frp_0.38.0_linux_amd64.tar.gz
```

解压后

```
.
├── frpc
├── frpc_full.ini
├── frpc.ini
├── frps
├── frps_full.ini
├── frps.ini
├── LICENSE
└── systemd
    ├── frpc.service
    ├── frpc@.service
    ├── frps.service
    └── frps@.service
```

分为客户端和服务端

客户端： 内网服务器

服务端： 拥有公网ip的服务器

## 简单配置

#### 服务端

```
cp frps /usr/bin/
cp frps.service /lib/systemd/system/frps.service
```

cat /etc/frp/frps.ini
```
[common]
# 用于客户端连接的端口
bind_port = 6000 
# 与客户端的保持一致。验证
token = 'abcdefghijklmn'
authentication_method = token
# web 服务穿透是使用
vhost_http_port = 8080
```

#### 客户端

```
cp frpc /usr/bin/
cp frpc.service /lib/systemd/system/frpc.service
```

cat /etc/frp/frpc.ini
```
[common]
# 服务端IP
server_addr = xxxxx 
# 服务端口，服务端保持一致
server_port = 6000
# 与服务端的保持一致。验证
authentication_method = token
token = 'abcdefghijklmn'

[ssh]
type = tcp
local_ip = 127.0.0.1
#客户端本机ssh端口
local_port = 22
#登陆访问IP的端口
remote_port = 2222
use_encryption = true
use_compression = true

[web]
type = http
local_ip = 127.0.0.1
#客户端服务端口
local_port = 8000
#dns
custom_domains = xxx.zhangeamon.top
# 如需要验证
#http_user = abc
#http_pwd = abc
```

#### 测试

ssh
```
ssh user@公网IP --port 2222
```

web , 注意端口号
```
curl http://xxx.zhangeamon.top：8080
```
