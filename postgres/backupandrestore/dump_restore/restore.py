#!/usr/bin/env python3
import yaml, os, glob, subprocess

cfg = yaml.safe_load(open("pg_conf.yaml"))
tgt = cfg["target"]
os.environ["PGPASSWORD"] = tgt["password"]

# 取工具路径，未配置则走默认
tools = cfg.get("tools", {})
psql = tools.get("psql", "psql")
pg_restore = tools.get("pg_restore", "pg_restore")

bak = cfg["backup"]["base_dir"]
print(f"=== restore from: {bak} ===")

# 1. 恢复业务角色和权限
print("=== restore globals ===")
subprocess.run([
    psql, "-h", tgt["host"], "-p", str(tgt["port"]), "-U", tgt["user"],
    "-d", "postgres", "-v", "ON_ERROR_STOP=0", "-f", os.path.join(bak, "globals.sql"),
])

# 2. 恢复业务数据库
print("=== restore databases ===")
for f in sorted(glob.glob(os.path.join(bak, "*.dump"))):
    db = os.path.basename(f).replace(".dump", "")
    print(f"  -> {db}")
    subprocess.run([
        pg_restore, "-h", tgt["host"], "-p", str(tgt["port"]), "-U", tgt["user"],
        "-C", "-d", "postgres", f,
    ])

print("\ndone")