# Deploy Contract

本文档固定 Mimir v1 的部署合同，只覆盖当前架构已实现的部署基线：

- `apps/web` 部署到 `Vercel`
- `services/api` 部署到 `Railway`
- 前端浏览器直连后端 REST + SSE
- 不包含真实上线步骤、CI/CD 流水线、域名与 HTTPS 运维

## 1. 生产拓扑

```text
Browser
  -> Vercel / apps/web
  -> Railway / services/api
  -> Railway PostgreSQL
  -> Railway Volume (artifact store)
```

约束：

- 前端不引入 BFF，不代理后端 token。
- 后端必须显式配置 CORS，允许 Vercel Web Origin 访问。
- 下载和 artifact URL 都是短期 `access_token` 绑定资源，不能被 CDN 长期缓存。

## 2. Backend Contract (`services/api` -> Railway)

### 2.1 Railway Service Settings

- Source Repo Root: 仓库根目录
- Root Directory: `/services/api`
- Config File Path: `/services/api/railway.json`
  - Railway 官方文档说明 config file 不跟随 Root Directory 自动寻找；monorepo 场景需要显式写绝对路径。
- Healthcheck Path: `/api/v1/health`

### 2.2 Build / Deploy Commands

- Build Command: `uv sync --frozen --no-dev`
- Pre-deploy Command: `uv run --no-sync alembic upgrade head`
- Start Command: `uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port ${PORT}`

说明：

- `uvicorn` 已作为生产依赖声明，避免 `--no-dev` 构建后缺少启动器。
- Start command 依赖 Railway 注入的 `PORT`。
- `/api/v1/health` 同时作为 Railway liveness probe 和发布后最小检查。

### 2.3 Production Required Env

必填：

- `MIMIR_PROVIDER_MODE=real`
- `MIMIR_DATABASE_URL` or Railway-injected `DATABASE_URL`
- `MIMIR_CORS_ALLOW_ORIGINS`
- `MIMIR_TASK_TOKEN_SECRET`
- `MIMIR_ACCESS_TOKEN_SECRET`
- `ZHIPU_API_KEY`
- `JINA_API_KEY`
- `E2B_API_KEY`

强烈建议：

- 挂载 Railway Volume，并使用 `RAILWAY_VOLUME_MOUNT_PATH`
  - 当前实现会自动把 artifact root 收敛到 `${RAILWAY_VOLUME_MOUNT_PATH}/mimir-artifacts`
  - 如果不想使用默认路径，可显式设置 `MIMIR_ARTIFACT_ROOT_DIR`

### 2.4 Production Optional Env

可按需要覆盖：

- `MIMIR_LLM_PROVIDER_MODE`
- `MIMIR_WEB_SEARCH_PROVIDER_MODE`
- `MIMIR_WEB_FETCH_PROVIDER_MODE`
- `MIMIR_E2B_PROVIDER_MODE`
- `MIMIR_ZHIPU_BASE_URL`
- `MIMIR_JINA_BASE_URL`
- `MIMIR_ZHIPU_TIMEOUT_SECONDS`
- `MIMIR_WEB_SEARCH_TIMEOUT_SECONDS`
- `MIMIR_WEB_FETCH_TIMEOUT_SECONDS`
- `MIMIR_E2B_REQUEST_TIMEOUT_SECONDS`
- `MIMIR_E2B_EXECUTION_TIMEOUT_SECONDS`
- `MIMIR_E2B_SANDBOX_TIMEOUT_SECONDS`
- 全部 `MIMIR_ZHIPU_MODEL_*`
- `MIMIR_IP_QUOTA_LIMIT`
- `MIMIR_IP_QUOTA_WINDOW_HOURS`
- `MIMIR_ACCESS_TOKEN_TTL_MINUTES`
- `MIMIR_CLIENT_HEARTBEAT_TIMEOUT_SECONDS`
- `MIMIR_CLEANUP_SCAN_INTERVAL_SECONDS`

### 2.5 Production Artifact / Storage Contract

- 当前 artifact store 仍是本地文件系统实现，因此生产必须依赖 Railway Volume 或等价持久挂载目录。
- `markdown zip`、`pdf`、图片 artifact 都写入同一 artifact root。
- 由于 Railway Volume 与 PostgreSQL 不共享事务，删除仍按补偿一致性执行：
  1. DB 标记 `cleanup_pending`
  2. 删除 artifact / sandbox / 临时文件
  3. 删除业务记录
- `access_token` 默认短期有效；刷新方式仍是重新 `GET /api/v1/tasks/{task_id}`，不能把旧下载 URL 长期缓存到外部系统。

### 2.6 CORS Contract

- `MIMIR_CORS_ALLOW_ORIGINS` 必须是逗号分隔的显式白名单。
- 至少包含正式 Vercel 域名，例如 `https://mimir-web.vercel.app`
- 当前实现不支持自动放行任意 Vercel Preview 域名；如需预览联调，必须把对应 preview URL 显式加入白名单。

## 3. Frontend Contract (`apps/web` -> Vercel)

### 3.1 Vercel Project Settings

- Root Directory: `apps/web`
- Framework Preset: `Next.js`
- Config File: `apps/web/vercel.json`
- Build Command: `pnpm build`
- Runtime Start: 使用 Vercel 默认 Next.js 运行时，不自定义 Node server

### 3.2 Production Required Env

必填：

- `NEXT_PUBLIC_API_BASE_URL`

规则：

- 正式环境应指向 Railway API 对外基址，例如 `https://mimir-api.up.railway.app`
- 不要依赖“未配置时回退到 `window.location.origin`”的 same-origin 逻辑；该回退只适合同域反向代理，不符合当前 Vercel/Railway 分离部署架构。

### 3.3 Production Optional Env

当前无额外前端 runtime 必填项。

## 4. Environment Matrix

### 4.1 Local Stub

后端：

- `MIMIR_PROVIDER_MODE=stub`
- `MIMIR_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:5432/postgres`
- `MIMIR_CORS_ALLOW_ORIGINS=http://localhost:3000`

前端：

- `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`

### 4.2 Local Real

后端：

- `MIMIR_PROVIDER_MODE=real`
- 或按需设置 `MIMIR_LLM_PROVIDER_MODE` / `MIMIR_WEB_SEARCH_PROVIDER_MODE` / `MIMIR_WEB_FETCH_PROVIDER_MODE` / `MIMIR_E2B_PROVIDER_MODE`
- `ZHIPU_API_KEY`
- `JINA_API_KEY`
- `E2B_API_KEY`
- `MIMIR_DATABASE_URL` 指向本地 smoke 数据库
- 可选 `MIMIR_ARTIFACT_ROOT_DIR=/tmp/mimir-artifacts-real`

前端：

- `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`

### 4.3 Production Required

后端：

- `MIMIR_PROVIDER_MODE=real`
- `MIMIR_DATABASE_URL` or `DATABASE_URL`
- `MIMIR_CORS_ALLOW_ORIGINS`
- `MIMIR_TASK_TOKEN_SECRET`
- `MIMIR_ACCESS_TOKEN_SECRET`
- `ZHIPU_API_KEY`
- `JINA_API_KEY`
- `E2B_API_KEY`

前端：

- `NEXT_PUBLIC_API_BASE_URL`

### 4.4 Production Optional

后端：

- `MIMIR_ARTIFACT_ROOT_DIR`
- `MIMIR_LLM_PROVIDER_MODE`
- `MIMIR_WEB_SEARCH_PROVIDER_MODE`
- `MIMIR_WEB_FETCH_PROVIDER_MODE`
- `MIMIR_E2B_PROVIDER_MODE`
- 全部 provider timeout、model、quota、TTL、cleanup 扫描相关 env

前端：

- 当前无

## 5. Local Validation Commands

### Backend Dry-run

```bash
cd services/api
UV_CACHE_DIR=/tmp/uv-cache uv sync --frozen --no-dev --dry-run
PORT=18000 UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
```

### Frontend Production Build

```bash
cd apps/web
NEXT_PUBLIC_API_BASE_URL=https://api.example.com pnpm build
```

### Config Static Validation

```bash
python -m json.tool services/api/railway.json >/dev/null
python -m json.tool apps/web/vercel.json >/dev/null
```

## 6. Known Release Boundaries

- 本任务包只固定 deploy config 和 env contract，不代表已经真实上线。
- 当前 backend artifact store 仍是本地文件系统实现；生产可靠性依赖 Railway Volume，而不是对象存储。
- 当前没有 CI/CD 发布流水线，也没有自动同步 Vercel preview domain 到 backend CORS 白名单。
- 当前没有把真实 writer 报告生成完整跑到公网环境；真实 E2B 已具备 baseline，但仍需独立发布前 smoke。
