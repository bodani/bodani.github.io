# mysql 内存占用分析



## 操作系统内存分析

### 系统内存类型

VSS 

| 内存类型 | 单独占用 | 共享     | 分配未使用 |
| -------- | -------- | -------- | ---------- |
| VSS      | √        | √        | √          |
| RSS      | √        | √        |            |
| PSS      | √        | 比例分配 |            |
| USS      | √        |          |            |

### 系统查看内存

#### ps 

```language
ps eo user,pid,vsz,rss $(pgrep -f 'mysqld')
```

#### top 

```
top pid  xxx  &&   shift + M
```

#### smem 

```language
# 安装 (CentOS/RHEL):
yum install smem

# 查看 mysql 进程内存分布
smem -t -p $(pgrep mysqld)

# 常见的用法选项:
smem -K                    # 显示 VSS 大小
smem -W                    # 显示 RSS 大小
smem -S                    # 按 PSS 排序
smem -P                    # 按 USS 排序
smem -t                    # 显示表格格式的汇总信息
```

常用参数说明：
- `-t`: 使用制表符分隔的纯文本格式输出结果
- `-c KISS`: 自定义显示的列 (K=虚拟共享、I=私有共享、M=匿名非共享)
- `--ps`: 进程详细信息摘要输出
- `-r` 或 `-H`: 按共享区域或进程层次排序
- `--total`: 汇总所有进程统计信息

常用筛选/查看场景:

**1. 查看特定进程的详细内存分布:**
```bash
# MSSQL Server 通常占用较多内存 (替换为你的 mysqld 进程号)
smem -k -t | grep $(pgrep mysqld)
```

**2. 对比 VSS/RSS/PSS/USS 四种内存视角:**
```bash
# -c 用于选择要显示的列，例如: 
#  pss  = proportional set size (共享页面按比例分摊后的物理页）
#  uss  = unique set size(当前驻留在主存里且没有和其他进程共享的独占物理分页数）。
# rss  = resident set size(V 区常驻集的当前常驻集包含的内存量）
# vsize = 一个虚拟内存区的内存分配总量。
smem -c pid,pid,vsz,rss,pss,uss,command
```

smem 的输出列含义：

| 列名   | 含义说明                                                     |
|--------|--------------------------------------------------------------|
| USS    | Unique Set Size，独占物理内存大小（不含共享页）              |
| PSS    | Proportional Set Size，比例分配的物理内存                    |
| CSS    | Collective Set Size，所有进程共享的页面                       |
| Swap   | 交换到磁盘的空间                                              |

查看 MySQL 相关示例：

**查询 mysqld 进程的 USS：**
```bash
smem -c "pid,rss,pss,uss,sz,state,nthreads,name,user" | grep mysqld  
```

**查看 PSS 和 USS 对比（有助于识别内存泄漏）：**
```bash
watch 'echo "RSS: $(pmap -w $(pgrep mysqld) | tail -1)" && sleep 5' && \
  watch "awk '{printf \"PSS:%s, USS:%s, VSS:%s\\n\", \$5,\$4,\$3}' /proc/\$(pgrep mysqld)/smaps \> mysqld.smaps.log; sleep 60"
```


#### pmap

```
   pmap  -x 121357 | sort -nrk3
```

- ​    Address：表示此内存段的起始地址
- ​    Kbytes：表示此内存段的大小(ps：这是虚拟内存)
- ​    RSS：表示此内存段实际分配的物理内存，这是由于Linux是延迟分配内存的，进程调用malloc时Linux只是分                   配了一段虚拟内存块，直到进程实际读写此内存块中部分时，Linux会通过缺页中断真正分配物理内存。
- ​    Dirty：此内存段中被修改过的内存大小，使用mmap系统调用申请虚拟内存时，可以关联到某个文件，也可不关联，当关联了文件的内存段被访问时，会自动读取此文件的数据到内存中，若此段某一页内存数据后被更改，即为Dirty，而对于非文件映射的匿名内存段(anon)，此列与RSS相等。
- ​    Mode：内存段是否可读(r)可写(w)可执行(x)
- ​    Mapping：内存段映射的文件，匿名内存段显示为anon，非匿名内存段显示文件名(加-p可显示全路径)。

    检查一段时间后新增了哪些内存段，或哪些变大
    
    pmap -x 1 > pmap-`date +%F-%H-%M-%S`.log
    
    icdiff pmap-2023-07-27-09-46-36.log pmap-2023-07-28-09-29-55.log | less -SR

#### 通过进程号查看

```
cat /proc/$pid/status/ | grep Vm
```

### 释放内存

```
sync
echo N > /proc/sys/vm/drop_caches ; N = 1 ,2 , 3
```



## Mysql 服务内存查看

mysql内存计算 https://www.mysqlcalculator.com/

### 内存占用统计

- 进程使用内存
- 缓存使用内存
- 连接使用内存
- 其他，如日志，临时存储，复制

mysql服务为单进程多线程运行方式

1. 所有线程共用共享全局内存
2.  线程独占内存

总内存 = 全局内存+线程数*线程独占内存+其他

###  共享内存

```
--- 查看全局内存参数设置
show variables where variable_name in ('innodb_buffer_pool_size','innodb_log_buffer_size','innodb_additional_mem_pool_size','key_buffer_size');

--- 计算全局内存
select (@@innodb_buffer_pool_size
+@@innodb_log_buffer_size
+@@key_buffer_size) / 1024/1024 AS MEMORY_MB;
```

### 单线程内存

```
--- 计算单个线程占用的内存
SELECT ( (  @@read_buffer_size 
+@@read_rnd_buffer_size 
+@@sort_buffer_size 
+@@join_buffer_size 
+@@binlog_cache_size 
+@@thread_stack 
+@@max_allowed_packet 
+@@net_buffer_length  )
) / ( 1024  *1024 ) AS MEMORY_MB;
```

正在运行的线程

```
SHOW FULL PROCESSLIST
```

### 通过mysql视图进行内存统计

#### 服务运行总内存

```
SELECT 
SUM(CAST(replace(current_alloc,'MiB','')  as DECIMAL(10, 2))  ) 
FROM sys.memory_global_by_current_bytes
WHERE current_alloc like '%MiB%';
```

#### 分事件统计内存

```
SELECT SUBSTRING_INDEX(event_name,'/', 2 ) AS
       code_area, sys.format_bytes(SUM(current_alloc))
       AS current_alloc
       FROM sys.x$memory_global_by_current_bytes
       GROUP BY SUBSTRING_INDEX(event_name,'/', 2 )
       ORDER BY SUM(current_alloc) DESC;

SELECT event_name,
    SUM(CAST(replace(current_alloc,'MiB','')  as DECIMAL(10, 2))  )
    FROM sys.memory_global_by_current_bytes
    WHERE current_alloc like '%MiB%' GROUP BY event_name  
     ORDER BY SUM(CAST(replace(current_alloc,'MiB','')  as DECIMAL(10, 2))  ) DESC ;

SELECT event_name,
       sys.format_bytes(CURRENT_NUMBER_OF_BYTES_USED)
FROM performance_schema.memory_summary_global_by_event_name
ORDER BY  CURRENT_NUMBER_OF_BYTES_USED DESC
LIMIT 10;


-- 查看内存分配器统计（需 MySQL 5.7+）
SELECT 
  EVENT_NAME, 
  COUNT_ALLOC 
FROM performance_schema.memory_summary_global_by_event_name 
WHERE EVENT_NAME LIKE 'memory/sql/%' 
ORDER BY COUNT_ALLOC DESC;
```

SELECT   sys.format_bytes(SUM(CURRENT_NUMBER_OF_BYTES_USED))
FROM performance_schema.memory_summary_global_by_event_name

#### 分账号统计

```
SELECT user,event_name,current_number_of_bytes_used/1024/1024 as MB_CURRENTLY_USED
FROM performance_schema.memory_summary_by_account_by_event_name
WHERE host<>"localhost"
ORDER BY  current_number_of_bytes_used DESC LIMIT 10;
```

#### performance 占用内存

```
show engine performance_schema status;
```

#### 其他

```
存在碎片的表
select concat('optimize table ',table_schema,'.',table_name,';'), data_free, engine from information_schema.tables 
where data_free>0 and engine !='MEMORY';

排序
SELECT table_schema, TABLE_NAME, concat(data_free/1024/1024, 'M') as data_free FROM `information_schema`.tables
WHERE data_free > 3 * 1024 * 1024 AND ENGINE = 'innodb' ORDER BY data_free DESC;
处理
optimize table xxxx_TABLES;
```

使用以下查询查看哪些事务正在等待，哪些事务正在阻塞它们

```sql
SELECT 
  r.trx_id waiting_trx_id, 
  r.trx_mysql_thread_id waiting_thread, 
  r.trx_query waiting_query, 
  b.trx_id blocking_trx_id, 
  b.trx_mysql_thread_id blocking_thread, 
  b.trx_query blocking_query 
FROM 
  performance_schema.data_lock_waits w 
  INNER JOIN information_schema.innodb_trx b ON b.trx_id = w.blocking_engine_transaction_id 
  INNER JOIN information_schema.innodb_trx r ON r.trx_id = w.requesting_engine_transaction_id;
```

或者，更简单的方式，直接看sys数据库中的 innodb_lock_waits 视图

```sql
SELECT 
    waiting_trx_id,
    waiting_pid,
    waiting_query,
    blocking_trx_id,
    blocking_pid,
    blocking_query
FROM
    sys.innodb_lock_waits;
```

### 内存相关参数 

#### 共享内存

**innodb_buffer_pool_size** 该部分缓存是 InnoDB 引擎最重要的缓存区域，是通过内存来弥补物理数据文件的重要手段，在云数据库 MySQL 上会采用实例规格配置的50% - 80%作为该部分大小（上图为1000MB * 0.5 = 500MB）。其中主要包含数据页、索引页、undo 页、insert buffer、自适应哈希索引、锁信息以及数据字典等信息。在进行 SQL 读和写的操作时，首先并不是对物理数据文件操作，而是先对 buffer_pool 进行操作，再通过 checkpoint 等机制写回数据文件。该空间的优点是可以提升数据库的性能、加快 SQL 运行速度，缺点是故障恢复速度较慢。

**innodb_log_buffer_size** 该部分主要存放 redo log 的信息，在云数据库 MySQL 上会设置64MB的大小。InnoDB 会首先将 redo log 写在这里，然后按照一定频率将其刷新回重做日志文件中。该空间不需要太大，因为一般情况下该部分缓存会以较快频率刷新至 redo log（Master Thread 会每秒刷新、事务提交时会刷新、其空间少于1/2时同样会刷新）。

**innodb_additional_mem_pool_size** 该部分主要存放 InnoDB 内的一些数据结构，在云数据库 MySQL 中统一设置为8MB。通常是在 buffer_pool 中申请内存的时候还需要在额外内存中申请空间存储该对象的结构信息。该大小主要与表数量有关，表数量越大需要更大的空间。

#### 私有内存

**read_buffer_size**  分别存放了对顺序扫描的缓存，当 thread 进行顺序扫描数据时会首先扫描该 buffer 空间以避免更多的物理读。

**read_rnd_buffer_size**  分别存放了对随机扫描的缓存，当 thread 进行随机扫描数据时会首先扫描该 buffer 空间以避免更多的物理读。

**sort_buffer_size**  需要执行 order by 和 group by 的 SQL 都会分配 sort_buffer，用于存储排序的中间结果。在排序过程中，若存储量大于 sort_buffer_size，则会在磁盘生成临时表以完成操作。

**join_buffer_size**  MySQL 仅支持 nest loop 的 join 算法，处理逻辑是驱动表的一行和非驱动表联合查找，这时就可以将非驱动表放入 join_buffer，不需要访问拥有并发保护机制的 buffer_pool。

**binlog_cache_size**  该区域用来缓存该 thread 的 binlog 日志，在一个事务还没有 commit 之前会先将其日志存储于 binlog_cache 中，等到事务 commit 后会将其 binlog 刷回磁盘上的 binlog 文件以持久化。

**tmp_table_size**  不同于上面各个 session 级的 buffer，这个参数可以在控制台上修改。该参数是指用户内存临时表的大小，如果该 thread 创建的临时表超过它设置的大小会把临时表转换为磁盘上的一张 MyISAM 临时表。

https://www.modb.pro/db/86827

#### 怀疑内存泄露

glibc

```
--- 统计内存
gdb -q -batch -ex 'call malloc_stats()' -p  121357
--- 手释放内存
gdb --batch --pid 121357 --ex 'call malloc_trim(0)'
```

## 处理方式

```
--- 关闭数据库服务，由自动重启机制重启
shutdown

select * from performance_schema.replication_group_memebers;
```



https://mp.weixin.qq.com/s?__biz=MjM5NzAzMTY4NQ==&mid=2653941614&idx=1&sn=8f1eea4f37e885122e3e216c34e76c2a&chksm=bd3b75048a4cfc124559482a159007ba861396ab5bcdaf3c2591de6a2a71adee5c7d590ac8f6#rd


## mgr 参数
```
@@group_replication_message_cache_size=1073741824
```

pmap -x $(pidof mysqld) | sort -k3 -nr | head -n 20



实测分析

```
pt-mysql-summary --user=administrator --password=zVft37KE9Z --host=10.2.14.23 --port=3306
```
分析内存

-- 限制临时表内存
SET persist tmp_table_size = 64 * 1024 * 1024;     -- 64M
SET persist max_heap_table_size = 64 * 1024 * 1024;

-- 降低排序/JOIN 缓冲区
SET persist sort_buffer_size = 128 * 1024;        -- 128K
SET persist join_buffer_size = 128 * 1024;

-- 缩小 InnoDB 缓冲池
SET persist innodb_buffer_pool_size = 700 * 1024 * 1024;  -- 700M

-- 增加线程缓存
SET persist thread_cache_size = 100;
SET persist max_connections = 100;



## mysql 内存问题分析

系统级别 
```
#top -p $(pidof mysqld)

PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM  TIME+ COMMAND 
1   1001      20   0   14.8g   5.9g  50568 S   0.7   0.6 211:56.90 mysqld
```

```
top -p $(pidof mysqld)  # 实时监控MySQL进程内存
cat /proc/$(pidof mysqld)/status | grep Vm  # 查看虚拟内存使用
```

```
SELECT * FROM sys.memory_global_total;  
SELECT EVENT_NAME, 
       ROUND(CURRENT_NUMBER_OF_BYTES_USED/1024/1024,2) AS memory_mb
FROM performance_schema.memory_summary_global_by_event_name
ORDER BY memory_mb DESC LIMIT 10; 
```
```
SELECT m.EVENT_NAME, t.PROCESSLIST_ID, 
       ROUND(m.CURRENT_NUMBER_OF_BYTES_USED/1024/1024,2) AS mem_mb
FROM performance_schema.memory_summary_by_thread_by_event_name m
JOIN performance_schema.threads t USING (THREAD_ID)
WHERE t.PROCESSLIST_ID != CONNECTION_ID()
ORDER BY m.CURRENT_NUMBER_OF_BYTES_USED DESC LIMIT 10;
```

## 压测

sysbench /usr/local/sysbench/share/sysbench/oltp_read_only.lua  --mysql-host=127.0.0.1 --mysql-port=3306 --mysql-user=root --mysql-password=root --mysql-db=sbtest --tables=15 --table-size=1000000 --threads=150 --time=60 run

关联
https://mp.weixin.qq.com/s?__biz=MzU5MDU1NDE2MA==&mid=2247484558&idx=1&sn=953551bf6e5830968019415c1f94bcde&chksm=ff3a1efe753cdc85689b7a0ac4323e926075f234ede914078a62a77435e8824aaecb23844424#rd

https://mp.weixin.qq.com/s?__biz=Mzg2Mjc5MzQ4OQ==&mid=2247483828&idx=1&sn=09eaef6aeaaa7cf1ed20d4bf7d9b5b12&chksm=ce033bcaf974b2dc80e826d648e69288156276086c7a017c1b8acc62272e3caf14ae10f745df#rd

https://segmentfault.com/a/1190000045371971

https://cloud.tencent.com/developer/inventory/14836/article/1621898

gdb --batch --pid `pidof mysqld` --ex 'call malloc_trim(0)'

连接时候需要的参数
```
read_buffer_size = 4M
read_rnd_buffer_size = 4M
sort_buffer_size = 4M
join_buffer_size = 4M
tmp_table_size = 32M
max_heap_table_size = 32M
max_connections = 512
```

## 处理

thread_cache_size = 0
innodb_flush_method=O_DIRECT



group_replication_single_primary_mode=ON
log_error_verbosity=3
group_replication_bootstrap_group=OFF 
group_replication_transaction_size_limit=<默认值150MB，但建议调低在20MB以内，不要使用大事务>
group_replication_communication_max_message_size=10M
group_replication_flow_control_mode=OFF #官方版本的流控机制不太合理，其实可以考虑关闭
group_replication_exit_state_action=READ_ONLY
group_replication_member_expel_timeout=5 