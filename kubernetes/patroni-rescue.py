#!/usr/bin/env python3
# patroni-rescue.py - 完全动态生成 Patroni 救援 Pod
# 用法: python3 patroni-rescue.py <namespace> <sts-name> <pod-ordinal>
# 示例: python3 patroni-rescue.py zhangjint helmbroker-pg1803 1
#
# 生成精简版 YAML

import sys
import subprocess
import yaml

def run_cmd(cmd):
    """执行 shell 命令并返回输出"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"错误执行命令: {cmd}")
        print(f"错误信息: {result.stderr}")
        sys.exit(1)
    return result.stdout

def get_sts_yaml(namespace, sts_name):
    """获取 StatefulSet 的 YAML 配置"""
    cmd = f"kubectl -n {namespace} get sts {sts_name} -o yaml"
    output = run_cmd(cmd)
    return yaml.safe_load(output)

def check_pvc(namespace, pvc_name):
    """检查 PVC 是否存在"""
    cmd = f"kubectl -n {namespace} get pvc {pvc_name} -o name"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0 and pvc_name in result.stdout

def filter_labels(labels):
    """过滤掉救援场景非必需的标签"""
    skip_keys = [
        'app.kubernetes.io/managed-by',
        'app.kubernetes.io/version', 
        'helm.sh/chart'
    ]
    return {k: v for k, v in labels.items() if k not in skip_keys}

def filter_env(env_list, namespace, rescue_pod):
    """处理环境变量：过滤非必需项，修改关键项"""
    new_env = []
    has_connect_address = False
    has_pg_connect_address = False

    # 需要过滤的环境变量
    skip_envs = {'ADMIN_USER', 'ADMIN_PASSWORD'}

    for env in env_list:
        name = env['name']

        # 跳过非必需的环境变量
        if name in skip_envs:
            continue

        # PATRONI_NAME -> 硬编码为救援 Pod 名称
        if name == 'PATRONI_NAME':
            new_env.append({'name': name, 'value': rescue_pod})
            continue

        # PATRONI_RESTAPI_CONNECT_ADDRESS -> 从 Pod IP 动态获取
        if name == 'PATRONI_RESTAPI_CONNECT_ADDRESS':
            has_connect_address = True
            new_env.append({
                'name': name,
                'valueFrom': {
                    'fieldRef': {
                        'apiVersion': 'v1',
                        'fieldPath': 'status.podIP'
                    }
                }
            })
            continue

        # PATRONI_POSTGRESQL_CONNECT_ADDRESS -> 从 Pod IP 动态获取
        if name == 'PATRONI_POSTGRESQL_CONNECT_ADDRESS':
            has_pg_connect_address = True
            new_env.append({
                'name': name,
                'valueFrom': {
                    'fieldRef': {
                        'apiVersion': 'v1',
                        'fieldPath': 'status.podIP'
                    }
                }
            })
            continue

        # PATRONI_KUBERNETES_NAMESPACE: valueFrom -> 硬编码 value
        if name == 'PATRONI_KUBERNETES_NAMESPACE':
            new_env.append({'name': name, 'value': namespace})
            continue

        # 其他环境变量保持原样
        new_env.append(env)

    # 如果原始没有 CONNECT_ADDRESS，在末尾添加
    if not has_connect_address:
        new_env.append({
            'name': 'PATRONI_RESTAPI_CONNECT_ADDRESS',
            'valueFrom': {
                'fieldRef': {
                    'apiVersion': 'v1',
                    'fieldPath': 'status.podIP'
                }
            }
        })

    if not has_pg_connect_address:
        new_env.append({
            'name': 'PATRONI_POSTGRESQL_CONNECT_ADDRESS',
            'valueFrom': {
                'fieldRef': {
                    'apiVersion': 'v1',
                    'fieldPath': 'status.podIP'
                }
            }
        })

    return new_env

def filter_resources(resources):
    """过滤掉 hugepages 等可能引发节点兼容性问题的资源限制"""
    if not resources:
        return resources

    filtered = {}
    for key, value in resources.items():
        if key == 'limits':
            filtered_limits = {k: v for k, v in value.items() if not k.startswith('hugepages-')}
            if filtered_limits:
                filtered['limits'] = filtered_limits
        elif key == 'requests':
            filtered['requests'] = value

    return filtered if filtered else None

def filter_volumes(volumes):
    """过滤掉 ConfigMap 的 defaultMode（默认420，不需要显式设置）"""
    new_volumes = []
    for vol in volumes:
        new_vol = {}
        # name 放前面
        if 'name' in vol:
            new_vol['name'] = vol['name']

        # 处理 persistentVolumeClaim
        if 'persistentVolumeClaim' in vol:
            new_vol['persistentVolumeClaim'] = vol['persistentVolumeClaim']

        # 处理 configMap，去掉 defaultMode
        if 'configMap' in vol:
            cm = dict(vol['configMap'])
            cm.pop('defaultMode', None)
            if cm:
                new_vol['configMap'] = cm

        # 处理 emptyDir
        if 'emptyDir' in vol:
            new_vol['emptyDir'] = vol['emptyDir']

        new_volumes.append(new_vol)

    return new_volumes

def process_volumes(sts, volumes, rescue_pod):
    """处理 volumes，包含 volumeClaimTemplates 的 PVC"""
    new_volumes = []

    # 首先处理 volumeClaimTemplates（如果有），生成具体的 PVC 挂载
    claim_templates = sts.get('spec', {}).get('volumeClaimTemplates', [])
    for claim in claim_templates:
        claim_name = claim.get('metadata', {}).get('name', 'storage-volume')
        pvc_name = f"{claim_name}-{rescue_pod}"
        new_volumes.append({
            'name': claim_name,
            'persistentVolumeClaim': {
                'claimName': pvc_name
            }
        })

    # 然后处理其他 volumes（ConfigMap, emptyDir 等）
    for vol in volumes:
        new_vol = {}
        if 'name' in vol:
            new_vol['name'] = vol['name']

        if 'persistentVolumeClaim' in vol:
            new_vol['persistentVolumeClaim'] = vol['persistentVolumeClaim']

        if 'configMap' in vol:
            cm = dict(vol['configMap'])
            cm.pop('defaultMode', None)
            if cm:
                new_vol['configMap'] = cm

        if 'emptyDir' in vol:
            new_vol['emptyDir'] = vol['emptyDir']

        new_volumes.append(new_vol)

    return new_volumes

def generate_rescue_pod(sts, namespace, sts_name, ordinal):
    """生成救援 Pod 配置"""
    rescue_pod = f"{sts_name}-{ordinal}"

    template = sts['spec']['template']
    spec = template['spec']

    # 找到 postgresql 容器
    pg_container = None
    for c in spec['containers']:
        if c['name'] == 'postgresql':
            pg_container = c
            break

    if not pg_container:
        print("错误: 找不到 postgresql 容器")
        sys.exit(1)

    # 构建救援 Pod - 过滤非必需标签
    labels = filter_labels(template.get('metadata', {}).get('labels', {}))

    rescue_pod_config = {
        'apiVersion': 'v1',
        'kind': 'Pod',
        'metadata': {
            'name': rescue_pod,
            'namespace': namespace,
            'labels': labels
        },
        'spec': {
            'hostname': rescue_pod,
            'subdomain': sts['spec'].get('serviceName', sts_name),
            'serviceAccountName': spec.get('serviceAccountName', 'default'),
        }
    }

    # 添加 affinity（如果有）
    if 'affinity' in spec:
        rescue_pod_config['spec']['affinity'] = spec['affinity']

    # 构建容器配置
    new_container = {
        'name': 'postgresql',
        'image': pg_container['image'],
        'imagePullPolicy': 'IfNotPresent',
        'env': filter_env(pg_container.get('env', []), namespace, rescue_pod),
        'ports': [
            {'containerPort': 8008, 'protocol': 'TCP'},
            {'containerPort': 5432, 'protocol': 'TCP'}
        ],
        'volumeMounts': pg_container.get('volumeMounts', []),
    }

    # 添加 resources（过滤 hugepages）
    if 'resources' in pg_container:
        filtered_res = filter_resources(pg_container['resources'])
        if filtered_res:
            new_container['resources'] = filtered_res

    rescue_pod_config['spec']['containers'] = [new_container]

    # 处理 volumes（包含 volumeClaimTemplates，过滤 defaultMode）
    template_volumes = spec.get('volumes', [])
    rescue_pod_config['spec']['volumes'] = process_volumes(sts, template_volumes, rescue_pod)

    # 设置 restartPolicy
    rescue_pod_config['spec']['restartPolicy'] = 'Never'

    return rescue_pod_config

def main():
    if len(sys.argv) != 4:
        print("用法: python3 patroni-rescue.py <namespace> <sts-name> <pod-ordinal>")
        print("示例: python3 patroni-rescue.py zhangjint helmbroker-pg1803 1")
        sys.exit(1)

    namespace = sys.argv[1]
    sts_name = sys.argv[2]
    ordinal = sys.argv[3]

    rescue_pod = f"{sts_name}-{ordinal}"
    output_file = f"/tmp/{rescue_pod}-rescue.yaml"

    print(f"=== Patroni 救援脚本 ===")
    print(f"命名空间: {namespace}")
    print(f"StatefulSet: {sts_name}")
    print(f"救援 Pod: {rescue_pod}")
    print()

    # 检查 PVC
    pvc_name = f"storage-volume-{rescue_pod}"
    print(f"检查 PVC {pvc_name}...")
    if not check_pvc(namespace, pvc_name):
        print(f"错误: PVC {pvc_name} 不存在!")
        print("可用的 PVC:")
        run_cmd(f"kubectl -n {namespace} get pvc | grep {sts_name} || true")
        print()
        print("如果 PVC 不存在，说明该 Pod 从未被创建过，没有数据可恢复。")
        sys.exit(1)
    print("✓ PVC 存在")
    print()

    # 获取 StatefulSet 配置
    print("获取 StatefulSet 配置...")
    sts = get_sts_yaml(namespace, sts_name)
    print("✓ 获取成功")
    print()

    # 生成救援 Pod
    print("生成救援 Pod YAML（精简版）...")
    rescue_config = generate_rescue_pod(sts, namespace, sts_name, ordinal)

    # 写入文件 - 使用标准 YAML 格式
    with open(output_file, 'w') as f:
        yaml.dump(rescue_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"✓ 救援 Pod YAML 已生成: {output_file}")
    print()

    # 输出使用步骤
    print("=== 使用步骤 ===")
    print(f"1. 应用救援 Pod:")
    print(f"   kubectl apply -f {output_file}")
    print()
    print(f"2. 等待 Pod 启动:")
    print(f"   kubectl -n {namespace} get pod {rescue_pod} -w")
    print()

if __name__ == '__main__':
    main()