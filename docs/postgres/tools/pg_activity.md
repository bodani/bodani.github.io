# 数据库实时运行信息查看

## 介绍

类似Linux top 命令 查看数据实时运行情况

![image](/images/pg_activity.png)
https://github.com/dalibo/pg_activity
## 安装 

测试环境centos7 postgresql10

#### 查看已安装的PG版本 
如果有9.2 版本，清理,如果没有postgresql10-devel 需要安装
```
 yum list installed | grep postgres
```
#### 设置环境变量

```
export PG_HOME=/usr/pgsql-10
export PATH=$PATH:$PG_HOME/bin/
```

#### 安装pg_activity

```
python3 -m pip install pg_activity psycopg2-binary
```

## 使用

与psql 连接方式相同
```
pg_activity -U xxx -p xxx 
```

#### 更多连接参数


#### 实时界面 ,按键说明
```
r 	Sort by READ/s, descending
w 	Sort by WRITE/s, descending
c 	Sort by CPU%, descending
m 	Sort by MEM%, descending
t 	Sort by TIME+, descending
```
