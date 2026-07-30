# 进程分析 strace,pstack

https://yq.aliyun.com/articles/647468

## 基本用法

```
pstack pid
```

```
strace -e trace=all -T -tt -p pid

strace -o server.strace -Ttt -p pid
```

##  应用举例

python
```
while True:
    print('hello')
```

查看应用进程
```
ps -ef | grep python
root     13491 13054 13 13:27 pts/0    00:00:06 python
```


```
 pstack 13491
#0  0x0000726388f9ea90 in __write_nocancel () at ../sysdeps/unix/syscall-template.S:81
#1  0x0000726388f292f3 in _IO_new_file_write (f=0x726389277400 <_IO_2_1_stdout_>, data=0x72638a18d000, n=2) at fileops.c:1258
#2  0x0000726388f2ab0e in new_do_write (to_do=2, data=0x72638a18d000 "1\n. \b[8@while True:\033[C", fp=0x726389277400 <_IO_2_1_stdout_>) at fileops.c:519
#3  _IO_new_do_write (fp=0x726389277400 <_IO_2_1_stdout_>, data=0x72638a18d000 "1\n. \b[8@while True:\033[C", to_do=2) at fileops.c:495
#4  0x0000726388f29a50 in _IO_new_file_xsputn (f=0x726389277400 <_IO_2_1_stdout_>, data=<optimized out>, n=1) at fileops.c:1326
#5  0x0000726388f1e05b in __GI__IO_fputs (str=0x726389cd2a8d "\n", fp=0x726389277400 <_IO_2_1_stdout_>) at iofputs.c:39
#6  0x0000726389c0b9c0 in PyFile_WriteString () from /lib64/libpython2.7.so.1.0
#7  0x0000726389c80d48 in PyEval_EvalFrameEx () from /lib64/libpython2.7.so.1.0
#8  0x0000726389c8908d in PyEval_EvalCodeEx () from /lib64/libpython2.7.so.1.0
#9  0x0000726389c89192 in PyEval_EvalCode () from /lib64/libpython2.7.so.1.0
#10 0x0000726389ca25cf in run_mod () from /lib64/libpython2.7.so.1.0
#11 0x0000726389ca4690 in PyRun_InteractiveOneFlags () from /lib64/libpython2.7.so.1.0
#12 0x0000726389ca487e in PyRun_InteractiveLoopFlags () from /lib64/libpython2.7.so.1.0
#13 0x0000726389ca4f0e in PyRun_AnyFileExFlags () from /lib64/libpython2.7.so.1.0
#14 0x0000726389cb5bdf in Py_Main () from /lib64/libpython2.7.so.1.0
#15 0x0000726388ed1555 in __libc_start_main (main=0x400640 <main>, argc=1, argv=0x7ffdadefef28, init=<optimized out>, fini=<optimized out>, rtld_fini=<optimized out>, stack_end=0x7ffdadefef18) at ../csu/libc-start.c:266
#16 0x000000000040066e in _start ()
```

```
strace -e trace=all -T -tt -p 13491
strace: Process 13491 attached
13:30:43.938900 write(1, "hello\n", 6)  = 6 <0.000032>
13:30:43.939029 write(1, "hello\n", 6)  = 6 <0.000034>
13:30:43.939124 write(1, "hello\n", 6)  = 6 <0.000014>
13:30:43.939176 write(1, "hello\n", 6)  = 6 <0.000009>
13:30:43.939212 write(1, "hello\n", 6)  = 6 <0.000022>
13:30:43.939258 write(1, "hello\n", 6)  = 6 <0.000009>
13:30:43.939294 write(1, "hello\n", 6)  = 6 <0.000011>
```
