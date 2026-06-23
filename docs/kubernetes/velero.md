# Velero 备份与恢复

- 使用 **Velero** 备份 Kubernetes 资源
- 使用 **MinIO（S3 兼容）** 作为备份仓库
- 使用 **Rook-Ceph RBD（`rook-ceph-block`）** 作为持久卷，并通过 **CSI VolumeSnapshot** 备份卷数据
- 使用 **FSB** 将卷内文件拷贝到 MinIO
---

## 架构说明

参考：[Velero 安装](https://velero.io/docs/v1.18/velero-install/) · [支持的 Provider](https://velero.io/docs/v1.18/supported-providers/) · [CSI 支持](https://velero.io/docs/v1.18/csi/) · [Rook CSI 快照](https://rook.github.io/docs/rook/latest/Storage-Configuration/Ceph-CSI/ceph-csi-snapshot/)

```text
┌─────────────────────────────────────────────────────────────┐
│ Kubernetes 集群                                              │
│  应用/PVC (rook-ceph-block)                                  │
│       ↓ CSI 快照 (RBD)                                       │
│  Velero Server + node-agent (可选 FSB)                       │
└──────────────────────────┬──────────────────────────────────┘
                           │ 备份元数据 +（可选）文件级卷数据
                           ▼
              MinIO / Ceph RGW（S3 兼容，AWS 插件）
              bucket: velero
```

| 组件 | 作用 |
|------|------|
| **BackupStorageLocation** | 存放备份包（K8s 资源 YAML、备份元数据等） |
| **CSI VolumeSnapshot** | 在 Ceph 中创建 RBD 快照；Velero 保存快照句柄（handle） |
| **node-agent + FSB** | 可选；将卷内文件拷贝到 MinIO，不依赖 Ceph 快照是否保留 |

> **说明**：`supported-providers` 页中的 **Volume Snapshotter** 主要指 AWS EBS / Azure Disk 等云盘插件。**Rook-Ceph 不在该表中**，应使用本文的 **CSI + EnableCSI** 路径。

---

## 前置条件

| 项 | 要求 |
|----|------|
| Kubernetes | ≥ 1.20（实践环境 v1.35+k3s） |
| Velero CLI | 与集群内 Server 版本一致（建议 v1.18.x） |
| MinIO | 已创建 bucket `velero`，账号具备读写权限 |
| Rook-Ceph | StorageClass `rook-ceph-block`，provisioner `rook-ceph.rbd.csi.ceph.com` |
| 快照能力 | 已安装 Snapshot CRD + snapshot-controller |

```bash
kubectl get sc | grep rook-ceph-block
kubectl get nodes
velero version --client-only
```

若执行 `velero version` 报错

```
An error occurred: error finding Kubernetes API server config in --kubeconfig, $KUBECONFIG, or in-cluster configuration: invalid configuration: no configuration has been provided, try setting KUBERNETES_MASTER environment variable
```

需设置环境变量

```bash
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
```

---

## 安装 Volume Snapshot CRD 与 Controller

若执行 `kubectl get volumesnapshotclass` 报错 **「doesn't have a resource type volumesnapshotclass」**，需先安装快照 API：

```bash
SNAPSHOTTER_VER=v8.2.0
BASE=https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/${SNAPSHOTTER_VER}/client/config/crd

kubectl apply -f ${BASE}/snapshot.storage.k8s.io_volumesnapshotclasses.yaml
kubectl apply -f ${BASE}/snapshot.storage.k8s.io_volumesnapshotcontents.yaml
kubectl apply -f ${BASE}/snapshot.storage.k8s.io_volumesnapshots.yaml

CTRL=https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/${SNAPSHOTTER_VER}/deploy/kubernetes/snapshot-controller
kubectl apply -f ${CTRL}/rbac-snapshot-controller.yaml
kubectl apply -f ${CTRL}/setup-snapshot-controller.yaml
```

验证：

```bash
kubectl get crd | grep snapshot.storage.k8s.io
kubectl api-resources | grep volumesnapshot
kubectl get pods -n kube-system | grep snapshot-controller
```

---

## 配置 Rook RBD VolumeSnapshotClass

### pool 与 secret

```bash
ROOK_NS=rook-ceph

# StorageClass 中的 pool 名（必须与下面 YAML 一致）
kubectl get sc rook-ceph-block -o jsonpath='{.parameters.pool}{"\n"}'

# RBD 相关 secret（VolumeSnapshotClass 需引用）
kubectl -n $ROOK_NS get secret | grep rbd
# 常见：rook-csi-rbd-provisioner、rook-csi-rbd-node
```

> **说明**：新版 Rook 可能没有 `app=csi-rbdplugin-provisioner` 的 Deployment，可用 `kubectl -n rook-ceph get pods | grep rbd` 确认 CSI 在运行。

### 创建 VolumeSnapshotClass

保存为 `rbd-snapclass.yaml`，**将 `pool` 改为实际值**：

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: rook-ceph-block-snapclass
  annotations:
    # 可选：设为该 driver 的默认快照类
    snapshot.storage.kubernetes.io/is-default-class: "true"
  labels:  # Velero 用 CSI 备份时会优先选带此标签的类
    velero.io/csi-volumesnapshot-class: "true"
driver: rook-ceph.rbd.csi.ceph.com  # kubectl get sc 中的  PROVISIONER
deletionPolicy: Retain   # 推荐 Retain，避免备份后 Ceph 快照被级联删除
parameters:
  clusterID: rook-ceph # 与 Rook 运行的 namespace 一致
  pool: replicapool  # ← 改成你 SC 里的 pool 名
  csi.storage.k8s.io/snapshotter-secret-name: rook-csi-rbd-provisioner
  csi.storage.k8s.io/snapshotter-secret-namespace: rook-ceph
```

```bash
kubectl apply -f rbd-snapclass.yaml
kubectl get volumesnapshotclass
```

### 手工验证快照（可选）

```bash
# 需已有 PVC demo-pvc
kubectl apply -f - <<'EOF'
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: test-snap
  namespace: demo-app
spec:
  volumeSnapshotClassName: rook-ceph-block-snapclass
  source:
    persistentVolumeClaimName: demo-pvc
EOF

kubectl -n demo-app get volumesnapshot test-snap
kubectl -n demo-app describe volumesnapshot test-snap   # 期望 readyToUse: true
```

---

## 安装 Velero

### MinIO 凭证

创建 `cred-velero`：

```ini
[default]
aws_access_key_id=admin
aws_secret_access_key=admin123
```

### 安装命令

```bash
velero install \
  --namespace velero \
  --features=EnableCSI \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.10.0 \
  --bucket velero \
  --secret-file ./cred-velero \
  --use-node-agent \
  --backup-location-config \
    region=minio,s3ForcePathStyle=true,s3Url=http://10.1.80.61:9000
```
--features  启用 CSI 快照

--use-node-agent 开启 FSB 备份

tips

FSB（File System Backup）的工作流程：

1 Velero 的 node-agent DaemonSet 在每个节点上运行
2 备份时，node-agent 挂载目标 PVC 到临时目录
3 通过 Kopia（Velero 1.14+ 默认）或 Restic 读取文件系统
4 增量压缩后上传到对象存储（你的 MinIO/S3）

> 将 `s3Url`、插件版本按环境修改。插件版本需与 Velero 版本匹配。

### 安装后检查

```bash
kubectl -n velero get pods
velero backup-location get          # PHASE 应为 Available
velero version
velero client config set features=EnableCSI   # 可选，describe 时显示 CSI 详情
```

---

## 标准操作流程

### 部署示例应用

**注意**：Pod 启动命令不要在每次启动时覆盖数据卷，否则恢复后会被误认为「备份失败」。

`demo-workload.yaml`：

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: demo-pvc
  namespace: demo-app
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: rook-ceph-block
---
apiVersion: v1
kind: Pod
metadata:
  name: demo-pod
  namespace: demo-app
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sleep", "infinity"]
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: demo-pvc
```

```bash
kubectl create namespace demo-app
kubectl apply -f demo-workload.yaml
kubectl wait -n demo-app pod/demo-pod --for=condition=Ready --timeout=120s
```

### 写入数据并确认（备份前必做）

```bash
kubectl exec -n demo-app demo-pod -- sh -c 'echo "backup-data-$(date +%s)" > /data/test.txt'
kubectl exec -n demo-app demo-pod -- cat /data/test.txt
```

### 创建备份

** CSI 快照**（卷数据在 Ceph RBD 快照中，MinIO 存 K8s 元数据）：

```bash
velero backup create demo-backup-01 \
  --include-namespaces demo-app \
  --csi-snapshot-timeout=20m \
  --wait

velero backup describe demo-backup-01 --details
```

期望在 `Backup Volumes` → `CSI Snapshots` 中看到 `Result: succeeded` 及 `Storage Snapshot ID`。


### 模拟灾难并恢复

```bash
# 删除命名空间（务必等待完成）
kubectl delete namespace demo-app --wait --timeout=300s

# 若 Pod 长期 Terminating，检查 finalizer 后必要时手动删 PVC
kubectl get pv | grep demo

# 恢复
velero restore create demo-restore-01 \
  --from-backup demo-backup-01 \
  --wait

velero restore describe demo-restore-01
velero restore logs demo-restore-01
```

### 验证恢复

```bash
kubectl wait -n demo-app pod/demo-pod --for=condition=Ready --timeout=120s
kubectl exec -n demo-app demo-pod -- cat /data/test.txt
```

内容与备份前 `cat` 一致即成功。

### 仅验证卷数据（排除 Pod，避免启动覆盖）

```bash
kubectl delete namespace demo-app --wait

velero restore create demo-restore-check \
  --from-backup demo-backup-01 \
  --exclude-resources=pods \
  --wait

kubectl run check-pvc -n demo-app --rm -it --restart=Never \
  --image=busybox:1.36 \
  -- sh -c 'cat /data/test.txt' \
  --overrides='{"spec":{"containers":[{"name":"c","image":"busybox:1.36","command":["cat","/data/test.txt"],"volumeMounts":[{"name":"d","mountPath":"/data"}]}],"volumes":[{"name":"d","persistentVolumeClaim":{"claimName":"demo-pvc"}}]}}'
```

### 混合存储备份

方式 一 
步骤 1：创建 Volume Policy ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mixed-storage-policy
  namespace: velero
  labels:
    velero.io/plugin-config: ""
    velero.io/resource-policy: "v1"
data:
  resourcepolicies: |
    version: v1
    volumePolicies:
      - conditions:
          storageClass:
            - rook-cephfs
            - rook-cephfs-hdd
        action:
          type: fs-backup
      - conditions:
          storageClass:
            - rook-ceph-block
            - rook-ceph-block-hdd
        action:
          type: snapshot
```

备份时引用该策略

```bash
velero backup create mixed-backup \
  --include-namespaces <your-namespace> \
  --resource-policies-configmap mixed-storage-policy \
  --ttl 2160h \  
  --wait
```

方式 二 ：Pod 注解（逐个控制，适合混合场景）

---

## 常见问题与处理

### 没有 `volumesnapshotclass` 资源类型

**现象**：`kubectl get volumesnapshotclass` 报错。  
**处理**：完成本文 **安装 CRD 与 snapshot-controller** 部分。

### `deploy -l app=csi-rbdplugin-provisioner` 为空

**现象**：按旧文档查不到 Deployment。  
**处理**：属正常，新版 Rook label 已变。用 `kubectl -n rook-ceph get pods | grep rbd` 确认 CSI 运行即可。

### 恢复 Completed 但 PVC 数据不对

| 原因 | 说明 | 处理 |
|------|------|------|
| Pod 启动覆盖数据 | `command` 中含 `echo ... > /data/xxx` | 改为 `sleep infinity`，写数据用 `kubectl exec` |
| 备份时卷内无数据 | 备份早于写入或 Pod 未 Ready | 先 `cat` 确认再 `velero backup create` |
| `deletionPolicy: Delete` | 备份后 Ceph RBD 快照可能被删 | 改为 **Retain**，重新备份 |
| 未删净命名空间就恢复 | ConfigMap 已存在等警告 | `kubectl delete ns ... --wait`，必要时删残留 PVC/PV |

**实践结论**：CSI 快照句柄一致、`ProvisioningSucceeded` 时，存储恢复通常已成功；若 `cat` 内容不对，优先查 **Pod 是否覆盖文件**。

### Restore 警告（通常可忽略）

| 警告 | 说明 |
|------|------|
| `ConfigMap:istio-ca-* already exists` | 命名空间未删净或 Istio 自动注入 |
| `ciliumendpoints.cilium.io already exists` | 集群已有 CRD |
| `VolumeGroupSnapshotContent ... no matches` | 未安装卷组快照 CRD，单卷 RBD 可忽略 |

### 命名空间删除卡住

```bash
kubectl get ns demo-app -o yaml | grep finalizers
kubectl -n demo-app get pvc,pod
# 必要时
kubectl -n demo-app delete pvc --all --wait=false
kubectl delete ns demo-app --wait --timeout=300s
```

---

## 备份策略选择

| 方式 | 卷数据存放位置 | 适用场景 |
|------|----------------|----------|
| 仅 CSI 快照 | Ceph RBD 快照 | 同集群/短期恢复；需 **Retain** 保留快照 |
| CSI + `--default-volumes-to-fs-backup` | Ceph 快照 + MinIO 文件 | 需要对象存储中有一份卷数据 |
| CSI Snapshot Data Movement | 快照数据搬到 MinIO | 长期保留、跨集群（需 node-agent） |

---

## 常用命令速查

### 备份

```bash
# 按命名空间
velero backup create <名称> --include-namespaces <ns> --csi-snapshot-timeout=20m --wait

# 按标签
velero backup create <名称> --selector app=myapp --wait

# 排除命名空间
velero backup create <名称> --exclude-namespaces kube-system,velero --wait

# 查看
velero backup get
velero backup describe <名称> --details
velero backup logs <名称>
velero backup delete <名称>
```

### 恢复

```bash
velero restore create <名称> --from-backup <备份名> --wait

# 映射到新命名空间
velero restore create <名称> --from-backup <备份名> \
  --namespace-mappings old-ns:new-ns --wait

# 排除资源类型
velero restore create <名称> --from-backup <备份名> \
  --exclude-resources=pods --wait

velero restore get
velero restore describe <名称>
velero restore logs <名称>
```

### 定时备份

```bash
velero schedule create daily-demo \
  --schedule="0 2 * * *" \
  --include-namespaces demo-app \
  --csi-snapshot-timeout=20m

velero schedule get
velero schedule describe daily-demo
```

### 存储位置与运维

```bash
velero backup-location get
velero snapshot-location get
velero version

kubectl logs -n velero deploy/velero -f --tail=100
kubectl logs -n velero -l name=node-agent --tail=50

# 卸载（不删除 MinIO 中已有备份）
velero uninstall --namespace velero
```

### CSI / Rook 排查

```bash
kubectl get volumesnapshotclass
kubectl -n <ns> get volumesnapshot,pvc,pv
kubectl describe volumesnapshotcontent
kubectl get volumesnapshotcontent -o yaml | grep snapshotHandle

kubectl -n rook-ceph get pods | grep rbd
kubectl -n rook-ceph logs deploy/<rbd-provisioner-deploy> -c csi-snapshotter --tail=50
```

---

## 完整演练清单（可复制）

```bash
# === 准备 ===
kubectl apply -f rbd-snapclass.yaml
velero backup-location get

# === 应用 ===
kubectl create ns demo-app
kubectl apply -f demo-workload.yaml
kubectl wait -n demo-app pod/demo-pod --for=condition=Ready --timeout=120s
kubectl exec -n demo-app demo-pod -- sh -c 'echo "MARK-$(date +%s)" > /data/test.txt'
kubectl exec -n demo-app demo-pod -- cat /data/test.txt

# === 备份 ===
velero backup create demo-backup-$(date +%Y%m%d) \
  --include-namespaces demo-app \
  --csi-snapshot-timeout=20m \
  --wait
velero backup describe demo-backup-$(date +%Y%m%d) --details | grep -A5 "CSI Snapshots"

# === 灾难 ===
kubectl delete namespace demo-app --wait --timeout=300s

# === 恢复 ===
velero restore create demo-restore-$(date +%Y%m%d) \
  --from-backup demo-backup-$(date +%Y%m%d) \
  --wait

# === 验证 ===
kubectl wait -n demo-app pod/demo-pod --for=condition=Ready --timeout=120s
kubectl exec -n demo-app demo-pod -- cat /data/test.txt
```

---

## 保留策略（保留多久）

需区分 **两层保留**，不要混为一谈：

| 层级 | 控制对象 | 说明 |
|------|----------|------|
| **Velero Backup TTL** | MinIO 中的备份包、Backup CR、关联清理 | 默认 **30 天**（720h）；到期由 gc-controller 清理 |
| **VolumeSnapshotClass `deletionPolicy`** | Ceph 中 RBD 快照 | `Retain`：K8s 删 VS 后快照仍留在 Ceph；`Delete`：可能被级联删除 |

参考：[Set a backup to expire](https://velero.io/docs/v1.18/how-velero-works/#set-a-backup-to-expire)

### 设置 Velero 备份保留时间

**单次备份：**

```bash
# 30 天（默认，可省略）
velero backup create my-bk --include-namespaces demo-app --ttl 720h0m0s --wait

# 60 天（约 2 个月）
velero backup create my-bk --include-namespaces demo-app --ttl 1440h0m0s --wait

# 90 天
velero backup create my-bk --include-namespaces demo-app --ttl 2160h0m0s --wait
```

**定时备份（Schedule 上设 TTL，每次生成的备份均按此过期）：**

```bash
velero schedule create daily-demo \
  --schedule="0 2 * * *" \
  --include-namespaces demo-app \
  --csi-snapshot-timeout=20m \
  --ttl 1440h0m0s
```

查看过期时间：

```bash
velero backup describe demo-backup-01 | grep -i expiration
```

### 备份过期时 Velero 会删除什么

过期后（gc 默认约 **每小时** 扫描一次，非实时）会删除：

- 集群中的 **Backup** 资源
- MinIO 中的 **备份文件**
- 与该备份关联的 **卷快照清理**（CSI 走 Velero 清理逻辑）
- 关联的 **Restore** 资源

> **CSI 场景注意**：仅 CSI 快照、未开 FSB 时，卷数据主要在 **Ceph RBD**；MinIO 以元数据与快照句柄为主。若需对象存储中长期保留卷**文件**，应使用 `--default-volumes-to-fs-backup` 或 [CSI Snapshot Data Movement](https://velero.io/docs/v1.18/csi-snapshot-data-movement/)。

### Ceph RBD 快照保留（存储侧）

建议 `VolumeSnapshotClass` 使用 **`deletionPolicy: Retain`**。Velero Backup 过期删除后，Ceph 中仍可能残留 **孤儿 RBD 快照**，需在存储侧定期巡检。

---

## 备份与快照的管理、清理

### Velero 侧（备份对象 + MinIO）

```bash
velero backup get
velero backup describe <名称>
velero schedule get

# 立即删除（触发关联清理）
velero backup delete <名称> --confirm

# 删除失败
kubectl get backup -n velero -l velero.io/gc-failure

velero schedule delete <schedule 名>
```

### 自动过期清理

- 设置了 **TTL** 的备份 → 到期后由 **garbage-collection** 自动删除（默认约 1 小时扫描一次）。
- 服务端可调：`--garbage-collection-frequency`（Velero Deployment 参数）。

### Ceph RBD 快照（Kubernetes + 存储）

```bash
kubectl get volumesnapshot -A
kubectl get volumesnapshotcontent

# Rook toolbox（pool/image 按实际修改）
kubectl -n rook-ceph exec deploy/rook-ceph-tools -- rbd snap ls <pool>/<image>
```

Backup 已删、PVC 已不存在但 Ceph 仍有 snap → **孤儿快照**，需运维脚本或手工清理；Velero 不会无限期管理 Ceph 内所有快照。

### 清理策略建议

| 目标 | 建议 |
|------|------|
| MinIO 备份保留 2 个月 | Schedule + `--ttl 1440h0m0s` |
| 控制 Ceph 空间 | VSC 用 `Retain` + 定期审计 orphan snap |
| 重要业务双份保障 | CSI + `--default-volumes-to-fs-backup` 或 CSI Data Movement |

---

## 备份与恢复粒度

**可以按 Namespace 备份，但不限于此。** Velero 按「资源 + 过滤规则」工作，Namespace 是最常用边界。

| 粒度 | 示例 |
|------|------|
| 整个命名空间 | `--include-namespaces demo-app` |
| 多个命名空间 | `--include-namespaces ns1,ns2` |
| 全集群排除部分 NS | `--exclude-namespaces kube-system,velero,rook-ceph` |
| 按标签 | `--selector app=mysql` |
| 只要某几类资源 | `--include-resources deployments,pvc,secrets` |
| 排除某类资源 | `--exclude-resources=configmaps` |
| 按卷策略 | Volume Policy（按 StorageClass / PVC 标签选 snapshot 或 fs-backup） |

```bash
# 整个 demo-app 命名空间（含 PVC、Pod、Service 等）
velero backup create bk1 --include-namespaces demo-app --wait

# 只备份 Deployment 和 PVC
velero backup create bk2 \
  --include-namespaces demo-app \
  --include-resources deployments,persistentvolumeclaims \
  --wait

# 全集群，排除系统 NS
velero backup create bk-all \
  --exclude-namespaces kube-system,kube-public,velero,rook-ceph \
  --wait
```

恢复默认还原备份中包含的 NS/资源；也可用 `--include-resources` 等做部分恢复。详见 [Resource filtering](https://velero.io/docs/v1.18/resource-filtering/)。

---

## 命名空间迁移与复制

### 同集群：复制 NS `a` → NS `b`（源 NS 保留）

```bash
# 1. 备份源 NS
velero backup create bk-prod \
  --include-namespaces production \
  --csi-snapshot-timeout=20m \
  --wait

# 2. 恢复到新 NS（源 NS 仍在）
velero restore create restore-prod-copy \
  --from-backup bk-prod \
  --namespace-mappings production:production-copy \
  --wait
```

说明：

- 目标 NS 若已有同名资源，可能出现 `already exists` 警告；**空 NS 再 restore** 最干净。
- PVC 从 CSI 快照 **新建卷**（新 PV），不是同一块盘挂两个 NS。
- Pod 启动命令勿覆盖 `/data`。

### 同集群：灾难恢复（删 NS 后原 NS 恢复）

```bash
kubectl delete namespace demo-app --wait --timeout=300s
velero restore create demo-restore-01 --from-backup demo-backup-01 --wait
```

### 跨集群迁移（Cluster A → Cluster B）

参考 [Cluster migration](https://velero.io/docs/v1.18/migration-case/)：

1. 两个集群的 Velero **指向同一 MinIO bucket**（目标集群 BSL 建议 `ReadOnly`）。
2. 在 A 上 `velero backup create`，在 B 上 `velero backup describe` 能看到同一备份。
3. 在 B 上 `velero restore create --from-backup ...`。

**Rook-Ceph 跨集群注意：**

| 方式 | 跨集群卷数据 |
|------|--------------|
| 仅 CSI 快照 | 快照在 **源集群 Ceph**；目标集群另一套 Ceph 通常 **不能** 直接用源 snapshot handle |
| **FSB** 或 **CSI Snapshot Data Movement** | 卷数据在 **MinIO**；目标集群用同名 StorageClass provision **新卷** |

同 Ceph、不同 NS → CSI 通常可行；**不同 K8s 集群 / 不同 Ceph** → 建议 FSB 或 CSI 数据搬运，并保证目标存在 `rook-ceph-block` 等 StorageClass。

目标集群只读 BSL 示例：

```bash
velero backup-location create bsl-migrate \
  --provider aws \
  --bucket velero \
  --config region=minio,s3ForcePathStyle=true,s3Url=http://10.1.80.61:9000 \
  --access-mode=ReadOnly
```

### 迁移 / 复制命令速查

```bash
# 同集群 NS 映射
velero restore create <名> \
  --from-backup <备份名> \
  --namespace-mappings 源 ns:目标 ns \
  --wait

# 跨集群（在目标集群执行）
velero restore create <名> --from-backup <备份名> --wait

# 只恢复部分资源到新 NS
velero restore create <名> \
  --from-backup <备份名> \
  --namespace-mappings old:new \
  --include-resources deployments,configmaps,persistentvolumeclaims \
  --wait
```

### 对照总表

| 需求 | 做法 |
|------|------|
| 保留 1～2 个月 | Backup/Schedule 的 `--ttl`（如 `720h` / `1440h`） |
| 清理备份 | `velero backup delete`；TTL 自动 gc；Ceph snap 另做巡检 |
| 按 NS 备份 | `--include-namespaces`（也支持标签、资源类型、多 NS） |
| NS 复制到另一 NS | `--namespace-mappings 源：目标` |
| 跨集群 | 共享 MinIO + FSB 或 CSI 数据搬运 |

---

## 环境参数备忘

| 参数 | 示例值 |
|------|--------|
| MinIO URL | `http://10.1.80.61:9000` |
| Bucket | `velero` |
| StorageClass | `rook-ceph-block` |
| CSI Driver | `rook-ceph.rbd.csi.ceph.com` |
| Rook 命名空间 | `rook-ceph` |
| Ceph pool | `replicapool`（以 `kubectl get sc` 为准） |
| VolumeSnapshotClass | `rook-ceph-block-snapclass` |
| 默认 Backup TTL | 30 天（720h） |

---

## 相关链接

- [Velero Supported Providers（S3 兼容含 MinIO/Ceph RGW）](https://velero.io/docs/v1.18/supported-providers/)
- [Velero CSI Support](https://velero.io/docs/v1.18/csi/)
- [File System Backup](https://velero.io/docs/v1.18/file-system-backup/)
- [CSI Snapshot Data Movement](https://velero.io/docs/v1.18/csi-snapshot-data-movement/)
- [Cluster migration](https://velero.io/docs/v1.18/migration-case/)
- [How Velero works - backup expire](https://velero.io/docs/v1.18/how-velero-works/#set-a-backup-to-expire)
- [Restore - namespace mappings](https://velero.io/docs/v1.18/restore-reference/)
- [Resource filtering](https://velero.io/docs/v1.18/resource-filtering/)
- [Rook Ceph CSI Snapshot](https://rook.github.io/docs/rook/latest/Storage-Configuration/Ceph-CSI/ceph-csi-snapshot/)

1 可完成k3s 无状态类型的备份恢复功能 到S3 
2 可以支持ceph的快照备份功能,本地快照
2 不依赖快照功能，可以支持FSB。（配置Kopia）直接备份文件系统 到S3. 事务型的数据库（pg，mysql等，需停服停写入。停业务层，自身的后台进程）不能保证完全恢复成功。
3 同一 Namespace 内多种 SC 混合存储备份，可以根据SC类型选择备份方式（快照或FSB）， 以前的实现方式是根据labels 进行筛选. 快照要打在sts，deployment,pvc 上

drycc 支持的一些问题， 
 恢复 serviceinstance 失败
 恢复 servicebindings 失败
 以上恢复顺序有问题
 存储在数据库中的信息？ 
 恢复后的ip 是新生成的。

备份命令
velero backup create demo-backup-01 \
  --include-namespaces demo-app \
  --csi-snapshot-timeout=20m \
  --wait

恢复命令
velero restore create demo-restore-01 \
  --from-backup demo-backup-01 \
  --wait