# HyperLogLog

## 使用场景

在应用中统计去重后的个数，传统的方法通常是这么操作 count(distict(xxx))。 如果数据量变大，或统计频繁，性能会越来越差。

可以考虑一个近似统计计算方法hll

```
create extension hll;
```

HyperLogLog 是一种算法, 可以用来估算数据集的基数. 基数是指一个集合中不同值的数目, 等同于 `COUNT(DISTINCT field)` 返回值. 对于超大数据集来说, 精确的基数统计往往需要消耗大量的内存与时间, 并且消耗的内存与时间会随着数据集基数的增加而成比例增加. 而 HyperLogLog 能够在常数级的内存与时间下, 以极低的误差来获取数据集基数的近似统计.

## 简单例子

```
-- 商店的到访统计
CREATE TABLE store_visitors (
            store_id              integer, -- 商店ID
            distinct_visitors     hll   -- 不重复的客户数
    );
    
-- 新店铺注册
INSERT INTO store_visitors(id, set) VALUES (1, hll_empty());

-- 模拟客户到访过程
UPDATE store_visitors SET set = hll_add(set, hll_hash_integer(12345)) WHERE id = 1;
UPDATE store_visitors SET set = hll_add(set, hll_hash_integer(12346)) WHERE id = 1;
UPDATE store_visitors SET set = hll_add(set, hll_hash_integer(12345)) WHERE id = 1;

-- 统计结果
SELECT hll_cardinality(set) FROM store_visitors WHERE id = 1;
```

hll 数据结构只使用很少的内存，而且不会随着数据量的增加性能下降。可以用来进行实时统计。



## 更实用的例子

### 创建测试数据表及数据

```
CREATE TABLE github_events
(
    event_id bigint,
    event_type text,
    event_public boolean,
    repo_id bigint,
    payload jsonb,
    repo jsonb,
    user_id bigint,
    org jsonb,
    created_at timestamp
);

\COPY github_events FROM events.csv CSV
数据源 https://examples.citusdata.com/events.csv
```

### 传统统计



```
-- 每分钟 最小粒度 events数量 
CREATE TABLE github_events_rollup_minute
(
    created_at timestamp,
    event_count bigint
);

-- 载入数据
INSERT INTO github_events_rollup_minute(
    created_at,
    event_count
)
SELECT
    date_trunc('minute', created_at) AS created_at,
    COUNT(*) AS event_count
FROM github_events
GROUP BY 1

```

一些限制

- 不可以进行distinct统计
- 不通维度的统计都需要建表。复杂度高。如按时间统计，按事件类型统计，按时间和事件类型综合统计。

### 使用hll 统计



	得益于hll 可以对两个或多个集合进行合并操作。

```
-- 一张表搞定多维统计
CREATE TABLE github_events_rollup_minute(
    created_at timestamp,
    event_type text,
    distinct_user_id_count hll
);

-- 载入数据
INSERT INTO github_events_rollup_minute(
    created_at,
    event_type,
    distinct_user_id_count
)

SELECT
    date_trunc('minute', created_at) AS created_at,
    event_type,
    hll_add_agg(hll_hash_bigint(user_id))
FROM github_events
GROUP BY 1, 2;

```

```
-- 按时间维度统计
SELECT
    EXTRACT(HOUR FROM created_at) AS hour,
    hll_cardinality(hll_union_agg(distinct_user_id_count)) AS distinct_count
FROM
    github_events_rollup_minute
WHERE
    created_at BETWEEN '2016-12-01 00:00:00'::timestamp AND '2016-12-01 23:59:59'::timestamp
GROUP BY 1
ORDER BY 1;

  hour |  distinct_count
-------+------------------
     5 |  10598.637184899
     6 | 17343.2846931687
     7 | 18182.5699816622
     8 | 12663.9497604266
(4 rows)
```

```
-- 按事件类型维度统计
SELECT
    EXTRACT(HOUR FROM created_at) AS hour,
    hll_cardinality(hll_union_agg(distinct_user_id_count)) AS distinct_push_count
FROM
    github_events_rollup_minute
WHERE
    created_at BETWEEN '2016-12-01 00:00:00'::timestamp AND '2016-12-01 23:59:59'::timestamp
    AND event_type = 'PushEvent'::text
GROUP BY 1
ORDER BY 1;


 hour | distinct_push_count
------+---------------------
    5 |    6206.61586498546
    6 |    9517.80542100396
    7 |    10370.4087640166
    8 |    7067.26073810357
(4 rows)
```

## 分布式数据库

	在分布式数据库中进行count(distinct(xxx)) 统计，传统方式实现的逻辑

- 在每个分片上进行distinct的结果进行汇总后，再次count(distinct())。最终只能在一台机器上进行聚合。
- map/reduce  性能较差

    citus利用hll 轻松解决

```
CREATE EXTENSION hll;
```

```
SET citus.count_distinct_error_rate TO 0.005;
```

```
CREATE TABLE github_events
(
    event_id bigint,
    event_type text,
    event_public boolean,
    repo_id bigint,
    payload jsonb,
    repo jsonb,
    user_id bigint,
    org jsonb,
    created_at timestamp
);

SELECT create_distributed_table('github_events', 'user_id');

\COPY github_events FROM large_events.csv CSV

-- 开始统计
SELECT
    COUNT(DISTINCT user_id)
FROM
    github_events;

-- 开始统计
SELECT
    COUNT(DISTINCT user_id)
FROM
    github_events
WHERE
    event_type = 'PushEvent'::text;
```


## 参数优化

			在分析型数据库PostgreSQL版中, HyperLogLog 的误差与内存消耗量受如下参数控制:

- log2m, 该参数控制着 HyperLogLog 对数据集基数估算的误差为: `1.04 / math.sqrt(2 ** log2m)`. 该参数同时也控制着 HyperLogLog 内存消耗量.
- regwidth, 该参数与 log2m 一起决定了 HyperLogLog 内存消耗量最多为 `(2 ** log2m) * regwidth / 8` 字节. 同时该函数也决定了 HyperLogLog 所能估算数据集基数的最大值.

```
默认值
hll(log2m=11, regwidth=5, expthresh=-1, sparseon=1)	
```

```
设置参数
select hll_set_defaults(16,5,-1,1);
```


