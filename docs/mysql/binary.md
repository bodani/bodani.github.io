# binlog 管理

- [MySQL 5.7](#mysql-57)
- [MySQL 8.0](#mysql-80)
- [MySQL 8.4](#mysql-84)

---

## MySQL 5.7 

### 配置

```
[mysqld]
log-bin=mysql-bin
server-id=1
binlog_format=ROW
expire_logs_days=7          # 自动清理 N 天前的 Binlog（5.7 主要用这个）
max_binlog_size=1G
sync_binlog=1
```

### 保留策略

```
SHOW VARIABLES LIKE 'log_bin%';
SHOW VARIABLES LIKE 'expire_logs_days';

-- 动态修改保留天数（需 GLOBAL，5.7 无 SET PERSIST）
SET GLOBAL expire_logs_days = 14;

SET GLOBAL max_binlog_size = 2 * 1024 * 1024 * 1024;  -- 2GB
```

### 查看 Binlog

```
SHOW BINARY LOGS;
SHOW MASTER LOGS;

SHOW MASTER STATUS;
```

### 手动管理 Binlog

```
-- 刷新日志（轮转新文件，并按 expire_logs_days 清理）
FLUSH BINARY LOGS;

-- 按文件或时间清理
PURGE BINARY LOGS TO 'mysql-bin.000010';
PURGE BINARY LOGS BEFORE '2024-01-01 00:00:00';
-- 旧写法（等价）
PURGE MASTER LOGS TO 'mysql-bin.000010';
PURGE MASTER LOGS BEFORE '2024-01-01 00:00:00';

-- 清空全部 Binlog（慎用；有从库时需先停复制）
RESET MASTER;
```

参考：[MySQL 5.7 — PURGE BINARY LOGS](https://dev.mysql.com/doc/refman/5.7/en/purge-binary-logs.html)

---

## MySQL 8.0

### 配置

```
[mysqld]
log-bin=mysql-bin
server-id=1
binlog_format=ROW
expire_logs_days=7                    # 已废弃，建议改用下面项
binlog_expire_logs_seconds=604800     # 推荐：7 天 = 604800 秒
max_binlog_size=1G
sync_binlog=1
```

### 保留策略

```
SHOW VARIABLES LIKE 'log_bin%';
SHOW VARIABLES LIKE 'binlog_expire_logs_seconds';

-- 动态修改保留时间（推荐，可持久化到 mysqld-auto.cnf）
SET PERSIST binlog_expire_logs_seconds = 86400;  -- 1 天

SET GLOBAL max_binlog_size = 2 * 1024 * 1024 * 1024;  -- 2GB
```

### 查看 Binlog

```
SHOW BINARY LOGS;
SHOW MASTER LOGS;

SHOW MASTER STATUS;
```

### 手动管理 Binlog

```
-- 刷新日志（轮转并按 binlog_expire_logs_seconds 清理）
FLUSH BINARY LOGS;

-- 按文件或时间清理（从库在线时可用）
PURGE BINARY LOGS TO 'mysql-bin.000010';
PURGE BINARY LOGS BEFORE '2024-01-01 00:00:00';

-- 清空全部 Binlog 与 GTID 历史（慎用）
RESET MASTER;
```

参考：[MySQL 8.0 — 控制复制源服务器的语句](https://dev.mysql.com/doc/refman/8.0/en/replication-statements-source.html)

---

## MySQL 8.4
### 配置

```
[mysqld]
log-bin=mysql-bin
server-id=1
binlog_format=ROW
binlog_expire_logs_seconds=86400   # 仅此项；无 expire_logs_days
binlog_expire_logs_auto_purge=ON   # 默认 ON，按秒数自动 purge
max_binlog_size=1G
sync_binlog=1
```

### 保留策略

```
SHOW VARIABLES LIKE 'log_bin%';
SHOW VARIABLES LIKE 'binlog_expire_logs%';

SET PERSIST binlog_expire_logs_seconds = 604800;  -- 7 天

SET GLOBAL max_binlog_size = 2 * 1024 * 1024 * 1024;  -- 2GB
```

### 查看 Binlog

```
SHOW BINARY LOGS;

SHOW BINARY LOG STATUS;
```

> 8.4 已移除 `SHOW MASTER STATUS`，请用 `SHOW BINARY LOG STATUS`。

### 手动管理 Binlog

```
-- 刷新日志
FLUSH BINARY LOGS;

-- 按文件或时间清理（从库在线时可用）
PURGE BINARY LOGS TO 'mysql-bin.000010';
PURGE BINARY LOGS BEFORE '2024-01-01 00:00:00';

-- 清空全部 Binlog 与 GTID 历史（慎用；8.4 无 RESET MASTER）
RESET BINARY LOGS AND GTIDS;

-- 可选：指定新 Binlog 序号起点
RESET BINARY LOGS AND GTIDS TO 1234;
```

**注意：**

- 日常删旧文件用 `PURGE BINARY LOGS`；彻底清空用 `RESET BINARY LOGS AND GTIDS`（会清空 GTID 历史）。
- 有副本运行时不要执行 `RESET BINARY LOGS AND GTIDS`。

参考：

- [RESET BINARY LOGS AND GTIDS](https://dev.mysql.com/doc/refman/8.4/en/reset-binary-logs-and-gtids.html)
- [SHOW BINARY LOG STATUS](https://dev.mysql.com/doc/refman/8.4/en/show-binary-log-status.html)
- [PURGE BINARY LOGS](https://dev.mysql.com/doc/refman/8.4/en/purge-binary-logs.html)
