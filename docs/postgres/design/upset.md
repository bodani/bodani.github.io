# upset 用法

### 创建表

```
DROP TABLE IF EXISTS "goods";
CREATE TABLE "goods" (
  "store_cd" int4 NOT NULL,
  "good_cd" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "name" varchar(255) COLLATE "pg_catalog"."default"
);

INSERT INTO "goods" VALUES (101, '1', '张三');
INSERT INTO "goods" VALUES (102, '2', '李四');
INSERT INTO "goods" VALUES (103, '3', '王五');

ALTER TABLE "goods" ADD CONSTRAINT "pr_cd_key" PRIMARY KEY ("store_cd", "good_cd");

```

### 数据存在则更新数据，不存在则插入数据

```
---
INSERT INTO GOODS VALUES ( 104, '4', '赵六' ) 
ON CONFLICT ON CONSTRAINT pr_key_cd DO
UPDATE 
	SET NAME = '更新' 
WHERE
	GOODS.STORE_CD = '104' 
	AND GOODS.GOOD_CD = '4'
----
pr_key_cd为必须为唯一主键，也可以用下面写法（注意：必须保证筛选出数据唯一）
INSERT INTO GOODS VALUES ( 104, '4', '赵六' ) 
ON CONFLICT ( STORE_CD, GOOD_CD ) DO
UPDATE 
	SET NAME = '更新' 
WHERE
	GOODS.STORE_CD = '104' 
	AND GOODS.GOOD_CD = '4'
	AND NAME <> '更新' ---过滤 没有必要的更新
```

### 数据存在则忽略，不存在则插入

```
INSERT INTO GOODS VALUES ( 104, '4', '赵六' ) 
ON CONFLICT ON CONSTRAINT pr_key_cd DO NOTHING;

-- 另一种实现方式
insert into goods select 103,'3','赵六' from (select 1) temp where not exists (select 1 from goods where store_cd=103 and good_cd = '3');
```

上面的两种的写法，是先执行insert如果主键冲突则执行update，没有冲突就执行insert了。

### 先执行update语句

```
WITH TABLE1 AS ( UPDATE GOODS SET NAME = '更新' WHERE STORE_CD = '104' AND GOOD_CD = '4' RETURNING * ) 
INSERT INTO GOODS SELECT  104, '4', '赵六' 
WHERE NOT EXISTS ( SELECT 1 FROM TABLE1 WHERE STORE_CD = '104' AND GOOD_CD = '4') 
```


