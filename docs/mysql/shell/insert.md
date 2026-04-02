
```
#!/bin/bash
## source ./xxx.sql
# 脚本用于在每5000条INSERT语句后面添加一个COMMIT语句
# 在第一行插入关闭自动提交，并在最后一条INSERT后面添加COMMIT
# 使用方法: ./add_commit_to_sql.sh input.sql output.sql

# 检查输入参数
if [ "$#" -ne 2 ]; then
    echo "使用方法: $0 输入文件.sql 输出文件.sql"
    exit 1
fi

# 读取输入输出文件名
INPUT_FILE=$1
OUTPUT_FILE=$2

# 检查输入文件是否存在
if [ ! -f "$INPUT_FILE" ]; then
    echo "错误: 文件 '$INPUT_FILE' 不存在。"
    exit 1
fi

# 计数器
count=0

# 首先关闭自动提交
echo "SET autocommit=0;" > "$OUTPUT_FILE"
echo "START TRANSACTION;" >> "$OUTPUT_FILE"

# 读取输入文件并处理每一行
while IFS= read -r line
do
    # 将读取的行写入输出文件
    echo "$line" >> "$OUTPUT_FILE"

    # 检查当前行是否为INSERT语句
    if [[ "$line" == INSERT* ]]; then
        # 增加计数器
        ((count++))

        # 检查计数器是否达到5000
        if [ $count -eq 5000 ]; then
            # 写入COMMIT语句
            echo "COMMIT;" >> "$OUTPUT_FILE"

            # 重置计数器
            count=0

            # 开启新的事务
            echo "START TRANSACTION;" >> "$OUTPUT_FILE"
        fi
    fi
done < "$INPUT_FILE"

# 检查最后是否还需要一个COMMIT
if [ $count -ne 0 ]; then
    echo "COMMIT;" >> "$OUTPUT_FILE"
fi

# 打开自动提交
echo "SET autocommit=1;" >> "$OUTPUT_FILE"

echo "处理完成。"
```