# wal 日志数量计算

PostgreSQL WAL日志文件数量计算工具

【功能描述】
    计算两个 PostgreSQL WAL (Write-Ahead Log) 文件之间的数量差值。
    用于估算 WAL 归档文件数量、监控 WAL 生成量、规划存储空间等场景。


【适用场景】
    - 计算主备库之间需要同步的 WAL 文件数量
    - 评估 PITR (Point-In-Time Recovery) 需要保留的 WAL 文件规模
    - 监控 WAL 归档目录文件增长情况
    - 规划 WAL 存储空间容量

## 计算文件

```
cat > wal_count.py << 'EOF'
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PostgreSQL WAL日志文件数量计算工具
"""

from __future__ import print_function
import sys
import os


def wal_to_numeric(filename):
    clean = filename.strip().lower()
    clean = os.path.basename(clean)
    
    if len(clean) == 24:
        wal_hex = clean[8:]
    elif len(clean) == 16:
        wal_hex = clean
    else:
        raise ValueError("WAL文件名长度无效: '%s' (应为24或16位十六进制)" % filename)
    
    try:
        log_id = int(wal_hex[:8], 16)
        seg_id = int(wal_hex[8:], 16)
    except ValueError:
        raise ValueError("WAL文件名包含无效字符: '%s'" % filename)
    
    return log_id * 256 + seg_id


def format_number(n):
    return "{:,}".format(n)


def print_usage():
    print("PostgreSQL WAL日志文件数量计算工具")
    print("")
    print("用法: python wal_count.py <start_wal> <end_wal>")
    print("示例: python wal_count.py 0000000500007D4700000033 0000000500007D48000000F4")


def main():
    args = sys.argv[1:]
    
    if not args or args[0] in ('-h', '--help', '-?'):
        print_usage()
        return 0
    
    if len(args) < 2:
        print("错误: 需要两个WAL文件名参数")
        return 1
    
    start_file = args[0]
    end_file = args[1]
    
    try:
        start_num = wal_to_numeric(start_file)
        end_num = wal_to_numeric(end_file)
    except ValueError as e:
        print("错误: %s" % str(e))
        return 2
    
    diff = end_num - start_num
    
    print("=" * 60)
    print("PostgreSQL WAL 文件数量计算结果")
    print("=" * 60)
    print("")
    print("起始WAL: %s" % start_file)
    print("结束WAL: %s" % end_file)
    print("")
    print("起始序号: %s" % format_number(start_num))
    print("结束序号: %s" % format_number(end_num))
    print("")
    print("-" * 60)
    print("间隔数量: %s (从起始到结束)" % format_number(diff))
    
    if diff >= 0:
        print("包含首尾: %s (间隔 + 1)" % format_number(diff + 1))
    else:
        print("警告: 结束WAL序号小于起始WAL序号！")
    
    print("-" * 60)
    
    return 0 if diff >= 0 else 1


if __name__ == "__main__":
    sys.exit(main() or 0)
EOF

chmod +x wal_count.py
```

## 示例
```
$ python3 wal_count.py 0000000500007D4700000033 0000000500007D48000000F4
============================================================
PostgreSQL WAL 文件数量计算结果
============================================================

起始WAL: 0000000500007D4700000033
结束WAL: 0000000500007D48000000F4

起始序号: 8,210,227
结束序号: 8,210,676

------------------------------------------------------------
间隔数量: 449  (从起始到结束)
包含首尾: 450  (间隔 + 1)
------------------------------------------------------------
```