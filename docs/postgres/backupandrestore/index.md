# 备份与恢复方案

本节包含了 PostgreSQL 数据库备份与恢复相关的文档和工具。

完善的备份策略是数据安全的最后一道防线，需要根据业务 RPO/RTO 要求选择合适的备份方案。

## 备份方案文档

- [备份方案设计](../backup/index.md) - 备份策略概述
- [逻辑备份](../backup/logical-backup.md) - pg_dump 逻辑备份
- [物理备份](../backup/physical-backup.md) - 文件系统级物理备份
- [pgBackRest](../backup/pgbackrest.md) - 专业备份工具 pgBackRest
- [WAL-G 备份](../backup/wal-g.md) - WAL-G 云原生备份工具
- [pgcopydb 迁移](../backup/pgcopydb.md) - pgcopydb 数据迁移工具
- [PITR 备份恢复](../backup/pitr.md) - 时间点恢复配置
- [备份恢复脚本](../backup/reback.md) - 自动化备份脚本
- [超级用户备份配置](../backup/reback_supper_user.md) - 备份专用超级用户配置

## 迁移工具

- [pg_migrate.py](pg_migrate.py) - PostgreSQL 迁移脚本
- [依赖说明](requestments.txt) - 迁移脚本依赖包
