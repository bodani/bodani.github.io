#!/usr/bin/env python3
"""
清理 ClickHouse 集群中残留的 replica（ZK 里 active=0 的残留节点）。
"""
import argparse
import sys
import json
from clickhouse_driver import Client

def get_replicated_tables(client, include_dbs=None, exclude_dbs=None):
    q = "SELECT database, name FROM system.tables WHERE engine LIKE 'Replicated%MergeTree%'"
    if include_dbs:
        q += " AND database IN (" + ",".join(f"'{d}'" for d in include_dbs) + ")"
    elif exclude_dbs:
        q += " AND database NOT IN (" + ",".join(f"'{d}'" for d in exclude_dbs) + ")"
    return client.execute(q)

def get_replica_status(client, db, table):
    """返回 (replica_name, replica_is_active_map)"""
    rows = client.execute(
        f"SELECT replica_name, replica_is_active FROM system.replicas "
        f"WHERE database = '{db}' AND table = '{table}'"
    )
    if not rows:
        return None, {}
    return rows[0][0], rows[0][1]

def parse_inactive_replicas(active_map):
    """
    replica_is_active 格式: {'name1':1,'name2':0,...}
    返回所有 value=0 的 replica_name 列表
    """
    inactive = []
    # ClickHouse 返回的可能是字符串形式的 map，需要解析
    if isinstance(active_map, str):
        # 去掉花括号，按逗号分割
        content = active_map.strip("{}")
        for item in content.split(","):
            item = item.strip()
            if not item:
                continue
            # 格式: 'name':0 或 'name':1
            if ":" in item:
                key_val = item.split(":", 1)
                name = key_val[0].strip().strip("'\"")
                val = key_val[1].strip()
                if val == "0":
                    inactive.append(name)
    elif isinstance(active_map, dict):
        for name, val in active_map.items():
            if val == 0 or val is False:
                inactive.append(name)
    return inactive

def main():
    p = argparse.ArgumentParser(description="清理 ClickHouse 残留 replica")
    p.add_argument("--host", required=True, help="健康节点地址")
    p.add_argument("--port", type=int, default=9000)
    p.add_argument("--user", default="default")
    p.add_argument("--password", default="")
    p.add_argument("--replica-name", default=None, help="只清理指定 replica 名（如 helmbroker-ck01-shard0-2）")
    p.add_argument("--databases", nargs="*", help="只扫描指定库")
    p.add_argument("--exclude-databases", nargs="*", default=["system","information_schema","INFORMATION_SCHEMA"])
    p.add_argument("--dry-run", action="store_true", default=True, help="默认只打印命令，不执行")
    p.add_argument("--execute", action="store_true", help="真正执行 DROP REPLICA")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    if not args.execute:
        print(">>> 当前是 --dry-run 模式，只打印要执行的命令。加 --execute 才会真正清理。")
        print()

    client = Client(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        send_receive_timeout=300
    )

    tables = get_replicated_tables(client, args.databases, args.exclude_databases)
    print(f"扫描到 {len(tables)} 张 ReplicatedMergeTree 表")

    # 收集所有需要清理的 (db, table, replica_name)
    to_clean = []

    for db, table in tables:
        try:
            my_replica, active_map = get_replica_status(client, db, table)
            if not active_map:
                continue

            inactive = parse_inactive_replicas(active_map)

            # 如果指定了 --replica-name，只处理匹配的
            if args.replica_name:
                if args.replica_name in inactive:
                    to_clean.append((db, table, args.replica_name))
                    if args.verbose:
                        print(f"[{db}.{table}] 发现残留: {args.replica_name}")
            else:
                for rep in inactive:
                    to_clean.append((db, table, rep))
                    if args.verbose:
                        print(f"[{db}.{table}] 发现残留: {rep}")

        except Exception as e:
            print(f"ERROR 扫描 {db}.{table}: {e}", file=sys.stderr)

    if not to_clean:
        print("没有发现残留 replica，无需清理。")
        return

    print(f"\n共发现 {len(to_clean)} 处残留，涉及 {len(set(r for _,_,r in to_clean))} 个 replica")

    # 去重：同一个 replica 在同一张表上只清理一次
    to_clean = list(set(to_clean))
    to_clean.sort()

    print("\n将要执行的命令：")
    for db, table, rep in to_clean:
        cmd = f"SYSTEM DROP REPLICA '{rep}' FROM TABLE `{db}`.`{table}`;"
        print(f"  {cmd}")

    if not args.execute:
        print(f"\n>>> 以上命令未执行。确认无误后加 --execute 参数重新运行。")
        return

    print(f"\n>>> 开始执行清理...")
    success = 0
    failed = 0
    for db, table, rep in to_clean:
        cmd = f"SYSTEM DROP REPLICA '{rep}' FROM TABLE `{db}`.`{table}`"
        try:
            client.execute(cmd)
            print(f"  ✓ {db}.{table} -> {rep}")
            success += 1
        except Exception as e:
            print(f"  ✗ {db}.{table} -> {rep}: {e}")
            failed += 1 

    print(f"\n清理完成: 成功 {success}, 失败 {failed}")

if __name__ == "__main__":
    main()