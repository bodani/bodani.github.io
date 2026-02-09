# 分区表

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

在设计分区表时，正确处理主键、唯一约束和索引是确保数据完整性和查询性能的重要环节。

### 主键与分区键的关系

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
    PRIMARY KEY (city_id)  -- 这将失败，因为分区键 logdate 不在主键中
) PARTITION BY RANGE (logdate);
错误:  unique constraint on partitioned table must include all partitioning columns
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

-- 这样确保了主键的全局唯一性
INSERT INTO measurement VALUES (1, '2024-01-15', 45, 100);  -- OK
INSERT INTO measurement VALUES (1, '2024-01-15', 40, 120);  -- 将违反唯一性约束，被拒绝

-- 大数据量插入演示，以便展示分区表性能优势
INSERT INTO measurement SELECT
    floor(random()*1000)::int,
    '2024-01-01'::date + (random() * 30)::int,
    floor(random()*100)::int,
    floor(random()*1000)::int
FROM generate_series(1, 500000);  -- 插入50万条记录
```

## 分区表使用

PostgreSQL 提供了多种表分区的方式以适应不同的应用场景。

### 范围分区

范围分区基于某个列的值区间进行划分，适用于按日期、数值范围等维度分区的场景。

```sql
-- 范围分区，包含适当的主键设计
CREATE TABLE measurement (
    city_id         int not null,
    logdate         date not null,
    peaktemp        int,
    unitsales       int,
    PRIMARY KEY (logdate, city_id)  -- 主键包含分区键 logdate
) PARTITION BY RANGE (logdate);

-- 创建具体分区
CREATE TABLE measurement_y2024m01 PARTITION OF measurement
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE measurement_y2024m02 PARTITION OF measurement
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

CREATE TABLE measurement_y2024m03 PARTITION OF measurement
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');

-- 插入数据
INSERT INTO measurement VALUES (1, '2024-01-15', 45, 100);
INSERT INTO measurement VALUES (2, '2024-02-15', 50, 120);

-- 查看分区
SELECT tableoid::regclass, * FROM measurement WHERE city_id = 1;
```

还可以通过指定更多分区键创建更复杂的多维范围分区:

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

## 其他重要注意事项

### 分区键选取

应当基于表的常用查询模式选择合适的分区键，如表单的创建时间、区域编码等。分区键通常是WHERE条件中频繁使用的字段，例如日期字段或地域编码。

### 分区大小考虑

一般认为一个分区表大小达到几GB到几十GB时才考虑使用分区。一个分区应该足够大以获得性能提升，但也不能过大以确保管理和维护的便利性。对于TB级的数据量，可以将每个月或每季度的数据放在一个分区中；对于较小的数据量（几百GB），则可能将每个季度或每年数据作为一个分区。

### 分区数量管理

过多的分区可能会导致：

- 过多的子表元数据，影响catalog扫描性能
- 更多的后台进程和内存开销
- 复杂的管理操作
  通常建议控制分区数量，根据业务需要在颗粒度和管理复杂度间找到平衡点。

### 默认分区

在使用 RANGE 或 LIST 分区时，可以创建一个默认分区来处理不在已定义分区范围内的数据：

```sql
CREATE TABLE measurement_default PARTITION OF measurement DEFAULT;
```

这样当尝试插入不符合任何已定义分区条件的值时，不会报错，而是将数据存入默认分区。

### 表结构变更的影响

更新父表结构会影响到已存在子表，但具体行为依赖于操作：

- 增加列（WITH DEFAULT 或 NULL）会传递到所有子分区
- 修改列数据类型可能会影响现有数据
- 删除列也会影响子分区
- 对现有子表结构的更改不会自动应用到新建分区

### 索引操作

在父表上创建的索引对新增分区生效，但不会对已存在的分区生效。这意味着需要为所有现有分区单独创建相应的索引：

- 使用 CONCURRENTLY 选项以避免锁定整个分区表
- 通过 pg_partman 等工具可帮助批量处理
- 考虑为高频查询字段在所有分区上都建立相应索引

### 分区键更新

直接更新分区键字段会变成复杂的动作，实际上是删除旧记录并在新分区中创建新记录。在应用中应避免频繁修改分区键的值。

### 主键和唯一约束注意事项

- 主键和唯一键必须包含分区键，否则无法保证跨分区的唯一性
- 本地唯一索引（只应用于分区）在跨分区操作中不能提供整体唯一性
- 为了在全局级别（跨越所有分区）实现主键或唯一性约束，必须包含分区键在内

### 分区创建管理

- 手动管理方式适用于分区较少且规律固定的场景
- 使用 pg_partman 等自动化工具可根据预定规则自动创建新分区
- 对于动态范围（如按需创建新分区），需配合业务逻辑创建分区表

### 分区裁剪参数优化

为了充分发挥分区表的性能优势，必须确保 enable_partition_pruning 参数被开启以激活分区裁剪功能。当 WHERE 子句包含分区键条件时，优化器会选择仅扫描相关的分区，大大提高了查询性能。

- 检查当前设置：`SHOW enable_partition_pruning;`
- 启用参数：`SET enable_partition_pruning = on;` （会话级）
- 永久设置需在 postgresql.conf 文件中修改

另外，对于某些场景，也应确保：

- enable_bitmapscan = on
- enable_indexonlyscan = on
- 对于复杂查询，确保约束排除功能有效（对于传统继承表，需要 enable_inheritance_optimization_parameters）

### 事务与锁定注意事项

在大量插入或更新数据时需特别注意锁定行为：

- 分区表的操作可能会在父表和涉及的分区上产生锁定
- 对单个分区的操作只会影响特定分区的锁定
- 批量操作前评估对整体系统的影响

## 唯一约束与索引在分区表中的行为

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

-- 正确：若要实现 customer_id 全局唯一，需要将其与分区键一起构成唯一约束
CREATE TABLE orders_fixed (
    order_id    int not null,
    order_date  date not null,
    customer_id int,
    PRIMARY KEY (order_date, order_id),
    UNIQUE (customer_id, order_date)  -- 这确保了跨分区的唯一性
) PARTITION BY RANGE (order_date);

-- 或者创建单独的索引来实现特定查询需求
CREATE TABLE orders_indexed (
    order_id    int not null,
    order_date  date not null,
    customer_id int,
    PRIMARY KEY (order_date, order_id)
) PARTITION BY RANGE (order_date);

-- 可以为特定查询创建局部索引
-- 这个索引将在每个分区上分别创建
CREATE INDEX orders_customer_idx ON orders_indexed (customer_id);
```

### 索引策略

在分区表中，创建索引需要特别注意：

1. 索引需要包含分区键以确保全局查询的有效性
2. 局部索引（每一分区一个）vs 全局索引（跨所有分区）的选择
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

-- 局部索引，在每一子分区上独立创建
CREATE INDEX orders_quantity_idx ON ONLY orders_composite (quantity);

-- 为新分区创建索引时，需要确保它们继承正确的索引结构
CREATE TABLE orders_2024 PARTITION OF orders_composite
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

-- 对大数据量测试，我们可以使用以下示例
-- 创建一个更大的表用于演示分区性能
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

-- 生成模拟销售数据，用于展示大数据量下的性能差异
-- 这里将生成 300万 条记录用于演示
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
```

### 大数据量性能对比测试

为了充分展示分区表在处理大数据量时的优势，这里提供具体的测试用例和方法。

```sql
-- 为了比较分区表和普通表的性能差异，我们创建一个非分区对照表
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

-- 在普通表上也创建相同的索引
CREATE INDEX idx_sales_product_date_unpart ON sales_data_unpartitioned (product_id, sale_date);
CREATE INDEX idx_sales_customer_unpart ON sales_data_unpartitioned (customer_id);
CREATE INDEX idx_sales_region_unpart ON sales_data_unpartitioned (region);

-- 往对照表中填充相同的数据集
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

-- 现在可以通过 EXPLAIN ANALYZE 来比较两种方式的性能

-- 比较1：查询特定日期范围的数据
-- 分区表的查询计划
EXPLAIN ANALYZE
SELECT COUNT(*), SUM(sale_amount)
FROM sales_data
WHERE sale_date >= '2024-06-01' AND sale_date < '2024-07-01';

-- 非分区表的相同查询
EXPLAIN ANALYZE
SELECT COUNT(*), SUM(sale_amount)
FROM sales_data_unpartitioned
WHERE sale_date >= '2024-06-01' AND sale_date < '2024-07-01';

-- 比较2：按产品ID查找
-- 分区表的查询
EXPLAIN ANALYZE
SELECT sale_id, sale_date, sale_amount
FROM sales_data
WHERE product_id = 1234
ORDER BY sale_date DESC
LIMIT 10;

-- 非分区表的相同查询
EXPLAIN ANALYZE
SELECT sale_id, sale_date, sale_amount
FROM sales_data_unpartitioned
WHERE product_id = 1234
ORDER BY sale_date DESC
LIMIT 10;

-- 比较3：聚合查询
-- 分区表的聚合操作
EXPLAIN ANALYZE
SELECT
    region,
    COUNT(*) as transaction_count,
    SUM(sale_amount) as total_sales
FROM sales_data
GROUP BY region;

-- 非分区表的聚合操作
EXPLAIN ANALYZE
SELECT
    region,
    COUNT(*) as transaction_count,
    SUM(sale_amount) as total_sales
FROM sales_data_unpartitioned
GROUP BY region;

-- 在真实的性能测试中，你会发现：
-- 1. 对于只涉及单个分区的查询，分区表性能会显著优于普通表
-- 2. 跨分区查询的性能则更依赖于具体的条件和索引配置
-- 3. 随着数据量的增加，优势会更明显
```

在大数据量的情况下，你还会遇到其他优化点和注意事项：

#### 数据分布

确保数据分布到各个分区中以均衡I/O操作：

```sql
-- 检查各分区的数据分布
SELECT
    schemaname,
    tablename,
    n_tup_ins - n_tup_del as approx_count
FROM pg_stat_user_tables
WHERE tablename LIKE 'sales%'
ORDER BY tablename;
```

#### 统计信息收集

对于大数据量分区表，需要定期更新统计信息：

```sql
-- 为单个分区收集统计信息
ANALYZE sales_jan2024;

-- 为所有分区收集统计信息
CALL partman.analyze_inherit('sales_data');
```

#### 重要的实现细节和注意事项

- 分区键选取: 应基于表的常用查询模式选择合适的分区键，如表单的创建时间、区域编码等
- 分区大小的划分: 通常建议单个分区表大小不要超过数十GB到上百GB，以确保管理和维护的便利性
- 分区表数量控制: 过多的分区可能造成元数据管理的开销过大，需要在粒度和管理复杂度间找平衡
- 启用分区剪枝: 确保启用参数 enable_partition_pruning 来优化查询计划
- 合理使用默认分区: 当遇到未知分区值时，默认分区能防止查询失败
- 索引操作对子表无效: 在父表创建的索引对新增分区生效，但对已存在的分区可能不生效

### 关于表转换的澄清

根据最新的理解，**不能直接将常规表转换为分区表，反之亦然**。但是，可以将现有的常规或分区表添加为分区表的分区，或从分区表中删除分区，将其转换为独立表。

#### 传统迁移方式

1. 停机：CREATE TABLE AS / 重建序列
2. 不停机：
   - 逻辑复制
   - 双写机制
   - 触发器+复制机制

#### 现代迁移方式（通过将常规表作为分区）

```sql
-- 场景：有一个很大的常规表包含所有数据
CREATE TABLE products_large (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    category_id INTEGER,
    price DECIMAL,
    create_time DATE
);
-- 例如此表包含了多年的累积数据

-- 步骤1：创建新的分区表框架
CREATE TABLE products_new (
    id SERIAL,
    name VARCHAR(255),
    category_id INTEGER,
    price DECIMAL,
    create_time DATE,
    PRIMARY KEY (create_time, id)
) PARTITION BY RANGE (create_time);

-- 步骤2：为新分区创建未来月份的分区
CREATE TABLE products_2024_feb PARTITION OF products_new
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
CREATE TABLE products_2024_mar PARTITION OF products_new
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');

-- 步骤3：将老表作为分区添加（将大表作为历史数据分区）
-- 首先重命名老表
ALTER TABLE products_large RENAME TO products_2023_and_before;

-- 将历史数据表添加为新分区表的一个分区
ALTER TABLE products_2023_and_before NO INHERIT products_large; -- 如果有继承
ALTER TABLE products_2023_and_before INHERIT products_new;

-- 或者使用 ATTACH PARTITION (PG11及以后版本)
-- 注意，这种方法需要先修改历史表使其结构完全匹配
-- ALTER TABLE products_new ATTACH PARTITION products_2023_and_before FOR VALUES FROM ('2000-01-01') TO ('2024-02-01');
```

## 将现有常规表作为分区表的分区

当表的尺寸超过了数据库服务器物理内存时，需要考虑转为分区表。这个过程有停机和不停机两种方式。

### 停机迁移

这种方法简单直观，但需要业务暂时停止服务。

#### SELECT INTO 方式

```sql
-- 假设有个现有的表 orders，需要转换为基于日期的分区表
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INT,
    order_date DATE,
    amount DECIMAL(10,2)
);

-- 在创建分区表时需要考虑原来的主键/唯一约束
CREATE TABLE orders_partitioned (
    id SERIAL,
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

-- 将数据迁移至新的分区表
INSERT INTO orders_partitioned (id, customer_id, order_date, amount) SELECT * FROM orders;

-- 重建索引
CREATE INDEX idx_orders_customer ON orders_partitioned (customer_id);
CREATE INDEX idx_orders_amount ON orders_partitioned (amount);

-- 停机操作: 重命名表
ALTER TABLE orders RENAME TO orders_old;
ALTER TABLE orders_partitioned RENAME TO orders;
```

#### COPY 方式

此方式适合非常大的数据迁移，因为 COPY 在大批量数据迁移方面有更好的性能表现。

```sql
-- 创建临时文件
\copy (SELECT * FROM orders) TO 'orders_backup.dump' WITH CSV HEADER;

-- 按上述相同步骤创建分区表...

-- 然后批量载入数据
\copy orders_partitioned FROM 'orders_backup.dump' WITH CSV HEADER;

-- 验证数据
SELECT COUNT(*) FROM orders_partitioned;
SELECT COUNT(*) FROM orders_old;
```

### 不停机迁移

不停机转换对于关键业务非常有价值，尽管过程更复杂。

#### 逻辑复制

使用 PostgreSQL 的逻辑复制特性，设置一个复制源表并逐步迁移:

```sql
-- 创建目标分区表，包含正确的主键/唯一约束
CREATE TABLE orders_subscription (
    id SERIAL,
    customer_id INT,
    order_date DATE,
    amount DECIMAL(10,2),
    PRIMARY KEY (order_date, id)
) PARTITION BY RANGE (order_date);

-- 为各个时段创建分区
CREATE TABLE orders_sub_2023 PARTITION OF orders_subscription
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');
CREATE TABLE orders_sub_2024 PARTITION OF orders_subscription
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

-- 创建所需的索引
CREATE INDEX orders_sub_customer_idx ON orders_subscription (customer_id);

-- 在源库创建publication
CREATE PUBLICATION orders_pub FOR TABLE orders;

-- 在目标库创建subscription，连接到源库
CREATE SUBSCRIPTION orders_sub
  CONNECTION 'host=source_server port=5432 dbname=db_name'
  PUBLICATION orders_pub;

-- 等待复制开始，然后执行上面停机方法的数据插入部分:
INSERT INTO orders_subscription (id, customer_id, order_date, amount) SELECT * FROM orders;

-- 最后切换应用连接到分区表，并删除临时表和逻辑复制设施
```

此方法需要注意:

- 初次数据同步期间需要等待复制完成
- 需要考虑网络中断等情况
- 资源开销较大

#### pg_partman + pg_write

PostgreSQL 版本 13 及以后内置的分区表功能已经非常强大和灵活。

使用 `pg_partman` 可自动化管理数据的移动和归档。首先确保你安装了 `pg_partman`:

```sql
-- 安装扩展
CREATE EXTENSION IF NOT EXISTS pg_partman;

-- 创建符合主键/索引要求的新分区表
CREATE TABLE orders_new (
    id BIGSERIAL,
    customer_id INT,
    order_date DATE NOT NULL,
    amount DECIMAL(10,2),
    PRIMARY KEY (order_date, id)  -- 必须包含分区键
) PARTITION BY RANGE (order_date);

-- 在已有表上启用分区
SELECT partman.create_parent('public.orders_new', 'order_date', 'time', 'monthly');

-- 也可以为现有分区创建历史记录
SELECT partman.undo_partition('public.orders_history', 'table_loop', 2);
```

这样可以将表在线转化为分区表，并自动处理后续的分区管理工作。

不停机转换的流程通常涉及:

1. 创建一个新的符合分区要求的分区表
2. 同时插入两个表（双写）
3. 使用某种机制对比两表是否同步
4. 将读操作切换到新表
5. 检查一致后移除老表

## 表分区管理

随着应用的发展，分区表管理成为一个关键任务，主要包括增加新分区、移除旧分区等操作。

### pg_pathman

pg_pathman 是一个 PostgreSQL 扩展，为 PostgreSQL 10 之前缺乏的声明式分区功能提供了高效的支持。在 Postgres 10 引入了原生的分区表功能后，它的价值逐渐降低。尤其在 PG 13+ 版本，官方原生分区性能大幅提升，pg_pathman 的维护也就逐渐停止。

尽管不再被积极开发，但 pg_pathman 仍提供一些原生分区功能所没有的功能，比如:

```sql
-- 注意：此仅为 pg_pathman 示例，非标准 SQL
-- CREATE INDEX ON partition_table_pathman(id);
-- 会自动在子分区创建对应的索引
```

不过，对于新项目，推荐使用官方提供的分区功能以获得更好的兼容性支持。

### pg_partman

`pg_partman` 扩展专门用于自动化管理 PostgreSQL 的分区表。它允许根据时间或序列自动创建、管理分区。对于需要按时间管理大量数据的应用特别有用。

安装:

```sql
-- 安装扩展
CREATE EXTENSION pg_partman;
```

使用 pg_partman 自动创建分区:

```sql
-- 创建父表，确保包含适当主键和唯一约束
CREATE TABLE test_data_time (
    id BIGSERIAL,
    created_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    data TEXT,
    PRIMARY KEY (created_time, id)  -- 主键包含分区键
) PARTITION BY RANGE (created_time);

-- 启用自动分区管理
SELECT partman.create_parent('public.test_data_time', 'created_time', 'time', 'daily',
                              p_premake := 2, -- 预创建2个未来分区
                              p_start_partition := to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD'));

-- 查看自动创建的分区
SELECT child_table, value_from, value_to
FROM partman.show_partition_info('test_data_time');
```

常见自动化管理功能:

- 定期创建未来分区
- 归档或删除旧分区
- 自动优化索引维护策略

对于分区维护工作来说，pg_partman 可以极大地减少管理开销。

```sql
-- 转换回非分区表
SELECT partman.undo_partition('public.test_data_time', 'table_loop', 2);
```

这些管理策略和工具可确保分区表随时间推移仍保持高性能及可管理性，为大规模数据库应用提供了可靠的基础。
