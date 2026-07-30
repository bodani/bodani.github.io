# 关于Ubuntu20.04下向日葵远程软件连接中断的解决方法

## 在终端下运行以下命令

```
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install lightdm
```
在安装lightdm时选择lightdm

## 切换lightdm图形页面

```
sudo dpkg-reconfigure lightdm
```

切换完成后重启电脑，就可以使用向日葵远程了
