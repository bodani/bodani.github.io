# pg_repack

pg_repack 是 PostgreSQL 的一个扩展工具，用于在线重组表和索引，解决表膨胀问题，而无需锁定整个表。

## 作用

- Online CLUSTER (ordered by cluster index)
- Ordered by specified columns
- Online VACUUM FULL (packing rows only)
- Rebuild or relocate only the indexes of a table

实际生产中重要是用来代替 vacuum full 进行存储空间整理，让数据更紧凑有序。并且释放存储空间给磁盘。在这个过程中不会锁表或长时间阻塞业务操作。

## 原理

pg_repack 通过创建一个新的表结构，将原表数据按顺序复制到新表中，然后通过原子性的重命名操作替换原表，从而实现在线重组。具体步骤如下：

1.  create a log table to record changes made to the original table
2.  add a trigger onto the original table, logging INSERTs, UPDATEs and DELETEs into our log table
3.  create a new table containing all the rows in the old table
4.  build indexes on this new table
5.  apply all changes which have accrued in the log table to the new table
6.  swap the tables, including indexes and toast tables, using the system catalogs
7.  drop the original table

## 应用

### 注意事项

- Only superusers or owners of tables and indexes can use the utility. To run pg_repack as an owner you need to use the option --no-superuser-check.
- Target table must have a PRIMARY KEY, or at least a UNIQUE total index on a NOT NULL column.

### 安装

对应数据库版本，直接安装就可以。

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql-17-repack  # 根据实际PostgreSQL版本调整

# CentOS/RHEL
sudo yum install pg_repack_17  # 根据实际PostgreSQL版本调整

```

### 使用方法

```
# 在需要进行repack 的database中 创建拓展
create extentions pg_repack
```

```bash
# 基本语法
pg_repack [OPTION]... [DBNAME]

```

````bash
# 常用选项
pg_repack -d database_name -t table_name    # 重组指定表
pg_repack -d database_name -c schema_name   # 重组指定模式下的所有表    ```bash
pg_repack -d database_name -a                  # 重组数据库中的所有表
pg_repack -d database_name --tablespace=ts_name # 将重组后的表移动到指定表空间
````

#### 常用参数

```

# 测试，不实际执行
-N, --dry-run print what would have been repacked

# 打印执行过程的详细信息
-e, --echo echo queries
```

## 拓展应用案例

### 数据迁移

将表数据从一个目录中迁移到另一个工作目录,

注意事项，如果是主从架构。各个数据库实例的多个目录结构要保持一致，这是表空间的要求。

```
  -s, --tablespace=TBLSPC            move repacked tables to a new tablespace
  -S, --moveidx                      move repacked indexes to TBLSPC too

```

#### 在 主库、备库 1、备库 2 上分别执行：

```
sudo mkdir -p /data/pgdata/pg_tblspc/new_fast_ssd
```

#### 确保目录属主为运行 PostgreSQL 的用户（通常是 postgres）

```
sudo chown postgres:postgres /data/pgdata/pg_tblspc/new_fast_ssd
sudo chmod 700 /data/pgdata/pg_tblspc/new_fast_ssd
```

### 只保留部分数据

原始方式，根据需求删除表中非保留数据。 然后利用 pg_repack 进行空间整理。

缺点： 删除过程耗时耗力，对数据库的性能影响也较大，并会产生大量的 WAL 日志和锁等待。 尤其是保留数据的占比只是一小部分的时候，需要删除大量数据。

改进方法:

分析 pg_repack 源代码。 代码结构有两部分 bin 目录为客户端，lib 目录下为服务端代码。

主要是对于修改这步的逻辑

3.  create a new table containing all the rows in the old table

对应的代码位置为 `lib/pg_repack.sql.in ` 安装后具体位置 /usr/share/postgresql/17/extension/pg_repack--1.5.2.sql

```
'INSERT INTO repack.table\_' || R.oid || ' SELECT ' || repack.get_columns_for_create_as(R.oid) || ' FROM ONLY ' || repack.oid2text(R.oid) AS copy_data,
```

这是将原始数据导入到新表中。

修改对于 sql 加入 where 过滤条件 如: 根据 created_time 字段保留 时间 2025-10-23 之后的数据。

```
'INSERT INTO repack.table_' || R.oid || ' SELECT ' || repack.get_columns_for_create_as(R.oid) || ' FROM ONLY ' || repack.oid2text(R.oid) || format(' WHERE created_time > %L', '2025-10-23 00:00:00'::timestamp)  AS copy_data,

```

确保非保留数据不在变动，否则数据重放阶段可能出问题，找不到更新的数据。（待验证）

注意，有外键数据约束的情况。
