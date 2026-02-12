# 达梦 v8 数据库安装 (Centos7)

## 前期准备

### 更换源

```
curl http://mirrors.aliyun.com/repo/Centos-7.repo > /etc/yum.repos.d/CentOS-Base.repo

# 更新yum缓存
yum clean all
yum makecache
```

### 安装必要的依赖包

```
yum install -y wget unzip gzip tar net-tools vim lrzsz ntp
```

### 启动 ntp 服务

```
systemctl start ntpd
systemctl enable ntpd
```

### 下载达梦数据库安装包（请根据实际版本调整下载链接）

### 系统用户

```
groupadd dinstall -g 2001
useradd  -G dinstall -m -d /home/dmdba -s /bin/bash -u 2001 dmdba
passwd dmdba
```

### 文件句柄

vi /etc/security/limits.conf

```
dmdba  soft      nice       0
dmdba  hard      nice       0
dmdba  soft      as         unlimited
dmdba  hard      as         unlimited
dmdba  soft      fsize      unlimited
dmdba  hard      fsize      unlimited
dmdba  soft      nproc      65536
dmdba  hard      nproc      65536
dmdba  soft      nofile     65536
dmdba  hard      nofile     65536
dmdba  soft      core       unlimited
dmdba  hard      core       unlimited
dmdba  soft      data       unlimited
dmdba  hard      data       unlimited
```

验证

```
su - dmdba
ulimit -a
```

### 数据目录准备

`注意： 如果是独立数据盘情景，需先挂着数据盘`

```
mkdir -p /dmdata/data ##归档保存目录
mkdir -p /dmdata/arch ##备份保存目录
mkdir -p /dmdata/dmbak

chown -R dmdba:dinstall /dmdata/data
chown -R dmdba:dinstall /dmdata/arch
chown -R dmdba:dinstall /dmdata/dmbak

chmod -R 755 /dmdata/data
chmod -R 755 /dmdata/arch
chmod -R 755 /dmdata/dmbak
```

## 安装数据库

### 挂载镜像

```
https://www.dameng.com/download/index.html
cd  /opt
https://download.dameng.com/eco/adapter/DM8/202512/dm8_20251208_x86_CentOS7_64.zip
unzip dm8_20250506_x86_rh7_64.zip
mount -o loop dm8_20250506_x86_rh7_64.iso /mnt
```

### 安装数据库

```
su - dmdba
cd /mnt
./DMInstall.bin -i
```

切换到 root 用户, 创建 DmAPService

```
/home/dmdba/dmdbms/script/root/root_installer.sh
```

### 配置数据库服务

#### 初始化实例

```
su - dmdba
cd /home/dmdba/dmdbms/bin

./dminit path=/dmdata/data SYSDBA_PWD=MMdba123 SYSAUDITOR_PWD=DMdba123 CHARSET=1 CASE_SENSITIVE=Y
```

- charset：字符集选项。取值范围 0、1、2。0 代表 GB18030，1 代表 UTF-8，2 代表韩文字符集 EUC-KR。缺省值为 0。可选参数。此参数在数据库创建成功后无法修改，可通过系统函数 SF_GET_UNICODE_FLAG()或 UNICODE()查询设置的参数值。

- case_sensitive： 标识符大小写敏感。当大小写敏感时，小写的标识符应用""括起，否则被系统自动转换为大写；当大小写不敏感时，系统不会转换标识符的大小写，系统比较函数会将大写字母全部转为小写字母再进行比较。取值：Y、y、1 表示敏感；N、n、0 表示不敏感。缺省值为 Y。可选参数。此参数在数据库创建成功后无法修改，可通过系统函数 SF_GET_CASE_SENSITIVE_FLAG()或 CASE_SENSITIVE()查询设置的参数值。

#### mysql 实例

```
vi /dmdata/data/DAMENG/dm.ini
```

```
COMPATIBLE_MODE=4
```

注册实例服务，root 用户 . 如下所示：

```
cd /home/dmdba/dmdbms/script/root/
./dm_service_installer.sh -t dmserver -dm_ini /dmdata/data/DAMENG/dm.ini -p DAMENG
```

#### 启动停止

```
sudo su - dmdba
cd /home/dmdba/dmdbms/bin

./DmServiceDAMENG start
```

## 关闭防火墙

```
systemctl stop firewalld
systemctl disable firewalld
```

## selinux 关闭

```
sed -i 's/^SELINUX=.*/SELINUX=disabled/' /etc/selinux/config
setenforce 0
```
