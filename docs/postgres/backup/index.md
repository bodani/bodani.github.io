# 备份与恢复

本节包含了 PostgreSQL 数据库的备份与恢复相关文档。

完善的备份策略是数据安全的最后一道防线，需要根据业务 RPO/RTO 要求选择合适的备份方案。

## 文档列表

- [备份方案设计](index.md) - 备份策略概述
- [逻辑备份](logical-backup.md) - pg_dump 逻辑备份与恢复
- [物理备份](physical-backup.md) - 文件系统级物理备份
- [pgBackRest](pgbackrest.md) - 专业备份工具 pgBackRest 配置使用
- [WAL-G 备份](wal-g.md) - WAL-G 云原生备份工具
- [pgcopydb 迁移](pgcopydb.md) - pgcopydb 数据迁移工具
- [PITR 备份恢复](pitr.md) - 基于时间点的恢复配置
- [备份恢复脚本](reback.md) - 自动化备份脚本实现
- [超级用户备份配置](reback_supper_user.md) - 备份专用超级用户配置
