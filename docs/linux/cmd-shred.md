# shred - 安全删除文件与清除敏感数据

`shred` 是一个用于安全覆盖文件内容的命令行工具，通过多次覆写文件数据来防止数据恢复，常用于安全删除包含敏感信息的文件。

## 基本语法

```bash
shred [选项] 文件...
```

## 常用选项

| 选项 | 说明 |
|------|------|
| `-n` | 设置覆写次数（默认 3 次） |
| `-u` | 覆写后删除文件 |
| `-v` | 显示操作进度 |
| `-z` | 最后一次用零覆写，隐藏删除痕迹 |
| `-f` | 强制修改权限以允许写入 |
| `-x` | 不删除文件，仅覆写内容 |

## 工作原理

`shred` 通过向文件写入随机数据多次覆写原有内容：

1. **多次覆写**：默认进行 3 轮随机数据覆写
2. **可选清零**：最后一次可选择用零覆盖，减少痕迹
3. **可选删除**：覆写后可直接删除文件（`-u`）

## 使用示例

### 安全删除单个文件

```bash
shred -u -v sensitive_file.txt
```

输出示例：
```
shred: sensitive_file.txt: pass 1/3 (random)...
shred: sensitive_file.txt: pass 2/3 (random)...
shred: sensitive_file.txt: pass 3/3 (random)...
shred: sensitive_file.txt: removing
shred: sensitive_file.txt: renamed to 000000000000
shred: 000000000000: renamed to 0000000000
shred: 0000000000: renamed to 00000
shred: 00000: renamed to 0
shred: sensitive_file.txt: removed
```

### 指定覆写次数后删除

```bash
# 进行 7 次覆写，最后清零，然后删除
shred -n 7 -z -u secret.doc
```

### 批量安全删除文件

```bash
# 删除目录下所有日志文件
shred -u -v /var/log/app/*.log
```

### 安全擦除整块磁盘

```bash
# ⚠️ 谨慎操作：这会永久删除磁盘上所有数据
shred -n 3 -v -z /dev/sdb
```

### 覆写但不删除（清空文件内容）

```bash
# 清空文件内容但保留空文件
shred -x old_data.csv
```

## 实际应用场景

### 安全删除密钥文件

```bash
# 删除 SSH 私钥时确保安全
shred -u -n 7 ~/.ssh/old_id_rsa
```

### 清理临时敏感数据

```bash
# 脚本中清理临时密码文件
TEMP_PASS=$(mktemp)
echo "MyP@ssw0rd" > "$TEMP_PASS"
# 使用密码后安全删除
shred -u -z "$TEMP_PASS"
```

### 丢弃旧硬盘前的数据擦除

```bash
# 彻底擦除整个分区
sudo shred -n 3 -v -z /dev/sda1
```

## 注意事项

1. **文件系统限制**：
   - 对日志文件系统（ext4、XFS、Btrfs 等）有效，但某些场景可能有残留
   - 无法安全删除 raid、快照、备份中的副本
   - 不支持擦除文件系统的元数据信息

2. **SSD 与闪存**：
   - SSD 由于 wear-leveling（磨损均衡）机制，`shred` 效果有限
   - 建议使用 SSD 内置的安全擦除（Secure Erase）命令

3. **重要提示**：
   - `shred` **不能**保证已存在备份、缓存副本或快照中的数据被清除
   - 加密磁盘上的文件解密前被覆写可能无效

## 替代工具

| 工具 | 适用场景 |
|------|---------|
| `rm -P` | BSD 系统的安全删除 |
| `srm` (secure-delete) | 更全面的安全删除套件 |
| `wipe` | 支持更多擦除模式 |
| `scrub` | 磁盘级安全擦除工具 |
| ATA Secure Erase | SSD 专用底层擦除 |
