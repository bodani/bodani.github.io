# Postgres 监控常用工具

#### 各种监控方式

- [zabbix](https://github.com/cavaliercoder/libzbxpgsql)  Monitor PostgreSQL with Zabbix

- [postgres_exporter](https://github.com/wrouesnel/postgres_exporter)  A PostgresSQL metric exporter for Prometheus

- [pgwatch2](https://github.com/cybertec-postgresql/pgwatch2) PostgreSQL metrics monitor/dashboard

- [pgmetrics](https://github.com/rapidloop/pgmetrics) Collect and display information and stats from a running PostgreSQL server 

- [pgdash](https://pgdash.io/)  (收费)

- [pganalyze](https://pganalyze.com) PostgreSQL Performance Monitoring

- [参考自己实现](https://yq.aliyun.com/live/927) 


#### 状态查看
[pgcenter](https://github.com/lesovsky/pgcenter)


```
pgcenter top
pgcenter: 2018-12-20 11:10:25, load average: 0.94, 0.84, 0.86                                                                         state [ok]: ::1:5432 postgres@postgres (ver: 10.6, up 8 days 19:57:54, recovery: f)
    %cpu: 15.0 us,  3.7 sy,  0.0 ni, 75.3 id,  5.7 wa,  0.0 hi,  0.2 si,  0.0 st                                                        activity:  5/1000 conns,  0/0 prepared,  2 idle,  0 idle_xact,  3 active,  0 waiting,  0 others
 MiB mem:   7821 total,    162 free,    424 used,     7235 buff/cached                                                                autovacuum:  0/3 workers/max,  0 manual,  0 wraparound, 00:00:00 vac_maxtime
MiB swap:   1023 total,    903 free,    120 used,      0/0 dirty/writeback                                                            statements: 1888 stmt/s, 2.330 stmt_avgtime, 00:00:00 xact_maxtime, 00:00:00 prep_maxtime      

pid     cl_addr      cl_port   datname       usename    appname    backend_type        wait_etype   wait_event     state    xact_age   query_age         change_age        query           
27908   ::1          40204     postgres      postgres   pgcenter   client backend                                  active   00:00:00   00:00:00          00:00:00          SELECT pid, client_addr AS cl_addr, client_port AS cl_port, datname, usename, left(application
27660   10.1.88.22   34224     timescaledb   postgres              client backend      LWLock       WALWriteLock   active   00:00:00   00:00:00          00:00:00          COMMIT                                                                                        
27410   10.1.88.22   34058     timescaledb   postgres              client backend                                  active   00:00:00   00:00:00          00:00:00          COMMIT                 
```

[pg_activity](/postgres/pg_activity)
```
pg_activity
- postgres@localhost:5432/postgres - Ref.: 2s
  Size:   60.54G -     0.00B/s        | TPS:        1243        | Active Connections:           2        | Duration mode:       query
  Mem.:   24.40% -     4.51G/62.66G   | IO Max:      342/s
  Swap:    2.10% -   515.50M/23.85G   | Read :      0.00B/s -      0/s
  Load:    0.93 1.38 1.49             | Write:      0.00B/s -      0/s
                                                                               RUNNING QUERIES
PID    DATABASE                      APP             USER           CLIENT   CPU% MEM%   READ/s  WRITE/s     TIME+  W  IOW              state   Query
33430  None                  walreceiver         postgres     10.1.80.6/32    1.0  0.0    0.00B    0.00B  0.000000  N    N             active
```

[pg_top]
```
pg_top
last pid: 15974;  load avg:  1.50,  1.79,  1.42;       up 508+22:42:20                                                                                                              10:03:51
134 processes: 134 sleeping
CPU states:  2.9% user,  0.0% nice,  0.7% system, 96.4% idle,  0.1% iowait
Memory: 60G used, 2497M free, 4K buffers, 54G cached
DB activity: 1272 tps,  0 rollbs/s,   0 buffer r/s, 100 hit%, 146256 row r/s, 2028 row w/s
DB I/O:     0 reads/s,     1 KB/s,   238 writes/s,  4812 KB/s
DB disk: 953.2 GB total, 694.9 GB free (27% used)
Swap: 1853M used, 22G free, 363M cached

  PID USERNAME PRI NICE  SIZE   RES STATE   TIME   WCPU    CPU COMMAND
15790 postgres  20    0   11G   81M sleep   0:00  0.78%  4.56% postgres: k3s_cg k3s_cg 10.1.40.92(37422) idle
29050 postgres  20    0   11G  122M sleep  41.6H  0.60%  3.18% postgres: zabbix zabbix ::1(55888) idle
29020 postgres  20    0   11G  120M sleep  41.7H  0.50%  2.98% postgres: zabbix zabbix ::1(55860) idle
29061 postgres  20    0   11G  120M sleep  41.7H  0.56%  2.98% postgres: zabbix zabbix ::1(55898) idle
29059 postgres  20    0   11G  122M sleep  41.6H  0.48%  2.98% postgres: zabbix zabbix ::1(55896) idle
29069 postgres  20    0   11G  120M sleep  41.6H  0.56%  2.98% postgres: zabbix zabbix ::1(55906) idle
```

[monitoring-stats](https://www.postgresql.org/docs/devel/monitoring-stats.html)


zabbix /var/lib/zabbix/postgresql/

```
wget https://git.zabbix.com/projects/ZBX/repos/zabbix/raw/templates/db/postgresql/postgresql/pgsql.bgwriter.sql
wget https://git.zabbix.com/projects/ZBX/repos/zabbix/raw/templates/db/postgresql/postgresql/pgsql.bgwriter.sql
wget https://git.zabbix.com/projects/ZBX/repos/zabbix/raw/templates/db/postgresql/postgresql/pgsql.cache.hit.sql
wget https://git.zabbix.com/projects/ZBX/repos/zabbix/raw/templates/db/postgresql/postgresql/pgsql.config.hash.sql
wget https://git.zabbix.com/projects/ZBX/repos/zabbix/raw/templates/db/postgresql/postgresql/pgsql.connections.prepared.sql
wget https://git.zabbix.com/projects/ZBX/repos/zabbix/raw/templates/db/postgresql/postgresql/pgsql.connections.sql
wget https://git.zabbix.com/projects/ZBX/repos/zabbix/raw/templates/db/postgresql/postgresql/pgsql.connections.sum.sql
wget https://git.zabbix.com/projects/ZBX/repos/zabbix/raw/templates/db/postgresql/postgresql/pgsql.dbstat.sql
wget https://git.zabbix.com/projects/ZBX/repos/zabbix/raw/templates/db/postgresql/postgresql/pgsql.dbstat.sum.sql
wget https://git.zabbix.com/projects/ZBX/repos/zabbix/raw/templates/db/postgresql/postgresql/pgsql.discovery.db.sql
wget https://git.zabbix.com/projects/ZBX/repos/zabbix/raw/templates/db/postgresql/postgresql/pgsql.frozenxid.sql
wget https://git.zabbix.com/projects/ZBX/repos/zabbix/raw/templates/db/postgresql/postgresql/pgsql.locks.sql
wget https://git.zabbix.com/projects/ZBX/repos/zabbix/raw/templates/db/postgresql/postgresql/pgsql.ping.time.sql
wget https://git.zabbix.com/projects/ZBX/repos/zabbix/raw/templates/db/postgresql/postgresql/pgsql.query.time.sql
wget https://git.zabbix.com/projects/ZBX/repos/zabbix/raw/templates/db/postgresql/postgresql/pgsql.replication.lag.sql
wget https://git.zabbix.com/projects/ZBX/repos/zabbix/raw/templates/db/postgresql/postgresql/pgsql.replication.recovery_role.sql
wget https://git.zabbix.com/projects/ZBX/repos/zabbix/raw/templates/db/postgresql/postgresql/pgsql.replication.status.sql
wget https://git.zabbix.com/projects/ZBX/repos/zabbix/raw/templates/db/postgresql/postgresql/pgsql.scans.sql
wget https://git.zabbix.com/projects/ZBX/repos/zabbix/raw/templates/db/postgresql/postgresql/pgsql.transactions.sql
wget https://git.zabbix.com/projects/ZBX/repos/zabbix/raw/templates/db/postgresql/postgresql/pgsql.uptime.sql
wget https://git.zabbix.com/projects/ZBX/repos/zabbix/raw/templates/db/postgresql/postgresql/pgsql.wal.stat.sql
```
https://git.zabbix.com/projects/ZBX/repos/zabbix/browse

