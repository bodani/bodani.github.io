# meminfo Linux 内存信息

## 介绍

/proc/meminfo是了解Linux系统内存使用状况的主要接口，我们最常用的”free”、”vmstat”等命令就是通过它获取数据的 

#### 内容解读

```
cat /proc/meminfo 
MemTotal:        8009504 kB  除了bios ，kernel本身占用的内存以外，可以被kernel所分配的内存。一般这个值固定不变。  
MemFree:         2385828 kB  未被使用的内存
MemAvailable:    4741232 kB  该值为系统估计值
Buffers:               0 kB  给文件做缓存大小
Cached:          4701848 kB  内存使用
SwapCached:        35516 kB  交换分区使用
Active:          4175652 kB  在活跃使用中的缓冲或高速缓冲存储器页面文件的大小，除非非常必要否则不会被移作他用. 
Inactive:        1037948 kB  在不经常使用中的缓冲或高速缓冲存储器页面文件的大小，可能被用于其他途径.
Active(anon):    2175852 kB
Inactive(anon):   570728 kB
Active(file):    1999800 kB
Inactive(file):   467220 kB
Unevictable:           0 kB
Mlocked:               0 kB
SwapTotal:       1048572 kB
SwapFree:         904956 kB
Dirty:               708 kB 等待被写回到磁盘的内存大小。
Writeback:             0 kB 正在被写回到磁盘的内存大小。
AnonPages:        482164 kB 
Mapped:          1991344 kB
Shmem:           2234828 kB
Slab:             247824 kB
SReclaimable:     194368 kB
SUnreclaim:        53456 kB
KernelStack:        6976 kB
PageTables:        63760 kB  管理内存分页页面的索引表的大小。
NFS_Unstable:          0 kB
Bounce:                0 kB
WritebackTmp:          0 kB
CommitLimit:     5053324 kB
Committed_AS:    5182268 kB
VmallocTotal:   34359738367 kB
VmallocUsed:       23696 kB
VmallocChunk:   34359707388 kB
HardwareCorrupted:     0 kB
AnonHugePages:     65536 kB
CmaTotal:              0 kB
CmaFree:               0 kB
HugePages_Total:       0    Hugepages在/proc/meminfo中是被独立统计的，与其它统计项不重叠
HugePages_Free:        0
HugePages_Rsvd:        0
HugePages_Surp:        0
Hugepagesize:       2048 kB
DirectMap4k:      133084 kB
DirectMap2M:     8255488 kB

```

## free

```
free -m
              total        used        free      shared  buff/cache   available
Mem:           7824         750         227          12        6845        6766
Swap:          4095          40        4055
```

- total 总内存 
- shared 应用共享使用内存
- buff/cache buff写占用 cache读占有
- available 应用可以申请的内存

#### 释放buff/cache示例

查看内存情况   buff/cache 194 
```
free -m
              total        used        free      shared  buff/cache   available
Mem:           7824         749        6879          12         194        6835
Swap:          4095          40        4055
```

读写操作
```
cp -r /opt /tmp
```

再次查看内存情况 buff/cache 6381
```
free -m
              total        used        free      shared  buff/cache   available
Mem:           7824         745         697          12        6381        6771
Swap:          4095          40        4055
```

清理 buff/cache
```
> sync                               #在清除前执行 ， 刷新脏数据
> echo 1 > /proc/sys/vm/drop_caches  #清除page cacheecho
> echo 2 > /proc/sys/vm/drop_caches  #清除回收slab分配器中的对象（包括目录项缓存和inode缓存
> echo 3 > /proc/sys/vm/drop_caches  #清除pagecache和slab分配器中的缓存对象
```

清除后内存释放
```
free -m
              total        used        free      shared  buff/cache   available
Mem:           7824         749        6880          12         194        6836
Swap:          4095          40        4055
```

## vmstat

```
 procs -----------memory---------- ---swap-- -----io---- -system-- -----cpu------ 
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st 
 1  0 240780 847772 122888 573556    0    0     2    56    9    3  1  2 96  1  0 
```

#### 解读

```
##>Procs 
   r: 运行的和等待(CPU时间片)运行的进程数，这个值也可以判断是否需要增加CPU(长期大于1) 
   b: 处于不可中断状态的进程数，常见的情况是由IO引起的 
##>Memory 
   swpd: 切换到交换内存上的内存(默认以KB为单位) 
         如果 swpd 的值不为0，或者还比较大，比如超过100M了，但是si, so 的值长期为0，这种情况我们可以不用担心，不会影响系统性能。 
   free: 空闲的物理内存 
   buff: 作为buffer cache的内存，对块设备的读写进行缓冲 
  cache: 作为page cache的内存, 文件系统的cache 
         如果 cache 的值大的时候，说明cache住的文件数多，如果频繁访问到的文件都能被cache住，那么磁盘的读IO bi 会非常小。  
##>Swap 
   si: 交换内存使用，由磁盘调入内存 
   so: 交换内存使用，由内存调入磁盘 
       内存够用的时候，这2个值都是0，如果这2个值长期大于0时，系统性能会受到影响。 
    磁盘IO和CPU资源都会被消耗。我发现有些朋友看到空闲内存(free)很少或接近于0时，就认为内存不够用了，实际上不能光看这一点的，还要结合si,so，如果free很少，但是si,so也很少(大多时候是0)，那么不用担心，系统性能这时不会受到影响的。   
##>Io 
   bi: 从块设备读入的数据总量(读磁盘) (KB/s) 
   bo: 写入到块设备的数据总理(写磁盘) (KB/s) 
       随机磁盘读写的时候，这2个 值越大（如超出1M），能看到CPU在IO等待的值也会越大    
##>System 
   in: 每秒产生的中断次数 
   cs: 每秒产生的上下文切换次数 
       上面这2个值越大，会看到由内核消耗的CPU时间会越多    
##>Cpu 
   us: 用户进程消耗的CPU时间百分比 
       us 的值比较高时，说明用户进程消耗的CPU时间多，但是如果长期超过50% 的使用，那么我们就该考虑优化程序算法或者进行加速了(比如 PHP/Perl) 
   sy: 内核进程消耗的CPU时间百分比 
       sy 的值高时，说明系统内核消耗的CPU资源多，这并不是良性的表现，我们应该检查原因。 
   wa: IO等待消耗的CPU时间百分比 
       wa 的值高时，说明IO等待比较严重，这可能是由于磁盘大量作随机访问造成，也有可能是磁盘的带宽出现瓶颈(块操作)。 
   id: CPU处在空闲状态时间百分比   

```

内存溢出问题

https://www.oracle.com/technical-resources/articles/it-infrastructure/dev-oom-killer.html

更多关于linux 系统内存问题定位方法

https://cloud.tencent.com/developer/article/2168100
