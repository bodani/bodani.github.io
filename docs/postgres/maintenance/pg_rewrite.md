# pg_rewrite - 在线表重写

## 概述

`pg_rewrite` 是一种 PostgreSQL 扩展工具，专门用于在不中断服务的情况下进行表重定义操作。与传统 `ALTER TABLE` 命令不同，它能够在数据迁移过程中保持对原表的读写访问权限，从而最小化业务影响。

### 核心特性

- **在线操作**：在表重写期间支持并发的读写访问
- **灵活变换**：支持改变列数据类型、调整列顺序、表分区等
- **零停机**：在最终原子替换前无需锁表
- **数据一致**：确保数据和变更的一致性
- **错误安全**：支持事务回滚机制

### 工作原理

`pg_rewrite` 的工作流程分为以下几个阶段：

#### 1. 准备阶段

- 验证源表和目标表的 replica identity
- 建立逻辑复制槽捕获变更
- 启动事务隔离所有操作

#### 2. 初始数据迁移阶段

- 将源表所有现有数据批量复制到目标表
- 检查约束并验证数据完整性
- 应用必要的类型转换

#### 3. 增量同步阶段

- 通过逻辑复制持续捕获源表上的 DML 变更（INSERT、UPDATE、DELETE）
- 将捕获到的变更实时应用到目标表
- 维持源表和目标表数据的一致性

#### 4. 最终原子替换阶段

- 获取表上所有访问的独占锁
- 应用最后剩余的所有变更
- 原子地交换源表和目标表的元数据信息
- 更新外键等相关的依赖对象

整个过程中，只有最后的原子替换阶段需要短暂的独占锁，这个阶段通常非常快，对业务影响极小。

### 应用场景

以下是使用 `pg_rewrite` 进行表重写的几个典型应用场景：

#### 数据类型修改

当原有列的数据类型接近容量极限时，如从 INTEGER 转换为 BIGINT。传统的 `ALTER TABLE` 命令在此类操作时会阻止表的读写访问，而 `pg_rewrite` 可以实现无缝升级。

#### 表分区改造

当发现单一表变得过大且适合进行分区设计时，可以使用 `pg_rewrite` 将普通表转换为分区表而不中断应用服务。

#### 调整列顺序

如果发现调整表中列的顺序能够显著减少磁盘空间占用（由于减少了填充字节），则可使用 `pg_rewrite` 实现该优化。

#### 表空间移动

与传统的 `ALTER TABLE ... SET TABLESPACE` 类似，但可以实现零停机时间，将表从一个表空间移到另一个表空间。

### 支持的操作组合

`pg_rewrite` 支持在一个操作中组合多种需求，例如：

- 同时修改多个列的数据类型
- 改变列顺序并移动到新表空间
- 迁移到分区表的同时修改字段类型

## 安装部署

### 前置要求

- PostgreSQL 服务器版本必须是 13 或更高版本
- 需要拥有 pg_config 二进制文件（通常在 PostgreSQL 开发包中）
- 系统需要支持 PostgreSQL 扩展功能

### 编译安装

```bash
# 克隆项目代码
git clone https://github.com/cybertec-postgresql/pg_rewrite.git
cd pg_rewrite

# 获取最新稳定版本（注意根据实际情况替换版本号）
git checkout <latest_stable_version>

# 编译和安装
make
make install
```

### 配置数据库参数

将以下参数添加到 `postgresql.conf` 配置文件中：

```ini
wal_level = logical
max_replication_slots = 1    # 或在当前值基础上加 1
shared_preload_libraries = 'pg_rewrite'  # 或添加到现有扩展列表中
```

### 重启服务

重启 PostgreSQL 集群使配置生效：

```bash
# 使用适当的命令重启服务
sudo systemctl restart postgresql
```

### 激活扩展

连接到目标数据库执行以下 SQL 语句激活扩展：

```sql
CREATE EXTENSION pg_rewrite;
```

## 基础用法

### 核心函数

主要函数是 `rewrite_table(source_table, target_table, backup_table_name)`，它执行以下操作：

- 将所有行从源表（source_table）复制到目标表（target_table）

```
-- 类似代码
INSERT INTO target_table SELECT * FROM source_table;
```

- 应用所有在数据迁移期间发生的数据变更（INSERT、UPDATE、DELETE）到目标表
- 锁定源表阻止新的读写访问
- 将源表重命名为备份表名，目标表重命名为源表原始名字

```
-- 类似代码
-- 原子操作，两个重命名同时生效
ALTER TABLE source_table RENAME TO backup_table_name;
ALTER TABLE target_table RENAME TO source_table;
```

完成原子替换操作

### 简单表转换

假设有一张表定义如下：

```sql
CREATE TABLE measurement (
    id              int,
    city_id         int not null,
    logdate         date not null,
    peaktemp        int,
    PRIMARY KEY(id, logdate)
);
```

现在需要将其转换为分区表，并将 id 列的类型改为 bigint：

```sql
-- 创建带分区和类型更改的新表结构
CREATE TABLE measurement_aux (
    id              bigint,
    city_id         int not null,
    logdate         date not null,
    peaktemp        int,
    PRIMARY KEY(id, logdate)
) PARTITION BY RANGE (logdate);
```

接下来为当前存在于 measurement 表中的所有行以及可能在处理期间插入的数据创建分区：

```sql
CREATE TABLE measurement_y2006m02 PARTITION OF measurement_aux
    FOR VALUES FROM ('2006-02-01') TO ('2006-03-01');

CREATE TABLE measurement_y2006m03 PARTITION OF measurement_aux
    FOR VALUES FROM ('2006-03-01') TO ('2006-04-01');

-- 继续添加其他时间的分区...
```

> 注意：源表（measurement）和目标表（measurement_aux）都必须有一个 replica identity。replica identity 用于处理应用程序在数据复制过程中的变更。如果表的 replica identity 设置为 DEFAULT 或 FULL，则主键约束提供了 identity 索引；否则如果表没有主键，需要使用 ALTER TABLE ... REPLICA IDENTITY USING INDEX ... 命令显式设置身份索引。

> 源表和目标表的身份索引的关键（列列表）必须相同。

执行表重写操作：

```sql
SELECT rewrite_table('measurement', 'measurement_aux', 'measurement_old');
```

## 约束处理

正确的约束管理是 `pg_rewrite` 成功运行的关键要素。

### 主键、唯一性约束

强烈建议在调用 `rewrite_table()` 之前向目标表添加源表的 PRIMARY KEY、UNIQUE 和 EXCLUDE 约束。这些约束在重写过程中强制执行，任何违反都将导致 `rewrite_table()` 失败并回滚。

### NOT NULL 约束

- PostgreSQL 版本 17 或更低：需提前添加 NOT NULL 约束到目标表
- PostgreSQL 版本 18 或更高：约束自动创建，需要后续验证

rewrite_table() 在此过程中绕过了 NOT NULL 约束的验证，但由于原始表中的数据已经满足约束，迁移过来的数据也会符合。

### 检查约束

CHECK 约束会由 `rewrite_table()` 自动（根据源表定义）在所有数据变更应用完成后创建。但是，这些约束会以 NOT VALID 状态创建，需要使用如下命令手动验证：

```sql
ALTER TABLE table_name VALIDATE CONSTRAINT constraint_name;
```

延迟验证是为了避免长时间锁定表带来的影响。

### 外键约束

外键约束也是自动生成的，并且处于 NOT VALID 状态，需要用以下命令验证：

```sql
ALTER TABLE table_name VALIDATE CONSTRAINT foreign_key_constraint_name;
```

特殊情况下，如果引用表是分区表且 PostgreSQL 版本小于 18，该版本尚不支持分区表上带有 NOT VALID 选项的外键约束，需要在重写完成后手动添加外键。

### 处理源表外键

建议删除涉及源表的所有外键，因为表会被重命名，应用不会更新原表，外键可能引起意外错误。

## 监控进度

对于执行时间较长的表重写操作，可以使用 `pg_rewrite_progress` 视图检查进度：

```sql
SELECT * FROM pg_rewrite_progress;
```

视图中的列包括：

- `src_table`: 源表名（对应第一个参数）
- `dst_table`: 目标表名（对应第二个参数）
- `src_table_new`: 备份表名（对应第三个参数）
- `ins_initial`: 初始迁移阶段插入的目标表记录数量
- `ins`: 应用程序在处理期间的新增数量
- `upd`: 更新操作数量
- `del`: 删除操作数量

这些"并发数据变化"也被同步到了分区表中以保证一致性。

## 配置参数

`pg_rewrite` 提供了一些 GUC 配置参数来控制系统行为：

### rewrite.max_xlock_time

**请在业务低峰期进行此操作！！！**

尽管正在处理的表,大部分时间可供读写操作访问，但在最终阶段需要独占锁（即进行表重命名），此时阻塞所有读写访问。

正常情况下这个阶段非常短暂，用户几乎无法察觉。

但如果在系统等待锁时源表发生了大量的变更，那么最终处理阶段的时长将成比例增长。关键在于这些变更必须在释放独占锁之前传播到目标表。

如果该扩展功能明显阻塞了表访问，考虑设置 `rewrite.max_xlock_time` 参数：

```sql
SET rewrite.max_xlock_time TO 100;  -- 100ms
```

这个设置表示排他锁不应持有超过 0.1 秒（100 毫秒）。如果最终阶段需要更多时间，该特定函数将释放独占锁，在两次尝试之间处理其他事务的提交更改，然后再尝试最终阶段。

若超出次数过多会报错，这时需要增加设置值或选择写入活动较低的时间处理。

默认值为 0，表示最终阶段可以按需占用任意时间。

## 实战示例与具体实践

### 实例 1：整数扩容（int到bigint）

这是一个典型的数据库维护需求，下面提供完整、详细的实际操作过程：

**第1步：准备工作**

首先检查表的状态和数据类型情况：
以下是我们示例中使用的 user_accounts 表的详细结构和一些测试数据：

**user_accounts 表结构：**

```sql
-- 示例中的原表结构定义
CREATE TABLE user_accounts (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status INTEGER DEFAULT 1,
    profile_data JSONB
);
```

**插入数据：**

```sql
-- 插入更多数据到接近限制的情况
INSERT INTO user_accounts (username, email, profile_data)
SELECT
    'user_' || generate_series,
    'user' || generate_series || '@company.com',
    jsonb_build_object('age', (20 + generate_series % 50), 'department',
                      (array['IT','HR','Finance','Sales','Marketing','Operations'])[((generate_series-1)%6)+1])
FROM generate_series(11, 1000);

-- 现在我们可以查询用户账户信息
SELECT user_id, username, email, created_at, status FROM user_accounts ORDER BY user_id LIMIT 10;
```

**添加适当的 replica identity（用于 pg_rewrite 正确跟踪变更）：**

```sql
-- 如果没有主键，需要指定 replica identity（这里我们已经有主键所以不需要）
-- ALTER TABLE user_accounts REPLICA IDENTITY USING INDEX user_accounts_pkey;
```

现在开始实际的转换操作：

```sql
-- 检查原表的结构和数据情况
\d user_accounts
SELECT COUNT(*) FROM user_accounts;
SELECT MAX(user_id) FROM user_accounts;

-- 评估是否需要转换
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'user_accounts' AND column_name = 'user_id';
```

**第2步：检查 Replica Identity 设置**

检查是否已有合适的 Replica Identity（这是确保 pg_rewrite 正确工作的重要步骤）：

```sql
-- 查看当前的 Replica Identity 设置
SELECT
    relname AS tablename,
    relreplident AS replica_identity_code,
    CASE relreplident
        WHEN 'd' THEN 'default (使用主键)'
        WHEN 'n' THEN 'nothing (无副本标识)'
        WHEN 'f' THEN 'full (全行作为标识)'
        WHEN 'i' THEN 'index (使用特定索引)'
    END AS replica_identity_desc
FROM pg_class
WHERE relname = 'user_accounts'
AND relkind = 'r';

-- 检查是否存在合适的标识符
SELECT c.attname, c.attnum, ci.indisreplident, ci.indisprimary, ci.indisunique
FROM pg_class r, pg_attribute c, pg_index ci
WHERE r.oid = c.attrelid AND r.relname = 'user_accounts'
AND r.oid = ci.indrelid AND c.attnum = ANY(ci.indkey)
ORDER BY r.relname, c.attnum;

--
SELECT
    relname,
    relreplident,
    CASE relreplident
        WHEN 'd' THEN '✅ 可以使用（pg_rewrite 接受）'
        WHEN 'i' THEN '✅ 可以使用（pg_rewrite 接受）'
        WHEN 'f' THEN '⚠️ 可以使用但性能差'
        WHEN 'n' THEN '❌ 必须修改！pg_rewrite 会失败'
    END AS pg_rewrite_status
FROM pg_class
WHERE relname = 'user_accounts';

```

**第3步：创建目标表**

根据原表创建具有目标数据类型的表格：

```sql
-- 创建具有更大整数类型的新表，保留所有的列和约束，但改变user_id为bigint
CREATE TABLE user_accounts_new (
    user_id BIGINT GENERATED ALWAYS AS IDENTITY,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status INTEGER DEFAULT 1,
    profile_data JSONB,
    CONSTRAINT pk_user_accounts_new PRIMARY KEY (user_id)
);
```

**第4步：执行 pg_rewrite**

启动重写过程：

```sql
SELECT rewrite_table('user_accounts', 'user_accounts_new', 'user_accounts_backup');
```

**第5步：验证数据迁移**
清理 user_accounts_backup 原表的备份

### 实例 2： 普通表转换为分区表

订单表进行分区
**第1步：检查源表**

```sql
--  创建源表（普通表）
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    order_date DATE NOT NULL,
    customer_id INTEGER NOT NULL,
    total_amount DECIMAL(10,2),
    discount_percent INTEGER DEFAULT 0,
    notes TEXT
);
--  插入测试数据
INSERT INTO orders (order_date, customer_id, total_amount, discount_percent, notes)
SELECT
    CURRENT_DATE - (random() * 365 * 5)::INTEGER,
    (random() * 1000)::INTEGER + 1,
    (random() * 1000)::DECIMAL(10,2),
    (random() * 30)::INTEGER,
    'Order ' || generate_series
FROM generate_series(1, 10000);

CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_orders_customer ON orders(customer_id);
-- 检查数据分布以确定最佳分区策略
SELECT
    CONCAT(EXTRACT(YEAR FROM order_date)) as year,
    count(*) as record_count
FROM orders
GROUP BY 1 ORDER BY 1 DESC;
```

**第2步：检查 Replica Identity 设置**

```
SELECT
    EXTRACT(YEAR FROM order_date) as year,
    COUNT(*) as record_count,
    pg_size_pretty(pg_total_relation_size('orders')) as table_size
FROM orders
GROUP BY 1 ORDER BY 1;
--  检查副本标识（关键！）
SELECT
    relname,
    relreplident,
    CASE relreplident
        WHEN 'd' THEN '✅ 已设置'
        WHEN 'n' THEN '❌ 需要设置'
        ELSE '⚠️ 其他状态'
    END as status
FROM pg_class WHERE relname = 'orders';
```

**第3步：设计新的表结构**

```sql
--  创建分区表
CREATE TABLE orders_partitioned (
    order_id BIGINT NOT NULL,
    order_date DATE NOT NULL,
    customer_id INTEGER NOT NULL,
    total_amount DECIMAL(10,2),
    discount_percent INTEGER DEFAULT 0,
    calculated_discount DECIMAL(10,2) GENERATED ALWAYS AS (
        total_amount * (discount_percent::DECIMAL / 100)
    ) STORED,
    notes TEXT,
    -- 分区表主键必须包含分区键
    CONSTRAINT pk_orders_partitioned PRIMARY KEY (order_id, order_date)
) PARTITION BY RANGE (order_date);
-- 创建分区（简化：只创建3个年分区）
CREATE TABLE orders_part_2022 PARTITION OF orders_partitioned
    FOR VALUES FROM ('2022-01-01') TO ('2023-01-01');
CREATE TABLE orders_part_2023 PARTITION OF orders_partitioned
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');
CREATE TABLE orders_part_2024 PARTITION OF orders_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
-- 创建默认分区（接收其他年份数据）
CREATE TABLE orders_part_default PARTITION OF orders_partitioned DEFAULT;
```

**第4步：创建初始分区**

为当前数据覆盖时间范围内的年月创建分片：

```sql
-- 假设有2020-2025年的数据，分别创建每个年度的月份分片
DO $$
DECLARE
    year INTEGER;
    month INTEGER;
BEGIN
    FOR year IN 2020..2025 LOOP
        FOR month IN 1..12 LOOP
            EXECUTE format(
                'CREATE TABLE orders_y%sm%s PARTITION OF orders_restructured ' ||
                'FOR VALUES FROM (%L) TO (%L)',
                LPAD(year::TEXT, 4, '0'),
                LPAD(month::TEXT, 2, '0'),
                format('%s-%s-01', year, LPAD(month::TEXT, 2, '0')),
                format('%s-%s-01',
                       CASE WHEN month=12 THEN year+1 ELSE year END,
                       LPAD(CASE WHEN month=12 THEN 1 ELSE month+1 END::TEXT, 2, '0'))
            );
        END LOOP;
    END LOOP;
END $$;
```

**第4步：执行 pg_rewrite**
启动重写过程：

```sql
-- 确保外键已临时禁用或被合理处理后执行
SELECT rewrite_table('orders', 'orders_restructured', 'orders_old');
```

**第5步：验证数据迁移**

## 专家级技巧与经验分享

### 避免锁升级策略

在高并发写入环境中应用 pg_rewrite：

1. 首先将 `max_xlock_time` 调整为合理的阈值（如 100ms），防止长时间互斥锁阻塞应用
2. 利用应用层控制窗口，将写入流量控制在较低水平下进行转换
3. 考虑在低峰时段进行转换以进一步降低风险
4. 关闭表的autovacuum。 可能带来额外的麻烦

## 局限性和注意事项

### 当前已知限制

- 如果目标表是分区表，则不允许将其外部分区(外部表)作为分区使用
- 索引不会自动重命名：当目标表重命名为源表名时，其索引不会重命名以匹配源表。如有需要，使用 ALTER INDEX 重命名。

### 并发限制

- 重写进行期间应避免运行 ALTER TABLE 命令，以防止死锁
- 允许 MVCC-unsafe 操作（参照 MVCC 注意事项文档的第一段）

### 适用范围

虽然 `pg_rewrite` 能够满足大多数表改造需求，但对于一些复杂场景仍需要考虑：

- 大型分区表转换
- 涉及复杂的外键关系链
- 在高并发写入环境下长时间运行的操作
- 对于系统表的修改操作

## 最佳实践

### 预防措施

1. 在生产环境中使用前，先在测试环境中进行全面验证
2. 确保目标表具备完整的约束定义
3. 评估所需的额外存储空间
4. 检查数据类型的转换兼容性
5. 考虑对备份策略的影响

### 性能考量

- 确保系统有足够的 IO 能力来支持复制槽的日志处理
- 在业务低峰期进行操作
- 监控系统资源使用情况

### 风险控制

- 保留原始数据的备份
- 准备回滚方案
- 验证数据完整性后再清理备份表

## 总结

`pg_rewrite` 是一个强大的 PostgreSQL 在线表重定义工具，特别适用于需要维持高可用性的生产环境。它提供了灵活的方式来进行各种类型的表结构变更，最小化业务中断时间。正确理解其工作原理和使用方法，可以在不影响应用服务的情况下完成复杂的数据库维护任务。

在实际操作中，请务必遵循本文档中提到的具体实践指南和最佳做法，这将极大提升表重写过程的成功率，保障系统稳定。
