# MGR GTID Diverged 处理

## 故障描述

当执行 `dba.rebootClusterFromCompleteOutage()` 重新引导完全中断的 MGR 集群时，出现 GTID 集不可兼容错误：

```javascript
mysqlsh root@helmbroker-mysql-0:3306
dba.rebootClusterFromCompleteOutage()
ERROR: RuntimeError: The instance 'helmbroker-mysql-2:3306' has an incompatible GTID set with the seed instance 'helmbroker-mysql-0:3306' (GTIDs diverged).
If you wish to proceed, the 'force' option must be explicitly set.
```

在 helmbroker-mysql-0 上无法正常恢复集群。


## 分析

### 问题原因

该错误表示 MGR 集群在灾难期间发生了**数据分叉 **(split brain)——各节点的 GTID 集合不再共享共同的前缀序列，处于不可合并的分歧状态。常见场景包括：

- **网络分区后多个节点继续服务**：quorum 丧失后独立接受写请求导致数据分裂
- **NO_QUORUM 状态下仍写入**：切换到 single-instance 模式处理后又被其他非同一数据源节点加入
- **灾难后的错误操作**：备份恢复顺序错误或误删重要信息

这是严重的脑裂后果，意味着已有永久性数据分叉发生。


### MGR 全局状态对照表

| 集群状态 | 状态说明 |
|----------|----------|
| **OK** | 所有节点 ONLINE，可容忍至少一个以上故障 |
| **OK_PARTIAL** | 有节点不可用，但仍可容忍部分故障 |
| **OK_NO_TOLERANCE** | 节点充足但无冗余（如三节点只剩两节点） |
| **NO_QUORUM** | 无法定人数，只能读取不能写入 |
| **OK_DIVERGED** | 各节点数据已分裂分叉 |
| **UNAVAILABLE** | 所有节点均为 OFFLINE |


### 诊断方法

通过执行以下命令确认是否存在 GTID 分歧：

```sql
-- 在所有集群成员节点执行
SELECT @@GLOBAL.GTID_EXECUTED;
```

若发现各节点的 `Executed_GTID_Set` 完全没有交集且无法追溯到一个共同的祖先序列，则表示已发生数据分叉。


## 解决方案

### 步骤 1：选择最新的种子节点

检查各个节点的 GTID 执行情况，找出其中事务最新的那台机器作为恢复入口点（例如 `helmbroker-mysql-2`）。


### 步骤 2：在新的种子上恢复集群

```bash
# SSH 登录到选定节点
ssh root@helmbroker-mysql-2

# 进入 mysqlsh 并执行恢复流程
mysqlsh --user=root localhost
JavaScript version: 15.x
---------------------------------------------------------

Connecting as user: root
Successfully connected via SSL/TLS

# 执行 cluster recovery - 这次能顺利通过！
dba.rebootFromCompleteOutage()
✔ Cluster successfully rebooted

### 步骤 3：验证集群恢复状态

```javascript
// 验证 cluster 状态
var clus = dba.getCluster();
clus.status();
```

正常情况下应看到大部分节点的 readWriteStatus 为 ONLINE。