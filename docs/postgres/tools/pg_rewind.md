# pg_rewind 时间线对齐

pg_rewind requires that the target server either has the wal_log_hints option enabled in postgresql.conf or data checksums enabled when the cluster was initialized with initdb. Neither of these are currently on by default. full_page_writes must also be set to on, but is enabled by default.

wal_log_hints

## 使用场景 

在数据库主从结构中，从变成主易。但是由主变为从却需要一番周折。  
如果是数据量少时重新使用pg_backup拉一份从即可，但是如果数据量大时，这个过程非常的耗时耗能。对线上业务也会有影响。      
在实际的场景中主从之间的数据绝大部分时一致的，只有非常少量的近期产生的数据是不一致的。  
有没有什么方式可以利用已有的数据，充分利用已有的数据呢？  
pg_rewind登场 告别一下回到解放前。

## 基本原理

数据库每次的主从切换时，timeLine会增加1。 新老数据库在不同的时间线上运行。
使用pg_rewind 将数据拉回到时间线(timeLine)产生分裂的那个点上。重新选择时间线，重放新时间线上的wal日志，使两个数据库重新回到一个时间线，并且数据一致。  


## 开始实验

背景: 

主从数据库结构

10.1.88.71 主库  
10.1.88.72 从库

目标

数据库主从兑换， 主降为从时使用pg_rewind校对时间线


## 实际操作

注意事项 : 

- 必须开启full_page_writes 默认开启
- 必须开启wal_log_hints 修改后需要重启 或者data block checksum 数据库初始化时设置

如果在初始化的时候没有开启checksum ,在version 12 及以后的版本中可以使用 [pg_checksum](https://www.modb.pro/db/103607) 重新设置  

1 将10.1.88.72从库变成主库

```
#从变主
touch /home/postgres.trigger
#查看日志
2019-03-15 14:15:02.608 CST [7831] LOG:  trigger file found: /home/postgres.trigger
2019-03-15 14:15:02.608 CST [7831] LOG:  redo done at 0/2000130
2019-03-15 14:15:02.608 CST [7831] LOG:  selected new timeline ID: 2
2019-03-15 14:15:02.608 CST [7828] LOG:  database system is ready to accept read only connections
2019-03-15 14:15:02.686 CST [7831] LOG:  archive recovery complete
2019-03-15 14:15:02.703 CST [7828] LOG:  database system is ready to accept connections
#此时两个数据库都可写
```

2 模拟向两个数据库中写数据

3 将数据库原主库（10.1.88.71）变为从库

##### 一下步骤必须按照顺序执行，并且中间不要操作失误！！！

a 停库

```
  systemctl stop postgresql-10
```

b 切换到postgres用户 进行时间线对齐

```
# 切用户
sudo su - postgres 
# 测试 -n
/usr/pgsql-10/bin/pg_rewind -n -D /var/lib/pgsql/10/data/ --source-server="hostaddr=10.1.88.72 user=postgres port=5432"
# 正式执行
/usr/pgsql-10/bin/pg_rewind -D /var/lib/pgsql/10/data/ --source-server="hostaddr=10.1.88.72 user=postgres port=5432" -P
```

c 修改 recovery.conf

```
mv recovery.done recovery.conf
```

vi recovery.conf
```
recovery_target_timeline='latest'
standby_mode = 'on'
primary_conninfo = 'user=postgres passfile=''/root/.pgpass'' host=10.1.88.72 port=5432 sslmode=prefer sslcompression=1 krbsrvname=postgres target_session_attrs=any'
```

#### 注意事项: 

host 指向新主库地址

以上过程中保持数据库是关闭状态!!!! ， 如果出现数据库以主库的形式运行的情况，pg_stat_replication 中的 flush_lsn , replay_lsn 不在更新。及主从数据不更新。 只能重新拉取。 

pg_rewind 会将 recovery.conf 会被 recovery.done。复制过程会，如果主库有的recovery.done文件，则会复制到备库并覆盖文件。此时重新修改recovery.done并重命名为recovery.conf

谨记，在启动数据前仔细检测 recovery.conf 文件。确保数据库以从库形式运行。

4 启动数据库，并验证

## 备注

以前操作时，主从切换后，主从状态是对的，但是向主库写数据，从库没有同步。（原因不详）    
今天按照上面的操作，测试的多次都成功了！！！

## 扩展

查看数据库timeline 等信息

```
# 在数据所在位置执行
/usr/pgsql-10/bin/pg_controldata .
```

## 更多

https://github.com/digoal/blog/blob/master/201901/20190128_02.md

## 应用

典型应用场景，在发生故障转移后，原主库重新加入集群中。

## 原理

基本思想是将所有文件系统级的变化从源集群复制到目标集群。

1 连接到源端数据库，可以对比找到本地数据库分叉点之前最后一次checkpoint的在wal日志中位置，解析分叉点后的WAL，记录这些事务修改了哪些数据块

2 对于数据文件，只从新主拉取被旧主修改了的数据块，并覆盖旧主数据文件中对应的数据块

3 拷贝WAL segments, `pg_xact`,  及配置文件， 忽略 `pg_dynshmem/`, `pg_notify/`, `pg_replslot/`, `pg_serial/`, `pg_snapshots/`, `pg_stat_tmp/`, and `pg_subtrans/` 

4 把旧主改成恢复模式，恢复的起点则设置为分叉点前的最近一次checkpoint

5 当启动旧主库后，自动重放wal日志即可完成数据的同步

参加官方文档 https://www.postgresql.org/docs/14/app-pgrewind.html

## 创建rewind 用户

```
CREATE USER {{ REWIND_USER }} ENCRYPTED PASSWORD '{{ REWIND_PASSWORD }}';
GRANT EXECUTE ON function pg_catalog.pg_ls_dir(text, boolean, boolean) TO {{ REWIND_USER }};
GRANT EXECUTE ON function pg_catalog.pg_stat_file(text, boolean) TO {{ REWIND_USER }};
GRANT EXECUTE ON function pg_catalog.pg_read_binary_file(text) TO {{ REWIND_USER }};
GRANT EXECUTE ON function pg_catalog.pg_read_binary_file(text, bigint, bigint, boolean) TO {{ REWIND_USER }};
```
