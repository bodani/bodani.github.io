# 避免 needrestart 自动重启 PostgreSQL

Ubuntu 24.04 上升级 `libc6` 等共享库后，`needrestart` 可能自动执行 `systemctl restart postgresql@16-main.service`，导致数据库在未确认的情况下重启。

## 现象

系统升级（尤其是 `libc6` 相关包）完成后，`needrestart` 检测到依赖该库的进程，并自动执行类似：

```bash
systemctl restart postgresql@16-main.service
```

PostgreSQL 实例被意外重启，业务出现短暂不可用。

## 原因

Ubuntu 较新版本默认集成 `needrestart`。`apt` / `unattended-upgrades` 在升级共享库后，会调用 `needrestart` 扫描仍占用旧库的进程，并按策略对对应 systemd 单元执行 `restart`。

PostgreSQL 进程链接 `libc`，因此 `libc6` 升级后极易被判定为「需要重启」。对数据库而言，服务重启意味着连接中断、事务失败，生产环境通常应在维护窗口内人工操作，而不是由包管理器自动触发。

## 排查确认

```bash
# 服务重启记录
journalctl -u postgresql@16-main.service --since "2 days ago"

# needrestart / apt 相关日志
journalctl --since "2 days ago" | grep -i needrestart
grep -i needrestart /var/log/apt/history.log /var/log/apt/term.log 2>/dev/null

# 确认本机已安装 needrestart
dpkg -l needrestart
```

## 处理办法

禁止 `needrestart` 对 PostgreSQL 相关 systemd 服务自动重启。在 `/etc/needrestart/conf.d/` 下增加覆盖配置：

```bash
sudo mkdir -p /etc/needrestart/conf.d
echo '$nrconf{override_rc}{qr(^postgresql.*\.service$)} = 0;' | sudo tee /etc/needrestart/conf.d/postgresql.conf
```

说明：

- `override_rc` 中值为 `0` 表示对该匹配的服务不自动重启（仅提示或忽略，取决于全局模式）
- 正则 `^postgresql.*\.service$` 可覆盖 `postgresql@16-main.service`、`postgresql.service` 等常见单元名

配置生效后，再升级 `libc6` 时不应再自动 `systemctl restart` PostgreSQL。

## 注意事项

- 生产库建议将 `needrestart` 全局模式设为交互或仅列出，避免静默重启关键服务；在 `/etc/needrestart/needrestart.conf` 中关注 `$nrconf{restart}`（`i` 交互 / `l` 仅列出 / `a` 自动）
- 使用 `unattended-upgrades` 时风险更高：无人值守升级叠加自动重启
- 配置排除后，若仍需让 PostgreSQL 加载新共享库，应在维护窗口内手动重启实例
