# vacuum 限流

## 限流目的 

清理是在后台运行的维护任务，对用户查询的影响最小。不应该消耗太多的资源(CPU和磁盘I/O)。

## 清理成本计算

清理过程相当简单，它从数据文件中读取页面(8kB的数据块)，并检查是否需要清理。如果没有dead tuples，页面将被简单地丢弃，而不进行任何更改。否则，它将被清理(删除dead tuples)，被标记为“脏的”，并最终被写出来

成本计算是基于以下三个基本操作的成本定义

```
vacuum_cost_page_hit = 1
vacuum_cost_page_miss = 10
vacuum_cost_page_dirty = 20
```

从shared_buffers读取页面，则计数为1。

如果shared_buffers中没有找到它而需要从操作系统中读取，计数为10(它可能仍然由RAM提供，但我们不知道)。

最后，如果页面被清理弄脏了，则计数为20

## 成本限制

通过限制一次性完成的工作量(默认设置为200)来实现限流，每次清理工作完成这么多工作(计数达到autovacuum_vacuum_cost_limit )，它就会休眠20毫秒。

```
autovacuum_vacuum_cost_delay = 20ms
autovacuum_vacuum_cost_limit = 200
```

## 进程数

```
autovacum_max_workers
```

增加清理的进程数据是否可以提高清理效率。不

成本限制是全局级别的，由所有的autovacuum进程共同承担。每个进程只会得到总成本限制的1/ autovacum_max_workers，因此增加进程数量只会让他们走得更慢。

## 表级限制设置

```
ALTER TABLE t SET (autovacuum_vacuum_cost_limit = 1000);
ALTER TABLE t SET (autovacuum_vacuum_cost_delay = 10);
```
