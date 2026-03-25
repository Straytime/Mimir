# Deploy Contract

本文档固定 Mimir v1 的部署合同，只覆盖当前架构已实现的部署基线：

- `apps/web` 部署到 `Vercel`
- `services/api` 部署到 `Railway`
- 前端浏览器直连后端 REST + SSE
- 不包含真实上线步骤、CI/CD 流水线、域名与 HTTPS 运维

发布前人工检查与待拍板决策见 [Release_Readiness_Checklist.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Release_Readiness_Checklist.md)。

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
- `report.pdf` 当前采用 `Python-Markdown(extra + sane_lists) -> sanitized HTML -> headless Chromium print-to-pdf`。
- Railway 不再只停留在“人工环境必须有 Chromium”的口头约束；`services/api/railpack.json` 是仓库内 provisioning source of truth，用于把 `chromium` 安装到最终镜像。
- 后端优先通过 `PATH` 发现 Chromium；若运行时路径不是标准位置，可用 `MIMIR_PDF_CHROMIUM_EXECUTABLE` 显式覆盖。

### 2.3 Production Required Env

必填：

- `MIMIR_PROVIDER_MODE=real`
- `MIMIR_DATABASE_URL` or Railway-injected `DATABASE_URL`
- `MIMIR_CORS_ALLOW_ORIGINS`
- `MIMIR_TASK_TOKEN_SECRET`
- `MIMIR_ACCESS_TOKEN_SECRET`
- `ZHIPU_API_KEY`
- `JINA_API_KEY`（optional；为空时 web_fetch 降级为免费无认证模式，受 RPM 限制）
- `E2B_API_KEY`

强烈建议：

- 挂载 Railway Volume，并使用 `RAILWAY_VOLUME_MOUNT_PATH`
  - 当前实现会自动把 artifact root 收敛到 `${RAILWAY_VOLUME_MOUNT_PATH}/mimir-artifacts`
  - 如果不想使用默认路径，可显式设置 `MIMIR_ARTIFACT_ROOT_DIR`
- 当 `python_interpreter` 需要稳定的中文图表输出时，使用自定义 E2B template，并通过 `MIMIR_E2B_TEMPLATE` 显式指向已发布的 template 名称
- `services/api/railpack.json` 必须随部署一起生效，以确保 `report.pdf` 的 Chromium runtime 被稳定 provision

### 2.4 Production Optional Env

可按需要覆盖：

- `MIMIR_LLM_PROVIDER_MODE`
- `MIMIR_WEB_SEARCH_PROVIDER_MODE`
- `MIMIR_WEB_FETCH_PROVIDER_MODE`
- `MIMIR_E2B_PROVIDER_MODE`
- `MIMIR_E2B_TEMPLATE`
- `MIMIR_PDF_CHROMIUM_EXECUTABLE`
- `MIMIR_ZHIPU_BASE_URL`
- `MIMIR_JINA_BASE_URL`
- `MIMIR_ZHIPU_TIMEOUT_SECONDS`
- `MIMIR_WEB_SEARCH_TIMEOUT_SECONDS`
- `MIMIR_WEB_FETCH_TIMEOUT_SECONDS`
- `MIMIR_E2B_REQUEST_TIMEOUT_SECONDS`
- `MIMIR_E2B_EXECUTION_TIMEOUT_SECONDS`
- `MIMIR_E2B_SANDBOX_TIMEOUT_SECONDS`
- `MIMIR_WRITER_MAX_ROUNDS`
- 全部 `MIMIR_ZHIPU_MODEL_*`
- `MIMIR_IP_QUOTA_LIMIT`
- `MIMIR_IP_QUOTA_WINDOW_HOURS`
- `MIMIR_ACCESS_TOKEN_TTL_MINUTES`
- `MIMIR_CLIENT_HEARTBEAT_TIMEOUT_SECONDS`
- `MIMIR_CLEANUP_SCAN_INTERVAL_SECONDS`

### 2.5 Production Artifact / Storage Contract

- 当前 artifact store 仍是本地文件系统实现，因此生产必须依赖 Railway Volume 或等价持久挂载目录。
- `markdown zip`、`pdf`、图片 artifact 都写入同一 artifact root。
- `report.pdf` 当前采用标准 `markdown / 受支持的 GFM 子集 -> HTML -> PDF` 导出路径，而不是手写 HTML 节点翻译器；实际渲染器为 headless Chromium。
- PDF HTML 在进入 Chromium 前必须先经过 allowlist sanitize，只保留导出所需标签、属性和安全 scheme。
- PDF 渲染用到的 artifact 图片资源会在导出层内联为受控数据 URI；主路径不再依赖 `--allow-file-access-from-files` 访问本地文件。
- Railway production 通过 `services/api/railpack.json` 的 `deploy.aptPackages=["chromium"]` 为最终镜像 provision Chromium；`MIMIR_PDF_CHROMIUM_EXECUTABLE` 只作为非标准路径 override。
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
- `JINA_API_KEY`（optional；为空时 web_fetch 降级为免费无认证模式，受 RPM 限制）
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
- `JINA_API_KEY`（optional；为空时 web_fetch 降级为免费无认证模式，受 RPM 限制）
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
- `MIMIR_WRITER_MAX_ROUNDS`（writer tool-call 轮次上限，默认 `5`）

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
