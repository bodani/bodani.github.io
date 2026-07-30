# 例子

```
select pg_current_wal_lsn(),pg_walfile_name(pg_current_wal_lsn()),pg_walfile_name_offset(pg_current_wal_lsn());
 pg_current_wal_lsn |     pg_walfile_name      |       pg_walfile_name_offset
--------------------+--------------------------+------------------------------------
 2478/BB36EC90      | 0000000300002478000000BB | (0000000300002478000000BB,3599504)
(1 row)
```

```
select x'36EC90'::int ;
  int4
---------
 3599504
(1 row)
```

# 说明

## 方法

- pg_current_wal_lsn()：获得当前wal日志写入位置。
- pg_walfile_name():转换wal日志位置为文件名。
- pg_walfile_name_offset():返回转换后的wal日志文件名和偏移量。

 
## LSN

 LSN:2478/BB36EC90

- 2478：代表wal文件的第二部分
- BB：代表wal文件的最后两位
- 36EC90：代表偏移量

## WAL	

0000000300002478000000BB
wal文件由8*3 = 24个字符，三部分组成，每部分由8个字符组成，代表含义如下

- 00000003：代表数据库运行的时间轴，如果恢复过数据库（主备切换）这个值会增大
- 00002478：对LSN的第二部分对应
- 000000BB：代表walfile文件的最后两位
