主节点故障OOM后 不选新主

主节点日志
Defaulted container "mysql" out of: mysql, metrics
mysql 06:00:45.69 
mysql 06:00:45.70 Welcome to the Drycc mysql container
mysql 06:00:45.71 Subscribe to project updates by watching https://github.com/drycc/containers
mysql 06:00:45.71 Submit issues and feature requests at https://github.com/drycc/containers/issues
mysql 06:00:45.72 
mysql 06:00:45.73 INFO  ==> ** Starting MySQL setup **
mysql 06:00:45.75 INFO  ==> Validating settings in MYSQL_*/MARIADB_* env vars
mysql 06:00:45.77 INFO  ==> Initializing mysql database
mysql 06:00:45.80 WARN  ==> The mysql configuration file '/opt/drycc/mysql/conf/my.cnf' is not writable. Configurations based on environment variables will not be applied for this file.
mysql 06:00:45.80 INFO  ==> Using persisted data
mysql 06:00:45.81 INFO  ==> Running mysql_upgrade
mysql 06:00:45.83 INFO  ==> Starting mysql in background
2026-04-15T06:00:45.856726-00:00 0 [Warning] [MY-010140] [Server] Could not increase number of max_open_files to more than 1048576 (request: 2000000)
2026-04-15T06:00:46.095043-00:00 0 [System] [MY-010116] [Server] /opt/drycc/mysql/bin/mysqld (mysqld 8.0.34) starting as process 41
2026-04-15T06:00:46.101710-00:00 1 [System] [MY-013576] [InnoDB] InnoDB initialization has started.
2026-04-15T06:00:48.217137-00:00 1 [System] [MY-013577] [InnoDB] InnoDB initialization has ended.
2026-04-15T06:00:48.393619-00:00 0 [System] [MY-013587] [Repl] Plugin group_replication reported: 'Plugin 'group_replication' is starting.'
2026-04-15T06:00:48.394009-00:00 0 [System] [MY-014010] [Repl] Plugin group_replication reported: 'Plugin 'group_replication' has been started.'
2026-04-15T06:00:50.643823-00:00 0 [System] [MY-010229] [Server] Starting XA crash recovery...
2026-04-15T06:00:50.656791-00:00 0 [System] [MY-010232] [Server] XA crash recovery finished.
2026-04-15T06:00:52.112842-00:00 0 [Warning] [MY-010068] [Server] CA certificate ca.pem is self signed.
2026-04-15T06:00:52.112875-00:00 0 [System] [MY-013602] [Server] Channel mysql_main configured to support TLS. Encrypted connections are now supported for this channel.
2026-04-15T06:00:52.694753-00:00 0 [System] [MY-011323] [Server] X Plugin ready for connections. Bind-address: '::' port: 33060, socket: /tmp/mysqlx.sock
2026-04-15T06:00:52.694866-00:00 0 [System] [MY-010931] [Server] /opt/drycc/mysql/bin/mysqld: ready for connections. Version: '8.0.34'  socket: '/opt/drycc/mysql/tmp/mysql.sock'  port: 3306  Source distribution.
2026-04-15T06:00:52.695831-00:00 4 [System] [MY-011565] [Repl] Plugin group_replication reported: 'Setting super_read_only=ON.'
2026-04-15T06:00:52.712312-00:00 12 [System] [MY-010597] [Server] 'CHANGE REPLICATION SOURCE TO FOR CHANNEL 'group_replication_applier' executed'. Previous state source_host='<NULL>', source_port= 0, source_log_file='', source_log_pos= 4, source_bind=''. New state source_host='<NULL>', source_port= 0, source_log_file='', source_log_pos= 4, source_bind=''.
2026-04-15T06:00:53.017611-00:00 0 [ERROR] [MY-013780] [Repl] Plugin group_replication reported: 'Failed to establish MySQL client connection in Group Replication. Error establishing connection. Please refer to the manual to make sure that you configured Group Replication properly to work with MySQL Protocol connections.'
2026-04-15T06:00:53.017672-00:00 0 [ERROR] [MY-011735] [Repl] Plugin group_replication reported: '[GCS] The group communication engine failed to test connectivity to the local group communication engine on helmbroker-mysql-0:3306. This may be due to one or more invalid configuration settings. Double-check your group replication local address, firewall, SE Linux and TLS configurations and try restarting Group Replication on this server.'
2026-04-15T06:00:53.122460-00:00 0 [ERROR] [MY-011735] [Repl] Plugin group_replication reported: '[GCS] The member was unable to join the group. Local port: 3306'
find: ‘/docker-entrypoint-startdb.d/’: No such file or directory
mysql 06:00:53.91 INFO  ==> Stopping mysql
2026-04-15T06:00:53.915257-00:00 0 [System] [MY-013172] [Server] Received SHUTDOWN from user <via user signal>. Shutting down mysqld (Version: 8.0.34).
2026-04-15T06:00:53.915389-00:00 14 [ERROR] [MY-010584] [Repl] Replica SQL for channel 'group_replication_applier': ... The replica coordinator and worker threads are stopped, possibly leaving data in inconsistent state. A restart should restore consistency automatically, although using non-transactional storage for data or info tables or DDL queries could lead to problems. In such cases you have to examine your data (see documentation for details). Error_code: MY-001756
2026-04-15T06:00:53.915448-00:00 14 [ERROR] [MY-011451] [Repl] Plugin group_replication reported: 'The applier thread execution was aborted. Unable to process more transactions, this member will now leave the group.'
2026-04-15T06:00:53.915571-00:00 12 [ERROR] [MY-011452] [Repl] Plugin group_replication reported: 'Fatal error during execution on the Applier process of Group Replication. The server will now leave the group.'
2026-04-15T06:00:53.915659-00:00 12 [ERROR] [MY-011735] [Repl] Plugin group_replication reported: '[GCS] The member is already leaving or joining a group.'
2026-04-15T06:00:53.915721-00:00 12 [ERROR] [MY-011644] [Repl] Plugin group_replication reported: 'Unable to confirm whether the server has left the group or not. Check performance_schema.replication_group_members to check group membership information.'
2026-04-15T06:00:53.915746-00:00 12 [ERROR] [MY-011712] [Repl] Plugin group_replication reported: 'The server was automatically set into read only mode after an error was detected.'
2026-04-15T06:00:53.915872-00:00 12 [System] [MY-011565] [Repl] Plugin group_replication reported: 'Setting super_read_only=ON.'
2026-04-15T06:01:00.123767-00:00 0 [Warning] [MY-010909] [Server] /opt/drycc/mysql/bin/mysqld: Forcing close of thread 11  user: 'mysql.session'.
2026-04-15T06:01:52.723703-00:00 4 [ERROR] [MY-011640] [Repl] Plugin group_replication reported: 'Timeout on wait for view after joining group'
2026-04-15T06:01:54.074457-00:00 0 [System] [MY-010910] [Server] /opt/drycc/mysql/bin/mysqld: Shutdown complete (mysqld 8.0.34)  Source distribution.
mysql 06:01:54.17 INFO  ==> ** MySQL setup finished! **

mysql 06:01:54.24 INFO  ==> ** Starting MySQL **
2026-04-15T06:01:54.281127-00:00 0 [Warning] [MY-010140] [Server] Could not increase number of max_open_files to more than 1048576 (request: 2000000)
2026-04-15T06:01:54.514314-00:00 0 [System] [MY-010116] [Server] /opt/drycc/mysql/bin/mysqld (mysqld 8.0.34) starting as process 1
2026-04-15T06:01:54.520535-00:00 1 [System] [MY-013576] [InnoDB] InnoDB initialization has started.
2026-04-15T06:01:54.851720-00:00 1 [System] [MY-013577] [InnoDB] InnoDB initialization has ended.
2026-04-15T06:01:54.954502-00:00 0 [System] [MY-013587] [Repl] Plugin group_replication reported: 'Plugin 'group_replication' is starting.'
2026-04-15T06:01:54.954775-00:00 0 [System] [MY-014010] [Repl] Plugin group_replication reported: 'Plugin 'group_replication' has been started.'
2026-04-15T06:01:54.999556-00:00 0 [Warning] [MY-010068] [Server] CA certificate ca.pem is self signed.
2026-04-15T06:01:54.999582-00:00 0 [System] [MY-013602] [Server] Channel mysql_main configured to support TLS. Encrypted connections are now supported for this channel.
2026-04-15T06:01:55.293583-00:00 0 [System] [MY-010931] [Server] /opt/drycc/mysql/bin/mysqld: ready for connections. Version: '8.0.34'  socket: '/opt/drycc/mysql/tmp/mysql.sock'  port: 3306  Source distribution.
2026-04-15T06:01:55.293590-00:00 0 [System] [MY-011323] [Server] X Plugin ready for connections. Bind-address: '::' port: 33060, socket: /tmp/mysqlx.sock
2026-04-15T06:01:55.294250-00:00 4 [System] [MY-011565] [Repl] Plugin group_replication reported: 'Setting super_read_only=ON.'
2026-04-15T06:01:55.313776-00:00 12 [System] [MY-010597] [Server] 'CHANGE REPLICATION SOURCE TO FOR CHANNEL 'group_replication_applier' executed'. Previous state source_host='<NULL>', source_port= 0, source_log_file='', source_log_pos= 4, source_bind=''. New state source_host='<NULL>', source_port= 0, source_log_file='', source_log_pos= 4, source_bind=''.
2026-04-15T06:01:58.584572-00:00 0 [ERROR] [MY-011735] [Repl] Plugin group_replication reported: '[GCS] Error connecting to all peers. Member join failed. Local port: 3306'
2026-04-15T06:01:58.811353-00:00 0 [ERROR] [MY-011735] [Repl] Plugin group_replication reported: '[GCS] The member was unable to join the group. Local port: 3306'
2026-04-15T06:02:07.384523-00:00 0 [ERROR] [MY-011735] [Repl] Plugin group_replication reported: '[GCS] Error connecting to all peers. Member join failed. Local port: 3306'
2026-04-15T06:02:07.489597-00:00 0 [ERROR] [MY-011735] [Repl] Plugin group_replication reported: '[GCS] The member was unable to join the group. Local port: 3306'
2026-04-15T06:02:16.486860-00:00 0 [ERROR] [MY-011735] [Repl] Plugin group_replication reported: '[GCS] Error connecting to all peers. Member join failed. Local port: 3306'
2026-04-15T06:02:16.517118-00:00 0 [ERROR] [MY-011735] [Repl] Plugin group_replication reported: '[GCS] The member was unable to join the group. Local port: 3306'
2026-04-15T06:02:25.285701-00:00 0 [ERROR] [MY-011735] [Repl] Plugin group_replication reported: '[GCS] Error connecting to all peers. Member join failed. Local port: 3306'
2026-04-15T06:02:25.498573-00:00 0 [ERROR] [MY-011735] [Repl] Plugin group_replication reported: '[GCS] The member was unable to join the group. Local port: 3306'
2026-04-15T06:02:33.886312-00:00 0 [ERROR] [MY-011735] [Repl] Plugin group_replication reported: '[GCS] Error connecting to all peers. Member join failed. Local port: 3306'
2026-04-15T06:02:34.186492-00:00 0 [ERROR] [MY-011735] [Repl] Plugin group_replication reported: '[GCS] The member was unable to join the group. Local port: 3306'
2026-04-15T06:02:41.448726-00:00 0 [ERROR] [MY-011735] [Repl] Plugin group_replication reported: '[GCS] Error connecting to all peers. Member join failed. Local port: 3306'
2026-04-15T06:02:41.521119-00:00 0 [ERROR] [MY-011735] [Repl] Plugin group_replication reported: '[GCS] The member was unable to join the group. Local port: 3306'
2026-04-15T06:02:48.630520-00:00 0 [ERROR] [MY-011735] [Repl] Plugin group_replication reported: '[GCS] Error connecting to all peers. Member join failed. Local port: 3306'
2026-04-15T06:02:48.714246-00:00 0 [ERROR] [MY-011735] [Repl] Plugin group_replication reported: '[GCS] The member was unable to join the group. Local port: 3306'
2026-04-15T06:02:55.324370-00:00 4 [ERROR] [MY-011640] [Repl] Plugin group_replication reported: 'Timeout on wait for view after joining group'
2026-04-15T06:02:55.324574-00:00 4 [ERROR] [MY-011735] [Repl] Plugin group_replication reported: '[GCS] The member is already leaving or joining a group.'
2026-04-15T06:02:55.348540-00:00 0 [ERROR] [MY-011735] [Repl] Plugin group_replication reported: '[GCS] Error connecting to all peers. Member join failed. Local port: 3306'
2026-04-15T06:02:55.415460-00:00 0 [ERROR] [MY-011735] [Repl] Plugin group_replication reported: '[GCS] The member was unable to join the group. Local port: 3306'

登录1节点查看
 MySQL  helmbroker-mysql-1:33060+ ssl  JS > dba.getCluster().status();
WARNING: Error connecting to Cluster: MYSQLSH 51004: Unable to find a primary member in the Cluster
Retrying getCluster() using a secondary member
WARNING: You are connected to an instance in state 'Read Only'
Write operations on the InnoDB cluster will not be allowed.

{
    "clusterName": "MXMGR", 
    "defaultReplicaSet": {
        "name": "default", 
        "primary": "helmbroker-mysql-0:3306", 
        "ssl": "REQUIRED", 
        "status": "OK_NO_TOLERANCE_PARTIAL", 
        "statusText": "Cluster is NOT tolerant to any failures. 1 member is not active.", 
        "topology": {
            "helmbroker-mysql-0:3306": {
                "address": "helmbroker-mysql-0:3306", 
                "instanceErrors": [
                    "NOTE: group_replication is stopped."
                ], 
                "memberRole": "PRIMARY", 
                "memberState": "OFFLINE", 
                "mode": "n/a", 
                "readReplicas": {}, 
                "role": "HA", 
                "status": "UNREACHABLE", 
                "version": "8.0.34"
            }, 
            "helmbroker-mysql-1:3306": {
                "address": "helmbroker-mysql-1:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.34"
            }, 
            "helmbroker-mysql-2:3306": {
                "address": "helmbroker-mysql-2:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.34"
            }
        }, 
        "topologyMode": "Single-Primary"
    }, 
    "groupInformationSourceMember": "helmbroker-mysql-1:3306"
} 
dba.getCluster();
WARNING: Error connecting to Cluster: MYSQLSH 51004: Unable to find a primary member in the Cluster
Retrying getCluster() using a secondary member
WARNING: You are connected to an instance in state 'Read Only'
Write operations on the InnoDB cluster will not be allowed.

<Cluster:MXMGR>
 MySQL  helmbroker-mysql-1:33060+ ssl  JS > dba.getCluster().status();
WARNING: Error connecting to Cluster: MYSQLSH 51004: Unable to find a primary member in the Cluster
Retrying getCluster() using a secondary member
WARNING: You are connected to an instance in state 'Read Only'
Write operations on the InnoDB cluster will not be allowed.

{
    "clusterName": "MXMGR", 
    "defaultReplicaSet": {
        "name": "default", 
        "primary": "helmbroker-mysql-0:3306", 
        "ssl": "REQUIRED", 
        "status": "OK_NO_TOLERANCE_PARTIAL", 
        "statusText": "Cluster is NOT tolerant to any failures. 1 member is not active.", 
        "topology": {
            "helmbroker-mysql-0:3306": {
                "address": "helmbroker-mysql-0:3306", 
                "instanceErrors": [
                    "NOTE: group_replication is stopped."
                ], 
                "memberRole": "PRIMARY", 
                "memberState": "OFFLINE", 
                "mode": "n/a", 
                "readReplicas": {}, 
                "role": "HA", 
                "status": "UNREACHABLE", 
                "version": "8.0.34"
            }, 
            "helmbroker-mysql-1:3306": {
                "address": "helmbroker-mysql-1:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.34"
            }, 
            "helmbroker-mysql-2:3306": {
                "address": "helmbroker-mysql-2:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.34"
            }
        }, 
        "topologyMode": "Single-Primary"
    }, 
    "groupInformationSourceMember": "helmbroker-mysql-1:3306"
}
重启所有节点后，重启集群查看，主节点变成了2 
dba.getCluster();
Dba.getCluster: This function is not available through a session to a standalone instance (metadata exists, instance belongs to that metadata, but GR is not active) (MYSQLSH 51314)
 MySQL  helmbroker-mysql-0:33060+ ssl  JS > 


  dba.getCluster().status();
{
    "clusterName": "MXMGR", 
    "defaultReplicaSet": {
        "name": "default", 
        "primary": "helmbroker-mysql-2:3306", 
        "ssl": "REQUIRED", 
        "status": "OK", 
        "statusText": "Cluster is ONLINE and can tolerate up to ONE failure.", 
        "topology": {
            "helmbroker-mysql-0:3306": {
                "address": "helmbroker-mysql-0:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.34"
            }, 
            "helmbroker-mysql-1:3306": {
                "address": "helmbroker-mysql-1:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.34"
            }, 
            "helmbroker-mysql-2:3306": {
                "address": "helmbroker-mysql-2:3306", 
                "memberRole": "PRIMARY", 
                "mode": "R/W", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.34"
            }
        }, 
        "topologyMode": "Single-Primary"
    }, 
    "groupInformationSourceMember": "helmbroker-mysql-2:3306"