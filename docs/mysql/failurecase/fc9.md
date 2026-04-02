# MGR 节点长时间处于 RECOVERING 状态处理


## 故障描述


在查看集群状态时发现有节点一直卡在 `RECOVERING` 状态无法恢复正常工作：


```javascript
db = dba.getCluster().status()

{
    "defaultReplicaSet": {        
        "name": "default", 
        "primary": "helmbroker-mysql-2:3306",         
        "ssl": "REQUIRED",         
        "status": "OK",           
        "statusText": "Cluster is ONLINE and can tolerate up to ONE failure. 1 member is not active.",           
        "topology": {                 
            "helmbroker-mysql-0:3306": {                         
                "memberRole": "SECONDARY",                  
                "recoveryStatusText": "Recovery in progress",                
                "status": "RECOVERING",                     
                "version": "8.0.34"                       
            },                    
            "helmbroker-mysql-1:3306": {"status": "ONLINE"},   
            "helmbroker-mysql-2:3306": {"status": "ONLINE"}     
        }  
    },    
    "topologyMode": "Single-Primary" 
}
```

**关键字段说明**："statusText"中包含 **"1 member is not active"**，表示有一个成员未激活正常工作。  


---


## 异常分析


需要进一步查看详细恢复信息来定位问题根源：


```javascript
// extended mode 关键输出重点关注 helmbroker-mysql-0:3306 中的 recovery.recoveryChannel 块
db = dba.getCluster().status({extended: 1})
{
    "groupViewId": "17748313446971307:3",     
    "topology": {
        "helmbroker-mysql-0:3306": {             
            "address": "helmbroker-mysql-0:3306", 
            "applierWorkerThreads": 8, 
            "fenceSysVars": ["read_only", "super_read_only"], 
            "memberId": "e2511118-1d26-11f1-b8b9-12f54fc6f25d", 
            "memberRole": "SECONDARY", 
            "memberState": "RECOVERING",            
            "mode": "n/a",            
            "readReplicas": {},                   
            "recovery": {            
                "cloneStartTime": "2026-03-27 11:26:43.962", 
                "cloneState": "Completed",                    
                "currentStage": "RECOVERY",               
                "currentStageState": "Completed",             
                "recoveryChannel": {                   
                    "applierStatus": "OFF",           
                    "applierThreadState": "",         
                    "receiverStatus": "OFF",          
                    "receiverThreadState": "",         
                    "replicationSsl": null,       
                    "source": null                      
                }                
            },         
            "role": "HA",       
            "status": "RECOVERING",           
            "version": "8.0.34"            
        },      
        "helmbroker-mysql-1:3306": { "address": "helmbroker-mysql-1:3306", "status": "ONLINE", "memberRole": "SECONDARY" },      
        "helmbroker-mysql-2:3306": { "address": "helmbroker-mysql-2:3306", "status": "ONLINE", "memberRole": "PRIMARY", "mode": "R/W" }     
    },    
    "groupInformationSourceMember": "helmbroker-mysql-2:3306",    
    "metadataVersion": "2.1.0" 
}
```


从恢复通道（recoveryChannel）状态可以看到三个关键问题点：


| Issue              | Status     | Impact                                   |
| ------------------ | ---------- | ---------------------------------------- |
| **applierStatus**  | OFF        | Applier 进程没启动，无法应用事务日志     |
| **receiverStatus** | OFF        | Receiver 未能成功连接到 master 源端      |
| **source**         | NULL       | ⚠️ CRITICAL—没有指定任何主库作为恢复源！ |


这是 helmbroker-mysql-0 长期卡顿在 RECOVERING 状态的根本原因。  


---


## 解决方案

通过**移除损坏实例 + 重新加入**刷新其全部复制配置元数据即可修复这个问题。  


### Step 1: Remove Instance (force)


强制将该 problematic node 移出 InnoDB Cluster:


```bash
dba.getCluster().removeInstance('helmbroker-mysql-0:3306', {'force': True});
```


运行后会看到类似输出：


```text
The instance will be removed from the InnoDB Cluster.
* Waiting for instance 'helmbroker-mysql-0:3306' to synchronize with the primary...
** Transactions replicated ############################################   === 95%
WARNING: An error occurred when trying to catch up with cluster transactions and the 
         instance might have been left in an inconsistent state that will lead to errors if it is reused.
```


注意 Warning 是正常的——此警告意味着该节点当前可能缺少一些近期的 transaction log，但因为我们打算 complete reboot 整个副本设置所以可以直接忽略这个 warning 继续下一步操作。  


### Step 2: Add Instance Rebootstrap


然后把它加回来用全新的 configuration bootstrap 完整链路配置：


```bash
# 继续使用 mysqlsh
dba.getCluster().addInstance('helmbroker-mysql-0:3306'); 
```

成功返回后将完成 full synchronization flow 整个过程。  


### Verification Check


完成后再次检查 extended status:


```javascript
dba.getCluster().status({extended: true})
```

确认 helmbroker-mysql-0 现在的 recoveryChannel 显示已连接且正在正常 working:


| Key                   | Before Fix        | After Re-add               |
| -------------------- | ----------------- | ------------------------- |
| **memberState**       | RECOVERING (stuck)| ONLINE                     |
| **receiverStatus**    | OFF               | ON (connection established)             |
| **source**          | NULL              | helmbroker-mysql-1:3306 |

此时 recoveryChannel 已经可以正常通信了 🎉</response>