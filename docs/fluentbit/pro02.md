# Fluent Bit 上传 OpenSearch 数据失败 - Shard 数量超限

## 问题描述

### 错误现象
Fluent Bit 日志显示多次尝试刷新数据到 OpenSearch 后失败，关键错误信息如下：

```
[2026/04/02 03:18:40] [ info] [input:tail:tail.0] inotify_fs_add(): inode=11276232 watch_fd=12 name=/var/log/containers/helmbroker-fluentbit-agent-9qpln_pre-geni3_fluentbit-b9e2a67b7a060c3dbda679518b987d8ff948382cc3c98a023a3c45c5606d83de.log
[2026/04/02 03:20:00] [ warn] [engine] failed to flush chunk '15-1775100000.2143131.flb', retry in 8 seconds: task_id=0, input=tail.0 > output=opensearch.1 (out_id=1)
[2026/04/02 03:20:01] [ warn] [engine] failed to flush chunk '15-1775100000.945834363.flb', retry in 11 seconds: task_id=1, input=tail.0 > output=opensearch.1 (out_id=1)
[2026/04/02 03:20:08] [error] [engine] chunk '15-1775100000.2143131.flb' cannot be retried: task_id=0, input=tail.0 > output=opensearch.1
[2026/04/02 03:20:12] [error] [engine] chunk '15-1775100000.945834363.flb' cannot be retried: task_id=1, input=tail.0 > output=opensearch.1
```

**关键特征：**
- 日志中出现 `failed to flush chunk` 警告，表示数据刷新失败
- 随后出现 `cannot be retried` 错误，表示重试次数耗尽，数据将丢失
- 问题持续发生，影响所有新的日志数据写入

### 环境信息
- **组件**: Fluent Bit + OpenSearch
- **部署方式**: Kubernetes DaemonSet
- **日志源**: 容器日志（`/var/log/containers/`）
- **输出目标**: OpenSearch 集群

## 问题分析

### 根本原因
OpenSearch 集群达到了默认的 **最大 Shard 数量限制（3000个）**，导致无法为新索引创建新的 Shard，Fluent Bit 的数据写入请求被拒绝。

### 验证方法

进入 Fluent Bit Pod 手动模拟数据上传，验证问题根因：

```bash
# 进入 Fluent Bit 容器
kubectl exec -it <fluentbit-pod-name> -n <namespace> -- /bin/sh

# 构造测试数据
cat > /tmp/test_bulk.json << 'EOF'
{ "index" : { "_index" : "test-index-2026-04-02", "_id" : "test-debug-001" } }
{ "@timestamp" : "2026-04-02T03:20:00.000Z", "message" : "test log message", "tag" : "kubernetes.test", "log" : "2026-04-02 03:20:00 [INFO] test" }
EOF

# 执行写入测试（使用实际的 OpenSearch 地址和凭据）
curl -k -u <username>:<password> \
  -X POST \
  -H "Content-Type: application/x-ndjson" \
  https://<opensearch-host>:9200/_bulk \
  --data-binary @/tmp/test_bulk.json
```

### 错误响应分析

OpenSearch 返回的错误信息：

```json
{
  "took": 6,
  "errors": true,
  "items": [{
    "index": {
      "_index": "test-index-2026-04-02",
      "_id": "test-debug-001",
      "status": 400,
      "error": {
        "type": "validation_exception",
        "reason": "Validation Failed: 1: this action would add [2] total shards, but this cluster currently has [2999]/[3000] maximum shards open;"
      }
    }
  }]
}
```

**错误解读：**
- `status`: 400 - 请求被拒绝
- `type`: validation_exception - 验证失败
- `reason`: 当前集群已有 2999 个 shard，达到 3000 上限，无法创建新 shard

### Shard 超限的发生机制

1. **索引自动创建**: Fluent Bit 按天（或按小时）自动创建新索引（如 `logs-2026.04.02`）
2. **Shard 分配**: 每个新索引默认分配 1 个主分片 + 1 个副本分片 = 2 个 shard
3. **累积增长**: 随着时间推移，索引数量不断增加，shard 总数持续增长
4. **达到上限**: 当 shard 数量达到 `cluster.max_shards_per_node × 节点数` 时，新索引创建被拒绝

### 常见触发场景
- 日志量增长，索引数量增加
- 索引生命周期管理（ILM）策略配置不当，旧索引未及时清理
- 索引分片数设置过大（如默认 5 主分片 + 1 副本 = 10 shard/索引）
- 长时间未清理历史日志索引

## 解决方案

### 方案一：清理过期索引（快速恢复）

**适用场景**: 需要快速恢复服务，释放 shard 资源

```bash
# 查看现有索引及其 shard 占用情况
curl -k -u <username>:<password> \
  "https://<opensearch-host>:9200/_cat/indices?v&h=index,docs.count,store.size,pri,rep,health"

# 删除 30 天前的旧索引（按日期命名格式）
# 示例：删除 2026.03.01 之前的索引
curl -k -u <username>:<password> \
  -X DELETE \
  "https://<opensearch-host>:9200/logstash-2026.03.*"

# 或者删除特定日期之前的所有匹配索引
for date in $(seq -w 1 31); do
  curl -k -u <username>:<password> \
    -X DELETE \
    "https://<opensearch-host>:9200/logs-2026.03.${date}"
done
```

**注意事项：**
- 删除前确认索引数据已不再需要，或已有备份
- 建议先关闭索引（`/_close`）而非直接删除，以便需要时可恢复
- 生产环境建议配置索引生命周期管理（ILM）自动清理

### 方案二：调整 OpenSearch Shard 限制（扩容）

**适用场景**: 业务增长需要更多索引，需要长期解决方案

```bash
# 调整每节点最大 shard 数量（持久化配置）
curl -k -u <username>:<password> \
  -X PUT \
  "https://<opensearch-host>:9200/_cluster/settings" \
  -H "Content-Type: application/json" \
  -d '{
    "persistent": {
      "cluster.max_shards_per_node": 2000
    }
  }'

# 临时调整（集群重启后失效）
curl -k -u <username>:<password> \
  -X PUT \
  "https://<opensearch-host>:9200/_cluster/settings" \
  -H "Content-Type: application/json" \
  -d '{
    "transient": {
      "cluster.max_shards_per_node": 2000
    }
  }'
```

**配置建议：**
- 默认值为 1000，可根据集群规模和内存大小适当调整
- 建议计算方式：`总内存(GB) × 20 ~ 30` 作为参考上限
- 过多 shard 会增加集群管理开销，影响性能

### 方案三：优化索引模板（减少 Shard 数量）

**适用场景**: 新索引 shard 数量过多，需要优化配置

```bash
# 查看当前索引模板
curl -k -u <username>:<password> \
  "https://<opensearch-host>:9200/_template"

# 创建或更新索引模板，减少 shard 数量
curl -k -u <username>:<password> \
  -X PUT \
  "https://<opensearch-host>:9200/_index_template/fluentbit-logs" \
  -H "Content-Type: application/json" \
  -d '{
    "index_patterns": ["logs-*", "fluentbit-*"],
    "template": {
      "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "index.refresh_interval": "30s"
      },
      "mappings": {
        "properties": {
          "@timestamp": { "type": "date" },
          "message": { "type": "text" },
          "kubernetes": { "type": "object" }
        }
      }
    }
  }'
```

**优化建议：**
- 日志场景建议单索引 1 主分片即可（数据量 < 50GB/天）
- 副本数可设为 0（日志可接受短暂丢失），或根据可用性要求设置
- 合理设置 `refresh_interval`，减少刷新频率提升写入性能

### 方案四：配置索引生命周期管理（ILM）

**适用场景**: 需要自动化管理索引生命周期

```bash
# 创建 ILM 策略
curl -k -u <username>:<password> \
  -X PUT \
  "https://<opensearch-host>:9200/_plugins/_ism/policies/logs_policy" \
  -H "Content-Type: application/json" \
  -d '{
    "policy": {
      "description": "日志索引生命周期策略",
      "default_state": "hot",
      "states": [
        {
          "name": "hot",
          "actions": [
            {
              "rollover": {
                "min_index_age": "1d",
                "min_size": "10gb"
              }
            }
          ],
          "transitions": [
            {
              "state_name": "warm",
              "conditions": { "min_index_age": "3d" }
            }
          ]
        },
        {
          "name": "warm",
          "actions": [
            { "replica_count": { "number_of_replicas": 0 } }
          ],
          "transitions": [
            {
              "state_name": "delete",
              "conditions": { "min_index_age": "30d" }
            }
          ]
        },
        {
          "name": "delete",
          "actions": [
            { "delete": {} }
          ]
        }
      ]
    }
  }'

# 应用策略到索引模板
curl -k -u <username>:<password> \
  -X PUT \
  "https://<opensearch-host>:9200/_index_template/logs-template" \
  -H "Content-Type: application/json" \
  -d '{
    "index_patterns": ["logs-*"],
    "template": {
      "settings": {
        "plugins.index_state_management.rollover_alias": "logs",
        "plugins.index_state_management.policy_id": "logs_policy"
      }
    }
  }'
```

## 验证与监控

### 验证问题是否解决

```bash
# 检查当前 shard 数量
curl -k -u <username>:<password> \
  "https://<opensearch-host>:9200/_cluster/health?pretty"

# 查看集群统计信息
curl -k -u <username>:<password> \
  "https://<opensearch-host>:9200/_cluster/stats"

# 再次测试数据写入
curl -k -u <username>:<password> \
  -X POST \
  -H "Content-Type: application/x-ndjson" \
  https://<opensearch-host>:9200/_bulk \
  --data-binary @/tmp/test_bulk.json
```

### 配置 Prometheus 告警

```yaml
groups:
  - name: opensearch-alerts
    rules:
      - alert: OpenSearchShardCountHigh
        expr: elasticsearch_cluster_health_active_shards > 2500
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "OpenSearch shard 数量接近上限"
          description: "当前 shard 数量为 {{ $value }}，接近 3000 限制，请检查索引清理策略"

      - alert: OpenSearchShardCountCritical
        expr: elasticsearch_cluster_health_active_shards > 2900
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "OpenSearch shard 数量即将耗尽"
          description: "当前 shard 数量为 {{ $value }}，已达到危急阈值，新索引将无法创建"
```

### 监控指标

| 指标 | 说明 | 建议阈值 |
|------|------|----------|
| `elasticsearch_cluster_health_active_shards` | 活跃 shard 总数 | 警告: 2500, 危急: 2900 |
| `elasticsearch_indices_store_size_bytes` | 索引存储大小 | 按业务需求 |
| `elasticsearch_cluster_health_status` | 集群健康状态 | 0=绿, 1=黄, 2=红 |

## 预防措施

### 1. 索引生命周期管理
- 配置 ILM 策略，自动清理过期索引
- 设置合理的索引保留周期（如 7-30 天）
- 对历史数据使用冷存储或快照备份

### 2. 索引分片优化
- 日志类索引建议使用 1 主分片 + 0/1 副本
- 避免使用默认的 5 主分片配置
- 根据日数据量估算合理的分片大小（建议 20-50GB/分片）

### 3. 监控告警
- 监控 shard 使用率，提前预警
- 监控索引增长速度，预测容量需求
- 设置磁盘空间使用率告警

### 4. 定期维护
- 定期检查并清理过期索引
- 定期审查索引模板配置
- 定期优化索引（force merge 旧索引）

## 故障排查流程

1. **确认现象**: 检查 Fluent Bit 日志，确认 `failed to flush chunk` 错误
2. **验证根因**: 手动测试 OpenSearch 写入，查看具体错误信息
3. **检查状态**: 查看当前 shard 使用情况和集群健康状态
4. **选择方案**: 根据紧急程度选择清理索引或调整配置
5. **执行修复**: 清理过期索引或调整 shard 限制
6. **验证恢复**: 测试数据写入，确认 Fluent Bit 恢复正常
7. **配置预防**: 设置 ILM 策略和监控告警

## 总结

Fluent Bit 数据上传失败，提示 `failed to flush chunk`，根本原因是 **OpenSearch 集群 shard 数量达到上限**。通过以下步骤可系统性地解决和预防此类问题：

1. **紧急恢复**: 清理过期索引，快速释放 shard 资源
2. **容量扩容**: 适当调整 `cluster.max_shards_per_node` 参数
3. **优化配置**: 调整索引模板，减少不必要的分片数量
4. **自动化管理**: 配置 ILM 策略，实现索引生命周期自动管理
5. **监控告警**: 建立完善的监控体系，提前发现和预防问题

建议在生产环境同时实施多种措施，确保日志系统的稳定性和可持续性。
