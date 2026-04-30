#### 备份恢复命令

```
备份：pg_dump -U postgres -v -F c -Z 4 -f ***.backup dbname  9压缩率最狠
恢复：pg_restore -U postgres -v -j 8 -d dbname ***.backup   8是采用8个线程

注意事项： 在恢复database前需要先创建好extentions

备份表：pg_dump -U postgres -t tablename dbname > 33.sql
恢复表：psql -U postgres -d dbname < 33.sql

只备份表结构 pg_dump -U postgres -s -t tablename dbname > 33.sql
只备份数据 pg_dump -U postgres -a -t tablename dbname > 33.sql
```

```
全库备份: pg_dumpall

只备份用户(角色)信息: pg_dumpall -g > roles.sql
```

#### 备份压缩并存储到 minio

```
  #!/bin/bash

  # PostgreSQL 设置
  # POSTGRES_USER="postgres"
  # POSTGRES_HOST="127.0.0.1"

  # MinIO 设置
  # MINIO_BUCKET="pgbackup"
  # MINIO_HOST="http://localhost:9000"
  # MINIO_ACCESS_KEY="admin123"
  # MINIO_SECRET_KEY="admin123"

  # 设置 MinIO 客户端别名
  mc alias set myminio $MINIO_HOST $MINIO_ACCESS_KEY $MINIO_SECRET_KEY

  # 创建以当前日期和时间命名的备份目录
  BACKUP_DIR="$(date +%Y%m%d%H%M)"
  MINIO_PATH="myminio/$MINIO_BUCKET/$BACKUP_DIR"

  # 备份全局对象
  echo "Backing up global objects to $MINIO_PATH/roles_globals.sql.gz"
  pg_dumpall -g -U "$POSTGRES_USER" -h "$POSTGRES_HOST" | pigz | mc pipe "$MINIO_PATH/roles_globals.sql.gz"

  # 获取所有非模板数据库的列表
  DATABASES=$(psql -U "$POSTGRES_USER" -h "$POSTGRES_HOST" -t -c "SELECT datname FROM pg_database WHERE datistemplate = false;")

  # 为每个数据库执行备份
  for DB in $DATABASES; do
    echo "Backing up $DB to $MINIO_PATH/$DB.sql.gz"
    pg_dump -U "$POSTGRES_USER" -h "$POSTGRES_HOST" "$DB" | pigz | mc pipe "$MINIO_PATH/$DB.sql.gz"
  done

  echo "Backup process completed!"
```

## copy 拷贝数据

```
数据拷贝到本地： psql -U postgres -d databasename  -p 5432 -h 10.1.1.1 -c "\copy (select * from $tablename where xxx) to '/tmp/db/$tablename.csv'";

数据拷贝到本地(加入csv 表头)： psql -U postgres -d databasename  -p 5432 -h 10.1.1.1 -c "\copy (select * from $tablename where xxx) to '/tmp/db/$tablename.csv' WITH (FORMAT CSV, HEADER, ENCODING 'UTF8')";

数据恢复到数据库: psql -U postgres -d databasename -p 5432 -h 127.0.0.1 -c "\copy $tablename from '/tmp/db/$tablename.csv'";
```

说明： copy 与 \copy 区别， \copy cvs 数据在 client 端、copy svs 数据在 server 端。

##### 注意事项: 需要在新数据库中对序列进行更新

```
psql -U postgres -d databasename -p 5432 -h 127. 0.0.1 -c "select setval('xxxx_id_seq', max(id)) from xxx_table";

```

copy from 数据量大时效率太低替代方法

```
/usr/pgsql-10/bin/pg_bulkload -U postgres -d dataname -i /xxx/xxx.csv -O tablename -l /tmp/xxx.log -P /tmp/xxx.bad -o "TYPE=CSV" -o $'DELIMITER=\t'
```

说明： pg_bulkload 为拓展形式。 需要在数据库中'create extends pg_bulkload' 。

## pg_bulkload 与 copy 区别

copy 将构造出的元组插入共享内存，同时写日志，pg_bulkload 绕过了共享内存，不写日志，这样会减少磁盘 I/O，但是也很危险。

##### 使用 pg_bulkload 方式导入数据时一定要注意，注意，注意！！！　由于不写 wal 日志从库无法同步，从库直接宕掉，直接宕掉！！！ 测试用就好,生产环境需谨慎

## 实时备份恢复

https://github.com/ossc-db/pg_rman

https://github.com/wal-e/wal-e

https://github.com/wal-g/wal-g

## 定期备份

https://github.com/postgrespro/pg_probackup

## 备份恢复管理

https://github.com/pgbackrest/pgbackrest

由于原始库中存在 extension 需要超级管理员权限进行恢复，恢复后将所有者变更为普通用户。
pg 中没有方法可以将整个 database 中 table 的 owner 进行修改，使用如下方法进行批量修改

批量修改表和视图的所有者

```
DO $$DECLARE r record;
BEGIN
FOR r IN SELECT tablename/viewname FROM pg_tables/pg_views WHERE schemaname = 'public'
LOOP
    EXECUTE 'alter table '|| r.tablename/r.viewname ||' owner to new_owner;';
END LOOP;
END$$;
```

---
