# 查看数据信息常用sql整理

## 库内存命中率
```
SELECT	
'index hit rate' AS name,
(sum(idx_blks_hit)) / nullif(sum(idx_blks_hit + idx_blks_read),0) AS ratio
FROM pg_statio_user_indexes
UNION ALL
SELECT
'table hit rate' AS name,
sum(heap_blks_hit) / nullif(sum(heap_blks_hit) + sum(heap_blks_read),0) AS ratio
FROM pg_statio_user_tables;
```
## 表内存命中率
```
SELECT relname AS relation, heap_blks_read AS heap_read, heap_blks_hit AS heap_hit,
((heap_blks_hit*100) / NULLIF((heap_blks_hit + heap_blks_read), 0)) AS ratio 
FROM pg_statio_user_tables order by ratio;
```
## 读IO内存占比
磁盘中读取和在内存中直接读取之间的数字和比
```
SELECT relname AS "relation", heap_blks_read AS heap_read, heap_blks_hit AS heap_hit, 
( (heap_blks_hit*100) / NULLIF((heap_blks_hit + heap_blks_read), 0)) AS ratioFROM pg_statio_user_tables;
```

## 表中索引命中率
```
SELECT relname,	
CASE idx_scan
WHEN 0 THEN NULL
ELSE round(100.0 * idx_scan / (seq_scan + idx_scan), 5)
END percent_of_times_index_used,
n_live_tup rows_in_table
FROM
pg_stat_user_tables
ORDER BY
n_live_tup DESC;
```

## 索引利用率
```
SELECT	
schemaname || '.' || relname AS table,
indexrelname AS index,
pg_size_pretty(pg_relation_size(i.indexrelid)) AS index_size,
idx_scan as index_scans
FROM pg_stat_user_indexes ui
JOIN pg_index i ON ui.indexrelid = i.indexrelid
WHERE NOT indisunique
AND idx_scan < 50
AND pg_relation_size(relid) > 5 * 8192
ORDER BY pg_relation_size(i.indexrelid) / nullif(idx_scan, 0) DESC NULLS FIRST,
pg_relation_size(i.indexrelid) DESC;
```

## 表空间大小 
```
SELECT
table_name,
pg_size_pretty(table_size) AS table_size,
pg_size_pretty(indexes_size) AS indexes_size,
pg_size_pretty(total_size) AS total_size
FROM (
SELECT
table_name,
pg_table_size(table_name) AS table_size,
pg_indexes_size(table_name) AS indexes_size,
pg_total_relation_size(table_name) AS total_size
FROM (
SELECT ('"' || table_schema || '"."' || table_name || '"') AS table_name
FROM information_schema.tables
) AS all_tables
ORDER BY total_size DESC
) AS pretty_sizes;
```
## 表膨胀率
```
-- Table bloat estimate
CREATE OR REPLACE VIEW monitor.pg_table_bloat AS
    SELECT CURRENT_CATALOG AS datname, nspname, relname , bs * tblpages AS size,
           CASE WHEN tblpages - est_tblpages_ff > 0 THEN (tblpages - est_tblpages_ff)/tblpages::FLOAT ELSE 0 END AS ratio
    FROM (
             SELECT ceil( reltuples / ( (bs-page_hdr)*fillfactor/(tpl_size*100) ) ) + ceil( toasttuples / 4 ) AS est_tblpages_ff,
                    tblpages, fillfactor, bs, tblid, nspname, relname, is_na
             FROM (
                      SELECT
                          ( 4 + tpl_hdr_size + tpl_data_size + (2 * ma)
                              - CASE WHEN tpl_hdr_size % ma = 0 THEN ma ELSE tpl_hdr_size % ma END
                              - CASE WHEN ceil(tpl_data_size)::INT % ma = 0 THEN ma ELSE ceil(tpl_data_size)::INT % ma END
                              ) AS tpl_size, (heappages + toastpages) AS tblpages, heappages,
                          toastpages, reltuples, toasttuples, bs, page_hdr, tblid, nspname, relname, fillfactor, is_na
                      FROM (
                               SELECT
                                   tbl.oid AS tblid, ns.nspname , tbl.relname, tbl.reltuples,
                                   tbl.relpages AS heappages, coalesce(toast.relpages, 0) AS toastpages,
                                   coalesce(toast.reltuples, 0) AS toasttuples,
                                   coalesce(substring(array_to_string(tbl.reloptions, ' ') FROM 'fillfactor=([0-9]+)')::smallint, 100) AS fillfactor,
                                   current_setting('block_size')::numeric AS bs,
                                   CASE WHEN version()~'mingw32' OR version()~'64-bit|x86_64|ppc64|ia64|amd64' THEN 8 ELSE 4 END AS ma,
                                   24 AS page_hdr,
                                   23 + CASE WHEN MAX(coalesce(s.null_frac,0)) > 0 THEN ( 7 + count(s.attname) ) / 8 ELSE 0::int END
                                       + CASE WHEN bool_or(att.attname = 'oid' and att.attnum < 0) THEN 4 ELSE 0 END AS tpl_hdr_size,
                                   sum( (1-coalesce(s.null_frac, 0)) * coalesce(s.avg_width, 0) ) AS tpl_data_size,
                                   bool_or(att.atttypid = 'pg_catalog.name'::regtype)
                                       OR sum(CASE WHEN att.attnum > 0 THEN 1 ELSE 0 END) <> count(s.attname) AS is_na
                               FROM pg_attribute AS att
                                        JOIN pg_class AS tbl ON att.attrelid = tbl.oid
                                        JOIN pg_namespace AS ns ON ns.oid = tbl.relnamespace
                                        LEFT JOIN pg_stats AS s ON s.schemaname=ns.nspname AND s.tablename = tbl.relname AND s.inherited=false AND s.attname=att.attname
                                        LEFT JOIN pg_class AS toast ON tbl.reltoastrelid = toast.oid
                               WHERE NOT att.attisdropped AND tbl.relkind = 'r' AND nspname NOT IN ('pg_catalog','information_schema')
                               GROUP BY 1,2,3,4,5,6,7,8,9,10
                           ) AS s
                  ) AS s2
         ) AS s3
    WHERE NOT is_na;

CREATE OR REPLACE VIEW monitor.pg_table_bloat_human AS
    SELECT nspname || '.' || relname AS name,
           pg_size_pretty(size)      AS size,
           pg_size_pretty((size * ratio)::BIGINT) AS wasted,
           round(100 * ratio::NUMERIC, 2)  as ratio
    FROM monitor.pg_table_bloat ORDER BY wasted DESC NULLS LAST;
```

## 索引膨胀率
```
CREATE OR REPLACE VIEW monitor.pg_index_bloat AS
    SELECT CURRENT_CATALOG AS datname, nspname, idxname AS relname, relpages::BIGINT * bs AS size,
           COALESCE((relpages - ( reltuples * (6 + ma - (CASE WHEN index_tuple_hdr % ma = 0 THEN ma ELSE index_tuple_hdr % ma END)
                                                   + nulldatawidth + ma - (CASE WHEN nulldatawidth % ma = 0 THEN ma ELSE nulldatawidth % ma END))
                                      / (bs - pagehdr)::FLOAT  + 1 )), 0) / relpages::FLOAT AS ratio
    FROM (
             SELECT nspname,
                    idxname,
                    reltuples,
                    relpages,
                    current_setting('block_size')::INTEGER                                                               AS bs,
                    (CASE WHEN version() ~ 'mingw32' OR version() ~ '64-bit|x86_64|ppc64|ia64|amd64' THEN 8 ELSE 4 END)  AS ma,
                    24                                                                                                   AS pagehdr,
                    (CASE WHEN max(COALESCE(pg_stats.null_frac, 0)) = 0 THEN 2 ELSE 6 END)                               AS index_tuple_hdr,
                    sum((1.0 - COALESCE(pg_stats.null_frac, 0.0)) *
                        COALESCE(pg_stats.avg_width, 1024))::INTEGER                                                     AS nulldatawidth
             FROM pg_attribute
                      JOIN (
                 SELECT pg_namespace.nspname,
                        ic.relname                                                   AS idxname,
                        ic.reltuples,
                        ic.relpages,
                        pg_index.indrelid,
                        pg_index.indexrelid,
                        tc.relname                                                   AS tablename,
                        regexp_split_to_table(pg_index.indkey::TEXT, ' ') :: INTEGER AS attnum,
                        pg_index.indexrelid                                          AS index_oid
                 FROM pg_index
                          JOIN pg_class ic ON pg_index.indexrelid = ic.oid
                          JOIN pg_class tc ON pg_index.indrelid = tc.oid
                          JOIN pg_namespace ON pg_namespace.oid = ic.relnamespace
                          JOIN pg_am ON ic.relam = pg_am.oid
                 WHERE pg_am.amname = 'btree' AND ic.relpages > 0 AND nspname NOT IN ('pg_catalog', 'information_schema')
             ) ind_atts ON pg_attribute.attrelid = ind_atts.indexrelid AND pg_attribute.attnum = ind_atts.attnum
                      JOIN pg_stats ON pg_stats.schemaname = ind_atts.nspname
                 AND ((pg_stats.tablename = ind_atts.tablename AND pg_stats.attname = pg_get_indexdef(pg_attribute.attrelid, pg_attribute.attnum, TRUE))
                     OR (pg_stats.tablename = ind_atts.idxname AND pg_stats.attname = pg_attribute.attname))
             WHERE pg_attribute.attnum > 0
             GROUP BY 1, 2, 3, 4, 5, 6
         ) est
    LIMIT 512;

CREATE OR REPLACE VIEW monitor.pg_index_bloat_human AS
    SELECT nspname || '.' || relname              AS name,
           pg_size_pretty(size)                   AS size,
           pg_size_pretty((size * ratio)::BIGINT) AS wasted,
           round(100 * ratio::NUMERIC, 2)         as ratio
    FROM monitor.pg_index_bloat;
```

## 表中锁状态
```
SELECT count(pg_stat_activity.pid) AS number_of_queries, 
  substring(trim(LEADING FROM regexp_replace(pg_stat_activity.query, '[\n\r]+'::text,' '::text, 'g'::text))
                FROM 0 FOR 200) AS query_name,  max(age(CURRENT_TIMESTAMP, query_start))
       AS max_wait_time, wait_event, usename, locktype, mode, granted 
                FROM pg_stat_activity LEFT JOIN pg_locks ON pg_stat_activity.pid = pg_locks.pid 
                   WHERE query != '<IDLE>' AND query NOT ILIKE '%pg_%' AND query NOT ILIKE '%application_name%'
                      AND query NOT ILIKE '%inet%' AND age(CURRENT_TIMESTAMP, query_start) > '5 milliseconds'::interval
  GROUP BY query_name,wait_event, usename, locktype, mode, granted  ORDER BY max_wait_time DESC;
```

## 被锁堵塞的语句
```
SELECT                                      
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    now() - blocked_activity.query_start AS blocked_duration,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    now() - blocking_activity.query_start AS blocking_duration,
    blocked_activity.query AS blocked_statement,
    blocking_activity.query AS blocking_statement
FROM                                                       
    pg_catalog.pg_locks AS blocked_locks
    JOIN pg_catalog.pg_stat_activity AS blocked_activity ON blocked_activity.pid = blocked_locks.pid
    JOIN pg_catalog.pg_locks AS blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
        AND blocking_locks.DATABASE IS NOT DISTINCT FROM blocked_locks.DATABASE
        AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
        AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
        AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
        AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
        AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
        AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
        AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
        AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
        AND blocking_locks.pid != blocked_locks.pid
    JOIN pg_catalog.pg_stat_activity AS blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE
    NOT blocked_locks.granted;
```

## 表中锁等待
```
with      
t_wait as      
(      
  select a.mode,a.locktype,a.database,a.relation,a.page,a.tuple,a.classid,a.granted,     
  a.objid,a.objsubid,a.pid,a.virtualtransaction,a.virtualxid,a.transactionid,a.fastpath,      
  b.state,b.query,b.xact_start,b.query_start,b.usename,b.datname,b.client_addr,b.client_port,b.application_name     
    from pg_locks a,pg_stat_activity b where a.pid=b.pid and not a.granted     
),     
t_run as     
(     
  select a.mode,a.locktype,a.database,a.relation,a.page,a.tuple,a.classid,a.granted,     
  a.objid,a.objsubid,a.pid,a.virtualtransaction,a.virtualxid,a.transactionid,a.fastpath,     
  b.state,b.query,b.xact_start,b.query_start,b.usename,b.datname,b.client_addr,b.client_port,b.application_name     
    from pg_locks a,pg_stat_activity b where a.pid=b.pid and a.granted     
),     
t_overlap as     
(     
  select r.* from t_wait w join t_run r on     
  (     
    r.locktype is not distinct from w.locktype and     
    r.database is not distinct from w.database and     
    r.relation is not distinct from w.relation and     
    r.page is not distinct from w.page and     
    r.tuple is not distinct from w.tuple and     
    r.virtualxid is not distinct from w.virtualxid and     
    r.transactionid is not distinct from w.transactionid and     
    r.classid is not distinct from w.classid and     
    r.objid is not distinct from w.objid and     
    r.objsubid is not distinct from w.objsubid and     
    r.pid <> w.pid     
  )      
),      
t_unionall as      
(      
  select r.* from t_overlap r      
  union all      
  select w.* from t_wait w      
)      
select locktype,datname,relation::regclass,page,tuple,virtualxid,transactionid::text,classid::regclass,objid,objsubid,     
string_agg(     
'Pid: '||case when pid is null then 'NULL' else pid::text end||chr(10)||     
'Lock_Granted: '||case when granted is null then 'NULL' else granted::text end||' , Mode: '||case when mode is null then 'NULL' else mode::text end||' , FastPath: '||case when fastpath is null then 'NULL' else fastpath::text end||' , VirtualTransaction: '||case when virtualtransaction is null then 'NULL' else virtualtransaction::text end||' , Session_State: '||case when state is null then 'NULL' else state::text end||chr(10)||     
'Username: '||case when usename is null then 'NULL' else usename::text end||' , Database: '||case when datname is null then 'NULL' else datname::text end||' , Client_Addr: '||case when client_addr is null then 'NULL' else client_addr::text end||' , Client_Port: '||case when client_port is null then 'NULL' else client_port::text end||' , Application_Name: '||case when application_name is null then 'NULL' else application_name::text end||chr(10)||      
'Xact_Start: '||case when xact_start is null then 'NULL' else xact_start::text end||' , Query_Start: '||case when query_start is null then 'NULL' else query_start::text end||' , Xact_Elapse: '||case when (now()-xact_start) is null then 'NULL' else (now()-xact_start)::text end||' , Query_Elapse: '||case when (now()-query_start) is null then 'NULL' else (now()-query_start)::text end||chr(10)||      
'SQL (Current SQL in Transaction): '||chr(10)||    
case when query is null then 'NULL' else query::text end,      
chr(10)||'--------'||chr(10)      
order by      
  (  case mode      
    when 'INVALID' then 0     
    when 'AccessShareLock' then 1     
    when 'RowShareLock' then 2     
    when 'RowExclusiveLock' then 3     
    when 'ShareUpdateExclusiveLock' then 4     
    when 'ShareLock' then 5     
    when 'ShareRowExclusiveLock' then 6     
    when 'ExclusiveLock' then 7     
    when 'AccessExclusiveLock' then 8     
    else 0     
  end  ) desc,     
  (case when granted then 0 else 1 end)    
) as lock_conflict    
from t_unionall     
group by     
locktype,datname,relation,page,tuple,virtualxid,transactionid::text,classid,objid,objsubid ;
```

## auto vacuum 预测
```
WITH table_opts AS (	
SELECT
pg_class.oid, relname, nspname, array_to_string(reloptions, '') AS relopts
FROM
pg_class INNER JOIN pg_namespace ns ON relnamespace = ns.oid
), vacuum_settings AS (
SELECT
oid, relname, nspname,
CASE
WHEN relopts LIKE '%autovacuum_vacuum_threshold%'
THEN substring(relopts, '.*autovacuum_vacuum_threshold=([0-9.]+).*')::integer
ELSE current_setting('autovacuum_vacuum_threshold')::integer
END AS autovacuum_vacuum_threshold,
CASE
WHEN relopts LIKE '%autovacuum_vacuum_scale_factor%'
THEN substring(relopts, '.*autovacuum_vacuum_scale_factor=([0-9.]+).*')::real
ELSE current_setting('autovacuum_vacuum_scale_factor')::real
END AS autovacuum_vacuum_scale_factor
FROM
table_opts
)
SELECT
vacuum_settings.relname AS table_name,
pg_size_pretty(pg_total_relation_size(pg_class.oid::regclass)) AS table_size,
to_char(psut.last_vacuum, 'YYYY-MM-DD HH24:MI') AS last_vacuum,
to_char(psut.last_autovacuum, 'YYYY-MM-DD HH24:MI') AS last_autovacuum,
to_char(pg_class.reltuples, '9G999G999G999') AS rowcount,
to_char(pg_class.reltuples / NULLIF(pg_class.relpages, 0), '999G999.99') AS rows_per_page,
to_char(autovacuum_vacuum_threshold
+ (autovacuum_vacuum_scale_factor::numeric * pg_class.reltuples), '9G999G999G999') AS autovacuum_vacuum_threshold,
psut.n_dead_tup AS dead_rows,
CASE
WHEN autovacuum_vacuum_threshold + (autovacuum_vacuum_scale_factor::numeric * pg_class.reltuples) < psut.n_dead_tup
THEN 'yes'
ELSE (autovacuum_vacuum_threshold + (autovacuum_vacuum_scale_factor::numeric * pg_class.reltuples) - psut.n_dead_tup)::varchar
END AS will_vacuum
FROM
pg_stat_user_tables psut INNER JOIN pg_class ON psut.relid = pg_class.oid
INNER JOIN vacuum_settings ON pg_class.oid = vacuum_settings.oid
ORDER BY 1
```

