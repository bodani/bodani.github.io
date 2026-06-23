# MongoDB 运维备份恢复操作手册

在 MongoDB 数据库运维中，备份和恢复是非常重要的任务，关系到数据安全和业务连续性。本文档提供了完整的 mongodump/mongorestore 和 mongoexport/mongoimport 操作手册，帮助您进行有效的数据保护和恢复工作。

## mongodump 与 mongorestore

mongodump 和 mongorestore 是 MongoDB 官方推荐的逻辑备份和恢复工具，它们可以完整备份和恢复整个数据库、特定数据库或指定的集合，是 MongoDB 数据备份的标准解决方案。

### 本地备份恢复

#### 完整数据库备份（带认证）

完整数据库备份是保障数据安全最常用的操作，它会导出所有数据库对象和数据。

```bash
# 基本完整备份
mongodump --host localhost:27017 \
  --username admin \
  --password "your_password" \
  --authenticationDatabase admin \
  --gzip \
  --out /backup/mongodb/$(date +%Y%m%d_%H%M%S)

# 带 oplog 的完整备份（用于一致性恢复）
mongodump --host localhost:27017 \
  --username admin \
  --password "your_password" \
  --authenticationDatabase admin \
  --oplog \
  --gzip \
  --out /backup/mongodb/full_$(date +%Y%m%d_%H%M%S)

# 副本集合备份
mongodump --host rs0/localhost:29910,localhost:29912,localhost:29913   --username admin   --password "your_password" --oplog  --authenticationDatabase admin   --gzip   --out /backup/mongodb/full_$(date +%Y%m%d_%H%M%S)
```

- gzip 压缩要比原格式节省大量的存储空间
- -j 指定并行备份的collections数量

#### 特定数据库/集合备份

当需要备份特定数据库或集合时，可以通过 `--db` 和 `--collection` 参数指定备份范围，这能有效节省存储空间和时间。

```bash
# 备份单个数据库
mongodump --host localhost:27017 \
  --db production_db \
  --out /backup/mongodb/production_$(date +%Y%m%d)

# 备份特定集合
mongodump --host localhost:27017 \
  --db production_db \
  --collection users \
  --out /backup/mongodb/users_backup

# 排除特定集合
mongodump --host localhost:27017 \
  --db production_db \
  --excludeCollection=system.profile \
  --excludeCollection=temp_logs \
  --out /backup/mongodb/filtered_backup
```

注意事项， 不可以带 --oplog 参数

#### 备份压缩与归档

使用压缩功能可以显著减少备份占用的磁盘空间，在备份和恢复速度上也有提升，特别推荐在生产环境使用。

```bash
# 使用 gzip 压缩备份（推荐）
mongodump --host localhost:27017 \
  --gzip \
  --out /backup/mongodb/compressed_$(date +%Y%m%d)

# 备份为归档文件（单文件）
mongodump --host localhost:27017 \
  backup/mongodb/archive_$(date +%Y%m%d_%H%M%S).archive

# 压缩归档文件
mongodump --host localhost:27017 \
  --archive \
  --gzip \
  --archive=/backup/mongodb/backup_$(date +%Y%m%d).archive.gz
```

#### 本地恢复操作

在执行恢复操作前，请确保目标 MongoDB 服务处于正常状态。

```bash
# 完整恢复（覆盖现有数据）
mongorestore --host localhost:27017 \
  --username admin \
  --password "your_password" \
  --authenticationDatabase admin \
  --drop \
  --gzip \
  /backup/mongodb/20240115_140000

# 恢复带 oplog 的备份
mongorestore --host localhost:27017 \
  --oplogReplay \
  --gzip \
  /backup/mongodb/full_20240115_020000

# 恢复特定数据库
mongorestore --host localhost:27017 \
  --db production_db \
  /backup/mongodb/production_20240115/production_db

# 恢复特定集合
mongorestore --host localhost:27017 \
  --db production_db \
  --collection users \
  /backup/mongodb/users_backup/production_db/users.bson

# 从归档文件恢复
mongorestore --host localhost:27017 \
  --archive=/backup/mongodb/archive_20240115.archive \
  --gzip
```

注意事项：

- 与备份命令向对应，如 同时带有 --gzip
- --drop 会先进行删除操作，需谨慎
- --dryRun 试运行，不实际执行
- -j, 并行恢复的collections 数量

#### 验证与清理

备份验证是确保数据可靠性的关键步骤，必须在业务正式切换之前完成，而定期清理备份有助于节约存储成本。

```bash
# 查看备份目录结构
ls -la /backup/mongodb/full_20240115_020000/

# 验证备份文件完整性
find /backup/mongodb/full_20240115_020000 -name "*.bson.gz" -type f | head -5

# 清理旧备份（保留最近30天）
find /backup/mongodb -name "*" -type d -mtime +30 -exec rm -rf {} \;
```

### 备份到 S3 方案

#### 直接流式备份到 S3（不落盘）

```
mongodump --host localhost:27017 \
 --archive \
 --gzip | \
 aws s3 cp - s3://your-bucket-name/mongodb-backups/backup*$(date +%Y%m%d*%H%M%S).archive.gz
```

### 从 S3 恢复数据

#### 直接流式恢复

```
aws s3 cp s3://your-bucket-name/mongodb-backups/backup_20240115.archive.gz - | \
 mongorestore --host localhost:27017 --archive --gzip
```

## mongoexport 与 mongoimport

mongoexport 和 mongoimport 适用于将 MongoDB 中的集合导出/导入为 JSON、CSV 格式的文件，主要用于与其他系统交换数据，而不是作为主要的备份策略。

### mongoexport 数据导出

#### 基础导出命令

根据数据用途和接收系统的需求，可以选择适当的文件格式进行数据导出，JSON 格式最为通用，CSV 格式便于数据分析。

```bash
# 导出为 JSON 格式
mongoexport --host localhost:27017 \
  --db production_db \
  --collection users \
  --out /export/users.json

# 导出为 JSON 数组
mongoexport --host localhost:27017 \
  --db production_db \
  --collection users \
  --jsonArray \
  --out /export/users_array.json

# 导出为 CSV 格式
mongoexport --host localhost:27017 \
  --db production_db \
  --collection users \
  --type=csv \
  --fields "name,email,created_at" \
  --out /export/users.csv

# 带认证的导出
mongoexport --host localhost:27017 \
  --username admin \
  --password "your_password" \
  --authenticationDatabase admin \
  --db production_db \
  --collection users \
  --out /export/users.json
```

#### 查询过滤导出

精确查询可以避免导出不必要的数据，特别是在进行数据分析或错误排查时十分有用。

```bash
# 导出特定条件的记录
mongoexport --host localhost:27017 \
  --db production_db \
  --collection users \
  --query '{ "status": "active", "created_at": { "$gte": { "$date": "2024-01-01T00:00:00Z" } } }' \
  --out /export/active_users.json

# 导出最近7天的数据
mongoexport --host localhost:27017 \
  --db production_db \
  --collection logs \
  --query '{ "timestamp": { "$gte": { "$date": "'$(date -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)'" } } }' \
  --out /export/recent_logs.json

# 排除特定字段
mongoexport --host localhost:27017 \
  --db production_db \
  --collection users \
  --fields="-_id,-password_hash,-salt" \
  --out /export/users_sensitive_removed.json
```

#### 分页和限制导出

在处理大数据集时，应避免一次性导出全部数据造成性能影响，可采用分批导出方式处理。

```bash
# 限制导出数量
mongoexport --host localhost:27017 \
  --db production_db \
  --collection users \
  --limit 1000 \
  --out /export/first_1000_users.json

# 跳过前 N 条记录
mongoexport --host localhost:27017 \
  --db production_db \
  --collection logs \
  --skip 50000 \
  --out /export/logs_from_50001.json

# 导出排序后的数据
mongoexport --host localhost:27017 \
  --db production_db \
  --collection users \
  --sort '{ "created_at": -1 }' \
  --limit 100 \
  --out /export/latest_100_users.json
```

#### 高级导出选项

合理配置导出选项可以提高导出效率并满足特定需求，如数据安全或系统负载控制。

```bash
# 导出时指定文件编码
mongoexport --host localhost:27017 \
  --db production_db \
  --collection users \
  --out /export/users.json \
  --quiet \
  --verbose

# 导出到压缩文件
mongoexport --host localhost:27017 \
  --db production_db \
  --collection users \
  --out /export/users.json

gzip /export/users.json

# 或者使用管道直接压缩
mongoexport --host localhost:27017 \
  --db production_db \
  --collection users | \
  gzip > /export/users.json.gz

# 分文件导出（按日期）
mongoexport --host localhost:27017 \
  --db production_db \
  --collection logs \
  --query '{ "date": "2024-01-15" }' \
  --out /export/logs_20240115.json

mongoexport --host localhost:27017 \
  --db production_db \
  --collection logs \
  --query '{ "date": "2024-01-16" }' \
  --out /export/logs_20240116.json
```

### mongoimport 数据导入

#### 基础导入命令

正确选择导入格式有助于提升数据导入效率，建议在导入前确认目标数据库是否有足够空间并做好相关备份。

```bash
# 导入 JSON 文件
mongoimport --host localhost:27017 \
  --db production_db \
  --collection users \
  --file /export/users.json

# 导入 JSON 数组
mongoimport --host localhost:27017 \
  --db production_db \
  --collection users \
  --file /export/users_array.json \
  --jsonArray

# 导入 CSV 文件
mongoimport --host localhost:27017 \
  --db production_db \
  --collection users \
  --type=csv \
  --headerline \
  --file /export/users.csv

# 导入 CSV 文件（指定字段）
mongoimport --host localhost:27017 \
  --db production_db \
  --collection users \
  --type=csv \
  --fields "name,email,age" \
  --file /export/users_no_header.csv

# 带认证的导入
mongoimport --host localhost:27017 \
  --username admin \
  --password "your_password" \
  --authenticationDatabase admin \
  --db production_db \
  --collection users \
  --file /export/users.json
```

#### 导入模式和验证

选择合适的导入模式能够实现不同的业务目标，在批量更新场景下尤为重要，需特别注意性能和安全性。

```bash
# 删除集合中原有数据后导入（覆盖模式）
mongoimport --host localhost:27017 \
  --db production_db \
  --collection users \
  --drop \
  --file /export/users.json

# 仅插入新记录（不覆盖）
mongoimport --host localhost:27017 \
  --db production_db \
  --collection users \
  --mode=insert \
  --file /export/new_users.json

# 合并/更新模式（根据_id更新）
mongoimport --host localhost:27017 \
  --db production_db \
  --collection users \
  --mode=upsert \
  --file /export/users_to_upsert.json

```

## 副本集备份及恢复
```
mongodb://用户名:密码@源节点1:端口,源节点2:端口,源节点3:端口/数据库?replicaSet=源RS名&authSource=admin
```

### 副本集数据导出

全量
```
mongodump \
  --uri="mongodb://user:pass@src1:27017,src2:27017,src3:27017/?replicaSet=rs0&authSource=admin" \
  --out=/data/migrate_backup \
  --oplog
```
指定库
```
mongodump \
  --uri="mongodb://user:pass@src1:27017,src2:27017,src3:27017/?replicaSet=rs0&authSource=admin" \
  --db=mydb \
  --out=/data/migrate_backup \
  --oplog
```
排除特定库
```
mongodump \
  --uri="mongodb://user:pass@src1:27017,src2:27017,src3:27017/?replicaSet=rs0&authSource=admin" \
  --excludeDatabase=admin \
  --out=/data/migrate_backup \
  --oplog
```
压缩导出
```
mongodump \
  --uri="mongodb://user:pass@src1:27017,src2:27017,src3:27017/?replicaSet=rs0&authSource=admin" \
  --excludeDatabase=admin \
  --out=/data/migrate_backup \
  --oplog --gzip
```

### 副本集数据导入

全量
```
mongorestore \
  --uri="mongodb://user:pass@dst1:27017,dst2:27017,dst3:27017/?replicaSet=rs1&authSource=admin" \
  --dir=/data/migrate_backup \
  --oplogReplay
```
指定库
```
mongorestore \
  --uri="mongodb://user:pass@dst1:27017,dst2:27017,dst3:27017/?replicaSet=rs1&authSource=admin" \
  --db=mydb \
  --dir=/data/migrate_backup/mydb \
  --drop \
  --oplogReplay
```

ubuntu 安装客户端工具
```
# 1. 创建缺失的目录
sudo mkdir -p /etc/apt/sources.list.d/

# 2. 重新添加 MongoDB 8.0 源
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] https://repo.mongodb.org/apt/ubuntu noble/mongodb-org/8.0 multiverse" | \
   sudo tee /etc/apt/sources.list.d/mongodb-org-8.0.list

# 3. 更新并安装
sudo apt-get update
sudo apt-get install -y mongodb-database-tools
```
