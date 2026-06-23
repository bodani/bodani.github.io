# 用户管理

## 用户查看

```
select * from mysql.user where user = 'root'\G;
Host: localhost
                    User: root
             Select_priv: Y
             Insert_priv: Y
             Update_priv: Y
             Delete_priv: Y
             Create_priv: Y
               Drop_priv: Y
             Reload_priv: Y
           Shutdown_priv: Y
            Process_priv: Y
               File_priv: Y
              Grant_priv: Y
         References_priv: Y
              Index_priv: Y
              Alter_priv: Y
            Show_db_priv: Y
              Super_priv: Y
   Create_tmp_table_priv: Y
        Lock_tables_priv: Y
            Execute_priv: Y
         Repl_slave_priv: Y
        Repl_client_priv: Y
        Create_view_priv: Y
          Show_view_priv: Y
     Create_routine_priv: Y
      Alter_routine_priv: Y
        Create_user_priv: Y
              Event_priv: Y
            Trigger_priv: Y
  Create_tablespace_priv: Y
                ssl_type: 
              ssl_cipher: 0x
             x509_issuer: 0x
            x509_subject: 0x
           max_questions: 0
             max_updates: 0
         max_connections: 0
    max_user_connections: 0
                  plugin: auth_socket
   authentication_string: 
        password_expired: N
   password_last_changed: 2024-11-12 11:15:54
       password_lifetime: NULL
          account_locked: N
        Create_role_priv: Y
          Drop_role_priv: Y
  Password_reuse_history: NULL
     Password_reuse_time: NULL
Password_require_current: NULL
         User_attributes: NULL

```


## auth_socket 验证插件的使用场景

验证方式有以下特点：

首先，这种验证方式不要求输入密码，即使输入了密码也不验证。这个特点让很多人觉得很不安全，实际仔细研究一下这种方式，发现还是相当安全的，因为它有另外两个限制；
只能用 UNIX 的 socket 方式登陆，这就保证了只能本地登陆，用户在使用这种登陆方式时已经通过了操作系统的安全验证；
操作系统的用户和 MySQL 数据库的用户名必须一致，例如你要登陆 MySQL 的 root 用户，必须用操作系统的 root 用户登陆。

auth_socket 这个插件因为有这些特点，它很适合我们在系统投产前进行安装调试的时候使用，而且也有相当的安全性，因为系统投产前通常经常同时使用操作系统的 root 用户和 MySQL 的 root 用户。当我们在系统投产后，操作系统的 root 用户和 MySQL 的 root 用户就不能随便使用了，这时可以换成其它的验证方式，可以使用下面的命令进行切换：

查看是否安装了插件
```
SELECT * FROM information_schema.PLUGINS WHERE PLUGIN_NAME LIKE '%socket%'\G;
```
安装插件
```
INSTALL PLUGIN auth_socket SONAME 'auth_socket.so';
```
创建用户
```
CREATE USER IF NOT EXISTS localroot@localhost IDENTIFIED WITH auth_socket AS 'mysql';
GRANT ALL ON *.* TO 'localroot'@localhost WITH GRANT OPTION;
GRANT PROXY ON ''@'' TO 'localroot'@localhost WITH GRANT OPTION;
```
## caching_sha2_password

从 MySQL 8.0.4 开始，MySQL 默认身份验证插件从 mysql_native_password 改为 caching_sha2_password
ALTER USER 'root'@'localhost' IDENTIFIED WITH caching_sha2_password BY 'test';

## 创建用户
```
CREATE USER 'myuser'@'%' IDENTIFIED WITH caching_sha2_password  BY 'mypassword';
GRANT ALL ON *.* TO 'myuser'@'%';
FLUSH PRIVILEGES;
```
'myuser'@'%' 用户名@IP 组成用户的唯一标识。即使用户名相同，如果ip不同代表两个不同的用户

## 修改密码
```
ALTER USER 'root'@'localhost' IDENTIFIED WITH caching_sha2_password BY 'pwd';
flush privileges;
```

## 查看用户权限
```
SHOW GRANTS FOR 'myuser'@'%';
```

## ssl 访问
```
-- 查看数据库服务是否支持ssl
show variables like '%have%ssl%';
+---------------+-------+
| Variable_name | Value |
+---------------+-------+
| have_openssl  | YES   |
| have_ssl      | YES   |
+---------------+-------+
-- 创建用户
CREATE USER 'myssluser'@'%' IDENTIFIED BY 'mysslpassword';
GRANT ALL ON *.* TO 'myssluser'@'%';
ALTER USER 'myssluser'@'%' REQUIRE SSL;
FLUSH PRIVILEGES;
SELECT ssl_type From mysql.user Where user='myssluser';
-- 普通登录失败
$ mysql -umyssluser -p
Enter password: 
ERROR 1045 (28000): Access denied for user 'myssluser'@'xxxxx' (using password: YES)
-- 使用ssl登录
$ mysql --ssl-mode=REQUIRED  -u myssluser -p
```