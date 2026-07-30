# 数据库免密码登陆

## 免密登陆


以下几种PG配置免密的方法。

#### 方法一：设置pg_hab.conf 认证方式为trust
```
#Type database user address method
host all postgres 127.0.0.1/32 trust
```
该方式最不安全，导致通过指定IP连接数据库的连接都可以任意登录数据，毫无安全保障。禁止在生产环境使用。

#### 方法二：设置PG环境变量PGPASSWORD

PGPASSWORD是PostgreSQL系统环境变量，在客户端设置后再远程连接数据库时，将优先使用这个密码。
```
[postgres@PG-1 ~]$ export PGPASSWORD=root
[postgres@PG-1 ~]$ psql -U postgres -h 127.0.0.1 -p 5432
Timing is on.
Border style is 2.
Null display is "NULL".
psql (13.2)
Type "help" for help.
```
此时数据库登录时，不在提示输入用户密码

#### 方法三：设置环境变量PGSERVICE

pg_service.conf 通过定义服务文件的方式，可以对多个数据库进行免密登录。
```

vi /home/postgres/.pg_service.conf
[backup]
hostaddr=127.0.0.1
port=5432
user=postgres
dbname=postgres
password=root
connect_timeout=10
[postgres@PG-1 ~]$ export PGSERVICE=backup
[postgres@PG-1 ~]$ psql -h 127.0.0.1 -p 5432 -U postgres
Timing is on.
Border style is 2.
Null display is "NULL".
psql (13.2)
Type "help" for help.
```
定义pg_service.conf文件，该文件可以包含多个模块，每个模块代表一个连接。

#### 方法四：设置.pgpass文件

改文件默认在/home/postgres/，且该文件的权限要为600，如果文件权限不对，则在登录会有相应的告警输出，并要求输入用户密码。
```
WARNING: password file "/home/postgres/.pgpass" has group or world access; permissions should be u=rw (0600) or less
Password for user postgres:
```
内容格式：
```
host:port:dbname:username:password
```
```
[postgres@PG-1 ~]$ cat .pgpass
127.0.0.1:5432:postgres:postgres:root
localhost:5432:postgres:postgres:root
```
文件权限：
```
[postgres@PG-1 ~]$ ll -h .pgpass
-rw------- 1 postgres postgres 76 2月 24 19:26 .pgpass
```
登录：
```
[postgres@PG-1 ~]$ psql -U postgres -h 127.0.0.1 -p 5432
Timing is on.
Border style is 2.
Null display is "NULL".
psql (13.2)
Type "help" for help.
```

#### 方法五： 设置pg_hab.conf 为 ident 或 peer

peer 方式一 
```
local   all    all       peer
```

peer 方式二
```
local   all    all       peer map=t
```

再配置pg_ident.conf
```
#mapping name      os user name      db user name
t                  os_user           postgres
```

ident 方式
```
host   all    all       ident map=t
```

再配置pg_ident.conf
```
#mapping name      os user name      db user name
t                  os_user           postgres
```

peer 和 ident 区别


- 都是基于操作系统用户认证，通过操作系统用户映射数据库用户进行认证，peer方式数据库访问客户端与数据库服务器必须在同一台操作系统上，ident方式则不是。
  peer使用unix socket会话，psql访问时不指定-h 或者-h localhost 或者-h $PGDATA

- ident使用tcp会话，psql访问时-h 127.0.0.1 或host


