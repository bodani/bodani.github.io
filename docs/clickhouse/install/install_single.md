# ClickHouse 单机版安装

## 简介

ClickHouse 是一个用于联机分析(OLAP)的列式数据库管理系统(DBMS)。本指南介绍如何安装和配置单机版 ClickHouse。

## 一键安装方式

### 1. 使用官方安装脚本

```bash
# 一键安装脚本
curl -s https://clickhouse.com/ | sh

# 或使用原始方式
curl -s https://packagecloud.io/install/repositories/altinity/clickhouse/script.deb.sh | sudo bash
sudo apt-get install -y clickhouse-server clickhouse-client
```

### 2. 手动安装

#### Debian/Ubuntu:

```bash
sudo apt-get install -y apt-transport-https ca-certificates dirmngr
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 8919F6BD2B48D754

echo "deb https://packages.clickhouse.com/deb stable main" | sudo tee /etc/apt/sources.list.d/clickhouse.list
sudo apt-get update
sudo apt-get install -y clickhouse-server clickhouse-client
```

#### CentOS/RHEL:

```bash
sudo yum install -y epel-release
sudo rpm --import https://repo.clickhouse.com/RPM-GPG-KEY-clickhouse
sudo yum-config-manager --add-repo https://repo.clickhouse.com/rpm/stable/x86_64
sudo yum install -y clickhouse-server clickhouse-client
```

## 配置单机版

### 1. 基础配置

修改主配置文件 `/etc/clickhouse-server/config.xml`:

```xml
<!-- 服务端口 -->
<tcp_port>9000</tcp_port>
<http_port>8123</http_port>

<!-- 监听地址 -->
<listen_host>::</listen_host>

<!-- 日志配置 -->
<logger>
    <level>warning</level>
    <console>1</console>
</logger>

<!-- 资源配置 -->
<max_memory_usage>10000000000</max_memory_usage>
<max_threads>16</max_threads>
```

### 2. 用户配置

在 `/etc/clickhouse-server/users.xml` 中配置用户:

```xml
<users>
    <default>
        <!-- 默认用户权限 -->
        <profile>default</profile>
        <quota>default</quota>
        <networks incl="networks" replace="replace">
            <ip>::/0</ip>
        </networks>
    </default>

    <app_user>
        <!-- 应用用户 -->
        <password>SecurePassword123</password>
        <profile>web</profile>
        <quota>default</quota>
        <networks>
            <ip>127.0.0.1</ip>
        </networks>
    </app_user>
</users>
```

## 启动和验证

### 1. 启动服务

```bash
# 启动服务
sudo systemctl start clickhouse-server

# 设置开机自启
sudo systemctl enable clickhouse-server

# 检查服务状态
sudo systemctl status clickhouse-server
```

### 2. 验证安装

```bash
# 使用clickhouse-client连接
clickhouse-client

clickhouse-client   --host xxx --port 9000   --user xxx   --password 'xxxx'
# 或使用HTTP接口测试
curl 'http://localhost:8123/'
```

在 ClickHouse 终端中执行测试命令:

```sql
-- 检查服务器版本
SELECT version();

-- 创建测试表
CREATE TABLE test_table
(
    id UInt32,
    name String,
    date Date
) ENGINE = MergeTree()
ORDER BY (id);

-- 插入测试数据
INSERT INTO test_table VALUES (1, 'John Doe', '2023-01-01');

-- 查询测试数据
SELECT * FROM test_table;
```

## 性能优化建议

### 1. 内存设置

```xml
<!-- 限制内存使用，防止OOM -->
<max_memory_usage>8000000000</max_memory_usage>
<!-- 在内存不足时使用磁盘 -->
<max_bytes_before_external_group_by>5000000000</max_bytes_before_external_group_by>
```

### 2. 并发设置

```xml
<!-- 调整最大线程数 -->
<max_threads>8</max_threads>
<!-- 最大并发查询数 -->
<max_concurrent_queries>100</max_concurrent_queries>
```

## 安全配置

### 1. 网络访问控制

```xml
<!-- 限制IP访问 -->
<networks incl="networks" replace="replace">
    <ip>::1</ip>
    <ip>127.0.0.1</ip>
    <ip>192.168.1.0/24</ip>
</networks>
```

### 2. 用户认证

设置强密码并限制用户权限，使用单独的用户进行不同操作：

```xml
<!-- 读写用户 -->
<rw_user>
    <password_sha256_hex>...</password_sha256_hex>
    <profile>readwrite</profile>
</rw_user>

<!-- 只读用户 -->
<ro_user>
    <password_sha256_hex>...</password_sha256_hex>
    <profile>readonly</profile>
</ro_user>
```

## 常见问题

### 启动失败

检查日志: `tail -f /var/log/clickhouse-server/clickhouse-server.log`

### 端口冲突

修改 `/etc/clickhouse-server/config.xml` 中的 `<tcp_port>` 和 `<http_port>` 值

## 附录

单机版适用于数据分析需求较小或概念验证的场景。当需要更高吞吐量或更大数据容量时，请考虑部署集群版。
