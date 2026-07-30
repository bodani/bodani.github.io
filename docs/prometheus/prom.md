## 安装  prometheus

### 下载
```
wget https://github.com/prometheus/prometheus/releases/download/v3.13.1/prometheus-3.13.1.linux-amd64.tar.gz
tar zxf prometheus-3.13.1.linux-amd64.tar.gz
cp prometheus /usr/local/bin/
```
### 创建 prometheus 用户
```
sudo useradd --no-create-home --shell /bin/false prometheus
```
### 创建配置和数据目录
```
sudo mkdir -p /etc/prometheus /var/lib/prometheus
```
### 设置权限
```
sudo chown -R prometheus:prometheus /etc/prometheus /var/lib/prometheus
sudo chmod 755 /var/lib/prometheus
```
### 确保二进制文件可执行
```
sudo chmod +x /usr/local/bin/prometheus
```
### 配置服务
```
sudo tee /etc/systemd/system/prometheus.service << 'EOF'
[Unit]
Description=Prometheus Monitoring System
Documentation=https://prometheus.io/docs/introduction/overview/
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=prometheus
Group=prometheus
ExecStart=/usr/local/bin/prometheus \
    --config.file=/etc/prometheus/prometheus.yml \
    --storage.tsdb.path=/var/lib/prometheus \
    --web.config.file=/etc/prometheus/web.yml \
    --storage.tsdb.retention.time=15d \
    --web.console.templates=/usr/local/bin/consoles \
    --web.console.libraries=/usr/local/bin/console_libraries \
    --web.listen-address=0.0.0.0:9090 \
    --web.enable-lifecycle
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
StartLimitInterval=0

# 安全加固
NoNewPrivileges=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=/var/lib/prometheus
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

[Install]
WantedBy=multi-user.target
EOF
```

### 设置密码

生成密码
```python 
import bcrypt
password = b"you-password"
hashed = bcrypt.hashpw(password, bcrypt.gensalt(rounds=10))
print(hashed.decode())
```
配置密码
`cat /etc/prometheus/web.yml`
```
basic_auth_users:
  admin: '$2b$10$WcCJMnHSauik0mKSGZZxa.6tWWlNIAFVXpOejgArxr23o9KcFDZUy'
```

配置 prometheus
`cat  /etc/prometheus/prometheus.yml`
```
# my global config
global:
  scrape_interval: 15s # Set the scrape interval to every 15 seconds. Default is every 1 minute.
  evaluation_interval: 15s # Evaluate rules every 15 seconds. The default is every 1 minute.
  # scrape_timeout is set to the global default (10s).

# Alertmanager configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          # - alertmanager:9093

# Load rules once and periodically evaluate them according to the global 'evaluation_interval'.
rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

# A scrape configuration containing exactly one endpoint to scrape:
# Here it's Prometheus itself.
scrape_configs:
  # The job name is added as a label `job=<job_name>` to any timeseries scraped from this config.
  - job_name: "node"
    static_configs:
      - targets:
        - localhost:9100
        labels:
           app: "node"
  - job_name: "prometheus"
    # metrics_path defaults to '/metrics'
    # scheme defaults to 'http'.
    static_configs:
      - targets: ["localhost:9090"]
       # The label name is added as a label `label_name=<label_value>` to any timeseries scraped from this config.
        labels:
          app: "prometheus"
    basic_auth:
      username: admin
      password: xxxx
```

验证配置
```
promtool check config /etc/prometheus/prometheus.yml
```

### 服务管理 
```
# 重载 systemd

sudo systemctl daemon-reload

# 启动服务
sudo systemctl start prometheus

# 设置开机自启
sudo systemctl enable prometheus

# 查看状态
sudo systemctl status prometheus
```
## 安装 node_exporter

### 下载
```
wget https://github.com/prometheus/node_exporter/releases/download/v1.12.1/node_exporter-1.12.1.linux-amd64.tar.gz
tar zxf  node_exporter-1.12.1.linux-amd64.tar.gz
cp node_exporter /usr/local/bin/
```
### 创建 node_exporter 用户
```
sudo useradd --no-create-home --shell /bin/false node_exporter
```
```
sudo tee /etc/systemd/system/node_exporter.service << 'EOF'
[Unit]
Description=Node Exporter
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=node_exporter
Group=node_exporter
ExecStart=/usr/local/bin/node_exporter
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```
### 服务管理
```
sudo systemctl daemon-reload
sudo systemctl enable --now node_exporter
```

## postgres_exporter

### 下载
```
wget https://github.com/prometheus-community/postgres_exporter/releases/download/v0.20.1/postgres_exporter-0.20.1.linux-amd64.tar.gz
tar zxf postgres_exporter-0.20.1.linux-amd64.tar.gz
cp postgres_exporter-0.20.1.linux-amd64/postgres_exporter /usr/local/bin/
```

### 创建 postgres_exporter 用户
```
useradd -r -s /bin/false postgres_exporter
```
### 配置数据库
```
用户
-- 创建监控专用用户
CREATE USER postgres_exporter WITH LOGIN;

-- 授予内置监控角色（PG 10+）
GRANT pg_monitor TO postgres_exporter;

-- 可选：如果需要查 pg_stat_statements，确保该用户有权限
-- GRANT SELECT ON pg_stat_statements TO postgres_exporter;
修改
pg_hba.conf

local   all   all   peer
local   all   postgres_exporter   peer

systemctl reload postgresql
```
### 配置服务

自定义监控sql（可选）
```
mkdir /etc/postgres_exporter
```

```
cat > /etc/postgres_exporter/query.yaml << 'EOF'
pg_postmaster:
  query: "SELECT pg_postmaster_start_time as start_time_seconds from pg_postmaster_start_time()"
  master: true
  metrics:
   - start_time_seconds:
       usage: "GAUGE"
       description: "Time at which postmaster started"
EOF
```
配置服务
```
cat > /etc/systemd/system/postgres_exporter.service << 'EOF'
[Unit]
Description=Prometheus PostgreSQL Exporter
After=network.target

[Service]
Type=simple
Restart=always
RestartSec=5
User=postgres_exporter 
Group=postgres_exporter

# Use Unix socket connection 
Environment="DATA_SOURCE_NAME=postgresql:///postgres?host=/var/run/postgresql&user=postgres_exporter&sslmode=disable"
# Use Custom query 
# Environment="PG_EXPORTER_EXTEND_QUERY_PATH=/etc/postgres_exporter/query.yaml"
ExecStart=/usr/local/bin/postgres_exporter --collector.postmaster --web.listen-address=":9187"
NoNewPrivileges=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=/tmp

[Install]
WantedBy=multi-user.target
EOF
```

### 服务管理
```
systemctl daemon-reload
systemctl enable --now postgres_exporter
systemctl status postgres_exporter
```

### 验证
```
curl -s http://localhost:9187/metrics | grep pg_up
```
可参考

https://cloud.tencent.com/document/product/1416/111837

## 配置alert
```
https://samber.github.io/awesome-prometheus-alerts/rules/
```
### 验证
```
promtool check rules rules/pg.yaml
```

## alertmanager

### 下载
```
wget https://github.com/prometheus/alertmanager/releases/download/v0.33.1/alertmanager-0.33.1.linux-amd64.tar.gz

tar zxf alertmanager-0.33.1.linux-amd64.tar.gz

cp alertmanager /usr/local/bin/
cp amtool /usr/local/bin/
```

### 创建alertmanager 用户
```
sudo useradd --no-create-home --shell /bin/false alertmanager
```

### 创建配置和数据目录
```
sudo mkdir -p /etc/alertmanager /var/lib/alertmanager
```
```
cp alertmanager.yml /etc/alertmanager/
```

### 配置服务
```
sudo tee /etc/systemd/system/alertmanager.service << 'EOF'
[Unit]
Description=Alertmanager
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=alertmanager
Group=alertmanager
ExecStart=/usr/local/bin/alertmanager \
    --config.file=/etc/alertmanager/alertmanager.yml \
    --storage.path=/var/lib/alertmanager \
    --web.listen-address=0.0.0.0:9093
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### 服务管理
```
sudo chown -R alertmanager:alertmanager /etc/alertmanager /var/lib/alertmanager
sudo systemctl daemon-reload
sudo systemctl enable --now alertmanager
```

### 配置prometheus
```
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - localhost:9093
```
## grafana

### 下载
```
https://github.com/grafana/grafana/releases/download/v13.1.1/grafana_13.1.1_29761037902_linux_amd64.deb

apt-get install ./grafana.deb

systemctl status grafana-server
```
