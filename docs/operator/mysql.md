# operator 管理mysql集群

## 安装 operator

### helm 安装 operator
```
$> helm repo add mysql-operator https://mysql.github.io/mysql-operator/
$> helm repo update
```

```
$> helm install my-mysql-operator mysql-operator/mysql-operator \
   --namespace mysql-operator --create-namespace
```

```
 kubectl -n mysql-operator set env deployment/mysql-operator   MYSQL_OPERATOR_K8S_CLUSTER_DOMAIN=cluster.local
```

#### 安装operator时设置私有镜像仓库

```
export REGISTRY="..."   # like 192.168.20.199:5000
export REPOSITORY="..." # like "mysql"
export NAMESPACE="mysql-operator"
helm install mysql-operator helm/mysql-operator \
    --namespace $NAMESPACE \
    --create-namespace \
    --set image.registry=$REGISTRY \
    --set image.repository=$REPOSITORY \
    --set envs.imagesDefaultRegistry="$REGISTRY" \
    --set envs.imagesDefaultRepository="$REPOSITORY"

```
#### 安装operator时设置需认证私有镜像仓库
```
export REGISTRY="..."   # like 192.168.20.199:5000
export REPOSITORY="..." # like "mysql"
export NAMESPACE="mysql-operator"
export DOCKER_SECRET_NAME="priv-reg-secret"

kubectl create namespace $NAMESPACE

kubectl -n $NAMESPACE create secret docker-registry $DOCKER_SECRET_NAME \
        --docker-server="https://$REGISTRY/v2/" \
        --docker-username=user --docker-password=pass \
        --docker-email=user@example.com

helm install mysql-operator helm/mysql-operator \
        --namespace $NAMESPACE \
        --set image.registry=$REGISTRY \
        --set image.repository=$REPOSITORY \
        --set image.pullSecrets.enabled=true \
        --set image.pullSecrets.secretName=$DOCKER_SECRET_NAME \
        --set envs.imagesPullPolicy='IfNotPresent' \
        --set envs.imagesDefaultRegistry="$REGISTRY" \
        --set envs.imagesDefaultRepository="$REPOSITORY"
```

### 安装mysql 集群

#### 所有配置变量
```
 helm show values mysql-operator/mysql-innodbcluster
```

#### 安装实例
```
 helm install mysql-80 mysql-operator/mysql-innodbcluster \
  --namespace mysql-80 \
  --values mysql-80-values.yaml \
  --set serverVersion=8.0.40 \
  --wait
```

cat mysql-80-values.yaml 
```
version: "8.0.34"
instances: 3

credentials:
  root:
    user: root
    password: Secret123
    host: "%"

tls:
  useSelfSigned: true

routerInstances: 2

serviceAccountName: mysql-80-sa
imagePullPolicy: IfNotPresent

podSpec:
  resources:
    requests:
      memory: "2Gi"
      cpu: "1000m"
    limits:
      memory: "4Gi"
      cpu: "2000m"

datadirVolumeClaimTemplate:
  storageClassName: topolvm-ssd
  resources:
    requests:
      storage: 5Gi

serverConfig:
  mysqld:
    innodb_buffer_pool_size: "1G"
    max_connections: "500"

backupProfiles: []
```

```
 helm -n mysql-80 uninstall mysql-80 
```

### 账户体系

localroot

helm upgrade ${RELEASE_NAME} mysql-operator/mysql-innodbcluster    -n ${NAMESPACE}     -f /tmp/mysql-80-metrics-upgrade.yaml     --wait     --timeout 15m
