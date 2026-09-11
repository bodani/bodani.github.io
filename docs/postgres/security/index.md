# 安全管理

本节包含了 PostgreSQL 安全管理相关的文档。

数据库安全是数据保护的第一道防线，涵盖用户权限、认证方式、加密传输、数据加密等多个方面。

## 文档列表

- [角色管理](role-manager.md) - 用户角色与权限管理
- [连接认证](login_nopasswd.md) - 免密登录与 pg_hba.conf 配置
- [SSL 安全](ssl.md) - SSL 加密传输配置
- [预编译 SQL](prepare.md) - PREPARE 语句与 SQL 注入防护
- [只读配置](readonly.md) - 只读用户与只读事务配置
- [列级加密](pgcrypto.md) - pgcrypto 扩展与数据加密