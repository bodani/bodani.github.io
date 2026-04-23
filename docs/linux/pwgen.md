# pwgen - 密码生成工具

`pwgen` 是一个用于生成随机密码的命令行工具，可以生成易于记忆或完全随机的密码。

## 安装

### Debian/Ubuntu
```bash
sudo apt-get install pwgen
```

### RHEL/CentOS/Rocky
```bash
sudo yum install pwgen
# 或
sudo dnf install pwgen
```

### macOS
```bash
brew install pwgen
```

## 基本语法

```bash
pwgen [选项] [密码长度] [密码数量]
```

## 常用选项

| 选项 | 说明 |
|------|------|
| `-s` | 生成完全随机的密码（更安全，但难记忆） |
| `-n` | 密码中至少包含一个数字 |
| `-c` | 密码中至少包含一个大写字母 |
| `-y` | 密码中包含特殊符号 |
| `-B` | 排除容易混淆的字符（如 0 和 O，1 和 l） |
| `-1` | 每行只输出一个密码 |
| `-v` | 排除元音字母，避免生成有含义的单词 |

## 使用示例

### 生成一个 8 位随机密码
```bash
pwgen -s 8 1
```
输出示例：
```
Kx9#mP2q
```

### 生成 10 个 12 位的可发音密码
```bash
pwgen 12 10
```
输出示例：
```
oogheiphae7u aigheib9Eigh eihae5Thohl8 ohk7Eew8deix Ahshae1ohPho
yie4xohV5zoo xee4eeNge2ai xae9Chi3Eefi roh7Oow0phei Chohthe5su1E
```

### 生成包含数字和大写字母的密码
```bash
pwgen -nc 12 1
```

### 生成包含特殊字符的强密码
```bash
pwgen -syn 16 1
```

### 生成易于阅读（排除混淆字符）的密码
```bash
pwgen -B -s 12 1
```

## 实际应用场景

### 生成数据库用户密码
```bash
# 生成 16 位强密码
pwgen -s 16 1

# 生成包含特殊字符的密码
pwgen -sy 16 1
```

### 批量生成密码
```bash
# 生成 20 个 10 位密码
pwgen -s 10 20

# 每行一个密码，方便脚本处理
pwgen -s1 10 20
```

### 生成安全的服务密码
```bash
# 结合多种选项生成高强度密码
pwgen -sncB 20 1
```

## 脚本中使用示例

```bash
#!/bin/bash
# 生成随机密码并赋值给变量
PASSWORD=$(pwgen -s 16 1)
echo "生成的密码: $PASSWORD"

# 生成带特殊字符的密码
DB_PASS=$(pwgen -sy 20 1)
echo "数据库密码: $DB_PASS"
```

## 注意事项

1. **安全性**：使用 `-s` 选项生成的完全随机密码比默认可发音密码更安全
2. **密码长度**：建议生产环境使用至少 16 位以上的密码
3. **特殊字符**：某些系统或服务对特殊字符有限制，使用前请确认
4. **密码管理**：生成的密码建议使用密码管理工具妥善保存

## 替代工具

- `openssl rand -base64 16` - 使用 OpenSSL 生成随机字符串
- `tr -dc 'a-zA-Z0-9' < /dev/urandom | head -c 16` - 使用系统随机设备
- `uuidgen` - 生成 UUID 作为密码
