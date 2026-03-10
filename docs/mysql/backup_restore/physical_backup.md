# 数据备份与恢复

## 物理备份

物理备份是对数据库文件系统的直接备份，保持数据文件的原始格式。这种方法快速高效，常用于大型数据库的备份。

### xtrabackup

Percona XtraBackup 是最流行的 MySQL 物理备份工具，支持热备份（无需停机）。

#### 安装 xtrabackup

```bash
# Ubuntu/Debian
wget https://repo.percona.com/apt/percona-release_0.1-6.$(lsb_release -sc)_all.deb
sudo dpkg -i percona-release_0.1-6.$(lsb_release -sc)_all.deb
sudo apt-get update
sudo apt-get install percona-xtrabackup-80

# CentOS/RHEL
sudo yum install https://repo.percona.com/yum/percona-release-latest.noarch.rpm
sudo percona-release setup ps80
sudo yum install percona-xtrabackup-80
```

#### 完整备份

```bash
# 基础完整备份
xtrabackup --user=root --password=your_password --backup --target-dir=/path/to/backup/directory

# 使用配置文件
xtrabackup --defaults-file=/etc/mysql/my.cnf --user=root --password=your_password --backup --target-dir=/path/to/backup/directory

# 指定数据库
xtrabackup --user=root --password=your_password --backup --target-dir=/path/to/backup/directory --databases="db1 db2"
```

#### 增量备份

```bash
# 基于上次备份的增量备份
xtrabackup --user=root --password=your_password --backup --target-dir=/path/to/incremental/backup --incremental-basedir=/path/to/base/backup
```

#### 准备备份

```bash
# 准备完整备份
xtrabackup --prepare --target-dir=/path/to/backup/directory

# 准备增量备份（两步操作）
xtrabackup --prepare --target-dir=/path/to/base/backup --incremental-dir=/path/to/incremental/backup

# 合并增量备份到基础备份
xtrabackup --prepare --target-dir=/path/to/base/backup --incremental-dir=/path/to/incremental/backup
```

#### 恢复备份

```bash
# 关闭MySQL服务
sudo systemctl stop mysql

# 清空数据目录
sudo rm -rf /var/lib/mysql/*

# 恢复备份
xtrabackup --copy-back --target-dir=/path/to/backup/directory

# 更改文件所有者
sudo chown -R mysql:mysql /var/lib/mysql

# 启动MySQL服务
sudo systemctl start mysql
```

#### 常用参数说明

- `--user`：连接 MySQL 的用户名
- `--password`：连接 MySQL 的密码
- `--host`：MySQL 主机地址
- `--port`：MySQL 端口号
- `--backup`：执行备份操作
- `--target-dir`：备份目标目录
- `--incremental-basedir`：增量备份的基准目录
- `--prepare`：准备备份数据（回滚未提交的事务）
- `--copy-back`：将备份复制回数据目录
- `--defaults-file`：指定 MySQL 配置文件
- `--databases`：只备份指定的数据库

### 备份脚本示例

```bash
#!/bin/bash

# MySQL连接信息
MYSQL_USER="root"
MYSQL_PASSWORD="your_password"
MYSQL_HOST="localhost"
MYSQL_PORT="3306"

# 备份目录设置
BACKUP_BASE_DIR="/backup/mysql"
DATE=$(date +%Y%m%d_%H%M%S)
BASE_BACKUP_DIR="$BACKUP_BASE_DIR/base"
INC_BACKUP_DIR="$BACKUP_BASE_DIR/inc"

# 确保备份目录存在
mkdir -p $BASE_BACKUP_DIR
mkdir -p $INC_BACKUP_DIR

# 创建硬链接基础备份，便于增量备份
LATEST_BACKUP=$(ls -t $BASE_BACKUP_DIR/*/ 2>/dev/null | head -n1)

if [ -n "$LATEST_BACKUP" ]; then
    # 执行增量备份
    xtrabackup --user=$MYSQL_USER --password=$MYSQL_PASSWORD \
        --backup --target-dir="$INC_BACKUP_DIR/$DATE" \
        --incremental-basedir="$LATEST_BACKUP"
    echo "Incremental backup completed: $INC_BACKUP_DIR/$DATE"
else
    # 执行基础备份
    xtrabackup --user=$MYSQL_USER --password=$MYSQL_PASSWORD \
        --backup --target-dir="$BASE_BACKUP_DIR/$DATE"
    echo "Full backup completed: $BASE_BACKUP_DIR/$DATE"
fi
```

## 逻辑备份

逻辑备份是将数据库的结构和数据导出为 SQL 语句，可读性好，便于跨版本和平台迁移。

### mysqldump

mysqldump 是 MySQL 官方提供的逻辑备份工具，支持多种导出选项。

#### 基本语法

```bash
mysqldump [options] db_name [tbl_name ...]
mysqldump [options] --databases db_name ...
mysqldump [options] --all-databases
```

#### 常用备份命令

```bash
# 备份单个数据库
mysqldump -u root -p database_name > backup_file.sql

# 备份多个数据库
mysqldump -u root -p --databases db1 db2 db3 > backup_file.sql

# 备份所有数据库
mysqldump -u root -p --all-databases > all_databases_backup.sql

# 备份特定表
mysqldump -u root -p database_name table1 table2 > backup_file.sql

# 包含创建数据库语句的备份
mysqldump -u root -p --databases --add-drop-database database_name > backup_file.sql

# 结构备份（仅表结构，不含数据）
mysqldump -u root -p --no-data database_name > structure_backup.sql

# 数据备份（仅数据，不含结构）
mysqldump -u root -p --no-create-info database_name > data_backup.sql
```

#### 高级选项

```bash
# 使用GTID进行备份（MySQL 5.6+）
mysqldump -u root -p --set-gtid-purged=ON --all-databases > backup.sql

# 并行处理（MySQL 8.0+）
mysqldump -u root -p --single-transaction --routines --triggers \
    --set-gtid-purged=ON --compress --hex-blob \
    --default-character-set=utf8mb4 --routines --triggers \
    --max-allowed-packet=1073741824 \
    database_name > backup.sql

# 大表备份优化
mysqldump -u root -p --single-transaction --quick --lock-tables=false \
    database_name > backup.sql

# 安全备份（过滤敏感字符）
mysqldump -u root -p --single-transaction --hex-blob database_name > backup.sql
```

#### 恢复操作

```bash
# 恢复备份文件
mysql -u root -p database_name < backup_file.sql

# 从压缩文件恢复
gunzip < backup_file.sql.gz | mysql -u root -p database_name

# 带进度监控的恢复
pv backup_file.sql | mysql -u root -p database_name
```

### mysqlpump

mysqlpump 是 MySQL 5.7+提供的改进版逻辑备份工具，支持并行处理。

#### 特性与优势

- 支持多线程备份，提高备份速度
- 支持并行处理表和数据库
- 更好的备份结构组织

#### 使用示例

```bash
# 并行备份所有数据库
mysqlpump -u root -p --parallel-schemas=4 --default-character-set=utf8mb4 > backup.sql

# 并行备份特定数据库
mysqlpump -u root -p --default-character-set=utf8mb4 database_name > backup.sql

# 限制并行度
mysqlpump -u root -p --parallel-schemas=2 --default-character-set=utf8mb4 --all-databases > backup.sql

# 备份时设置压缩
mysqlpump -u root -p --compress-algorithms=zlib --default-character-set=utf8mb4 database_name > backup.sql
```

### mydumper

mydumper 是一个高性能的 MySQL 逻辑备份工具，提供多线程备份能力。

#### 安装

```bash
# Ubuntu/Debian
sudo apt-get install mydumper

# CentOS/RHEL
sudo yum install mydumper
```

#### 使用示例

```bash
# 基本备份
mydumper -u root -p password -o /path/to/backup/

# 多线程备份
mydumper -u root -p password -o /path/to/backup/ -j 4

# 备份特定数据库
mydumper -u root -p password -o /path/to/backup/ -B database_name

# 压缩备份
mydumper -u root -p password -o /path/to/backup/ --compress

# 优化查询
mydumper -u root -p password -o /path/to/backup/ --compress --long-query-guard 600
```

### mysqlsh

MySQL Shell 提供了现代的 MySQL 客户端功能，包含备份/恢复功能。

#### 全局导出和导入

```javascript
// MySQL Shell - 逻辑导出
var dump = util.dumpSchemas(["database_name"], "/path/to/dump");

// MySQL Shell - 完整实例导出
var dump = util.dumpInstance("user@host:port", {
  dumpDir: "/path/to/dump",
  threads: 4,
  excludeSchemas: ["information_schema", "performance_schema"],
});

// MySQL Shell - 导入
util.loadDump("/path/to/dump", { threads: 4 });
```

### CSV 导出备份

有时需要将特定数据导出为 CSV 格式进行分析或迁移。

#### 使用 SELECT INTO OUTFILE 导出

```sql
-- 基本CSV导出
SELECT car_id, timestamp
INTO OUTFILE '/tmp/mx_task_data.csv'
FIELDS TERMINATED BY ','
LINES TERMINATED BY '\n'
FROM mx_task_picture_info;

-- 带字段引用的CSV导出
SELECT id, name, email
INTO OUTFILE '/tmp/users.csv'
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
FROM users;

-- 带列名的CSV导出（使用UNION）
(SELECT 'id', 'name', 'email')
UNION
(SELECT id, name, email
INTO OUTFILE '/tmp/users_with_headers.csv'
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
FROM users);
```

#### 使用 mysql 命令导出 CSV

```bash
# 直接使用mysql命令导出为CSV
mysql -u root -p -e "SELECT * FROM database_name.table_name;" \
--batch --raw --silent --skip-column-names \
| sed 's/\t/,/g' > output.csv

# 包含列名的导出
mysql -u root -p -e "SELECT * FROM database_name.table_name;" \
--batch --raw --silent --column-names \
| sed 's/\t/,/g' > output_with_headers.csv
```

## 备份策略和最佳实践

### 选择备份方式

1. **物理备份适用于**：

   - 大型数据库
   - 对备份和恢复时间有严格要求
   - 需要跨服务器克隆

2. **逻辑备份适用于**：
   - 跨版本升级迁移
   - 小到中型数据库
   - 需要选择性恢复特定表
   - 需要编辑备份文件

### 备份计划建议

- **每日基础备份**：执行完整物理备份
- **每小时增量备份**：记录变化数据
- **事务日志备份**：记录每条事务
- **备份验证**：定期验证备份文件完整性
- **多地备份**：至少两个地理位置的备份

### 备份存储管理

```bash
# 自动化备份脚本
#!/bin/bash

BACKUP_DIR="/backup/mysql"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

# 创建每日备份目录
mkdir -p $BACKUP_DIR/daily

# 执行备份
mysqldump -u root -p --single-transaction --routines --triggers \
    --set-gtid-purged=ON --hex-blob --all-databases \
    | gzip > $BACKUP_DIR/daily/backup_$DATE.sql.gz

# 清理旧备份
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
```

### 备份监控

```bash
# 备份监控脚本
#!/bin/bash

BACKUP_FILE=$1
if [ -f "$BACKUP_FILE" ]; then
    FILE_SIZE=$(stat -c%s "$BACKUP_FILE")
    if [ $FILE_SIZE -gt 1024 ]; then
        echo "Backup successful: $BACKUP_FILE ($FILE_SIZE bytes)"
        exit 0
    else
        echo "Error: Backup file is too small, possible failure"
        exit 1
    fi
else
    echo "Error: Backup file does not exist: $BACKUP_FILE"
    exit 1
fi
```

### 安全注意事项

1. **备份文件加密**：

   ```bash
   # 使用gzip加密压缩
   mysqldump -u root -p database_name | gpg --cipher-algo AES256 --compress-algo 1 --symmetric | gzip > backup.gpg.gz
   ```

2. **备份目录权限**：

   ```bash
   # 仅允许root和mysql用户访问
   chmod 700 /backup/mysql
   chown -R mysql:mysql /backup/mysql
   ```

3. **网络传输加密**：使用 scp 或 sftp 传输备份文件

### 重要生产环境注意事项

#### GTID 相关问题

**注意：`--set-gtid-purged` 参数可能产生风险**

使用 `--set-gtid-purged=ON` 参数会产生 `SET @@SESSION.SQL_LOG_BIN=0;` 和相关 GTID 重置语句，在 MySQL Group Replication (MGR) 环境中可能导致主从不一致问题。

- **在 MGR 环境中**：不要使用 `--set-gtid-purged=ON` 除非明确知道自己在做什么
- **替代方案**：在高可用环境下应使用 `--set-gtid-purged=OFF` 或完全不使用此参数
- **问题现象**：在生产环境中遇到过使用 `--set-gtid-purged` 会在恢复后生成 `SET @@SESSION.SQL_LOG_BIN=0` 这类语句，导致复制链路中断，造成主从不一致
- **安全恢复方式**：对于集群环境，应当预先规划恢复过程，并在恢复前后验证复制状态

示例安全的备份命令：

```bash
# 针对 MGR 或复制环境的安全备份
mysqldump -u root -p --single-transaction --master-data=2 \
    --routines --triggers --hex-blob \
    --default-character-set=utf8mb4 --all-databases > backup.sql

# 恢复前需要检查复制状态
SHOW SLAVE STATUS\G
# 或针对 MGR
SHOW STATUS LIKE '%group_replication%';
```
