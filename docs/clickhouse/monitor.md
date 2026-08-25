监控

http://ip:8123/dashboard

http://ip:8001/metrics


SELECT
    database,
    table,
    engine,
    is_leader,
    total_replicas,
    active_replicas,
    replica_is_active
FROM system.replicas
ORDER BY database, table;

