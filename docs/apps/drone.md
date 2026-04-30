kind: pipeline
type: docker
name: full-cicd

# ==========================================
# 全局配置：定义所有步骤共享的卷和代理
# ==========================================
volumes:
  # 关键优化：缓存 node_modules，避免每次重复下载
  - name: node_cache
    host:
      path: /var/cache/drone/node_modules/${DRONE_REPO_NAME}
  
  # Docker 层缓存，加速镜像构建
  - name: docker_cache
    host:
      path: /var/cache/drone/docker

# 全局环境变量
environment:
  NPM_REGISTRY: https://registry.npmmirror.com
  DOCKER_REGISTRY: registry.company.com
  APP_NAME: user-service

steps:
  # ==========================================
  # 阶段 1：依赖安装与缓存
  # ==========================================
  - name: install-deps
    image: node:18-alpine
    volumes:
      - name: node_cache
        path: /drone/src/node_modules  # 挂载缓存卷到容器
    commands:
      # 配置国内镜像加速（企业内网场景）
      - npm config set registry $NPM_REGISTRY
      # ci 比 install 更严格，会严格按照 package-lock.json 安装
      - npm ci --prefer-offline --no-audit
      # 缓存验证：显示依赖树，便于问题排查
      - npm list --depth=0 || true
    # 失败策略：如果依赖安装失败，立即终止整个流水线
    failure: ignore  # 生产环境应设为 false

  # ==========================================
  # 阶段 2：代码质量门禁（并行执行）
  # ==========================================
  # 2.1 静态代码检查
  - name: lint
    image: node:18-alpine
    volumes:
      - name: node_cache
        path: /drone/src/node_modules
    commands:
      - npm run lint:ci  # 使用 ci 模式，发现错误立即退出非零状态码
      - npm run lint:markdown  # 检查文档格式
    depends_on:
      - install-deps  # 明确依赖：必须等 install 完成

  # 2.2 安全审计（依赖漏洞扫描）
  - name: security-audit
    image: node:18-alpine
    volumes:
      - name: node_cache
        path: /drone/src/node_modules
    commands:
      # 检查高危漏洞，如果有 high/critical 级别漏洞，构建失败
      - npm audit --audit-level=high --production
      # 或使用更专业的 snyk/sonarqube
      - echo "Scanning with SonarQube..."
    depends_on:
      - install-deps

  # ==========================================
  # 阶段 3：测试阶段（并行执行，但依赖质量门禁）
  # ==========================================
  - name: unit-test
    image: node:18-alpine
    environment:
      NODE_ENV: test
      # 从 Drone Secrets 注入测试数据库连接（不在代码中暴露）
      TEST_DB_URL:
        from_secret: test_database_url
    volumes:
      - name: node_cache
        path: /drone/src/node_modules
    commands:
      # 初始化测试数据库 schema
      - npx knex migrate:latest --env test
      # 运行单元测试并生成覆盖率报告
      - npm run test:unit -- --coverage --reporter=junit --outputFile=junit.xml
      # 覆盖率阈值检查（硬性指标：必须 > 80%）
      - npx nyc check-coverage --lines 80 --functions 80 --branches 70
    # 产物收集：测试报告供后续步骤或 Drone UI 展示
    when:
      status:
        - success
        - failure  # 即使失败也收集报告，便于调试

  # 集成测试：需要依赖外部服务（如 Redis、MySQL）
  - name: integration-test
    image: node:18-alpine
    environment:
      REDIS_URL: redis:6379  # 引用下方 services 定义的服务
      DB_HOST: mysql
    volumes:
      - name: node_cache
        path: /drone/src/node_modules
    commands:
      - npm run test:integration
    # 只有 main 分支才跑集成测试（节约资源）
    when:
      branch:
        - main
        - release/*
    depends_on:
      - unit-test  # 单元测试通过才跑集成测试，快速失败

  # ==========================================
  # 阶段 4：构建产物（Docker 镜像）
  # ==========================================
  - name: build-image
    image: plugins/docker  # 官方 Docker 插件，优化过的构建环境
    volumes:
      - name: docker_cache
        path: /var/lib/docker  # 挂载 Docker 层缓存
    settings:
      repo: ${DOCKER_REGISTRY}/${DRONE_REPO_OWNER}/${APP_NAME}
      # 标签策略：分支名 + Commit SHA + latest（主干）
      tags:
        - ${DRONE_COMMIT_SHA:0:8}  # 短 SHA，唯一标识
        - ${DRONE_BRANCH//\//-}    # 分支名（替换 / 为 -，避免非法字符）
        - latest
      dockerfile: Dockerfile
      context: .
      # 构建参数传递给 Dockerfile
      build_args:
        - NPM_REGISTRY=${NPM_REGISTRY}
        - BUILD_TIME=${DRONE_BUILD_CREATED}
        - GIT_COMMIT=${DRONE_COMMIT_SHA}
      # 镜像仓库认证（从 Secrets 读取）
      username:
        from_secret: docker_username
      password:
        from_secret: docker_password
      # 镜像扫描：构建完成后立即检查 CVE
      scan: true
      scan_image: aquasec/trivy:latest
    when:
      status:
        - success
      # 只有代码检查和测试都通过才构建
      event:
        - push
        - tag
    depends_on:
      - lint
      - security-audit
      - unit-test

  # ==========================================
  # 阶段 5：部署到 Drycc（多环境策略）
  # ==========================================
  
  # 5.1 开发环境：任何 feature 分支自动部署
  - name: deploy-dev
    image: drycc/cli:latest  # 假设的 Drycc 客户端镜像
    environment:
      DRYCC_SERVER: https://drycc-dev.company.com
      DRYCC_TOKEN:
        from_secret: drycc_dev_token
    commands:
      - drycc login $DRYCC_SERVER --token=$DRYCC_TOKEN
      # 配置应用（如果不存在则创建）
      - drycc apps:create ${APP_NAME} || true
      # 设置环境变量（数据库连接等）
      - drycc config:set NODE_ENV=development LOG_LEVEL=debug -a ${APP_NAME}
      # 关键：拉取刚才构建的镜像部署
      - drycc pull ${DOCKER_REGISTRY}/${DRONE_REPO_OWNER}/${APP_NAME}:${DRONE_COMMIT_SHA:0:8} -a ${APP_NAME}
      # 健康检查：等待 Pod Ready
      - dryce ps:wait -a ${APP_NAME} --timeout=120s
      # 通知飞书/钉钉（可选）
      - echo "部署成功：${DRONE_COMMIT_MESSAGE}"
    when:
      branch:
        - develop
        - feature/*
      event:
        - push
    depends_on:
      - build-image
    # 失败重试策略：网络抖动时自动重试
    retry:
      max: 2
      delay: 10s

  # 5.2 生产环境：main 分支且需要人工审批（使用 promote 事件）
  - name: deploy-prod
    image: drycc/cli:latest
    environment:
      DRYCC_SERVER: https://drycc.company.com
      DRYCC_TOKEN:
        from_secret: drycc_prod_token
      SLACK_WEBHOOK:
        from_secret: slack_webhook
    commands:
      - drycc login $DRYCC_SERVER --token=$DRYCC_TOKEN
      # 生产使用固定应用名
      - drycc config:set NODE_ENV=production LOG_LEVEL=warn -a ${APP_NAME}
      # 金丝雀发布：先部署 1 个实例验证
      - drycc ps:scale web=1 -a ${APP_NAME}
      - drycc pull ${DOCKER_REGISTRY}/${DRONE_REPO_OWNER}/${APP_NAME}:${DRONE_COMMIT_SHA:0:8} -a ${APP_NAME}
      #  smoke test（冒烟测试）
      - curl -f https://${APP_NAME}.company.com/health || (echo "健康检查失败，回滚..." && drycc releases:rollback -a ${APP_NAME} && exit 1)
      # 全量发布
      - drycc ps:scale web=3 -a ${APP_NAME}
      # 发送通知
      - |
        curl -X POST $SLACK_WEBHOOK -H 'Content-type: application/json' \
        --data '{"text":"🚀 '${APP_NAME}' 已发布到生产环境\n版本：'${DRONE_COMMIT_SHA:0:8}'\n提交者：'${DRONE_COMMIT_AUTHOR}'"}'
    when:
      # 关键：只在手动触发 promote 事件时执行，防止误操作
      event:
        - promote
      target:
        - production
    depends_on:
      - build-image

  # ==========================================
  # 阶段 6：清理与通知（无论成败都执行）
  # ==========================================
  - name: notify
    image: plugins/slack  # 官方 Slack 插件
    settings:
      webhook: https://hooks.slack.com/services/xxx
      channel: devops-alerts
      template: |
        {{#success build.status}}
          ✅ 构建成功: {{repo.name}}@{{build.branch}}
          提交: {{truncate build.commit 8}} by {{build.author}}
          耗时: {{since build.started}}
        {{else}}
          ❌ 构建失败: {{repo.name}}@{{build.branch}}
          步骤: {{build.failedSteps}} 失败
          日志: {{build.link}}
        {{/success}}
    when:
      status:
        - success
        - failure  # 无论成败都通知
    depends_on:
      - deploy-dev
      - deploy-prod

# ==========================================
# 服务依赖：集成测试需要的外部组件
# ==========================================
services:
  - name: mysql
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: test
      MYSQL_DATABASE: test_db
    # 健康检查：确保 MySQL 启动后再执行集成测试
    commands:
      - echo "等待 MySQL 就绪..."

  - name: redis
    image: redis:7-alpine

# ==========================================
# 触发器：定义什么情况下运行此 Pipeline
# ==========================================
trigger:
  branch:
    - main
    - develop
    - feature/*
    - release/*
  event:
    - push
    - pull_request
    - tag
    - promote  # 手动部署事件
