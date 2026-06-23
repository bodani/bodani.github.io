# patroni 故障恢复

## 背景

Patroni 集群基于 StatefulSet 部署，并配置为顺序启动 (`podManagementPolicy: OrderedReady`)。当集群出现故障重启时，如果节点 (pod-0) 由于磁盘问题或其他原因无法正常启动，后续 pod(如 pod-1, pod-2 等) 将始终处于 Pending 等待状态，导致整个集群无法启动。

在这种场景下，我们需要通过救援手段利用其他健康副本中的数据进行恢复，使整个集群恢复正常运作。

### 问题描述

- **严格启动顺序**: Patroni 配置 `Pod Management Policy: OrderedReady`，确保前面的 Pod 正常运行后，后面的 Pod 才会启动
- **法定数量限制**: 如果集群可用成员不足半数（Quorum），将无法完成 Leader 选举
- **STS 自动调度的局限**: 直接 `delete pod` 可能导致 STS 尝试重建原序号 pod，若数据盘已损坏则可能陷入循环故障

## 解决方案

救援的核心方案是通过一个健康的副本来初始化集群。流程如下：

1. **检查 PVC 是否存在** - 确认该节点有存储可恢复的数据
2. **生成临时 Pod** - 根据 StatefulSet 模板动态构造一个新的 Pod 用于救援
3. **运行集群服务** - 临时 Pod 内启动 Patroni 服务与其他 node 建立连接并从 healthy replica 恢复
4. **恢复正常 STS** - 待服务恢复后，删除救援 Pod，原有 STS 继续按计划调度

> ⚠️ 注意：由于是独立于 STS 之外的临时 Pod，建议指定 pod 副本序号为某个已经确认为数据正常的节点（通常是 pod-1）进行启动来作为初始入口。避免直接使用主节点的 ordinal(往往是 0)。

## 工具说明

项目中提供配套脚本 [patroni-rescue.py](./patroni-rescue.py)

```bash
#!/usr/bin/env python3
# patroni-rescue.py - 完全动态生成 Patroni 救援 Pod
# 用法：python3 patroni-rescue.py <namespace> <sts-name> <pod-ordinal>
# 示例：python3 patroni-rescue.py zhangjint helmbroker-pg1803 1
```

该脚本执行以下步骤：

1. **验证 PVC 存在性**：确保救援 Pod 所需的数据盘已就绪并可挂载
2. **获取 sts 配置信息**：从 k8s cluster 里拉取下需要复制的全部字段，包括 image、port mapping、env variables 等关键设定
3. **过滤精简配置**：清除一些不必要的标签和环境变量 (如 helm chart metadata/credentials)
4. **自动生成 YAML 文件**输出到 `/tmp/{rescue-pod}-rescue.yaml`

### 脚本特性

| 过滤器 | 功能说明 |
|--------|----------|
| Label 过滤 | 移除 `app.kubernetes.io/managed-by`, `helm.sh/chart` 等非必要标签 |
| Env 处理 | PATRONI_NAME 硬编码为当前救援 Pod 名称；自动设置 Pod IP 相关的 PATRONI_*_CONNECT_ADDRESS |
| 资源隔离 | 清除 hugepages-*类型资源请求以防止因节点资源受限导致的调度失败 |
| Volume 管理 | dynamic PVC mount + configMap volume without defaultMode set |
| Affinity 兼容 | 保留原 sts 定义的 nodeAffinity/affinity 规则，使 Pod 调度行为与原有集群一致 |

## 使用方法

### 基本语法

```bash
python3 patroni-rescue.py <namespace> <sts-name> <pod-ordinal>
```

参数说明:


| 参数 | 说明 | 示例 |
|------|------|------|
| `<namespace>` | Kubernetes 命名空间 | `default` / `db-production` |
| `<sts-name>` | StatefulSet 资源名 | `postgres-cluster-helmbroker-pg1803` / `replica-0-7d9d9f74b2-xvxxx` |
| `<pod-ordinal>` | **用作救援基准源**的节点序列号（需该节点数据完整且可以接入网络） | `0`, `1`, `2` 等数字 |


### 操作实例

假设我们的 Patroni PostgreSQL 集群有以下状态

- Namespace: `zhangjint`
- StatefulSet 名称：`helmbroker-pg1803`
- Pod-0 异常宕机且 disk error


```bash
# Step 1: 生成救援 Pod (选择 pod-1 为数据源)
python3 patroni-rescue.py zhangjint helmbroker-pg1803 1
```

#### 输出示例
```
=== Patroni 救援脚本 ===
命名空间：zhangjint
StatefulSet: helmbroker-pg1803
救援 Pod: helmbroker-pg1803-1

检查 PVC storage-volume-helmbroker-pg1803-1...
✓ PVC 存在

获取 StatefulSet 配置...
✓ 获取成功

生成救援 Pod YAML（精简版）...
✓ 救援 Pod YAML 已生成：/tmp/helmbroker-pg1803-1-rescue.yaml

=== 使用步骤 ===
1. 应用救援 Pod:
   kubectl apply -f /tmp/helmbroker-pg1803-1-rescue.yaml

2. 等待 Pod 启动:
   kubectl -n zhangjint get pod helmbroker-pg1803-1 -w
```

待pod1 启动后进入容器利用patroni 进行pod0 节点的恢复