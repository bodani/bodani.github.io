准备 MinIO 凭证
在工作目录创建 cred-velero（与 supported-providers 中 S3 兼容方式一致）：

[default]
aws_access_key_id=admin
aws_secret_access_key=admin123


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

安装后检查
kubectl -n velero get pods
velero backup-location get
# 期望 PHASE 为 Available
velero version

vim rbd-snapclass.yaml
cat  rbd-snapclass.yaml 
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: rook-ceph-block-snapclass
  annotations:
    # 可选：设为该 driver 的默认快照类
    snapshot.storage.kubernetes.io/is-default-class: "true"
  labels:
    # Velero 用 CSI 备份时会优先选带此标签的类
    velero.io/csi-volumesnapshot-class: "true"
driver: rook-ceph.rbd.csi.ceph.com
deletionPolicy: Delete   # 备份场景也可用 Retain，快照更不易被误删
parameters:
  clusterID: rook-ceph    # 与 Rook 运行的 namespace 一致
  pool: replicapool       # ← 改成你 SC 里的 pool 名
  csi.storage.k8s.io/snapshotter-secret-name: rook-csi-rbd-provisioner
  csi.storage.k8s.io/snapshotter-secret-namespace: rook-ceph


kubectl apply -f rbd-snapclass.yaml
kubectl get volumesnapshotclass
kubectl create ns demo-app 
namespace/demo-app created
root@server-60-11:/opt/velero# kubectl apply -f - <<'EOF'
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: test-snap
  namespace: demo-app
spec:
  volumeSnapshotClassName: ceph-rbd-snapclass
  source:
    persistentVolumeClaimName: demo-pvc
EOF
volumesnapshot.snapshot.storage.k8s.io/test-snap created



六、部署示例应用（带 PVC）
kubectl create namespace demo-app

#cat demo-workload.yaml 
# demo-workload.yaml
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
  storageClassName: rook-ceph-block    # 改成你的 StorageClass
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
      command: ["sh", "-c", "sleep 36000"]
      
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: demo-pvc


kubectl apply -f demo-workload.yaml
kubectl wait -n demo-app pod/demo-pod --for=condition=Ready --timeout=120s
写数据
kubectl exec -n demo-app demo-pod -- /bin/sh -c 'echo "123" > /data/tt.txt'
kubectl exec -n demo-app demo-pod -- /bin/sh -c 'cat  /data/tt.txt'


七、执行备份
velero backup create demo-backup-01 \
  --include-namespaces demo-app \
  --csi-snapshot-timeout=20m \
  --wait

若 CSI 快照不稳定，可加上文件系统备份作为兜底：

velero backup create demo-backup-02 \
  --include-namespaces demo-app \
  --csi-snapshot-timeout=20m \
  --default-volumes-to-fs-backup \
  --wait

# 销毁
kubectl delete ns demo-app --wait
## restore
velero restore create demo-restore-01 \
  --from-backup demo-backup-01 \
  --wait
## verify  
kubectl wait -n demo-app pod/demo-pod --for=condition=Ready --timeout=120s
kubectl exec -n demo-app demo-pod -- /bin/sh -c 'cat  /data/tt.txt'
