# swapoff（关闭交换分区）

### 监控报警

告警规则（Prometheus）:

```yaml
# AlertRule
(1 - (node_memory_SwapFree_bytes / node_memory_SwapTotal_bytes)) * 100 > 80
```

当 swap 使用率超过 80% 时触发告警。

---

### 查看业务，确认可以关闭

在业务机器上手动检查内存情况：

```bash
# 以 GB 为单位查看内存使用情况
free -g
```

**决策依据**: 

| 条件 | 说明 |
|------|------|
| 物理内存充足 | Mem Free 和 Available 较高，不是因内存不足导致的频繁交换 |
| Swap 分配较小且非必须使用 | 当前的 swap 未被内存压力大量置换 |
| 结合业务判断 | 当前负载允许短暂停顿 |

如果上述条件都满足，则可以继续执行 `swapoff`:

```bash
sudo swapoff -a -v     # verbose: 显示详细信息模式
```

预期成功结束。

---

###  `swapoff -a -v`长时间卡住怎么办？

本以为`swapoff -a -v` ，轻松搞定，没想到

在执行 `swapoff -a -v`后如果出现 CPU 负载飙升和长时间等待，并且报警使用率达到100%。

分析问题

#### 查找占用 swap 的进程

```bash
smem -s swap -r | head -10 
```

输出示例：
```
PSS      RSS      USS  Swap  COMMAND       
   2.9 G    300 M      5 K   2.9 G nginx     
   6.1 G    800 M    128 K   6.1 G prometheus
```

确定是哪个应用占用了 swap，然后根据业务情况决定是否停止进程。

####  监控执行进度

是卡住了，还是进展缓慢？

通过以下方式观察当前 swap 使用情况：

```bash
watch -n 60 'cat /proc/swaps'
```

每 60 秒刷新一次观察是否有活跃的 swap entries。如果有数据表明仍在进行 writeback，耐心等待即可。



#### 监控在过程中反到 100% 的原因分析

在执行 `swapoff -a -v`期间的监控系统可能会报告异常（指标接近或超过 100%），这是因为：

**原因**: `swap off process`:

- SWAP total value（分母）在不断递减直到变为 `0 bytes`, 也可通过观察这个值的趋势查看关闭的进展.
- 计算出的 `(1-SwapFreeBytes/SwaptotalBys)⋅100`比值趋近极限值。


这个现象只是过程过渡期产生，并不代表系统真正的错误状态——只要看到最终`Swaptotal =0`表示操作顺利完成~！🎉

---