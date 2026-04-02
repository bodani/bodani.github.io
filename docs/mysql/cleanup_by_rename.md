# MySQL 数据清理（Rename 方案）

> 适用于 MySQL 8.0.34+，通过建新表+导入保留数据+Rename 切换，避免 DELETE 大量数据的性能问题

## 前置检查

```sql
-- 确认表结构
DESCRIBE old_table;
SHOW INDEX FROM old_table;

-- 确认数据分布
SELECT 
    COUNT(*) AS total_rows,
    COUNT(CASE WHEN id <= 1000 THEN 1 END) AS keep_rows
FROM old_table;

-- 确认磁盘空间（需大于表大小 × 2）
SELECT 
    ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024 / 1024, 2) AS size_gb 
FROM information_schema.TABLES 
WHERE table_name = 'old_table' AND table_schema = DATABASE();
```

## 操作步骤

### 1. 创建新表

```sql
CREATE TABLE new_table LIKE old_table;

-- 验证结构
SHOW CREATE TABLE new_table\G
```

### 2. 导入保留数据

```sql
-- 小数据量（< 100万行）
INSERT INTO new_table 
SELECT * FROM old_table 
WHERE id <= 1000;

-- 大数据量（分批导入）
INSERT INTO new_table SELECT * FROM old_table WHERE id BETWEEN 1 AND 100000;
INSERT INTO new_table SELECT * FROM old_table WHERE id BETWEEN 100001 AND 200000;
-- ...
```

### 3. 数据校验

```sql
-- 行数核对
SELECT 
    (SELECT COUNT(*) FROM new_table) AS new_count,
    (SELECT COUNT(*) FROM old_table WHERE id <= 1000) AS old_count;

-- 抽查数据一致性
SELECT o.id, o.col1, n.col1 
FROM old_table o 
JOIN new_table n ON o.id = n.id 
WHERE o.id IN (100, 500, 999);
```

### 4. Rename 切换

```sql
-- 原子切换（秒级完成）
RENAME TABLE 
    old_table TO old_table_bak_$(date +%Y%m%d),
    new_table TO old_table;

-- 验证
SHOW TABLES LIKE 'old_table%';
SELECT COUNT(*) FROM old_table;
```

## 回滚

```sql
-- 如出现问题，立即回滚
RENAME TABLE 
    old_table TO new_table_err,
    old_table_bak_$(date +%Y%m%d) TO old_table;
```

## 清理

```sql
-- 确认业务正常后，删除备份表
DROP TABLE old_table_bak_$(date +%Y%m%d);
```

## 按时间清理示例

```sql
-- 保留 90 天内数据
CREATE TABLE new_table LIKE old_table;

INSERT INTO new_table 
SELECT * FROM old_table 
WHERE create_time >= DATE_SUB(NOW(), INTERVAL 90 DAY);

RENAME TABLE old_table TO old_table_bak, new_table TO old_table;
```
