# MySQL Public Key Retrieval 错误

## 问题
Java应用连接MySQL 8.0+数据库时出现公钥检索错误：
```
java.sql.SQLNonTransientConnectionException: Public Key Retrieval is not allowed
```
应用无法通过JDBC建立数据库连接，影响业务正常运行。

## 分析
该错误是由于MySQL 8.0默认认证方式变更导致的兼容性问题：

1. **认证插件变更**：MySQL 8.0默认使用`caching_sha2_password`插件，取代了旧版的`mysql_native_password`
2. **安全限制**：JDBC驱动默认禁止公钥检索作为安全防护措施
3. **驱动兼容性**：旧版MySQL JDBC驱动不完全支持新的认证机制
4. **SSL配置影响**：当SSL未启用时，公钥检索成为必要的认证步骤

## 解决
1. **修改连接参数**（推荐）：

```
   jdbc:mysql://localhost:3306/dbname?allowPublicKeyRetrieval=true&useSSL=false
```

2. **更改用户认证方式**：

```
ALTER USER 'username'@'host' IDENTIFIED WITH mysql_native_password BY 'password';
```

3. **升级JDBC驱动**：

```
   <dependency> <!-- Maven配置 -->
       <groupId>mysql</groupId>
       <artifactId>mysql-connector-java</artifactId>
       <version>8.0.30+</version>
   </dependency>
```

4. **启用SSL连接**（安全推荐）：

```
jdbc:mysql://localhost:3306/dbname?useSSL=true&requireSSL=true
```

**最佳实践**：生产环境建议使用方案1或4，配合SSL确保连接安全，同时保持MySQL 8.0的新认证优势。