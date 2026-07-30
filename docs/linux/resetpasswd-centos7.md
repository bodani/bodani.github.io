# Centos7 重置密码

#### 进入开机界面
![images](/images/resetpassword01.png)

#### 按e 后 修改如下两处 
![images](/images/resetpassword02.png)

#### ctrl+X 进入系统


![images](/images/resetpassword03.png)

上图中最后一个指令为保持设置
```
touch /.autorelabel
```

#### 重新进入系统

```
exec /sbin/init
```


