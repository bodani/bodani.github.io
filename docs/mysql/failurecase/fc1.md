# MySQL连接错误 "Unknown MySQL server host 'localhost'"

## 问题描述

### 错误现象
客户端连接MySQL时出现以下错误：
```
Error: 2005 (HY000): Unknown MySQL server host 'localhost' (-11)
Error: 2005 (HY000): Unknown MySQL server host 'localhost' (-11)
Error: 2005 (HY000): Unknown MySQL server host 'localhost' (-11)
```

### MySQL进程状态
MySQL进程列表显示多个未认证用户连接：
```
| 4508 | unauthenticated user | localhost:38414 | NULL | Connect |    1 | login | NULL |
| 24509 | unauthenticated user | localhost:38418 | NULL | Connect |    1 | login | NULL |
```

### 相关配置
- MySQL配置：`back_log=2000`
- 系统配置：`ulimit -n`（文件描述符限制）
- 系统TCP参数：`net.ipv4.tcp_max_syn_backlog`

## 问题分析

### 根本原因
这是一个典型的**连接积压（connection backlog）问题**，在高并发场景下出现。错误代码 `-11` 对应系统错误 `EAGAIN`，表示资源暂时不可用。

### 问题发生机制
1. **高并发连接请求**：短时间内大量连接尝试到达MySQL服务器
2. **连接队列溢出**：
   - TCP层：SYN队列满，新连接被拒绝
   - MySQL层：`back_log` 队列满，连接无法进入登录队列
   - 系统资源：文件描述符不足，无法创建新连接句柄
3. **连接失败**：客户端连接超时或失败，误报为"未知主机"错误

## 解决方案

### 1. 优化系统参数

#### 增加文件描述符限制
```bash
# 临时生效
ulimit -n 65535

# 永久生效，编辑 /etc/security/limits.conf，添加：
mysql soft nofile 65535
mysql hard nofile 65535
```

#### 调整TCP参数
```bash
# 临时生效
sysctl -w net.ipv4.tcp_max_syn_backlog=2048
sysctl -w net.core.somaxconn=2048

# 永久生效，编辑 /etc/sysctl.conf，添加或修改：
net.ipv4.tcp_max_syn_backlog = 2048
net.core.somaxconn = 2048
net.ipv4.tcp_syncookies = 1
```
执行 `sysctl -p` 使配置生效。

### 2. 优化MySQL配置

#### 修改MySQL配置文件（my.cnf）
```ini
[mysqld]
# 增加积压连接队列大小
back_log = 2000

# 禁用DNS解析（如果不需要）
skip-name-resolve

# 合理设置最大连接数
max_connections = 500

# 其他相关优化
wait_timeout = 600
interactive_timeout = 600
```

#### 重启MySQL服务
```bash
systemctl restart mysqld
# 或
service mysql restart
```

### 3. 检查网络与解析配置

#### 验证localhost解析
```bash
cat /etc/hosts | grep localhost
```
应有以下内容：
```
127.0.0.1   localhost localhost.localdomain
::1         localhost localhost.localdomain
```

#### 测试不同连接方式
```bash
# 使用IP地址连接
mysql -h 127.0.0.1 -u username -p

# 使用localhost连接
mysql -h localhost -u username -p
```

### 4. 监控与验证

#### 监控MySQL连接状态
```sql
-- 查看当前连接数
SHOW STATUS LIKE 'Threads_connected';

-- 查看最大连接数配置
SHOW VARIABLES LIKE 'max_connections';

-- 查看连接相关状态
SHOW STATUS LIKE '%connect%';
SHOW STATUS LIKE '%abort%';
```

#### 检查系统连接状态
```bash
# 查看MySQL端口监听状态
ss -lnt | grep :3306

# 查看TCP连接统计
netstat -s | grep -i listen

# 查看当前连接数
netstat -an | grep :3306 | wc -l
```

#### 监控系统资源
```bash
# 查看文件描述符使用情况
cat /proc/sys/fs/file-nr

# 查看系统负载
top
htop

# 监控网络连接
iftop
nethogs
```

## 预防措施

### 1. 定期监控
- 设置MySQL连接数监控告警
- 监控系统文件描述符使用率
- 监控TCP连接状态

### 2. 连接池优化
- 应用层使用连接池管理数据库连接
- 合理设置连接池大小和超时时间
- 实现连接重试机制

### 3. 架构优化
- 考虑读写分离，分散连接压力
- 使用数据库代理中间件
- 实施限流和熔断机制

### 4. 定期维护
- 定期清理空闲连接
- 优化查询语句，减少连接持有时间
- 定期重启MySQL释放资源

## 故障排查流程

1. **确认现象**：收集错误日志和客户端报错信息
2. **检查状态**：查看MySQL进程列表和连接状态
3. **验证配置**：检查系统参数和MySQL配置
4. **测试连接**：使用不同方式测试连接
5. **调整参数**：根据实际情况调整相关参数
6. **监控验证**：调整后监控系统状态，确认问题解决
7. **记录归档**：记录问题和解决方案，更新运维文档

## 总结

"Unknown MySQL server host 'localhost'" 错误通常不是真正的DNS解析问题，而是**高并发场景下的连接资源耗尽**。通过优化系统TCP参数、文件描述符限制和MySQL的 `back_log` 配置，可以有效解决此类问题。同时，建立完善的监控体系和预防措施，可以避免问题再次发生。