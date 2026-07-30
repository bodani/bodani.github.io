# 找回supper user 权限

##### 背景

意外删除postgres supper user 权限 

##### 找回方法

关闭数据库 用单用户模式重新启动
```
/usr/lib/postgresql/xxxx/bin/postgres --single -D $PGDATA

```

重新设置supper user 权限
```
alter user postgres with superuser;
```
