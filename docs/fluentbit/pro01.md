# Fluent Bit 输出到 MinIO 失败 - S3 文件名过长与签名错误

## 问题描述

### 错误现象
Fluent Bit 日志显示输出到 MinIO 时发生多种错误：

```
[2024/08/20 01:49:40] [error] [/root/go/src/fluent-bit/src/flb_http_client.c:1201 errno=32] Broken pipe
[2024/08/20 01:49:41] [error] [/root/go/src/fluent-bit/src/flb_http_client.c:1201 errno=32] Broken pipe
[2024/08/20 01:49:41] [error] [output:s3:s3.0] PutObject request failed
[2024/08/20 02:09:45] [error] [output:s3:s3.0] PutObject request failed
[2024/08/20 02:10:05] [error] [output:s3:s3.0] PutObject API responded with error='SignatureDoesNotMatch', 
message='The request signature we calculated does not match the signature you provided. Check your key and signing method.'
[2024/08/20 02:10:05] [error] [output:s3:s3.0] Raw PutObject response: HTTP/1.1 403 Forbidden
```

**关键特征：**
- `Broken pipe` 错误：网络连接中断
- `PutObject request failed`：对象上传请求失败
- `SignatureDoesNotMatch`：签名不匹配，返回 403 Forbidden
- 问题发生在 Kubernetes 容器日志收集场景下

### 环境信息
- **组件**: Fluent Bit + MinIO (S3 兼容存储)
- **部署方式**: Kubernetes DaemonSet
- **日志源**: 容器日志（Kubernetes Pod 日志）
- **输出目标**: MinIO 对象存储

## 问题分析

### 根本原因
**S3 对象键（Object Key）过长**，导致 MinIO 拒绝请求或生成错误的签名。Kubernetes 容器日志的 `$TAG` 变量包含完整的 Pod 名称、命名空间、容器名等信息，导致生成的文件路径超出限制。

### 验证方法

检查当前 Fluent Bit 配置中的 `s3_key_format`：

```bash
# 查看 Fluent Bit 配置文件
kubectl get configmap fluent-bit-config -n <namespace> -o yaml | grep -A5 s3_key_format

# 查看实际生成的文件名长度
kubectl logs -f <fluentbit-pod-name> -n <namespace> | grep "s3_key_format"
```

### 问题发生机制

1. **Tag 变量内容**: Fluent Bit 的 `$TAG` 在 Kubernetes 环境下包含完整信息：
   ```
   kubernetes.var.log.containers.<pod-name>_<namespace>_<container-name>-<container-id>.log
   ```
   
2. **文件名生成**: 默认配置 `/logs/$TAG/%Y/%m/%d/%H/%M/%S.log` 会生成极长的路径：
   ```
   /logs/kubernetes.var.log.containers.my-pod-abc123_my-namespace_my-container-1234567890abcdef/2024/08/20/01/49/40.log
   ```

3. **MinIO 限制**: 
   - S3 对象键最大长度为 1024 字节
   - 某些版本的 MinIO 对长路径的支持存在问题
   - 签名计算时，过长的 URL 可能导致签名不匹配

### 常见触发场景
- Kubernetes 环境下 Pod 名称较长
- 使用默认 `$TAG` 变量直接作为 S3 路径的一部分
- 多级日期时间格式化进一步增加路径长度
- MinIO 版本与 Fluent Bit S3 插件版本不兼容

## 解决方案

### 方案一：缩短 S3 Key 格式（推荐）

**适用场景**: Pod 名称较长，需要快速解决问题

修改 Fluent Bit 配置，使用 `$TAG` 的部分内容或自定义格式：

```yaml
[OUTPUT]
    Name            s3
    Match           *
    bucket          my-bucket
    region          us-east-1
    endpoint        http://minio-service:9000
    tls             Off
    # 使用 $TAG[4] 只取 Tag 的第 5 部分（通常是 Pod 名）
    s3_key_format   /logs/$TAG[4]/%Y/%m/%d/%H/%M/%S.log
    total_file_size 100M
    upload_timeout  10m
```

**修改说明：**
- `$TAG[4]`: 取 Tag 的第 5 个部分（按 `.` 分割）
- 例如 `kubernetes.var.log.containers.my-pod.default.my-container` → 取 `my-pod`
- 大幅减少路径长度，避免超出限制

### 方案二：使用静态路径 + 动态文件名

**适用场景**: 需要保留日期分层结构

```yaml
[OUTPUT]
    Name            s3
    Match           *
    bucket          my-bucket
    region          us-east-1
    endpoint        http://minio-service:9000
    tls             Off
    # 使用日期作为路径，使用短 UUID 作为文件名
    s3_key_format   /logs/%Y/%m/%d/$UUID.log
    total_file_size 100M
    upload_timeout  10m
```

**替代方案 - 使用记录中的字段：**

```yaml
[FILTER]
    Name    modify
    Match   *
    Add     short_tag ${TAG[4]}

[OUTPUT]
    Name            s3
    Match           *
    bucket          my-bucket
    s3_key_format   /logs/$short_tag/%Y/%m/%d/%H.log
```

### 方案三：关闭 Multipart Upload

**适用场景**: 遇到 `CreateMultipartUpload` 相关错误

如果错误日志中出现：
```
[error] [output:s3:s3.2] CreateMultipartUpload: Could not parse response
[error] [output:s3:s3.2] Could not initiate multipart upload
```

在配置中添加：

```yaml
[OUTPUT]
    Name            s3
    Match           *
    bucket          my-bucket
    region          us-east-1
    endpoint        http://minio-service:9000
    tls             Off
    # 关闭分片上传，使用单文件上传
    use_put_object  On
    s3_key_format   /logs/$TAG[4]/%Y/%m/%d/%H/%M/%S.log
    total_file_size 50M
```

**说明：**
- `use_put_object On`: 使用简单的 PUT 对象 API，而非分片上传
- 适合小文件场景，减少并发 worker 数量
- 单文件大小建议控制在 100MB 以内

### 方案四：优化 Fluent Bit 配置完整示例

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: logging
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         1
        Log_Level     info
        Daemon        off
        Parsers_File  parsers.conf
        HTTP_Server   On
        HTTP_Listen   0.0.0.0
        HTTP_Port     2020

    [INPUT]
        Name              tail
        Tag               kube.*
        Path              /var/log/containers/*.log
        Parser            docker
        DB                /var/log/flb_kube.db
        Mem_Buf_Limit     50MB
        Skip_Long_Lines   On
        Refresh_Interval  10

    [FILTER]
        Name                kubernetes
        Match               kube.*
        Kube_URL            https://kubernetes.default.svc:443
        Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
        Merge_Log           On
        Keep_Log            Off
        K8S-Logging.Parser  On
        K8S-Logging.Exclude On

    # 提取短标签用于 S3 路径
    [FILTER]
        Name    modify
        Match   kube.*
        Add     pod_name ${kubernetes['pod_name']}
        Add     namespace ${kubernetes['namespace_name']}

    [OUTPUT]
        Name              s3
        Match             kube.*
        bucket            fluentbit-logs
        region            us-east-1
        endpoint          http://minio.logging.svc.cluster.local:9000
        tls               Off
        # 使用 pod_name 和 namespace 构建短路径
        s3_key_format     /logs/$namespace/$pod_name/%Y/%m/%d/%H.log
        use_put_object    On
        total_file_size   100M
        upload_timeout    10m
        store_dir         /tmp/fluent-bit/s3
```

## 验证与监控

### 验证配置是否正确

```bash
# 1. 检查 Fluent Bit 配置语法
kubectl exec -it <fluentbit-pod> -- fluent-bit --dry-run -c /fluent-bit/etc/fluent-bit.conf

# 2. 查看 Fluent Bit 日志
kubectl logs -f <fluentbit-pod> -n logging | grep -i "s3\|error"

# 3. 验证 MinIO 中是否有新文件生成
kubectl run minio-client --rm -it --image=minio/mc -- \
  mc alias set myminio http://minio.logging.svc.cluster.local:9000 <access-key> <secret-key> && \
  mc ls myminio/fluentbit-logs/logs/ --recursive
```

### 监控指标

在 Prometheus 中添加 Fluent Bit 监控：

```yaml
apiVersion: v1
kind: ServiceMonitor
metadata:
  name: fluent-bit
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: fluent-bit
  endpoints:
  - port: metrics
    path: /api/v1/metrics/prometheus
```

**关键指标告警规则：**

```yaml
groups:
  - name: fluentbit-alerts
    rules:
      - alert: FluentBitHighErrorRate
        expr: rate(fluentbit_output_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Fluent Bit 错误率过高"
          description: "Fluent Bit {{ $labels.name }} 错误率超过 0.1/s"

      - alert: FluentBitS3UploadFailures
        expr: increase(fluentbit_output_s3_failed_uploads_total[1h]) > 10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Fluent Bit S3 上传失败次数过多"
          description: "过去 1 小时内 S3 上传失败 {{ $value }} 次"

      - alert: FluentBitBufferOverflow
        expr: fluentbit_input_bytes_total > 1000000000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Fluent Bit 缓冲区可能溢出"
          description: "输入数据量过大，可能导致数据丢失"
```

### 检查 S3 上传状态

```bash
# 查看 Fluent Bit 内部指标
curl -s http://<fluentbit-pod-ip>:2020/api/v1/metrics | jq '.outputs'

# 查看输出插件状态
curl -s http://<fluentbit-pod-ip>:2020/api/v1/metrics/prometheus | grep fluentbit_output
```

## 预防措施

### 1. 配置规范
- **限制 Tag 长度**: 使用 `$TAG[N]` 语法提取必要部分
- **路径层级控制**: 避免过深的目录层级（建议不超过 5 层）
- **文件名规范化**: 使用简短的日期格式，避免包含完整容器 ID

### 2. 监控告警
- 监控 S3 上传失败次数
- 监控 Fluent Bit 错误日志
- 设置 MinIO 存储桶大小告警

### 3. 配置模板建议

```yaml
# 推荐的 S3 Key 格式模板
# 模板 1: 按 Pod + 日期
s3_key_format   /logs/$namespace/$pod_name/%Y/%m/%d/%H.log

# 模板 2: 按服务 + 日期（需先提取服务名）
s3_key_format   /logs/$service/%Y/%m/%d/%H.log

# 模板 3: 纯日期分层
s3_key_format   /logs/%Y/%m/%d/%H/$UUID.log
```

### 4. 测试验证
部署前在测试环境验证：

```bash
# 测试 S3 连接
kubectl run --rm -it s3-test --image=amazon/aws-cli -- \
  aws s3 ls s3://my-bucket/logs/ --endpoint-url=http://minio:9000

# 测试文件上传
kubectl run --rm -it s3-test --image=amazon/aws-cli -- \
  aws s3 cp /etc/hosts s3://my-bucket/logs/test/pod-name/2024/08/20/01.log \
  --endpoint-url=http://minio:9000
```

## 故障排查流程

1. **确认现象**: 检查 Fluent Bit 日志，确认 `SignatureDoesNotMatch` 或 `Broken pipe` 错误
2. **检查配置**: 查看 `s3_key_format` 配置，确认是否使用了完整的 `$TAG`
3. **验证路径长度**: 计算实际生成的 S3 Key 长度是否超过 1024 字节
4. **测试连接**: 验证 MinIO 服务可访问，凭据正确
5. **修改配置**: 使用 `$TAG[N]` 缩短路径，或关闭 `use_put_object`
6. **应用配置**: 更新 ConfigMap，重启 Fluent Bit Pod
7. **验证修复**: 检查新日志是否正常上传到 MinIO

## 总结

Fluent Bit 输出到 MinIO 失败，主要问题是 **S3 对象键过长** 导致的签名错误或连接中断。解决方案包括：

1. **缩短 S3 Key**: 使用 `$TAG[4]` 等语法提取 Tag 的部分内容
2. **优化路径结构**: 使用 Pod 名、Namespace 等短字段构建路径
3. **关闭分片上传**: 设置 `use_put_object On` 避免 MultipartUpload 问题
4. **监控告警**: 建立 S3 上传失败的监控体系

建议在 Kubernetes 环境下，始终使用缩短后的标签变量，避免因 Pod 名称过长导致的各种 S3 存储问题。
