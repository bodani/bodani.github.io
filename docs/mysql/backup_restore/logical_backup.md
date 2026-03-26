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
# 备份实践
mysqldump -u root -p --single-transaction --routines --triggers --events \
    --set-gtid-purged=OFF  --hex-blob \
    --default-character-set=utf8mb4 \
    --max-allowed-packet=1073741824 \
    database_name > backup.sql

# 大表备份优化
mysqldump -u root -p --single-transaction --quick  \
    database_name > backup.sql

--quick (最关键的大表优化)
作用原理：
默认情况下，mysqldump 会为每个表将所有数据行一次性读取到客户端内存，然后再写入输出文件。
使用 --quick 后，改为逐行读取、缓冲并立即写入输出文件，显著减少客户端内存占用。
大表场景价值：
避免内存耗尽：对于有上千万行的大表，默认方式可能消耗数GB内存，甚至导致客户端OOM崩溃。--quick 将内存占用降至最低。
更早开始写入：数据可以边读边写，而不是等整个表读完再写。
代价：略微增加网络往返次数，但对大表备份来说，内存安全的收益远大于此开销。

--compression-algorithms='zstd,zlib,uncompressed' 压缩的参数
```

### 注意事项

- 参数 --set-gtid-purged 默认为Auto. 在备份的文件中输出 set@@gloabal.gtid_purged为源库的gtid_executed和set@@session.sql_log_bin=0.
  session.sql_log_bin=0.在mgr 或主从结构中会造成主从数据不一致。
- 备份用户及权限， 用户和权限在mysql database中，需要单独处理。 如使用 --all-databases 的时候，在恢复的时候需要特殊注意。如mysql ,mysql_innodb_cluster_metadata 等库小心被覆盖。 

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

### 常用参数详解

#### 并行度

- --parallelism=N: 为每个队列指定线程的个数， 默认2
- --parallel-schemas=[N:] db*list: 创建新的备份队列,N是该队列的线程数，db_list 是该队列中包括的数据库名，可以使用%和*对数据库名进行匹配。

#### 正则表达式

- --include-databases
- --exclude-databases
- --include-tables
- --exclude-tables
- --exclude-users
- --include-users

### 使用示例

```bash
# 并行备份 第一个队列 db1,db2 的并行度 是4, 第二个队列 db3的并行度是 3
mysqlpump -u root -p --parallel-schemas=4: db1, db2 --parallel-schemas=3: db3 > backup.sql

# 备份用户
mysqlpump -u root -p --exclude-databases=% --users  > users.sql

# 限制并行度
mysqlpump -u root -p --parallel-schemas=2 --default-character-set=utf8mb4 --all-databases > backup.sql

# 备份时设置压缩
mysqlpump -u root -p --compress-algorithms=zlib --default-character-set=utf8mb4 database_name > backup.sql
```

### 注意事项

- mysqlpump is deprecated as of MySQL 8.0.34 ,推荐 mysqlsh
- 备份的文件中 存在session.sql_log_bin=0.
- 导出数据的时区

## mydumper

mydumper 是一个高性能的 MySQL 逻辑备份工具，支持多线程备份和恢复，相比传统的 mysqldump 工具具有更好的性能表现。

[源码地址](https://github.com/mydumper/mydumper)

### 安装

```bash
# Ubuntu/Debian
# 添加仓库
sudo apt-get update
sudo apt-get install -y wget
# 下载最新版本（请检查最新版本号）
wget https://github.com/mydumper/mydumper/releases/download/v0.15.1-3/mydumper_0.15.1-3.bullseye_amd64.deb
# 安装
sudo dpkg -i mydumper_0.15.1-3.bullseye_amd64.deb
# 解决依赖问题
sudo apt-get install -f
```

```bash
# 添加仓库
sudo yum install -y epel-release
# 下载 RPM 包
wget https://github.com/mydumper/mydumper/releases/download/v0.15.1-3/mydumper-0.15.1-3.el7.x86_64.rpm
# 安装
sudo yum install -y mydumper-0.15.1-3.el7.x86_64.rpm
```

### 简单使用示例

- -B , --databases 指定备份的库
- -T , --tables-list 指定备份表

```bash
# 备份整个数据库到指定目录
mydumper \
  --host=localhost \
  --user=root \
  --password=your_password \
  --outputdir=/backup/mysql \
  --verbose=3


# 备份单个数据库
mydumper \
  --database=mydb \
  --outputdir=/backup/mydb \
  --user=root \
  --password=your_password


# 备份特定表
mydumper \
  --database=mydb \
  --tables-list=table1,table2 \
  --outputdir=/backup/tables \
  --user=root \
  --password=your_password

# 恢复整个备份
myloader \
  --directory=/backup/mysql \
  --user=root \
  --password=your_password \
  --verbose=3

# 恢复指定数据库
myloader \
  --directory=/backup/mydb \
  --database=newdb \
  --user=root \
  --password=your_password
```

### 并行和一致性

并行备份
MyDumper 支持多线程并行备份，显著提高备份速度，可以对单个大表进行并行导出。

- --rows , 每个线程每次处理100行
- --chun-filesize， 单位MB ,指定并行的文件大小单位

```
# 使用 8 个线程进行备份
mydumper \
  --threads=8 \
  --outputdir=/backup/parallel \
  --user=root \
  --password=your_password \
  --compress
```

一致性保证
MyDumper 提供多种一致性级别：

```
# 1. 使用 FTWRL（默认） - 全局锁，保证完全一致性
mydumper \
  --lock-all-tables \
  --outputdir=/backup/consistent \
  --user=root \
  --password=your_password

# 2. 使用事务一致性（推荐用于 InnoDB）
mydumper \
  --trx-consistency-only \
  --outputdir=/backup/trx_consistent \
  --user=root \
  --password=your_password

# 3. 使用快照（需要支持快照的存储引擎）
mydumper \
  --snapshot-interval=10 \
  --outputdir=/backup/snapshot \
  --user=root \
  --password=your_password

# 4. 最小化锁时间（每个表单独锁）
mydumper \
  --less-locking \
  --outputdir=/backup/less_lock \
  --user=root \
  --password=your_password
```

正则表达式指定数据库对象
使用正则表达式过滤

```
# 备份匹配正则表达式的数据库
mydumper \
  --regex='^test_db' \
  --outputdir=/backup/regex_db \
  --user=root \
  --password=your_password

# 排除匹配正则表达式的数据库
mydumper \
  --regex='^(?!temp_).*' \
  --outputdir=/backup/exclude_temp \
  --user=root \
  --password=your_password

# 备份匹配正则表达式的数据库
mydumper \
  --regex='^test_db' \
  --outputdir=/backup/regex_db \
  --user=root \
  --password=your_password

# 排除匹配正则表达式的数据库
mydumper \
  --regex='^(?!temp_).*' \
  --outputdir=/backup/exclude_temp \
  --user=root \
  --password=your_password
```

## MySQL Shell

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

备份到s3

```
 echo "
                  import os
                  from datetime import datetime, timezone, timedelta

                  now_utc = datetime.now(timezone.utc)
                  cst_timezone = timezone(timedelta(hours=8))
                  now_cst = now_utc.astimezone(cst_timezone)
                  now_str =  now_cst.strftime('%Y%m%d%H%M')
                  endpoint=os.getenv('AWS_ENDPOINT_URL')
                  bucket_name=os.getenv('AWS_BUCKET_NAME')

                  util.dump_instance(now_str, {'s3BucketName': bucket_name, 's3EndpointOverride': endpoint, 'threads': 1, 'maxRate': '8M', 'compatibility': ['strip_restricted_grants', 'strip_definers', 'ignore_missing_pks'] ,'excludeSchemas': ['mysql_innodb_cluster_metadata','sys','information_schema','performance_schema','mondb'],'compatibility':['strip_restricted_grants', 'strip_definers', 'ignore_missing_pks'] })
                  " > /tmp/dump_instance.py

                  mysqlsh --uri=${MYSQL_ROOT_USER}@${MYSQL_HOST}:${MYSQL_PORT_NUMBER} -p${MYSQL_ROOT_PASSWORD} --py < /tmp/dump_instance.py
```

```
从s3 恢复

export AWS_ACCESS_KEY_ID=LTAI5tAzj
export AWS_SECRET_ACCESS_KEY=tcWmL

# 登录数据库 -u 用户 -h 目标数据库IP -p密码
mysqlsh -u administrator -h 10.43.xxx.xx -pExxxxxamiSV --sql
# 登录后执行
SET GLOBAL local_infile = ON;
\js
# 执行恢复语句，有颜色字体内容修改为对应的值
# dirname 为通常为备份的时间点，在s3上查看 例如202406140100。
# bucketname: 桶名

util.loadDump('dirname', {'s3BucketName': 'bucketname', 's3EndpointOverride': 'http://10.43.129.xxx:9000'})
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
