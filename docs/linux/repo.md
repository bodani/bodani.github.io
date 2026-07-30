# Centos7 私有源搭建

## 介绍

为了保证IDC内所有主机版本一致。

目前问题， 当主机执行yum update 时，软件版本不可控。每个主机版本完全取决于更新的时机。

造成了同一个IDC内的版本的差异，比如有的数据库的版本为10.06,有的为10.13。尤其是使用了如postgis等拓展的时候。版本混乱，甚至主从之间都不一致。

## 实现方法

#### 思路

一台机器做源服务统一管理所有软件的版本，更新策略（私有源服务中心）。其他主机指向私有源。

#### 方法

- reposync , yumdownloader 下载源，将远程服务源下载到本地
- nginx 将本地源对外提供服务
- createrepo 生成本地源

## 一个例子

#### 服务端

rpm 数据
```
# 创建仓库存储目录
mkdir -p /var/www/repo/base/Packages

#备份原repo
mkdir -p /etc/yum.repos.d/backups
mv -f /etc/yum.repos/*.repo /etc/yum.repos.d/backups/

#使用阿里云加速
wget -O /etc/yum.repos.d/CentOS-Base.repo http://mirrors.aliyun.com/repo/Centos-7.repo

#下载所有源，体量过大
reposync -r base -p /var/www/html/

# 按需下载 ntp 为例
yum install --downloadonly --downloaddir=/var/www/repo/base/Packages/ ntp

# 下载依赖
repotrack ntp

# 更新repo.xml
createrepo -v /var/www/repo/base/Packages

```

nginx 配置
```
cat << EOF > repo.conf
server {
        listen       80;
        listen       [::]:80;
        server_name  mirrors.zhangeamon.top;
        root         /data/www/mirrors/;

        autoindex on;
        autoindex_localtime on; 
}

EOF
```
#### 客户端

```
cat << EOF > /etc/yum.repos.d/private.repo

[base]
name=private
baseurl=http://mirrors.zhangeamon.top/base/Packages/
enabled=1
gpgcheck=0 

EOF

```
