#!/usr/bin/env python3
import yaml, re, os, subprocess

cfg = yaml.safe_load(open("pg_conf.yaml"))
src, bk = cfg["source"], cfg["backup"]
os.environ["PGPASSWORD"] = src["password"]

# 取工具路径，未配置则走默认
tools = cfg.get("tools", {})
pg_dumpall = tools.get("pg_dumpall", "pg_dumpall")
pg_dump = tools.get("pg_dump", "pg_dump")
psql = tools.get("psql", "psql")

outdir = bk["base_dir"]
os.makedirs(outdir, exist_ok=True)

# 1. globals：只要一行里出现任何系统角色名，整行跳过
print("=== backup globals ===")
r = subprocess.run(
    [pg_dumpall, "-h", src["host"], "-p", str(src["port"]), "-U", src["user"], "-g"],
    capture_output=True, text=True,
)

roles = set(bk["system_roles"])
pat = re.compile(r'\b(?:' + '|'.join(re.escape(r) for r in roles) + r')\b')

lines = [ln for ln in r.stdout.splitlines() if not pat.search(ln)]
open(os.path.join(outdir, "globals.sql"), "w").write("\n".join(lines))

# 2. 获取业务数据库列表
skip = ",".join(f"'{x}'" for x in bk["skip_dbs"])
sql = f"SELECT datname FROM pg_database WHERE datistemplate=false AND datname NOT IN ({skip}) ORDER BY datname"
r = subprocess.run(
    [psql, "-h", src["host"], "-p", str(src["port"]), "-U", src["user"], "-d", "postgres", "-Atc", sql],
    capture_output=True, text=True,
)
dbs = [x for x in r.stdout.strip().split("\n") if x]

# 3. 备份业务库
print("=== backup databases ===")
for db in dbs:
    f = os.path.join(outdir, f"{db}.dump")
    subprocess.run(
        [pg_dump, "-h", src["host"], "-p", str(src["port"]), "-U", src["user"], "-C", "-Fc", db, "-f", f],
        check=True,
    )
    print(f"  {db} -> {f}")

print(f"\ndone: {outdir}")