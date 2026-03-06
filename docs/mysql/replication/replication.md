MySQL 主从复制搭建运维文档

本文档详细介绍了在 MySQL 8.0 版本下，如何在 Ubuntu Linux 服务器上搭建主从复制环境。文档涵盖以下三种方式：

    原始方式（基于二进制日志的复制）

    GTID 方式（基于全局事务标识符的复制）

    Clone 插件方式（MySQL 8.0 新增的克隆插件）

每种方式均考虑主库已有历史数据的情况，并提供详细的操作步骤。
环境准备

    操作系统：Ubuntu 20.04 LTS

    MySQL 版本：8.0.x

    主库 IP：192.168.1.100

    从库 IP：192.168.1.101

    复制用户：repl

    复制用户密码：repl_password

1.  原始方式：基于二进制日志的复制
    1.1 主库配置

        编辑 MySQL 配置文件：

            打开配置文件：
            bash
            复制

            sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf

            添加以下配置：
            ini
            复制

            [mysqld]
            server_id = 1
            log_bin = /var/log/mysql/mysql-bin.log
            binlog_format = ROW

            重启 MySQL 服务：
            bash
            复制

            sudo systemctl restart mysql

        创建复制用户：

            登录 MySQL：
            bash
            复制

            mysql -u root -p

            创建用户并授权：
            sql
            复制

            CREATE USER 'repl'@'%' IDENTIFIED BY 'repl_password';
            GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';
            FLUSH PRIVILEGES;

        备份主库数据：

            使用 mysqldump 备份数据：
            bash
            复制

            mysqldump --all-databases --master-data=2 --single-transaction > master_dump.sql

            将备份文件传输到从库：
            bash
            复制

            scp master_dump.sql user@192.168.1.101:/tmp/

1.2 从库配置

    编辑 MySQL 配置文件：

        打开配置文件：
        bash
        复制

        sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf

        添加以下配置：
        ini
        复制

        [mysqld]
        server_id = 2
        relay_log = /var/log/mysql/mysql-relay-bin.log
        read_only = 1

        重启 MySQL 服务：
        bash
        复制

        sudo systemctl restart mysql

    恢复主库数据：

        登录 MySQL：
        bash
        复制

        mysql -u root -p < /tmp/master_dump.sql

    配置主库连接信息：

        登录 MySQL：
        bash
        复制

        mysql -u root -p

        查看备份文件中的 MASTER_LOG_FILE 和 MASTER_LOG_POS：
        bash
        复制

        head -n 50 /tmp/master_dump.sql | grep "CHANGE MASTER TO"

        配置主库信息：
        sql
        复制

        CHANGE MASTER TO
        MASTER_HOST='192.168.1.100',
        MASTER_USER='repl',
        MASTER_PASSWORD='repl_password',
        MASTER_LOG_FILE='mysql-bin.000001',  -- 替换为实际值
        MASTER_LOG_POS=1234;                 -- 替换为实际值

    启动复制：
    sql
    复制

    START SLAVE;

    检查复制状态：
    sql
    复制

    SHOW SLAVE STATUS\G

        确保 Slave_IO_Running 和 Slave_SQL_Running 都为 Yes。

2.  GTID 方式：基于全局事务标识符的复制
    2.1 主库配置

        编辑 MySQL 配置文件：

            添加以下配置：
            ini
            复制

            [mysqld]
            server_id = 1
            log_bin = /var/log/mysql/mysql-bin.log
            binlog_format = ROW
            gtid_mode = ON
            enforce_gtid_consistency = ON

            重启 MySQL 服务：
            bash
            复制

            sudo systemctl restart mysql

        创建复制用户：

            同原始方式。

        备份主库数据：

            使用 mysqldump 备份数据：
            bash
            复制

            mysqldump --all-databases --set-gtid-purged=ON --single-transaction > master_dump.sql

            将备份文件传输到从库：
            bash
            复制

            scp master_dump.sql user@192.168.1.101:/tmp/

2.2 从库配置

    编辑 MySQL 配置文件：

        添加以下配置：
        ini
        复制

        [mysqld]
        server_id = 2
        relay_log = /var/log/mysql/mysql-relay-bin.log
        read_only = 1
        gtid_mode = ON
        enforce_gtid_consistency = ON

        重启 MySQL 服务：
        bash
        复制

        sudo systemctl restart mysql

    恢复主库数据：

        同原始方式。

    配置主库连接信息：

        登录 MySQL：
        bash
        复制

        mysql -u root -p

        配置主库信息：
        sql
        复制

        CHANGE MASTER TO
        MASTER_HOST='192.168.1.100',
        MASTER_USER='repl',
        MASTER_PASSWORD='repl_password',
        MASTER_AUTO_POSITION=1;

    启动复制：
    sql
    复制

    START SLAVE;

    检查复制状态：
    sql
    复制

    SHOW SLAVE STATUS\G

        确保 Slave_IO_Running 和 Slave_SQL_Running 都为 Yes。

3.  Clone 插件方式：基于克隆插件的复制
    3.1 主库配置

        安装 Clone 插件：

            登录 MySQL：
            bash
            复制

            mysql -u root -p

            安装插件：
            sql
            复制

            INSTALL PLUGIN clone SONAME 'mysql_clone.so';

        创建复制用户：

            同原始方式。

3.2 从库配置

    安装 Clone 插件：

        登录 MySQL：
        bash
        复制

        mysql -u root -p

        安装插件：
        sql
        复制

        INSTALL PLUGIN clone SONAME 'mysql_clone.so';

    克隆主库数据：

        登录 MySQL：
        bash
        复制

        mysql -u root -p

        执行克隆操作：
        sql
        复制

        CLONE INSTANCE FROM 'repl'@'192.168.1.100' IDENTIFIED BY 'repl_password';

    配置主库连接信息：

        同 GTID 方式。

    启动复制：
    sql
    复制

    START SLAVE;

    检查复制状态：
    sql
    复制

    SHOW SLAVE STATUS\G

        确保 Slave_IO_Running 和 Slave_SQL_Running 都为 Yes。

## 前提

复制要求所有的表都有主键

```
SELECT
    t.table_schema,
    t.table_name
FROM
    information_schema.tables t
LEFT JOIN
    information_schema.statistics s
ON
    t.table_schema = s.table_schema
    AND t.table_name = s.table_name
    AND s.non_unique = 0
WHERE
    t.table_schema NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
    AND t.table_type = 'BASE TABLE'
    AND s.index_name IS NULL
ORDER BY
    t.table_schema,
    t.table_name;

```

使用clone , 8.0.17 开始 推出了 clone 插件
