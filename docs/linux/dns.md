# DNS 泛域名应用 (nip.io/sslip.io)

## 简介

泛域名解析（Wildcard DNS）是一种 DNS 配置方式，允许使用通配符 `*` 来匹配任意子域名。`nip.io` 和 `sslip.io` 是两种常用的免费泛域名解析服务，可将 IP 地址嵌入域名中实现快速解析。

[nip.io 官网](https://nip.io) | [sslip.io 官网](https://sslip.io)

## 服务格式

### nip.io

格式：`<子域名>.<IP>.nip.io`

示例：
- `192.168.1.10.nip.io` → 解析到 `192.168.1.10`
- `app.192.168.1.10.nip.io` → 解析到 `192.168.1.10`
- `api.10.0.0.5.nip.io` → 解析到 `10.0.0.5`

### sslip.io

格式：`<子域名>.<IP>.sslip.io`（IP 中的点换成横线）

示例：
- `192-168-1-10.sslip.io` → 解析到 `192.168.1.10`
- `app.192-168-1-10.sslip.io` → 解析到 `192.168.1.10`

## 使用场景

### 本地开发测试

无需修改 hosts 文件，直接通过域名访问本地服务：

```bash
# 本地服务运行在 127.0.0.1:8080
curl http://dev.127.0.0.1.nip.io:8080
curl http://api.127.0.0.1.nip.io:8080
```

### Kubernetes 容器环境

快速为集群服务分配可访问域名：

```bash
# 查看服务 IP
kubectl get svc
# NAME         TYPE        CLUSTER-IP      PORT(S)
# my-service   ClusterIP   10.96.123.45    80/TCP

# 直接通过 nip.io 访问
curl http://my-service.10.96.123.45.nip.io
```

### 临时测试环境

快速搭建测试环境，无需购买域名：

```bash
# 服务器 IP 为 203.0.113.10
curl http://app1.203.0.113.10.nip.io
curl http://api.203.0.113.10.nip.io
```

## 实际应用示例

### 示例 1：Shell 脚本动态生成域名

```bash
#!/bin/bash

# 获取本机 IP
LOCAL_IP=$(hostname -I | awk '{print $1}')

# 生成 nip.io 域名
DOMAIN="app.${LOCAL_IP}.nip.io"
echo "访问地址: http://${DOMAIN}"

# 启动服务
python3 -m http.server 8000 &
```

### 示例 2：Nginx 反向代理配置

```nginx
# 使用 map 替代正则，更易维护且性能更好
map $host $backend_port {
    default              8080;
    ~^api\.              8081;
    ~^web\.              8082;
    ~^admin\.            8083;
}

server {
    listen 80;
    server_name *.192.168.1.100.nip.io;
    
    location / {
        proxy_pass http://127.0.0.1:$backend_port;
    }
}
```

### 示例 3：Docker Compose 环境变量

```yaml
version: '3'
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
    environment:
      - VIRTUAL_HOST=web.192.168.1.10.nip.io
  
  api:
    image: myapp:latest
    ports:
      - "8080:8080"
    environment:
      - VIRTUAL_HOST=api.192.168.1.10.nip.io
```

### 示例 4：快速测试 Web 应用

```bash
# 启动 Python 简易 HTTP 服务
python3 -m http.server 3000

# 从同一网络的其他设备访问（假设本机 IP 是 192.168.1.50）
curl http://myapp.192.168.1.50.nip.io:3000
```

## 验证解析

使用 dig 或 nslookup 验证域名解析：

```bash
# 查询 nip.io 解析
dig +short 192.168.1.10.nip.io
# 输出: 192.168.1.10

# 查询 sslip.io 解析
dig +short 192-168-1-10.sslip.io
# 输出: 192.168.1.10

# 使用 nslookup
nslookup app.10.0.0.5.nip.io
```

## 注意事项

1. **安全性**：仅适用于开发和测试环境，**不要用于生产环境**
2. **网络可达性**：确保目标 IP 是可达的（同一网络或公网可访问）
3. **防火墙限制**：部分企业防火墙可能拦截对 nip.io/sslip.io 的 DNS 查询
4. **IPv6 支持**：sslip.io 支持 IPv6，格式为 `2001-db8--1.sslip.io`
5. **延迟问题**：公共 DNS 服务可能有轻微延迟

## 替代方案

如需更稳定的私有方案，可考虑：

### dnsmasq 本地配置泛域名

  缺点 IP 固定不灵活
```bash
# 安装 dnsmasq
sudo apt-get install dnsmasq

# 配置泛域名解析
echo 'address=/.local.test/127.0.0.1' | sudo tee /etc/dnsmasq.d/local.conf

# 重启服务
sudo systemctl restart dnsmasq
```

### coredns 配置泛域名

CoreDNS 的 template 插件，可以写正则提取 IP：
```
local.test {
    template IN A {
        match "([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)\.local\.test"
        answer "{{ .Match }}.local.test 60 IN A {{ .Group 1 }}.{{ .Group 2 }}.{{ .Group 3 }}.{{ .Group 4 }}"
        fallthrough
    }
    forward . 114.114.114.114
}
```
这样 10.1.50.210.local.test 就能自动解析到 10.1.50.210。

## 参考链接

- [nip.io 官网](https://nip.io)
- [sslip.io 官网](https://sslip.io)
- [GitHub - nip.io](https://github.com/exentriquesolutions/nip.io)
