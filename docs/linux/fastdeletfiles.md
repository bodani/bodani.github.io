# 快速删除大量文件

## 生成大量文件
```
mkdir lostfiles
cd lostfiles
```

cat create_files.sh
```
for i in $(seq 1 1500000)
do
  echo test >>$i.txt
done
```

```
time sh create_files.sh

real	3m44.841s
user	0m13.208s
sys	3m14.523s
````
## 快速删除方式对比


```
time rsync --delete-before -d /tmp/null/ lostfiles/

real	1m14.937s
user	0m1.769s
sys	0m54.957s
```

```
time rm lostfiles/ -rf

real	1m4.221s
user	0m0.776s
sys	0m40.334s
```

```
time find ./lostfiles/ -type f  -delete

real	1m0.695s
user	0m0.851s
sys	0m41.294s

```

```
time perl -e 'for(<*>){((stat)[9]<(unlink))}'

real	1m9.959s
user	0m2.955s
sys	0m50.202s
```

## 应用

- 快速清除minio bucket 数据 

```
清除bucket数据
time find ./bucket001/ -type f  -delete

清除bucket元数据
time find .minio.sys/buckets/bucket001 -type f  -delete
```

