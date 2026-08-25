#!/usr/bin/env python3
"""
极简版：从健康 ClickHouse 节点批量导出 Replicated*MergeTree 表的 CREATE TABLE（含 UUID）。
自动在前面加上 CREATE DATABASE IF NOT EXISTS。
"""
import argparse
import sys
from clickhouse_driver import Client

def main():
    p = argparse.ArgumentParser(description="导出 ReplicatedMergeTree 建表语句（保留 UUID 和宏）")
    p.add_argument("--host", required=True, help="健康节点地址")
    p.add_argument("--port", type=int, default=9000)
    p.add_argument("--user", default="default")
    p.add_argument("--password", default="")
    p.add_argument("--out", default="create_replicas.sql", help="输出 SQL 文件")
    p.add_argument("--databases", nargs="*", help="只导出指定库，空格分隔")
    p.add_argument("--exclude-databases", nargs="*", default=["system","information_schema","INFORMATION_SCHEMA"])
    args = p.parse_args()

    client = Client(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        send_receive_timeout=300
    )

    # 1. 查出所有 Replicated*MergeTree 表
    q = "SELECT database, name FROM system.tables WHERE engine LIKE 'Replicated%MergeTree%'"
    if args.databases:
        q += " AND database IN (" + ",".join(f"'{d}'" for d in args.databases) + ")"
    elif args.exclude_databases:
        q += " AND database NOT IN (" + ",".join(f"'{d}'" for d in args.exclude_databases) + ")"
    
    tables = client.execute(q)
    print(f"找到 {len(tables)} 张 ReplicatedMergeTree 表")

    # 2. 开启 UUID 显示
    try:
        client.execute("SET show_table_uuid_in_table_create_query_if_not_nil = 1")
    except Exception:
        pass

    # 3. 收集需要的数据库，去重
    databases = sorted(set(db for db, _ in tables))

    # 4. 先生成 CREATE DATABASE，再生成 CREATE TABLE
    out_lines = []
    
    for db in databases:
        out_lines.append(f"CREATE DATABASE IF NOT EXISTS `{db}`;")
    
    out_lines.append("")  # 空行分隔

    for db, table in tables:
        ddl = client.execute(f"SHOW CREATE TABLE `{db}`.`{table}`")[0][0]
        out_lines.append(f"-- {db}.{table}")
        out_lines.append(f"{ddl};")
        out_lines.append("")  # 空行

    # 5. 写入文件
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines))

    print(f"已写入 {args.out}，共 {len(tables)} 张表，涉及 {len(databases)} 个库")

if __name__ == "__main__":
    main()