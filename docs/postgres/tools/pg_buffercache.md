# pg_buffercache

## 通过插件查看PG数据缓存

```
create extension pg_buffercache;
```

## 查看当前database缓存使用情况
```
select c.relname,relname,pg_size_pretty(pg_table_size(c.oid)),pg_size_pretty(count(*) * 8192) as buffered,
round(100.0*count(*)/(select setting FROM pg_settings where name = 'shared_buffers')::integer,1) as buffer_percent,
round(100.0 * count(*) *  8192/pg_table_size(c.oid)) as percent_of_table
from pg_class c inner join pg_buffercache b on b.relfilenode = c.relfilenode inner join pg_database d on (b.reldatabase = d.oid and d.datname = current_database())                     
group by c.oid ,c.relname order by 3 desc limit 10;
```


