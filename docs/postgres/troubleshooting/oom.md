# 数据库 OOM 预防

降低 PostgreSQL 主进程被操作系统 OOM Killer 误杀的风险，可从崩溃重启策略、内存 overcommit、oom_score_adj 等方面入手。

## restart_after_crash

默认开启崩溃后自动重启：

```sql
postgres=# show restart_after_crash;
 restart_after_crash
---------------------
 on
(1 row)
```

## vm.overcommit

```bash
# vi /etc/sysctl.conf

# 0 表示内核将检查是否有足够的可用内存供应用进程使用；如果有足够的可用内存，内存申请允许；否则，内存申请失败，并把错误返回给应用进程
# 1 表示内核允许分配所有的物理内存，而不管当前的内存状态如何
# 2 表示内核允许分配超过所有物理内存和交换空间总和的内存
vm.overcommit_memory = 2
vm.overcommit_ratio = 90 # overcommit_memory= 2 时生效
vm.swappiness = 1 # 交换分区

# sysctl -p
```

## oom_score_adj

`oom_score_adj` 的取值范围为 -1000 到 1000，值越大，被 OS 干掉的风险越大。

启动前设置：

```bash
# vi /usr/lib/systemd/system/postgresql-10.service
# Disable OOM kill on the postmaster
OOMScoreAdjust=-1000
Environment=PG_OOM_ADJUST_FILE=/proc/self/oom_score_adj
Environment=PG_OOM_ADJUST_VALUE=0
```

启动后设置：

```bash
Pid=`head -n 1 /PATH/TO/postmaster.pid` && echo -1000 > /proc/$Pid/oom_score_adj
```

## NUMA

（待补充）
