# Linux 系统登陆记录

## 背景

登陆系统时，尤其是具有外网ip的主机时经常会看到类似如下信息。

```
There were 12039 failed login attempts since the last successful login.
```
说明你的系统被尝试登陆破解。

大部分的破解基本都是自动机器扫描，配合自己的数据字典暴力破解。

## 系统登陆成功记录

查看命令

`last`

原理 读取解析 /var/log/wtmp

例如: 查看最近十次登陆记录

```
last -10
```

查看某个时间段的登陆记录

```
last -s 2021-10-10 -t 2021-10-20
```

## 系统登陆失败记录

查看命令

`lastb`

## 查看所有登陆成功和被拒绝登陆的用户

查看命令

`lastlog`
