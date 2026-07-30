# perf linux 性能分析

#### 收集数据 
```
sudo perf record -F 99 -p 13204 -g -- sleep 30
```
```
-F 99表示每秒99次，
-p 13204是进程号
-g表示记录调用栈
sleep 30则是持续30秒
```

#### 数据解析

```
perf script -i perf.data &> perf.unfold
``` 

#### 数据展现

```
git clone https://github.com/brendangregg/FlameGraph.git

将perf.unfold中的符号进行折叠
./stackcollapse-perf.pl perf.unfold &> perf.folded

生成svg图
./flamegraph.pl perf.folded > perf.svg
```

#### 用浏览器打开查看

#### 结果解读

https://www.ruanyifeng.com/blog/2017/09/flame-graph.html
