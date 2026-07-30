# 客户端故障转移

利用 PostgreSQL libpq 的多主机连接与 `target_session_attrs`，在不引入 VIP 及中间路由节点的情况下，实现应用侧故障转移。

## 多主机连接

PostgreSQL libpq 支持多主机配置，同时支持 `target_session_attrs` 主机角色判断。配置了多个主机时，会按顺序尝试连接，直到获取到成功的连接为止。

结合数据库自动 HA 软件，可实现应用系统层级的高可用。

## 连接成功判断

- 成功建立连接
- `target_session_attrs` 配置

`read-write` 含义：连接到的节点为可读写。如果连接的是从节点（只读），则不能连接成功。根据 `show transaction_read_only;` 判断节点的可读写性。

## 具体示例

### psql

```bash
psql 'postgres://192.168.6.15:65432,192.168.6.16:65432/postgres?target_session_attrs=read-write'
```

### Python

```python
import psycopg2

conn = psycopg2.connect(
    database="postgres",
    host="192.168.6.15,192.168.6.16",
    user="postgres",
    password="sqlite123",
    port="5432",
    target_session_attrs="read-write",
)
cur = conn.cursor()
cur.execute("select pg_is_in_recovery(),now(),inet_server_addr()")
row = cur.fetchone()
```
