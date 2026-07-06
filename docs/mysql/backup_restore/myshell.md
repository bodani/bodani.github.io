# MySQL 8.0 逻辑备份与恢复（MySQL Shell）


---

## 一、环境准备

### 1.1 源库与目标库要求

| 项目 | 要求 |
|------|------|
| MySQL Server | 8.0.x（建议源/目标版本一致或目标版本 ≥ 源版本） |
| MySQL Shell | 8.0.x（建议与 Server 版本接近） |
| 备份用户权限 | `RELOAD`, `LOCK TABLES`, `BACKUP_ADMIN`, `SELECT`, `SHOW VIEW`, `TRIGGER`, `EVENT`, `PROCESS` |
| 恢复用户权限 | 目标库需具备 `CREATE`, `DROP`, `ALTER`, `INSERT`, `INDEX`, `TRIGGER`, `EVENT`, `CREATE ROUTINE`, `EXECUTE` 等权限 |
| 目标库参数 | `local_infile = ON`（恢复前必须开启） |

### 1.2 检查目标库 local_infile

在目标库执行：

```sql
SHOW VARIABLES LIKE 'local_infile';
-- 若值为 OFF，需修改为 ON
SET GLOBAL local_infile = ON;
-- 或在 my.cnf 中永久配置：
[mysqld]
local_infile = ON
```

---

## 二、备份阶段（源库）


### 登录并连接数据库

```shell
mysqlsh -h xxx -u xx -pxx
```

### 2.1 备份命令

```javascript
util.dumpInstance("/data/backup/mysql_dump", {
    threads: 4,
    maxRate: "8M",
    compression: "zstd",          
    consistent: true,              
    users: true,                  
    excludeSchemas: [
        "mysql_innodb_cluster_metadata",
        "sys",
        "information_schema",
        "performance_schema",
        "mondb"
    ],
    compatibility: [
        "strip_restricted_grants",
        "strip_definers",
        "ignore_missing_pks"
    ]
});
```

### 2.2 参数说明

| 参数 | 说明 |
|------|------|
| `threads` | 并行备份线程数，建议根据 CPU 和磁盘 I/O 调整（默认 4） |
| `maxRate` | 单线程读取限速，如 `"8M"` 表示每线程 8 MB/s，避免影响线上业务 |
| `compression` | `zstd`（默认，压缩比高）、`gzip`、`none`。备份文件自动压缩 |
| `consistent` | `true` 时加全局读锁保证一致性（默认），`false` 适合从库或允许短暂不一致， 默认true |
| `users` | 是否不导出用户/角色/权限，默认true |
| `excludeSchemas` | 排除系统库和不需要的业务库（如 `mondb`） |
| `compatibility` | `strip_restricted_grants` 移除受限权限；`strip_definers` 移除视图/存储过程 DEFINER；`ignore_missing_pks` 忽略无主键表 |

### 2.3 备份输出结构

备份目录会自动创建，结构如下：

```
/data/backup/mysql_dump/
├── @.json                    # 备份元数据
├── @.done.json               # 完成标记
├── @.sql                     # 全局 DDL（如创建数据库）
├── db1/
│   ├── @.done.json
│   ├── table1@00000.tsv.zst  # 压缩后的数据文件
│   ├── table1@@.json         # 表元数据
│   └── table1.sql            # 表结构 DDL
├── db2/
│   └── ...
└── ...
```

> **注意**：当 `users: false` 时，**不会生成 `@.users.sql`**

### 2.4 仅备份指定库（可选）

若不需要全实例备份，可使用 `util.dumpSchemas`：

```javascript
util.dumpSchemas(
    ["db1", "db2", "db3"],
    "/data/backup/schema_dump_20260622",
    {
        threads: 4,
        compression: "zstd",
        users: false,
        compatibility: ["strip_restricted_grants", "strip_definers", "ignore_missing_pks"]
    }
)
```

---

## 三、数据传输阶段

### 3.1 打包压缩（源服务器）

备份目录本身已包含 `zstd` 压缩的数据文件，但为传输方便，可整体打包：

```bash
# 进入备份目录父路径
cd /data/backup

# 打包（保留目录结构）
tar -czf mysql_dump.tar.gz mysql_dump

# 或仅打包不二次压缩（因为内部已是 zstd）
tar -cf mysql_dump.tar mysql_dump
```

### 3.2 传输到目标服务器

```bash
# 方式一：scp
scp mysql_dump.tar.gz user@target_host:/data/backup/

# 方式二：rsync（推荐大文件/断点续传）
rsync -avz --progress mysql_dump/ user@target_host:/data/backup/mysql_dump/
```

### 3.3 解压（目标服务器）

```bash
cd /data/backup
# 若使用了 tar.gz
tar -xzf mysql_dump.tar.gz

# 若使用了 rsync 直接传目录，则无需解压
```

---

## 四、恢复阶段（目标库）

### 登录并连接数据库

```shell
mysqlsh -h xxx -u xx -pxx
```
### 4.1 推荐恢复命令

```javascript
util.loadDump("/data/backup/mysql_dump", {
    threads: 4,
    loadDdl: true,  
    loadData: true,        
    loadUsers: false,      
    ignoreExistingObjects: false, 
    resetProgress: true    
});
```

### 4.2 恢复参数说明

| 参数 | 说明 |
|------|------|
| `threads` | 并行恢复线程数，建议与备份时一致或根据目标库性能调整 |
| `loadDdl` | 是否导入表结构、视图、存储过程等 DDL（默认 `true`） |
| `loadData` | 是否导入表数据（默认 `true`） |
| `loadUsers` | **关键**：默认 `false`，不导入备份中的用户，**完全保留目标库现有账户** |
| `ignoreExistingObjects` | `false`（默认）遇到已存在对象报错；`true` 跳过 |
| `resetProgress` | `true` 时忽略断点续传进度文件，从头恢复 |
| `skipBinlog` | `true` 时恢复过程不写 binlog（默认 `false`） |
| `updateGtidSet` | GTID 同步策略：`off`（默认）、`replace`、`append` |

### 4.3 保留目标库账户

有些场景要避免将目标库的账号覆盖掉，比如mgr的组复制，或重要的管理账号等。

备份文件包含完整用户定义，必要时可手动执行 `@.users.sql` 做用户迁移。

---

## 五、恢复后验证

### 5.1 检查数据完整性

```sql
-- 目标库执行：对比表数量和记录数
SELECT table_schema, COUNT(*) AS table_count 
FROM information_schema.tables 
WHERE table_schema NOT IN ('mysql','sys','information_schema','performance_schema')
GROUP BY table_schema;

-- 检查关键表记录数
SELECT COUNT(*) FROM db1.table1;
```

### 5.2 验证目标库用户未被覆盖

```sql
-- 检查用户列表应与恢复前一致
SELECT user, host FROM mysql.user ORDER BY user;

-- 检查关键用户权限
SHOW GRANTS FOR 'app_user'@'%';
```

### 5.3 检查恢复日志

MySQL Shell 恢复时会输出进度和警告，重点关注：
- `Skipping CREATE/ALTER USER statements` — 正常，说明用户被跳过
- `Recreating indexes - done` — 索引重建完成
- `0 warnings were reported during the load` — 无警告最佳

---

## 六、常见问题与处理

### Q1: 恢复时报 "Duplicate objects found in destination database"

**原因**：目标库已存在同名库/表，且 `ignoreExistingObjects` 为 `off`。

**处理**：
- 若确认要覆盖：恢复前手动 `DROP DATABASE` 或设置 `ignoreExistingObjects: "drop"`
- 若只想增量更新：目前 `util.loadDump` 不支持增量，需手动处理

### Q2: 如何只恢复部分库？

```javascript
util.loadDump("/data/backup/full_dump", {
    includeSchemas: ["db1", "db2"],  // 仅恢复指定库
    loadUsers: false,
    threads: 4
})
```
### Q3: 备份文件能否直接用于 `mysql` 命令行导入？

**不能**。`util.dumpInstance` 生成的格式是 MySQL Shell 专用的（分块 TSV + zstd 压缩），必须使用 `util.loadDump` 恢复。

### Q4: 无主键表备份失败？

已在 `compatibility` 中加入 `ignore_missing_pks`，或备份时设置 `chunking: false` 对该表禁用分块。

### Q5: 恢复过程中断，如何断点续传？

默认会自动从进度文件（`load-progress.<uuid>.progress`）继续。如需从头开始：

```javascript
util.loadDump("/data/backup/dump", { resetProgress: true, threads: 4 })
```
---

## 七、一键脚本示例

### 7.1 备份脚本（源库）

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/data/backup/mysql_dump_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="/data/backup/backup.log"

mysqlsh --uri=backup_user@source_host:3306 --js <<EOF
util.dumpInstance("${BACKUP_DIR}", {
    threads: 4,
    maxRate: "8M",
    compression: "zstd",
    consistent: true,
    users: false,
    excludeSchemas: [
        "mysql_innodb_cluster_metadata",
        "sys",
        "information_schema",
        "performance_schema"
    ],
    compatibility: [
        "strip_restricted_grants",
        "strip_definers",
        "ignore_missing_pks"
    ]
})
EOF

echo "Backup completed: ${BACKUP_DIR}" >> ${LOG_FILE}
```

### 7.2 恢复脚本（目标库）

```bash
#!/bin/bash
# restore.sh
DUMP_DIR="$1"
LOG_FILE="/data/backup/restore.log"

mysqlsh --uri=root@target_host:3306 --js <<EOF
util.loadDump("${DUMP_DIR}", {
    threads: 4,
    loadDdl: true,
    loadData: true,
    loadUsers: false,
    ignoreExistingObjects: "off",
    resetProgress: true
})
EOF

echo "Restore completed from: ${DUMP_DIR}" >> ${LOG_FILE}
```

---