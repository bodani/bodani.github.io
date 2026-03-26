# 组复制降级 - 导出的sql文件中关闭 binlog 。

导出 sql 内容如下
```
SET @MYSQLDUMP_TEMP_LOG_BIN = @@SESSION.SQL_LOG_BIN;
SET @@SESSION.SQL_LOG_BIN= 0;

--
-- GTID state at the beginning of the backup 
--

SET @@GLOBAL.GTID_PURGED=/*!80000 '+'*/ '3fe37f9c-77f2-11f0-b048-ce130ea7b404:1-10,
8e97d6a3-77f2-11f0-b506-ce130ea7b404:1-1636922:1950241-1950310,
8e97e79d-77f2-11f0-b506-ce130ea7b404:1-20,
cabb3e3c-c8fe-11f0-9d27-12b6dcb5af12:1-55487';
```

## 分析

在使用 mysqldump 或 DataGrap 等间接使用 mysqldump 备份数据的时候 默认会加入 `SESSION.SQL_LOG_BIN= 0`。 导致主从数据库数据不一致。

```
mysqldump -u xxx  -pxxx -h xxxx --single-transaction --routines --triggers --events  --hex-blob     --default-character-set=utf8mb4     --max-allowed-packet=1073741824   --all-databases > /tmp/all_backup.sql
```


## 解决

mysqldump 备份的时候加入 参数 `--set-gtid-purged=OFF` 
