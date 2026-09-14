# 故障案例

此页面汇总了各类故障排除案例，包括常见问题及解决方案。

## 连接与配置问题

- [MySQL 连接错误 "Unknown MySQL server host 'localhost'"](./fc1.md)
- [MySQL TLS 版本不匹配](./fc2.md)
- [MySQL Public Key Retrieval 错误](./fc3.md)

## MGR 组复制问题

- [组复制数据在导入的时候被覆盖](./fc4.md)
- [组复制降级 - 导出的 sql 文件中关闭 binlog](./fc5.md)
- [集群加入节点失败 - 实例已存在于另一个集群](./fc6.md)
- [MGR 集群脑裂 - NO_QUORUM 状态处理](./fc7.md)
- [MGR GTID Diverged 处理](./fc8.md)
- [MGR 节点长时间处于 RECOVERING 状态处理](./fc9.md)
- [MGR 复制延迟临时优化](./fc10.md)
- [MGR 删除数据时报错 3100](./fc11.md)
- [集群状态查看与故障排查](./fc12.md)
- [Kubernetes 环境 MySQL Pod 排查](./fc13.md)
- [MySQL Shell 无法找到主节点](./fc14.md)

## 其他问题

- [主节点故障 OOM 后不选新主](./pro02.md)
- [内存相关问题与 group_concat 配置](./mem.md)
- [其他常见问题处理](./pro1.md)

## 简述

这些案例涵盖了数据库运维过程中可能遇到的各种实际问题和对应的解决方法，包括配置错误、性能问题、数据损坏等方面的问题排查和修复过程。每个案例均包含了问题背景、现象描述、排查步骤以及最终解决方案。