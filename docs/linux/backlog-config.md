# Linux backlog/somaxconn 内核参数

## Linux 网络状态查看
```
netstat -n | awk '/^tcp/ {++S[$NF]} END {for(a in S) print a, S[a]}'
```

https://www.cnblogs.com/dream397/p/14785967.html
