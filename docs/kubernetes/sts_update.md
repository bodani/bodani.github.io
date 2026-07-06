# sts 滚动更新

控制 sts 逐个更新

```
updateStrategy:
 type: RollingUpdate
 rollingUpdate:
  partition: 3
```

在更新 sts 时 大于 partition 的pod 将重启。 小于等于 partiton 的pod 保持不动

3 个副本的 将 partition 从3 依次改成 2 ->1 -> 0 .实现分部重启

一个修改mysql的示例

```
查看mysql 集群的状态,保证集群完全恢复后再操作下一个节点
dba.getCluster().status()
shell.options['dba.restartWaitTimeout']=300;

重启后重新加入集群
dba.getCluster().rejoinInstance('root@helmbroker-mysql-01-1:3306');

集群主节点切换
dba.getCluster().setPrimaryInstance('helmbroker-mysql-01-1:3306')
```

- name: MALLOC_ARENA_MAX
              value: "1"
