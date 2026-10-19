# pg_partman

`pg_partman` 扩展专门用于自动化管理 PostgreSQL 的分区表。它允许根据时间或序列自动创建、管理分区。
对于需要按时间管理的大量数据应用非常适用。

## 安装
```sql
-- 安装扩展
CREATE SCHEMA IF NOT EXISTS partman;
CREATE EXTENSION pg_partman SCHEMA partman;
```

## 创建分区
```sql
-- 创建父表
CREATE TABLE test_data_time (
    id BIGSERIAL,
    created_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    data TEXT
) PARTITION BY RANGE (created_time);

-- 创建模版表
CREATE TABLE partman.test_data_time_template (LIKE test_data_time);

-- 配置子表主键
ALTER TABLE partman.test_data_time_template ADD PRIMARY KEY (id);

-- 启用自动分区管理， 根据p_premake ， p_interval， p_start_partition 这三个参数计算设定分区的具体范围。
SELECT partman.create_parent('public.test_data_time', 
                              p_control := 'created_time',
                              p_premake := 2, -- 预创建2个未来分区
                              p_interval := '1 day',
                              p_template_table := 'partman.test_data_time_template', -- 这个sechema 一定要加上
                              p_start_partition := to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD')); -- 从当前时间开始

-- 查看自动创建的分区
\dP+
SELECT * FROM partman.show_partitions('public.test_data_time');

-- 由partman 管理的分区表配置
SELECT * FROM partman.part_config ORDER BY 1;
```

## 管理
常见自动化管理功能:

- 定期创建未来分区
- 归档或删除旧分区

对于分区维护工作来说，pg_partman 可以极大地减少管理开销。

### 分区配置
查看当前分区表的配置项
```
SELECT * FROM partman.part_config where parent_table = 'public.test_data_time';
```

手动触发，根据具体的配置创建新分区，对过期分区进行归档或删除。
按 premake 预建未来分区 + 按 retention 清理/分离过期分区 + 可选 analyze。
```
CALL partman.run_maintenance_proc();
```
当分区表的配置项 automatic_maintenance = on（默认）时，执行上面的存储过程会对分区表自动进行管理。off 则跳过管理。
### 归档
创建归档SCHEMA
```
CREATE SCHEMA archive AUTHORIZATION <子表的owner>;
```
更新对应的归档保存策略
```
UPDATE partman.part_config
SET retention           = '180 days',   -- 超过它完全过期的分区开始处理
    retention_keep_table = true,         -- DETACH 保留，不 DROP
    retention_keep_index = true,         -- 归档后索引也留着
    retention_schema     = 'archive'     -- 归档去哪
WHERE parent_table = 'public.test_data_time';
```
手动触发
```
CALL partman.run_maintenance_proc();
```
### 删除
更新对应的删除策略
```
UPDATE partman.part_config
SET retention = '90 days',
    retention_keep_table  = false,
    detach_before_drop    = true     -- 先 DETACH 再 DROP，锁更短、留退路
WHERE parent_table = 'public.test_data_time';
```
手动触发
```
CALL partman.run_maintenance_proc();
```

### 参数设置方式
-- 归档：第三个参数 keep_table=true → DETACH 保留
```
SELECT partman.drop_partition_time('public.test_data_time', '180 days', true, true, NULL, true);
```
-- 删除：keep_table=false
```
SELECT partman.drop_partition_time('public.test_data_time', '90 days', false);
```

## 自动化管理

这些管理策略和工具可确保分区表随时间推移仍保持高性能及可管理性，为大规模数据库应用提供了可靠的基础。

### 配置bgw

```
`postgresql.conf` 配置（需重启）：
shared_preload_libraries = 'pg_partman_bgw' -- 这个要重启
pg_partman_bgw.dbname   = 'partdb5,partdb7'     -- 逗号分隔多个库；必填。可以reload
pg_partman_bgw.role     = 'partman_maintainer'   -- 强烈建议非 superuser 专用角色
pg_partman_bgw.interval = 3600                    # 秒，默认 1 小时
pg_partman_bgw.analyze  = 'off'
pg_partman_bgw.jobmon   = 'on'
```

```
CEATE ROLE partman_maintainer WITH LOGIN;   -- 生产建议再设密码或限制连接

GRANT ALL ON SCHEMA partman TO partman_maintainer;
GRANT ALL ON ALL TABLES IN SCHEMA partman TO partman_maintainer;
GRANT EXECUTE ON ALL FUNCTIONS  IN SCHEMA partman TO partman_maintainer;
GRANT EXECUTE ON ALL PROCEDURES IN SCHEMA partman TO partman_maintainer;

GRANT ALL ON SCHEMA public TO partman_maintainer;              -- 分区表所在的 schema
GRANT TEMPORARY ON DATABASE partdb5 TO partman_maintainer; 
```

### 应用cron 扩展
 pg_cron

### 其他

定时应用调用
```
CALL partman.run_maintenance_proc();
```
## 规划分区表

partman 可按时间，序列以及相关的类型。如uuidv7 , 包括时间的文本等。

## 存在历史数据
pg_dump -h 127.0.0.1 -U postgres -p 17432 -d partdb8 -s -t public.test_data_time > table_ddl.sql
### 可停服务迁移

#### 注意事项: 

##### 外键处理。
  
1. 版本前提：PG 12 起声明式分区表才支持外键（两个方向都支持）；PG 11 及以下完全不支持任何涉及分区表的 FK。
2. FK 绑定的是 OID，不是表名。partman 改造时会把旧表 rename 成 xxx_old、新分区表占用原名——所有指向旧表的外键仍然指向旧表，必须重建，不会自动转移。
3. 没有全局唯一索引：父表上的 PK/UNIQUE 约束必须包含全部分区键，这直接决定了别人能不能引用你。

假设 test_data_time 原主键是 (id)，按 created_time 分区后，父表主键只能建成：

```SQL
ALTER TABLE public.test_data_time
  ADD CONSTRAINT test_data_time_pkey PRIMARY KEY (id, created_time);
```
于是引用方必须改成复合外键：

```SQL
ALTER TABLE public.referencing_table
  ADD CONSTRAINT fk_xxx FOREIGN KEY (data_id, created_time)
  REFERENCES public.test_data_time (id, created_time);
```
##### 序列处理。

#### 数据迁移

1. 修改原表表名。新建分区表（相关衍生序列，子表等都和父表名有关）。 
2. 新表与原有表权限，约束，索引，默认值。
3. 查询现有数据范围。select max(created_time) , min(created_time) from original_table;是否有异常数据
4. 设计分区表。根据已有数据范围，及预计未来数据创建分区
5. 迁移数据，分批多次迁移

原数据表
```
CREATE TABLE public.test_data_time (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_time timestamptz NOT NULL DEFAULT now(),
    data         text
);
-- 生成近60天数据
INSERT INTO public.test_data_time (created_time, data)
SELECT date_trunc('day', now()) - interval '60 days'
           + (random() * interval '60 days'),
       'data_' || g || '_' || md5(random()::text)
FROM generate_series(1, 500000) g;
```
迁移前期准备
```
-- 查看现有数据的范围
SELECT min(created_time), max(created_time), count(*)FROM public.test_data_time;

-- 修改原表名及相关序列,索引等名称
BEGIN;
ALTER TABLE public.test_data_time RENAME TO test_data_time_old;
ALTER TABLE public.test_data_time_old RENAME CONSTRAINT test_data_time_pkey TO test_data_time_old_pkey;
ALTER SEQUENCE public.test_data_time_id_seq RENAME TO test_data_time_old_id_seq;
COMMIT;
```
创建新分区表
```
-- 导出原表定义
pg_dump -h 127.0.0.1 -U postgres -p 17432 -d partdb8 -s -t public.test_data_time > table_ddl.sql
```
```
CREATE TABLE public.test_data_time (
    id           bigint GENERATED BY DEFAULT AS IDENTITY,  -- 迁移期 BY DEFAULT
    created_time timestamptz NOT NULL DEFAULT now(),
    data         text
) PARTITION BY RANGE (created_time);

-- 权限 等
GRANT SELECT, INSERT, UPDATE, DELETE ON public.test_data_time TO app_user;
-- identity 序列无需单独授权
-- 业务索引建在父表，自动传播到所有分区
CREATE INDEX idx_test_data_time_created ON public.test_data_time (created_time)

CREATE TABLE partman.template_public_test_data_time (like test_data_time_old);
ALTER TABLE partman.template_public_test_data_time ADD PRIMARY KEY (id);

-- 分区表范围， 根据[ p_start_partition ,  当前时间 + p_premake × interval ]计算
SELECT partman.create_parent(
    p_parent_table    := 'public.test_data_time',
    p_control         := 'created_time',
    p_type            := 'range',
    p_interval        := '1 day',
    p_premake         := 3,
    p_start_partition := '2026-08-13',
    p_template_table  := 'partman.template_public_test_data_time');

UPDATE partman.part_config
SET retention = '90 days', retention_keep_table = true
WHERE parent_table = 'public.test_data_time';
```
分批迁移数据
```
-- 利用partman 方法进行分批迁移
CALL partman.partition_data_proc(
      p_parent_table := 'public.test_data_time',
      p_source_table := 'public.test_data_time_old',
      p_interval := '1 day', p_loop_count := 5, p_wait := 0);

-- 这个迁移函数存在bug,（如数据） 当迁移失败可用原始的 sql ,
-- 原始sql 分批迁移
INSERT INTO public.test_data_time SELECT * FROM public.test_data_time_old where created_time::text >= '2026-09-14 00:00:00+08' AND created_time::text < '2026-09-15 00:00:00+08';

VACUUM ANALYZE test_data_time;
```
迁移后整理验收
```
SELECT setval('public.test_data_time_id_seq', (SELECT max(id) FROM public.test_data_time));

ALTER TABLE public.test_data_time ALTER COLUMN id SET GENERATED ALWAYS;

验证
SELECT (SELECT count(*) FROM public.test_data_time_old) AS old_cnt,  -- 0
       (SELECT count(*) FROM public.test_data_time)     AS new_cnt; 

-- default 是否存在数据
SELECT * FROM partman.check_default(p_exact_count := true);
-- 分区管理
CALL partman.run_maintenance_proc();
```


### 在线迁移

注意事项，原始表中的外键。如果存在需要事先断开，删除。

思路，新建一个没有默认分区的分区表，把原始表挂载为新分区表的默认分区。

原始数据表 
```
CREATE TABLE public.original_table (
    col1 bigint not null PRIMARY KEY GENERATED ALWAYS AS IDENTITY
    , col2 text not null
    , col3 timestamptz DEFAULT now() not null
    , col4 text);

CREATE INDEX CONCURRENTLY ON public.original_table (col3);

INSERT INTO public.original_table (col2, col3, col4) VALUES ('stuff', generate_series(now() - '1 week'::interval, now(), '5 minutes'::interval), 'stuff');
```

创建分区表
```
CREATE TABLE public.new_partitioned_table (
    col1 bigint not null GENERATED BY DEFAULT AS IDENTITY
    , col2 text not null
    , col3 timestamptz DEFAULT now() not null
    , col4 text) PARTITION BY RANGE (col3);

CREATE INDEX ON public.new_partitioned_table (col3);
```
创建模版表
```
-- 注意这里依据原始表，并根据原始表进行创建，减少迁移后名称修改
CREATE TABLE partman.original_table_template (LIKE public.original_table);

ALTER TABLE partman.original_table_template ADD PRIMARY KEY (col1);
```

创建分区
```
-- 查看原始数据范围，及是否有异常数据
SELECT min(col3), max(col3) FROM original_table;
--- 1 开始分区时间稍微延后，确保在迁移的时候不会有新数据写入分区子表中
--- 2 premake 尽量少，减少后期修改名称
--- 3 default_table =false ，不创建默认的分区
SELECT partman.create_partition(
    p_parent_table := 'public.new_partitioned_table'
    , p_control := 'col3'
    , p_interval := '1 day'
    , p_template_table:= 'public.original_table_template'
    , p_premake := 1
    , p_start_partition := (CURRENT_TIMESTAMP+'2 days'::interval)::text
    , p_default_table := false
);

UPDATE partman.part_config SET parent_table = 'public.original_table', premake = 4 WHERE parent_table = 'public.new_partitioned_table';
```
将原始表挂载为新分区的default子表。

开始迁移
```
BEGIN;

LOCK TABLE public.original_table IN ACCESS EXCLUSIVE MODE;
LOCK TABLE public.new_partitioned_table IN ACCESS EXCLUSIVE MODE;

SELECT max(col1)+1 FROM public.original_table;

ALTER TABLE public.original_table RENAME TO original_table_default;

-- IF using an IDENTITY column
ALTER TABLE public.original_table_default ALTER col1 DROP IDENTITY;

ALTER TABLE public.new_partitioned_table RENAME TO original_table;
ALTER TABLE public.new_partitioned_table_p20230330 RENAME TO original_table_p20230330;

-- IF using an IDENTITY column
ALTER SEQUENCE public.new_partitioned_table_col1_seq RENAME TO original_table_col1_seq;

-- IF using an IDENTITY column
ALTER TABLE public.original_table ALTER col1 RESTART WITH <<<VALUE OBTAINED ABOVE>>>;

ALTER TABLE public.original_table ATTACH PARTITION public.original_table_default DEFAULT;
COMMIT; or ROLLBACK;

```
迁移数据
```
--- 将默认分区的数据迁移到对应的分区表中，先处理近期数据 p_loop_count 为迁移的分区总数量，每次迁移一个分区。可分多次进行
CALL partman.partition_data_proc('public.original_table',
                                 p_loop_count := 10,
                                 p_order      := 'DESC');
--- 验证默认分区是否还存在数据
SELECT * FROM partman.check_default(p_exact_count := true);
```
修改分区表自动属性
```
ALTER TABLE public.original_table ALTER col1 SET GENERATED ALWAYS;
```
补齐中间间隔的分区。 （原因是在创建分区时开始时间是当前时间稍向后预留了一段时间）
```
SELECT * FROM partman.partition_gap_fill('public.original_table');
```
自动维护分区表
```
SELECT partman.run_maintenance('public.original_table');
```

## 分区表转换为普通表

离线方式
```
-- 利用这个方法分批进行数据迁移
CALL partman.undo_partition_proc(
    p_parent_table := 'public.original_table'
    , p_target_table := 'public.new_regular_table'
    , p_interval := '1 hour'::text
    , p_loop_count := 500
    , p_keep_table := false);
```
## 原始分区表转换为partman 管理

### 第一步
将原始分区表的子表表名改为 partman 的命名方式：
```
_pYYYYMMDD            - 间隔大于 1 天的所有时间分区
_pYYYYMMDD_HH24MISS   - 间隔小于 1 天的所有时间分区
_p#####               - 序列/ID 分区，后缀取该表最小可能值（如 _p10、_p20000）
```
命名方式分两种情况处理：

- **子表名已含下边界**（如 `hits_time20230226`、`hits_id1000`）：直接对名字做字符串重排即可，成本低、不读数据。
- **子表名与数据无关**（如 `_aa/_bb/_cc`）：需读取每个子表控制列的 `min()` 反推边界（时间用 `date_trunc` 对齐、序列用取模对齐），再拼接命名。

命名很重要，pathman 依赖子表的名字来记录分区的范围

### 第二步
注意开始时间对齐：根据 `p_start_partition` 和间隔计算起始边界，避免与现有分区产生**边界重叠**或**缝隙**。
```
SELECT partman.create_partition(
    '父表名', '分区列', '间隔',
    p_start_partition := '开始时间'
);
```
作用：

1. 把父表写进 `partman.part_config`，
2. 认领已存在的老分区，纳入 partman 管理
3. 从起始点补齐到 `当前时间 + premake`（默认 `premake=4`，即未来 4 个；首次创建还会回溯补历史分区，除非指定了 `p_start_partition`）。

补充：`p_start_partition` 不传时，起始点 = `当前时间 − 间隔×premake`（往前 4 个）；传了则以给定值为起点，不再固定往前补。序列型一旦传了 `p_start_partition`，完全不创建历史分区。

### 重点：存在写操作时，官方文档建议第一、二步必须在同一个事务中完成（不是很理解，感觉解释的牵强）
**原因：**

1. **窗口期的并发写会让 `create_partition` 直接失败。** 改名提交后到 `create_partition` 之间存在窗口期，写入仍在继续。此刻「当前时间」可能已超出最后一个子表上界，新数据会落进 `DEFAULT`；接着 `create_partition` 要新建覆盖该区间的分区，而原生分区**禁止 attach 一个范围已包含 DEFAULT 中现有数据的分区** → 报错中止。同理，若窗口期数据导致新分区边界与已有分区重叠，也会触发 `overlap` 错误。
2. **验证时间导致「验证的 ≠ 提交的」。** 分两步时，你在事务里验证通过后提交，但验证到提交之间写入没停，状态可能已变化。
3. **回滚补救代价高。** 若第二步失败需回滚、再把子表名改回去，这些 `ALTER TABLE ... RENAME` 要 `ACCESS EXCLUSIVE` 锁，在写入高负载下会长时间阻塞业务，窗口被拉长、风险叠加。

**同一事务如何解决：** `create_partition` 建分区时会对父表加锁，把并发写挡在转换之外，直到整体提交。数据不会在两步之间溜进 DEFAULT；要么整体成功（名字对 + config 对），要么整体回滚（回到原始干净状态），不会留下「名字改了、config 没建」的半成品。

**能否分开：** 能停写 → 可以分开（但建议同事务，便于失败整体回滚）；停不了写 → 必须同事务。

### 实操技巧：回滚式验证

在一个事务里完成「改名 + `create_partition`」，用 `\d+` 和 `partman.part_config` 验证结果，确认无误再 `COMMIT`；有问题直接 `ROLLBACK`，改名一并撤销，无需手工回退。

## partman 管理转换为原始分区表

能否调整分区范围？ 分区计算方式为下一个分区的起点是，上个分区的起点+分区间隔。

调大会有区间缝隙，后期通过手动补齐。

调小直接回重叠报错。 

建议重新规划一个新分区，之后将原分区迁移到新分区中。


