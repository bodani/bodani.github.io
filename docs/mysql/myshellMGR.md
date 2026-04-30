# mysql-shell 管理组复制

## 安装
```
sudo apt-get install mysql-shell
```

创建超级用户
```
create user administrator@'%' identified with 'caching_sha2_password'  by 'password';
grant all PRIVILEGES on *.* to administrator@'%' WITH GRANT OPTION;
flush privileges;
show grants for administrator@'%';
```
## 创建集群
```
创建集群，第一个节点
mysqlsh -uadministrator -ppassword -h 10.10.2.11 

shell.options['dba.restartWaitTimeout']=300;
var cluster=dba.createCluster('YOURMGR',{disableClone:false});
加入节点 1 
dba.getCluster().addInstance('administrator:cluster_password@10.10.2.12:3306',{recoveryMethod:'clone'})
加入节点 2
dba.getCluster().addInstance('administrator:cluster_password@10.10.2.12:3306',{recoveryMethod:'clone'})
```
使用 mysqlsh 创建集群会自动创建组复制的相关用户，并不是使用的这个administrator 账号。


查看状态
```
dba.getCluster().status();
```

```
mysql router 
# 创建配置文件
mysqlrouter --bootstrap mysql_user@host:port  -d /etc/mysql/conf/router --name myrouter --force --user=mysql
```

```
# 启动router
cd /etc/mysql/conf/router && sh start.sh
```

```
https://github.com/rluisr/mysqlrouter_exporter
```
注意事项apparmor aa-teardown

```
# 验证
mysql -h xxx -P 6446 -pmysql_4U

mysql -h xxx -P 6447 -pmysql_4U
```

```
#mysqlsh 配置验证，修复
dba.checkInstanceConfiguration();
dba.configureInstance();
```

## 扩容节点
查看状态
```
dba.getCluster().status();
```
加入前验证集群
```
dba.checkInstanceConfiguration('user@10.10.2.13:3306');
```
加入前配置集群
```
dba.configureInstance('user@10.10.2.13:3306');
```
加入集群
```
dba.getCluster().addInstance('user@10.10.2.13:3306');
```
重新加入集群 
```
cluster.rejoinInstance() 
```

## 缩容
```
cluster.removeInstance("root@instanceWithOldUUID:3306", {force: true})
cluster.rescan()
```

## 指定主节点
```
cluster.setPrimaryInstance()
```

## 重启集群
当所有集群中的节点都处于关闭状态时
```
dba.rebootClusterFromCompleteOutage();
```

API

```
https://dev.mysql.com/doc/dev/mysqlsh-api-python/8.0/
```

