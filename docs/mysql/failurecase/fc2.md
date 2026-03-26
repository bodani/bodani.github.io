# MySQL TLS版本不匹配

## 问题
客户端连接MySQL数据库时出现TLS协议错误：
```
Error: 2026 (HY000): connecting to destination failed with TLS error: error:0A00010B:SSL routines::wrong version number
```
多个客户端连接尝试均失败，无法建立安全的数据库连接。

## 分析
该错误表明客户端与MySQL服务器之间的TLS/SSL协议版本不兼容。主要原因为：
1. **版本不匹配**：MySQL 8.0+默认要求TLSv1.2+，而客户端可能使用旧版本TLSv1.0或TLSv1.1
2. **配置冲突**：服务器SSL配置限制了可接受的TLS版本范围
3. **组件过时**：客户端或服务器的OpenSSL库版本过旧，不支持新协议
4. **强制SSL**：服务器配置了强制SSL连接，但客户端协议栈不兼容

## 解决
1. **升级OpenSSL**：`sudo apt-get update && sudo apt-get install --only-upgrade openssl`
2. **调整MySQL配置**：修改`my.cnf`，设置`tls_version = TLSv1.2,TLSv1.3`
3. **指定客户端参数**：连接时使用`--tls-version=TLSv1.2 --ssl-mode=REQUIRED`
4. **测试诊断**：使用`openssl s_client -connect server:3306 -tls1_2 -starttls mysql`验证
5. **重启服务**：`sudo systemctl restart mysql`使配置生效

执行后验证连接：`mysql --ssl-mode=REQUIRED --tls-version=TLSv1.2 -h host -u user -p`