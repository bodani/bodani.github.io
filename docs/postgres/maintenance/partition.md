# 声明式分区表

在现代数据库管理中，数据量不断增长导致单表性能下降成为常见的问题。PostgreSQL 的表分区功能可以帮助将大表拆分成更小的、更易管理的部分，从而提高性能并简化数据管理。

## 表分区的意义

表分区是指将一个大表的数据按照一定的规则分布在多个物理子表中，但在逻辑上仍然被视为一个表。这种方式带来诸多益处：

- **性能优化**：减少扫描的数据量，提升查询速度
- **管理简便**：易于管理和维护数据生命周期
- **数据局部性**：减少锁竞争
- **索引局部性**：较小的索引可提升索引命中率
- **批量删除高效**：可以直接删除整个分区来清除数据
- **并发提升**：不同分区的访问可并行进行

PostgreSQL 自 10 版本开始提供原生的分区支持，之后的版本也持续对其功能和性能进行改进，目前已成为处理大规模数据的理想手段。

## 分区表设计

在设计分区表时，正确处理主键、唯一约束、索引和序列是确保数据完整性和查询性能的重要环节。

### 分区键选取

应当基于表的常用查询模式选择合适的分区键，如记录的创建时间、区域编码等。分区键最好是 WHERE 条件中频繁使用的字段，便于利用分区裁剪只扫描涉及的分区。同时分区键应取值稳定、不会频繁更新（分区键更新会导致行在分区间的移动）。

### 主键与唯一约束（必须包含分区键）

在 PostgreSQL 分区表中，主键和唯一约束有特殊的要求：它们必须包含分区键。

#### 为什么要将分区键纳入主键？

这是因为在 PostgreSQL 中，唯一约束（包括主键）只能在同一分区内部强制执行。如果主键或唯一约束不含分区键，那么就无法保证跨分区的唯一性。

```sql
-- 错误示例：在分区键 logdate 之外单独使用非分区字段作为主键会失败
CREATE TABLE measurement_bad (
    city_id         int not null,
    logdate         date not null,
    peaktemp        int,
    unitsales       int,
    PRIMARY KEY (city_id)  -- 将失败，因为分区键 logdate 不在主键中
) PARTITION BY RANGE (logdate);
-- 错误:  unique constraint on partitioned table must include all partitioning columns

-- 正确示例：主键或唯一约束必须包含分区键
CREATE TABLE measurement_good (
    city_id         int not null,
    logdate         date not null,
    peaktemp        int,
    unitsales       int,
    PRIMARY KEY (logdate, city_id)  -- 分区键 logdate 包含在主键中
) PARTITION BY RANGE (logdate);
```

#### 联合主键最佳实践

通常的做法是将分区键作为主键的一部分：

```sql
-- 示例：将日期和城市ID共同作为复合主键
CREATE TABLE measurement (
    city_id         int not null,
    logdate         date not null,
    peaktemp        int,
    unitsales       int,
    PRIMARY KEY (logdate, city_id)
) PARTITION BY RANGE (logdate);

-- 创建分区
CREATE TABLE measurement_y2024m01 PARTITION OF measurement
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE measurement_y2024m02 PARTITION OF measurement
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- 主键（logdate, city_id）保证了全局唯一性
INSERT INTO measurement VALUES (1, '2024-01-15', 45, 100);  -- OK
INSERT INTO measurement VALUES (1, '2024-01-15', 40, 120);  -- 将违反唯一性约束，被拒绝
```
**凡是在分区表上声明的主键或唯一约束，都必须把分区键（列或表达式）纳入其中**。

### 分区大小考虑

一般认为一个表大小达到几GB到几十GB时（官方推荐当数据量到达物理内存大小时）才考虑使用分区。对于TB级的数据量，可以将每个月或每季度的数据放在一个分区中；对于较小的数据量（几百GB），则可能将每个季度或每年数据作为一个分区。

### 分区数量管理

过多的分区可能会导致：

- 过多的子表元数据，影响 catalog 扫描性能
- 更多的后台进程和内存开销
- 复杂的管理操作

通常建议控制分区数量，根据业务需要在颗粒度和管理复杂度间找到平衡点。

### 分区键更新

直接更新分区键字段会变成复杂的动作，实际上是删除旧记录并在新分区中创建新记录。在应用中应避免频繁修改分区键的值。

## 分区表使用

PostgreSQL 提供了多种表分区的方式以适应不同的应用场景。

### 范围分区

范围分区基于某个列的值区间进行划分，适用于按日期、数值范围等维度分区的场景。以下沿用第一节定义好的 measurement 分区表：

```sql
-- 查看数据被路由到哪个分区（tableoid 表示物理分区）
INSERT INTO measurement VALUES (1, '2024-01-15', 45, 100);
INSERT INTO measurement VALUES (2, '2024-02-15', 50, 120);

SELECT tableoid::regclass, * FROM measurement WHERE city_id = 1;
```

还可以通过指定更多分区键创建更复杂的多维范围分区：

```sql
-- 多列范围分区
CREATE TABLE quarterly_report (
    id              bigserial,
    department      text,
    quarter_date    date,
    amount          decimal(10, 2),
    PRIMARY KEY (department, quarter_date, id)  -- 分区键包含在主键中
) PARTITION BY RANGE (department, quarter_date);

CREATE TABLE report_dep_a_q1 PARTITION OF quarterly_report
    FOR VALUES FROM ('A', '2024-01-01') TO ('A', '2024-04-01');

CREATE TABLE report_dep_b_q1 PARTITION OF quarterly_report
    FOR VALUES FROM ('B', '2024-01-01') TO ('B', '2024-04-01');
```

### 列表分区

List 分区基于预定义的值列表进行分区，适用于按明确分类（如国家、状态代码等）对数据进行组织的场景。

```sql
-- List 分区，根据区域代码创建分区
CREATE TABLE regions_data (
    region_code char(2) NOT NULL,
    store_id    integer NOT NULL,
    sales       numeric,
    region_name varchar(50),
    PRIMARY KEY (region_code, store_id)
) PARTITION BY LIST (region_code);

-- 为不同的地区码创建分区
CREATE TABLE regions_us_west PARTITION OF regions_data
    FOR VALUES IN ('WA', 'OR', 'CA');

CREATE TABLE regions_us_east PARTITION OF regions_data
    FOR VALUES IN ('NY', 'PA', 'MD');

CREATE TABLE regions_us_south PARTITION OF regions_data
    FOR VALUES IN ('TX', 'FL', 'GA');

CREATE TABLE regions_us_central PARTITION OF regions_data
    FOR VALUES IN ('IL', 'MI', 'OH');

CREATE TABLE regions_international PARTITION OF regions_data
    FOR VALUES IN ('GB', 'FR', 'DE', 'JP', 'KR', 'SG');

-- 也可以用DEFAULT分区捕获未预定义的值
CREATE TABLE regions_default PARTITION OF regions_data DEFAULT;

-- 测试插入数据
INSERT INTO regions_data VALUES ('CA', 1, 10000, 'California');
INSERT INTO regions_data VALUES ('NY', 2, 12000, 'New York');
INSERT INTO regions_data VALUES ('DE', 3, 8000, 'Germany');
INSERT INTO regions_data VALUES ('CN', 4, 15000, 'China');  -- 会被放入default分区

-- 查看数据分布到哪些分区
SELECT tableoid::regclass, * FROM regions_data;
```

使用 List 分区的优点:

- 当需要按确切类别组织数据时特别有效
- 适用于有限的、已知值集合的情况
- 可以利用分区裁剪显著提高查询性能

### Hash 分区

Hash 分区通过对分区键应用哈希函数并将结果映射到指定分区的方式进行数据分配。这种类型适合数据需要随机分布到不同分区以均匀分摊工作负载的场景。

```sql
-- 在 Hash 分区中，同样要确保主键包含分区键
CREATE TABLE employees (
    id int not null,
    name text,
    email text,
    PRIMARY KEY (id, name)  -- id 是分区键，也需要包含在主键中
) PARTITION BY HASH (id);

-- 创建 4 个分区
CREATE TABLE emp_p0 PARTITION OF employees
    FOR VALUES WITH (MODULUS 4, REMAINDER 0);

CREATE TABLE emp_p1 PARTITION OF employees
    FOR VALUES WITH (MODULUS 4, REMAINDER 1);

CREATE TABLE emp_p2 PARTITION OF employees
    FOR VALUES WITH (MODULUS 4, REMAINDER 2);

CREATE TABLE emp_p3 PARTITION OF employees
    FOR VALUES WITH (MODULUS 4, REMAINDER 3);

-- 插入测试数据
INSERT INTO employees VALUES (1, 'Alice', 'alice@example.com');
INSERT INTO employees VALUES (2, 'Bob', 'bob@example.com');
INSERT INTO employees VALUES (3, 'Charlie', 'charlie@example.com');
```

### 各种分区方法的比较和选择

| 分区类型 | 使用场景         | 优点                     | 缺点                 |
| -------- | ---------------- | ------------------------ | -------------------- |
| Range    | 按时间或数值范围 | 易理解，适合时间序列数据 | 数据可能分布不均     |
| List     | 按预定义列表值   | 易于控制具体分区         | 限制固定值集合       |
| Hash     | 需要随机均匀分布 | 均匀分布数据             | 对查询优化有一定难度 |

## 序列（Sequence）注意事项

分区表通常需要一个自增 id 列，其底层是序列（sequence）。序列在分区表上的行为与普通表存在差异，全局唯一性以及迁移时的序列同步等问题。

### 序列是全局共享的

- 分区表的 `SERIAL/BIGSERIAL` 或 `IDENTITY` 列在父表上只创建一个序列，**所有分区共享同一个序列**，从而保证跨分区的自增值全局唯一。
- 通过 `PARTITION OF` 创建的新分区会继承父表列的默认值：对 `SERIAL/BIGSERIAL`（本质是 `nextval('父表序列')` 默认值）各版本都继承，因此直接往分区插入也能自动生成 id。
- 一个使用 `BIGSERIAL` 的设计提醒：序列是全局递增的，直接向某个分区插入时生成的 id 必须落在该分区的取值范围内，否则会违反分区约束。

### 唯一性由什么保证？

- 序列能保证"实际写进去的自增 id 不冲突"，但它不是唯一性约束，数据库不会因此拦截重复值。
- 真正的唯一性只能靠主键/唯一约束来强制，而它们必须包含分区键。若业务主键是 `id`、分区键是其他列（如 `sale_date`），`PRIMARY KEY (id)` 会因不包含分区键而创建失败。

此时通常有两种取舍：

- 将分区键并入主键，如 `PRIMARY KEY (sale_date, id)`（推荐，可用数据库强制唯一）；
- 或只在每个分区上单独建 `PRIMARY KEY (id)`，依赖共享序列保证实际值不重复，但数据库无法强制全局唯一，需要应用层保证。

### 迁移、挂载分区时的序列同步

这是最容易出问题的地方：老表与新分区表各带一条独立序列，数据搬过去后若序列值区间重叠，就会产生重复 id。

```sql
-- 场景：老表 products_large(id SERIAL) 迁移到分区表 products_new(id SERIAL)
-- 两条序列各自从 1 开始，直接搬运数据会造成主键冲突。
-- 迁移完成后，务必将新表序列推进到大于现有数据最大值：

SELECT setval(
    pg_get_serial_sequence('products_new', 'id'),
    (SELECT COALESCE(max(id)::bigint, 1) FROM products_new)
);
```

用 `ATTACH PARTITION` 挂载历史表时，被挂载的表会保留它自己的序列和默认值（ATTACH 只校验结构、NOT NULL 与约束，不会统一默认值与序列）：

```sql
-- 挂载后建议把历史分区的默认值改为父表序列，并重绑序列归属，避免出现两套编号
ALTER TABLE products_2023_and_before ALTER COLUMN id SET DEFAULT nextval('products_new_id_seq');
ALTER SEQUENCE products_new_id_seq OWNED BY products_new.id;
```

### 其他序列注意事项

- `nextval()` 不随事务回滚：即使 INSERT 失败、事务回滚，已取出的序列值也不会退回，之后会出现 id 空洞。这是正常现象，不应作为主键乱序的判断依据。
- 需要"每个分区独立编号自 1 开始"（如按日的流水号、班次号）时，父表单序列无法满足，应该改为：`(分区键, 序号)` 复合唯一键，或在业务层/每个分区内维护独立计数器。
- 优先使用 `GENERATED ALWAYS AS IDENTITY`（禁止应用显式指定 id）。当需要导入历史数据时，用 `OVERRIDING SYSTEM VALUE` 强制写入既有 id：

```sql
INSERT INTO products_new (id, name, category_id, price, create_time) OVERRIDING SYSTEM VALUE
SELECT * FROM products_old;
```


## 其他注意事项

### 默认分区

在使用 RANGE 或 LIST 分区时，可以创建一个默认分区来处理不在已定义分区范围内的数据。

```sql
CREATE TABLE measurement_default PARTITION OF measurement DEFAULT;
```

这样当尝试插入不符合任何已定义分区条件的值时，不会报错，而是将数据存入默认分区。

默认分区不建议存储大量数据：它会拖慢新分区的挂载，因为挂载分区时需要扫描默认分区来检查数据是否满足新分区的约束。若默认分区数据量很大，可提前在被挂载分区上手工创建匹配的 CHECK 约束，避免挂载时做全表数据检查；挂载完成后可删除该 CHECK 约束。

### 索引操作

当前不支持在分区表上并发(concurrently)生成索引。 然而，你可以在每个分区上单独的并发构建索引，然后最终以非并发的方式创建分区索引，以减少对分区表的写入被锁定的时间。在这种情况下，生成分区索引仅是元数据操作。

需要区分以下两种行为：

- `CREATE INDEX ... ON parent (...)`（父表上建索引）：会自动递归应用到所有现存分区，此后新建的分区也会自动继承同样的索引结构。
- `CREATE INDEX ... ON ONLY parent (...)`（只在父表建索引）：不会应用到现有分区，之后新建的分区也不会被包含。仅在极特殊场景下使用。

### 表结构变更的影响

更新父表结构会影响到已存在子表，但具体行为依赖于操作：

- 增加列（WITH DEFAULT 或 NULL）会传递到所有子分区
- 修改列数据类型可能会影响现有数据
- 删除列也会影响子分区

### 分区创建管理

- 手动管理方式适用于分区较少且规律固定的场景
- 使用 pg_partman 等自动化工具可根据预定规则自动创建新分区
- 对于动态范围（如按需创建新分区），需配合业务逻辑创建分区表

### 分区裁剪参数优化

为了充分发挥分区表的性能优势，必须确保 `enable_partition_pruning` 参数被开启以激活分区裁剪功能。当 WHERE 子句包含分区键条件时，优化器会选择仅扫描相关的分区，大大提高了查询性能。

- 检查当前设置：`SHOW enable_partition_pruning;`
- 启用参数：`SET enable_partition_pruning = on;` （会话级）
- 永久设置需在 postgresql.conf 文件中修改

另外，对于某些场景，也应确保：

- enable_bitmapscan = on
- enable_indexonlyscan = on

### 事务与锁定注意事项

在大量插入或更新数据时需特别注意锁定行为：

- 分区表的操作可能会在父表和涉及的分区上产生锁定
- 对单个分区的操作只会影响特定分区的锁定
- 批量操作前评估对整体系统的影响


## 唯一约束、索引与性能

### 跨分区唯一约束

由于唯一约束只能在同一分区内部验证，要实现真正的跨分区唯一性，分区键必须是唯一约束的一部分。

```sql
-- 错误：尝试在分区键外创建全局唯一约束不会成功
CREATE TABLE orders (
    order_id    int not null,
    order_date  date not null,
    customer_id int,
    PRIMARY KEY (order_date, order_id),
    UNIQUE (customer_id)  -- 这个约束只会在各自分区内部强制执行
) PARTITION BY RANGE (order_date);

错误:  unique constraint on partitioned table must include all partitioning columns

-- 正确：若要实现 customer_id 全局唯一，需要将其与分区键一起构成唯一约束
CREATE TABLE orders_fixed (
    order_id    int not null,
    order_date  date not null,
    customer_id int,
    PRIMARY KEY (order_date, order_id),
    UNIQUE (customer_id, order_date)  -- 这确保了跨分区的唯一性
) PARTITION BY RANGE (order_date);

-- 或者创建单独的索引来实现特定查询需求（索引不是约束，不强制唯一）
CREATE TABLE orders_indexed (
    order_id    int not null,
    order_date  date not null,
    customer_id int,
    PRIMARY KEY (order_date, order_id)
) PARTITION BY RANGE (order_date);

-- 可以为特定查询创建索引，这个索引将在每个分区上分别创建
CREATE INDEX orders_customer_idx ON orders_indexed (customer_id);
```

### 索引策略

在分区表中，创建索引需要特别注意：

1. 索引需要包含分区键以确保全局查询的有效性
2. 局部索引（每一分区一个）vs 全局索引（父表一个，自动复制到各分区）的选择
3. 如何为频繁查询的字段创建合适索引

```sql
-- 在订单分区表中创建复合索引，包含分区键和查询字段
CREATE TABLE orders_composite (
    order_id     int not null,
    order_date   date not null,
    customer_id  int,
    product_id   int,
    quantity     int,
    PRIMARY KEY (order_date, order_id) 
) PARTITION BY RANGE (order_date);

-- 创建包含分区键的复合索引，用于客户产品组合查询
CREATE INDEX orders_customer_product_idx ON orders_composite (customer_id, product_id, order_date);

-- 局部索引：只在父表上创建，不复制到分区（不推荐，除非明确知道目的）
CREATE INDEX orders_quantity_idx ON ONLY orders_composite (quantity);

-- 新增分区时，父表上的索引会自动应用到新分区
CREATE TABLE orders_2024 PARTITION OF orders_composite
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

### 大数据量性能对比测试

为了充分展示分区表在处理大数据量时的优势，这里提供具体的测试用例和方法。

#### 测试数据准备

创建一个基于日期的分区表，以及一个普通表作为对照（插入都经由父表进行，identity 各版本均可用，细节见「序列（Sequence）注意事项」一节）：

```sql
CREATE TABLE sales_data (
    sale_id         bigint generated always as identity,
    sale_date       date not null,
    product_id      int not null,
    customer_id     int not null,
    quantity_sold   int not null,
    sale_amount     numeric(10, 2) not null,
    region          varchar(50),
    PRIMARY KEY (sale_date, sale_id)  -- 确保分区键包含在主键中
) PARTITION BY RANGE (sale_date);

-- 创建多个月的分区
CREATE TABLE sales_jan2024 PARTITION OF sales_data
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE sales_feb2024 PARTITION OF sales_data
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
CREATE TABLE sales_mar2024 PARTITION OF sales_data
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');
CREATE TABLE sales_apr2024 PARTITION OF sales_data
    FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
CREATE TABLE sales_may2024 PARTITION OF sales_data
    FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');
CREATE TABLE sales_jun2024 PARTITION OF sales_data
    FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');
CREATE TABLE sales_jul2024 PARTITION OF sales_data
    FOR VALUES FROM ('2024-07-01') TO ('2024-08-01');
CREATE TABLE sales_aug2024 PARTITION OF sales_data
    FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
CREATE TABLE sales_sep2024 PARTITION OF sales_data
    FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');
CREATE TABLE sales_oct2024 PARTITION OF sales_data
    FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
CREATE TABLE sales_nov2024 PARTITION OF sales_data
    FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
CREATE TABLE sales_dec2024 PARTITION OF sales_data
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

-- 生成模拟销售数据（300万条），用于展示大数据量下的性能差异
INSERT INTO sales_data (sale_date, product_id, customer_id, quantity_sold, sale_amount, region)
SELECT
    '2024-01-01'::date + (floor(random() * 365))::int as sale_date,
    floor(random() * 10000 + 1)::int as product_id,
    floor(random() * 50000 + 1)::int as customer_id,
    floor(random() * 10 + 1)::int as quantity_sold,
    round((random() * 1000 + 10)::numeric, 2) as sale_amount,
    case (floor(random() * 4)::int)
        when 0 then 'North'
        when 1 then 'South'
        when 2 then 'East'
        else 'West'
    end as region
FROM generate_series(1, 3000000) s(i);

-- 创建适当的索引以优化查询性能
CREATE INDEX idx_sales_product_date ON sales_data (product_id, sale_date);
CREATE INDEX idx_sales_customer ON sales_data (customer_id);
CREATE INDEX idx_sales_region ON sales_data (region);
ANALYZE VERBOSE sales_data;

-- 创建非分区的对照表，并填充相同的数据集
CREATE TABLE sales_data_unpartitioned (
    sale_id         bigint generated always as identity,
    sale_date       date not null,
    product_id      int not null,
    customer_id     int not null,
    quantity_sold   int not null,
    sale_amount     numeric(10, 2) not null,
    region          varchar(50),
    PRIMARY KEY (sale_date, sale_id)
);

INSERT INTO sales_data_unpartitioned (sale_date, product_id, customer_id, quantity_sold, sale_amount, region)
SELECT
    '2024-01-01'::date + (floor(random() * 365))::int as sale_date,
    floor(random() * 10000 + 1)::int as product_id,
    floor(random() * 50000 + 1)::int as customer_id,
    floor(random() * 10 + 1)::int as quantity_sold,
    round((random() * 1000 + 10)::numeric, 2) as sale_amount,
    case (floor(random() * 4)::int)
        when 0 then 'North'
        when 1 then 'South'
        when 2 then 'East'
        else 'West'
    end as region
FROM generate_series(1, 3000000) s(i);  -- 同样生成300万条记录

CREATE INDEX idx_sales_product_date_unpart ON sales_data_unpartitioned (product_id, sale_date);
CREATE INDEX idx_sales_customer_unpart ON sales_data_unpartitioned (customer_id);
CREATE INDEX idx_sales_region_unpart ON sales_data_unpartitioned (region);

ANALYZE VERBOSE sales_data_unpartitioned;
```

#### 性能对比查询

通过 `EXPLAIN ANALYZE` 对比分区表与普通表的执行计划：

```sql
-- 比较1：查询特定日期范围的数据（分区裁剪生效，只扫描单个分区）
EXPLAIN ANALYZE
SELECT COUNT(*), SUM(sale_amount)
FROM sales_data
WHERE sale_date >= '2024-06-01' AND sale_date < '2024-07-01';

-- 非分区表的相同查询（扫描全表）
EXPLAIN ANALYZE
SELECT COUNT(*), SUM(sale_amount)
FROM sales_data_unpartitioned
WHERE sale_date >= '2024-06-01' AND sale_date < '2024-07-01';

-- 比较2：按产品ID查找
EXPLAIN ANALYZE
SELECT sale_id, sale_date, sale_amount
FROM sales_data
WHERE product_id = 1234
ORDER BY sale_date DESC
LIMIT 10;

EXPLAIN ANALYZE
SELECT sale_id, sale_date, sale_amount
FROM sales_data_unpartitioned
WHERE product_id = 1234
ORDER BY sale_date DESC
LIMIT 10;

-- 比较3：聚合查询
EXPLAIN ANALYZE
SELECT
    region,
    COUNT(*) as transaction_count,
    SUM(sale_amount) as total_sales
FROM sales_data
GROUP BY region;

EXPLAIN ANALYZE
SELECT
    region,
    COUNT(*) as transaction_count,
    SUM(sale_amount) as total_sales
FROM sales_data_unpartitioned
GROUP BY region;
```

在真实的性能测试中，你会发现：

1. 对于只涉及单个分区的查询（分区裁剪生效），分区表性能会显著优于普通表
2. 跨分区查询的性能则更依赖于具体的条件和索引配置
3. 随着数据量的增加，优势会更明显

#### 数据分布检查

确保数据分布到各个分区中以均衡 I/O 操作：

```sql
-- 检查各分区的数据分布
SELECT
    schemaname,
    relname,
    n_tup_ins - n_tup_del as approx_count
FROM pg_stat_user_tables
WHERE relname LIKE 'sales%'
ORDER BY relname;
```

## 普通表转换分区表

**不能直接将常规表转换为分区表，反之亦然**。但是，可以将现有的常规表（或分区表）添加为分区表的分区，或从分区表中删除分区，将其转换为独立表。当表尺寸超过了数据库服务器物理内存时，通常需要考虑转为分区表，迁移方式有停机和不停机两种。

### 停机迁移

简单直观，但需要业务暂时停止服务。

#### SELECT INTO / CREATE TABLE AS 方式

```sql
-- 假设有个现有的表 orders，需要转换为基于日期的分区表
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INT,
    order_date DATE,
    amount DECIMAL(10,2)
);

-- 批量插入 300 万条模拟数据
INSERT INTO orders (customer_id, order_date, amount)
SELECT
    -- 随机生成 customer_id (1 到 50,000)
    floor(random() * 50000 + 1)::int AS customer_id,
    -- 随机生成 order_date (覆盖 2023-01-01 到 2025-12-31)
    -- 基础日期 '2023-01-01' + 随机天数 (0 到 1095 天，约3年)
    ('2023-01-01'::date + (floor(random() * 1095))::int)::date AS order_date,
    -- 随机生成 amount (10.00 到 1010.00)
    round((random() * 1000 + 10)::numeric, 2) AS amount
FROM generate_series(1, 3000000) s(i);

-- 创建分区表。id 用 bigserial 而不是 ALWAYS identity：迁移时要显式插入历史 id，而
-- ALWAYS identity 拒绝应用显式指定值（除非 OVERRIDING SYSTEM VALUE）
CREATE TABLE orders_partitioned (
    id bigserial,
    customer_id INT,
    order_date DATE,
    amount DECIMAL(10,2),
    PRIMARY KEY (order_date, id)  -- 重定义主键以包含分区键
) PARTITION BY RANGE (order_date);

-- 为不同时间段创建分区
CREATE TABLE orders_2023 PARTITION OF orders_partitioned
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');
CREATE TABLE orders_2024 PARTITION OF orders_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
CREATE TABLE orders_2025 PARTITION OF orders_partitioned
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');


-- 将数据迁移至新的分区表， 单次迁移数量过大可进行多次批量迁移。
INSERT INTO orders_partitioned (id, customer_id, order_date, amount) SELECT * FROM orders;
VACUUM ANALYZE orders_partitioned;

-- 重建索引
CREATE INDEX idx_orders_customer ON orders_partitioned (customer_id);
CREATE INDEX idx_orders_amount ON orders_partitioned (amount);

-- 数据迁移完成后，务必同步序列，避免新旧编号冲突（见「序列（Sequence）注意事项」）
SELECT setval(
    pg_get_serial_sequence('orders_partitioned', 'id'),
    (SELECT COALESCE(max(id)::bigint, 1) FROM orders_partitioned)
);

-- 停机操作: 重命名表
ALTER TABLE orders RENAME TO orders_old;
ALTER TABLE orders_partitioned RENAME TO orders;
```

#### COPY 方式

此方式适合非常大的数据迁移，因为 COPY 在大批量数据迁移方面有更好的性能表现。

```sql
-- 创建临时文件（psql 元命令）
\copy (SELECT * FROM orders) TO 'orders_backup.dump' WITH CSV HEADER;

-- 按上述相同步骤创建分区表...

-- 然后批量载入数据
\copy orders_partitioned FROM 'orders_backup.dump' WITH CSV HEADER;

-- 序列同步与重命名操作参照上一节

-- 验证数据
SELECT COUNT(*) FROM orders_partitioned;
SELECT COUNT(*) FROM orders_old;
```

### 不停机迁移：将老表挂载为分区

通过 `ATTACH PARTITION` 将现有大表（作为历史数据分区）挂载到新建的分区表上，无需移动历史数据，实现不停机迁移。

```
-- 场景：有一个很大的常规表包含所有数据（例如此表包含多年的累积数据）
CREATE TABLE products_large (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    category_id INTEGER,
    price DECIMAL,
    create_time DATE
);
```

```sql
-- 插入 300万条 数据
INSERT INTO products_large (name, category_id, price, create_time)
SELECT
    -- 1. 随机生成产品名称 (例如: Product_12345)
    'Product_' || floor(random() * 100000)::int AS name,
    -- 2. 随机生成分类 ID (1 到 50)
    floor(random() * 50 + 1)::int AS category_id,
    -- 3. 随机生成价格 (10.00 到 1000.00)
    round((random() * 990 + 10)::numeric, 2) AS price,
    -- 4. 随机生成日期 (覆盖 2024-02-01 到 2024-03-31)
    -- 基础日期 '2024-02-01' + 随机天数 (0 到 59 天，共60天)
    ('2024-02-01'::date + (floor(random() * 60))::int)::date AS create_time
FROM generate_series(1, 3000000) AS s(i);
```

```sql
-- 查看数据分别边界
select min(create_time), max(create_time) from products;
    min     |    max     
------------+------------
 2024-02-01 | 2024-03-31
```

```sql
-- 步骤1：创建新的分区表框架
CREATE TABLE products_new (
    id SERIAL,
    name VARCHAR(255),
    category_id INTEGER,
    price DECIMAL,
    create_time DATE,
    PRIMARY KEY (create_time, id)
) PARTITION BY RANGE (create_time);
```
```sql
-- 步骤2：为新分区创建未来月份的分区。 根据现有数据边界范围进行创建。
CREATE TABLE products_202404 PARTITION OF products_new
    FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
CREATE TABLE products_202405 PARTITION OF products_new
    FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');
```
```sql
-- 步骤3：将老表作为分区添加（先重命名，并让结构与分区表一致）
ALTER TABLE products_large RENAME TO products_2023_and_before;
ALTER TABLE products_2023_and_before ALTER COLUMN create_time SET NOT NULL;
ALTER TABLE products_2023_and_before DROP CONSTRAINT products_large_pkey;

-- ATTACH 前验证结构与约束（如 NOT NULL、CHECK）与分区表完全匹配
ALTER TABLE products_new ATTACH PARTITION products_2023_and_before default;
```

```sql
-- 步骤4：序列同步（老表保留了它自己的序列与默认值）
-- 将历史分区的默认值统一到父表序列，并重绑归属，避免生成重复 id
ALTER TABLE products_2023_and_before ALTER COLUMN id SET DEFAULT nextval('products_new_id_seq');
ALTER SEQUENCE products_new_id_seq OWNED BY products_new.id;

ALTER TABLE products_new RENAME TO products;
```
挂载前注意：ATTACH PARTITION 会扫描老表数据做约束校验（校验失败则回滚），数据量很大时会消耗较长时间和资源；老表上的索引不会被自动继承，需按分区表索引结构补齐。

### 不停机迁移：其他工具与机制

- **pg_rewrite**：第三方扩展，通过在源表上安装触发器，把增删改操作实时同步复制到目标分区表，待数据追平后在低峰期切换流量并校验一致性。适合不允许断写的核心业务，但对存量数据的批量搬迁仍需要单独处理（COPY）。
- **双写机制**：应用层同时写入新旧表，待老表数据与存量核对一致后切换读/写流量。
- **触发器 + 复制机制**：通过触发器或逻辑复制同步写入，切换到新表后清理触发器。

## 表分区管理

随着应用的发展，分区表管理成为一个关键任务，主要包括增加新分区、移除旧分区等操作。


### 创建分区表
```
CREATE TABLE measurement (
    city_id         int not null,
    logdate         date not null,
    peaktemp        int,
    unitsales       int
) PARTITION BY RANGE (logdate);
```
### 添加分区
方式一， 直接在父表上创建分区
```
CREATE TABLE measurement_y2006m02 PARTITION OF measurement
    FOR VALUES FROM ('2006-02-01') TO ('2006-03-01');
```

方式二, 创建子表并挂载到父表
```
CREATE TABLE measurement_y2008m02
  (LIKE measurement INCLUDING DEFAULTS INCLUDING CONSTRAINTS)
  TABLESPACE fasttablespace;

ALTER TABLE measurement_y2008m02 ADD CONSTRAINT y2008m02
   CHECK ( logdate >= DATE '2008-02-01' AND logdate < DATE '2008-03-01' );

ALTER TABLE measurement ATTACH PARTITION measurement_y2008m02
    FOR VALUES FROM ('2008-02-01') TO ('2008-03-01' ); 
```
### 删除分区

方式一， 直接删除分区子表， 需要在父表上拿到ACCESS EXCLUSIVE锁
```
DROP TABLE measurement_y2006m02;
```
方式二， 卸载分区为独立的表
```
ALTER TABLE measurement DETACH PARTITION measurement_y2006m02;
ALTER TABLE measurement DETACH PARTITION measurement_y2006m02 CONCURRENTLY; --只需要父表上的SHARE UPDATE EXCLUSIVE锁
```

## 核心要点回顾

- 主键/唯一约束必须包含分区键，否则无法跨分区强制唯一
- 分区键应选取 WHERE 条件频繁使用、取值稳定的字段
- 序列属于父表、所有分区共享，保证自增 id 全局不冲突，但不是唯一性约束
- identity 列自 PG 10 起即可用于分区表；PG 17 前分区不继承 identity 属性（写入须经由父表）
- 迁移/挂载分区后务必同步序列（setval），避免新旧编号冲突
- 启用 enable_partition_pruning 以发挥分区裁剪优势
- 默认分区不要存放大量数据，否则会拖慢后续分区挂载

## 分区表订单 ID 唯一性设计

PostgreSQL 分区表无全局索引，唯一约束通过各分区的本地唯一索引实现，由此产生两条铁律：

主键/唯一约束必须包含全部分区键，否则 DDL 直接报错：

```Text
ERROR: unique constraint on partitioned table must include all partitioning columns
原理：分区路由是分区键的确定性函数，约束含分区键时，重复行必然落入同一分区，"本地唯一" ⟹ "全局唯一"。
```

复合主键 PRIMARY KEY (order_date, order_id) 只保证组合唯一：

```Sql
INSERT INTO orders VALUES (100, '2024-01-15');  -- ✅
INSERT INTO orders VALUES (100, '2024-01-16');  -- ✅ 也成功！order_id=100 重复
```

### 业务上如何保证 order_id 全局唯一

#### 方案 1：靠生成器保证"天然唯一"（最常用）
```sql
CREATE TABLE orders (
    order_id    bigint GENERATED ALWAYS AS IDENTITY,  -- 全局序列发号
    order_date  date not null,
    ...
    PRIMARY KEY (order_date, order_id)
) PARTITION BY RANGE (order_date);
```
单一序列发号，order_id 事实上不会重复；
⚠️ 但这是"生成器保证"，不是数据库约束——OVERRIDING SYSTEM VALUE 手动插值仍可制造重复，属约定而非强约束。

#### 方案 2：订单号内嵌日期，直接按 order_id 分区（两全其美，推荐）(uuidv7)

让 ID 自带路由信息（雪花算法 / 日期前缀发号，大型订单系统的典型做法）：

```sql
-- order_id 高位编码日期，如 2024011500000123
CREATE TABLE orders (
    order_id    bigint not null,
    customer_id int,
    ...
    PRIMARY KEY (order_id)          -- ✅ 合法！分区键就是 order_id
) PARTITION BY RANGE (order_id);
CREATE TABLE orders_2024_01 PARTITION OF orders
    FOR VALUES FROM (2024010100000000) TO (2024020100000000);
```

收益非常全面：

| 能力 | 效果 |
|---|---|
| order_id 全局唯一 | ✅ 数据库级强约束（分区键=主键，本地检查⟹全局唯一） |
| WHERE order_id = ? | ✅ 分区裁剪，只查 1 个分区 |
| 按月份查/删旧数据 | ✅ 范围条件 order_id >= ... AND order_id < ... 同样裁剪，DROP PARTITION 照常 |
| 无需应用额外传 order_date | ✅ ID 自带日期 |

#### 方案 3：UUID / 应用层保证 (uuidv4)

最轻量，但无数据库兜底，且 UUID 无序会加剧索引膨胀，订单场景一般不推荐作主键。


#### tips uuid

UUIDv4——除了 6 个固定 bit，全是随机数
```text
f47ac10b-58cc-4372-a567-0e02b2c3d479
                 ↑    ↑
              version variant
                 4    8~b
```

UUIDv7——前 48 bit 是时间戳，天然按时间排序
```text
018cc251-f400-7f3a-8c1e-5b2d9f0a1b3c
└─48bit Unix毫秒─┘ │ └12b┘│ └───62bit 随机───┘
                  版本7 rand_a   rand_b
```

| 生成方式 | 版本 | 依赖 |
|---|---|---|
| `gen_random_uuid()` | v4 | PG13+ 内置 |
| `uuid_generate_v4()` | v4 | uuid-ossp 扩展 |
| `uuid_generate_v7()` | v7 | pg_uuidv7 扩展 |
| `uuidv7()` | v7 | **PG18 内置** |
| 应用代码生成 | 取决于库 | Java/Python/Go 库版本各异 |
