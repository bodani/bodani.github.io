# Linux 字符集

## Centos 字符集

```
-bash: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)                                                                                                                                        
/bin/sh: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)                                                                                                                                      
/bin/sh: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)                                                                                                                                      
/bin/sh: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)
```

```
yum -y install glibc-locale-source glibc-langpack-en

localedef -f UTF-8 -i en_US en_US.UTF-8

```
