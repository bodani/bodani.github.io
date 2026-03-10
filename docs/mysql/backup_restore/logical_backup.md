# 逻辑备份

逻辑备份是将数据库的结构和数据导出为 SQL 语句，可读性好，便于跨版本和平台迁移。常用的逻辑备份工具有 mysqldump、mysqlpump、mydumper 等。

## mysqldump

mysqldump 是 MySQL 官方提供的逻辑备份工具，支持多种导出选项，是最常用和可靠的备份工具之一。

### 基本语法

```bash
mysqldump [options] db_name [tbl_name ...]
mysqldump [options] --databases db_name ...
mysqldump [options] --all-databases
```

### 常用备份命令

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

### 高级选项

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

### 恢复操作

```bash
# 恢复备份文件
mysql -u root -p database_name < backup_file.sql

# 从压缩文件恢复
gunzip < backup_file.sql.gz | mysql -u root -p database_name

# 带进度监控的恢复
pv backup_file.sql | mysql -u root -p database_name
```

## mysqlpump

mysqlpump 是 MySQL 5.7+提供的改进版逻辑备份工具，支持并行处理，显著提高了备份速度。

### 特性与优势

- 支持多线程备份，提高备份速度
- 支持并行处理表和数据库
- 更好的备份结构组织
- 可以更好地控制对象粒度

### 使用示例

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

## mydumper

mydumper 是一个高性能的 MySQL 逻辑备份工具，提供多线程备份能力，比 mysqldump 快很多倍。

### 安装

```bash
# Ubuntu/Debian
sudo apt-get install mydumper

# CentOS/RHEL
sudo yum install mydumper

# 或从源码编译安装
git clone https://github.com/mydumper/mydumper.git
cd mydumper
cmake .
make && sudo make install
```

### 使用示例

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

# 并行恢复
myloader -u root -p password -d /path/to/backup/ -j 4
```

## MySQL Shell 导出

MySQL Shell (mysqlsh) 是现代的 MySQL 客户端工具，提供了更高级的数据导出功能。

### 全局导出和导入

```javascript
// MySQL Shell - 逻辑导出（按 Schema）
var dump = util.dumpSchemas(["database_name"], "/path/to/dump");

// MySQL Shell - 完整实例导出
var dump = util.dumpInstance("user@host:port", {
  dumpDir: "/path/to/dump",
  threads: 4,
  excludeSchemas: ["information_schema", "performance_schema"],
});

// MySQL Shell - 导入（从 dump）
util.loadDump("/path/to/dump", { threads: 4 });

// MySQL Shell - 表导出
util.exportTable("table_name", "/path/to/table.sql", {
  where: "column = 'value'",
  threads: 2,
  fieldsTerminatedBy: ",",
  fieldsEnclosedBy: '"',
  linesTerminatedBy: "\n",
});
```

## CSV 导出备份

在某些情况下，需要将特定数据导出为 CSV 格式进行分析或迁移。

### 使用 SELECT INTO OUTFILE 导出

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

### 使用 mysql 命令导出 CSV

```bash
# 直接使用mysql命令导出为CSV
mysql -u root -p -e "SELECT * FROM database_name.table_name;" \
--batch --raw --silent --skip-column-names \
| sed 's/\t/,/g' > output.csv

# 包含列名的导出
mysql -u root -p -e "SELECT * FROM database_name.table_name;" \
--batch --raw --silent --column-names \
| sed 's/\t/,/g' > output_with_headers.csv

# 处理包含逗号或引号的数据
mysql -u root -p -e "SELECT id, CONCAT('\"', name, '\"') AS quoted_name, age FROM users;" \
--batch --raw --silent \
| sed 's/\t/,/g' > output.csv
```

## 逻辑备份策略比较

| 工具        | 优势                         | 适用场景               |
| ----------- | ---------------------------- | ---------------------- |
| mysqldump   | 稳定可靠，兼容性好，参数丰富 | 一般备份，中小数据库   |
| mysqlpump   | 支持并行处理，速度快         | 大数据库，MySQL 5.7+   |
| mydumper    | 速度极快，支持多线程         | 大数据量、快速备份场景 |
| MySQL Shell | 功能强大，现代客户端         | 集群、最新版本MySQL    |

## 备份最佳实践

### 备份频率设定

1. **每日全量备份** - 针对核心业务数据库
2. **增量或差异备份** - 在全量备份之间
3. **事务日志备份** - 记录每一笔操作
4. **校验备份一致性** - 定期恢复测试

### 安全性考量

1. **加密备份文件**

   ```bash
   # 使用gzip压缩并使用gpg加密
   mysqldump -u root -p database_name | gpg --cipher-algo AES256 --compress-algo 1 --symmetric | gzip > backup.gpg.gz
   ```

2. **设置备份目录权限**

   ```bash
   # 仅允许管理员和MySQL用户访问
   chmod 700 /backup/mysql
   chown -R mysql:mysql /backup/mysql
   ```

3. **网络传输使用加密通道**（scp, sftp等）

### 生产环境重要注意事项

对于使用 MySQL Group Replication (MGR) 等高可用架构的环境需要注意：

1. **GTID 参数的潜在问题**：`--set-gtid-purged=ON` 参数在高可用环境中可能导致复制中断
2. **安全策略**：在 MGR 环境中谨慎使用此参数
3. **恢复前后验证**：恢复后需检查复制状态和一致性
