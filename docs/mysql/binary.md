# binlog 管理

## 配置
```
[mysqld]
log-bin=mysql-bin          # 启用 Binlog 并定义文件名前缀
server-id=1                # 集群中唯一标识
binlog_format=ROW          # 推荐 ROW 模式（数据一致性高）
expire_logs_days=7         # 自动清理 7 天前的 Binlog（MySQL 5.x）
binlog_expire_logs_seconds=604800  # MySQL 8.x 等效配置（7天=604800秒）
max_binlog_size=1G         # 单个 Binlog 文件最大 1GB
sync_binlog=1
```

## 保留策略

```
-- 查看当前配置
SHOW VARIABLES LIKE 'log_bin%';
SHOW VARIABLES LIKE 'expire_logs_days';

-- 动态修改保留天数（MySQL 5.x）
SET GLOBAL expire_logs_days = 14;
-- 动态修改保留天数  (MySQL 8.x）
SET PERSIST binlog_expire_logs_seconds=86400; -- （一天）
-- 动态修改文件大小限制（MySQL 8.x） ，单个文件的大小
SET GLOBAL max_binlog_size = 2 * 1024 * 1024 * 1024;  -- 2GB
```
```
-- 列出所有 Binlog 文件
SHOW BINARY LOGS;

-- 查看当前写入的 Binlog 文件及位置
SHOW MASTER STATUS;
```

## ​​手动管理 Binlog​​

```
​​刷新日志​​（强制生成新文件）

FLUSH BINARY LOGS;  -- 等同于 FLUSH LOGS

​​切换日志文件​​

PURGE BINARY LOGS TO 'mysql-bin.000010';  -- 删除指定文件前的所有 Binlog
PURGE BINARY LOGS BEFORE '2024-01-01 00:00:00';  -- 删除指定时间前的日志

​​重置所有 Binlog（慎用）​​

RESET MASTER; 
```

