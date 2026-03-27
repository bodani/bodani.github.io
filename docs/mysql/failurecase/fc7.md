# MGR 集群脑裂 - NO_QUORUM 状态处理

## 故障描述

当集群中有部分节点出现 UNREACHABLE 状态时，若多数节点（半数或以上）失效，集群进入 `NO_QUORUM` 状态：

```javascript
js> cluster.status()
{
    "clusterName": "mycluster",
    "defaultReplicaSet": {
        "name": "default",
        "primary": "192.168.33.21:3306",
        "status": "NO_QUORUM",
        "statusText": "Cluster has no quorum as visible from '192.168.33.21:3306' and cannot process write transactions.",
        "topology": {
            "192.168.33.21:3306": { "status": "ONLINE" },
            "192.168.33.22:3306": { "status": "UNREACHABLE" },
            "192.168.33.23:3306": { "status": "(MISSING)" }
        }
    }
}
```

此状态下只剩下一个活跃节点只能提供查询，无法写入，执行写入操作会卡住。


## 分析

### 问题原因

集群过半节点失效导致失去法定人数（quorum），组复制协议无法继续进行一致性决策。可能场景包括：
- 网络分割导致节点间通信中断（UNREACHABLE）
- 多个节点同时宕机或未启动 Group Replication（MISSING/OFFLINE）

### MGR 节点状态说明

| 状态 | 说明 |
|------|------|
| **ONLINE** | 节点正常运行 |
| **OFFLINE** | 实例运行但未加入集群 |
| **RECOVERING** | 实例已加入集群，正在同步数据 |
| **ERROR** | 同步数据发生异常 |
| **UNREACHABLE** | 与其他节点通讯中断（可能网络问题或节点崩溃） |
| **MISSING** | 节点已加入集群，但未启动组复制 |

#### MGR 集群全局状态说明

| 集群状态 | 状态说明 |
|----------|----------|
| **OK** | 所有节点处于 ONLINE 状态，且有冗余节点（可以容忍一个以上节点失效） |
| **OK_PARTIAL** | 有节点不可用，但仍有冗余节点可容忍故障 |
| **OK_NO_TOLERANCE** | 有足够的 ONLINE 节点，但已无冗余容量（例如：两节点集群中一节点挂掉，无法容忍进一步故障） |
| **NO_QUORUM** | 有节点处于 ONLINE 状态，但达不到法定人数（quorum），无法执行写入操作，只能读取 |
| **UNKNOWN** | 不是 ONLINE 或 RECOVERING 状态，尝试连接其他实例查看状态 |
| **UNAVAILABLE** | 组内所有节点均为 OFFLINE 状态，但实例正在运行，可能刚重启尚未加入 Cluster |


## 解决方案

### 第一步：强制恢复 Quorum

在活跃的 single-partition 上恢复单节点集群的仲裁权限，使其可以正常读写：

```javascript
// 连接到可用节点
cluster.forceQuorumUsingPartitionOf('root@helmbroker-mysql-base-demo-2:3306')
```

这样可以让剩余存活的独立节点获得仲裁权从而继续正常提供读写服务（请注意数据一致性问题）。

### 第二步：修复后的节点重新加回集群

待异常节点恢复并修复后再次通过 `addInstance` 加回集群：

```javascript
dba.getCluster().addInstance('host:port')
```

恢复期间可通过观察日志确认状态是否正常。注意修改 mysqld-auto.cnf 配置文件中的 `group_replication_start_on_boot = ON` 选项以便下次启动时自动加入 Cluster。