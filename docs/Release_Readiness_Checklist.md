# Release Readiness Checklist

本文档用于 Mimir v1 发布前的最终人工检查。

适用范围：

- `apps/web -> Vercel`
- `services/api -> Railway`
- 当前 R1 基线

不包含：

- CI/CD 发布流水线配置
- 真正上线执行记录
- 产品功能变更

配套文档：

- [Deploy_Contract.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Deploy_Contract.md)
- [Architecture.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Architecture.md)
- [OpenAPI_v1.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/OpenAPI_v1.md)
- [Execution_Log.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Execution_Log.md)

## 1. 使用方式

发布负责人应按以下顺序执行：

1. 先完成“待拍板决策”。
2. 再逐项完成“发布前检查项”。
3. 最后确认“发布后观察项”和回滚联系人已明确。

建议在本次发布记录中附带：

- 发布负责人
- 执行日期
- Web 部署版本
- API 部署版本
- 最终 go / no-go 结论

## 2. 待拍板决策

以下项目当前仍属上线决策，不应假装已经定案。

| 决策项 | 当前约束 / 已知事实 | 建议 | 状态 |
| --- | --- | --- | --- |
| 生产 API 域名 | `apps/web` 必须显式设置 `NEXT_PUBLIC_API_BASE_URL` 指向 Railway API | 确认唯一正式 API 域名 | `待确认` |
| 生产 Web 域名 | 后端 CORS 必须显式白名单正式 Web Origin | 确认唯一正式 Web 域名 | `待确认` |
| 是否支持 Vercel Preview 访问 API | 当前后端只支持显式白名单，不会自动放行任意 preview 域名 | 默认不支持；若需要，手工加入白名单并限制范围 | `待确认` |
| CORS 白名单策略 | 当前实现是逗号分隔的显式白名单 | 推荐“正式域名固定白名单 + preview 按需显式加入” | `待确认` |
| production 是否允许 `stub` fallback | 当前 deploy contract 把 production required 定为 `MIMIR_PROVIDER_MODE=real` | 推荐不允许 production fallback 到 `stub` | `待确认` |
| Railway Volume 的 artifact 保留策略 | 当前 artifact store 依赖 Railway Volume，cleanup 采用补偿一致性 | 确认 Volume 挂载目录、故障后人工保留期、手动清理负责人 | `待确认` |

## 3. 发布前检查项

### 3.1 文档与合同

- [ ] 已阅读 [Deploy_Contract.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Deploy_Contract.md)
- [ ] 已阅读本清单并完成“待拍板决策”
- [ ] 已确认本次发布不引入新的 API / SSE 契约漂移
- [ ] 已确认不依赖 test-only 注入、mock server 或本地 smoke hack

### 3.2 Backend Railway 配置

- [ ] Railway Service Root Directory 已设为 `/services/api`
- [ ] Railway Config File Path 已设为 `/services/api/railway.json`
- [ ] Build Command 与仓库合同一致：`uv sync --frozen --no-dev`
- [ ] Pre-deploy Command 与仓库合同一致：`uv run --no-sync alembic upgrade head`
- [ ] Start Command 与仓库合同一致：`uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port ${PORT}`
- [ ] Healthcheck Path 已设为 `/api/v1/health`
- [ ] Railway PostgreSQL 已绑定到 API 服务
- [ ] Railway Volume 已挂载到 API 服务

### 3.3 Frontend Vercel 配置

- [ ] Vercel Project Root Directory 已设为 `apps/web`
- [ ] Vercel Framework Preset 为 `Next.js`
- [ ] 构建命令与仓库合同一致：`pnpm build`
- [ ] `NEXT_PUBLIC_API_BASE_URL` 已填入正式 API 基址
- [ ] 已确认生产不依赖 same-origin fallback

### 3.4 环境变量完整性

Backend required：

- [ ] `MIMIR_PROVIDER_MODE=real`
- [ ] `MIMIR_DATABASE_URL` 或 `DATABASE_URL`
- [ ] `MIMIR_CORS_ALLOW_ORIGINS`
- [ ] `MIMIR_TASK_TOKEN_SECRET`
- [ ] `MIMIR_ACCESS_TOKEN_SECRET`
- [ ] `ZHIPU_API_KEY`
- [ ] `JINA_API_KEY`
- [ ] `E2B_API_KEY`

Backend recommended：

- [ ] `RAILWAY_VOLUME_MOUNT_PATH` 已存在，或显式设置 `MIMIR_ARTIFACT_ROOT_DIR`
- [ ] 所有 `MIMIR_ZHIPU_MODEL_*` 已确认是否沿用默认 `glm-5`
- [ ] timeout / quota / cleanup 相关 env 已按生产期望确认

Frontend required：

- [ ] `NEXT_PUBLIC_API_BASE_URL`

### 3.5 数据库与迁移

- [ ] 目标数据库连接正确指向生产实例，而不是本地 smoke / test DB
- [ ] `alembic upgrade head` 已在目标环境成功执行
- [ ] 发布前已确认不存在未应用 migration
- [ ] 发布后如需回滚，已明确回滚负责人和数据库回滚策略

### 3.6 健康检查与基础连通性

- [ ] `GET /api/v1/health` 在目标环境返回 `200`
- [ ] 返回体包含 `status=ok`
- [ ] Web 能访问 API 基址
- [ ] Web 到 API 的 CORS preflight 正常
- [ ] SSE `GET /api/v1/tasks/{task_id}/events` 在生产域名组合下可连接

### 3.7 Provider 与密钥

- [ ] 智谱 key 已配置
- [ ] Jina key 已配置
- [ ] E2B key 已配置
- [ ] 已确认生产日志不会打印完整密钥、token、完整 prompt 或完整网页正文
- [ ] 已确认 production 不会误切到 `stub`

### 3.8 Token / 安全

- [ ] `MIMIR_TASK_TOKEN_SECRET` 与 `MIMIR_ACCESS_TOKEN_SECRET` 已为生产独立随机值
- [ ] 未使用默认开发 secret
- [ ] 已确认下载 / artifact URL 依赖短期 `access_token`
- [ ] 已确认 `access_token_invalid -> GET /tasks/{id} -> refresh URL` 的客户端恢复路径仍成立

### 3.9 Artifact / Download

- [ ] Railway Volume 可写
- [ ] artifact root 目录存在且权限正确
- [ ] `markdown.zip`、`report.pdf`、图片 artifact 的文件流能从 Volume 读取
- [ ] 已确认 CDN / 代理层不会缓存带 `access_token` 的下载 URL
- [ ] 已确认 artifact 清理失败时会进入 `cleanup_pending` 补偿

### 3.10 Cleanup / 终态

- [ ] 已确认 cleanup worker 会持续扫描 `cleanup_pending`
- [ ] 已确认 `task.expired` 后进入清理
- [ ] 已确认 `task.failed` 后进入清理
- [ ] 已确认 `task.terminated` 后进入清理
- [ ] 已确认 E2B sandbox 会在 revision 完成、失败、终止或过期时销毁

### 3.11 Feedback Revision

- [ ] 已确认 `POST /feedback` 仅在 `awaiting_feedback + delivered` 可用
- [ ] 已确认 feedback 提交后会创建新 revision，而不是覆盖旧 revision
- [ ] 已确认旧搜集结果会复用，新 revision 的 `collect_agent_calls_used` 会归零

### 3.12 Real Provider Smoke 证据

- [ ] 已有一条真实 LLM + `web_search` + `web_fetch` smoke 记录
- [ ] 已有一条真实 E2B baseline smoke 记录
- [ ] 若发布前再次做人工 smoke，已准备 heartbeat 保活，避免 collection 阶段误触发 `heartbeat_timeout`
- [ ] 已确认任务进入 `collecting` 且持续超过 1 个 heartbeat interval 时，前端仍会持续 `POST /heartbeat` 直到终态
- [ ] 已记录本次发布使用的 smoke 日期与执行人

### 3.13 Go / No-Go

- [ ] 上述必填项全部完成
- [ ] “待拍板决策”全部已定案
- [ ] 发布负责人给出 `go`

若任一项未完成，结论应为 `no-go`。

## 4. 发布后观察项

上线后建议至少观察一轮完整研究任务，重点看以下信号。

### 4.1 风控与重试

- [ ] 智谱 LLM 是否出现 `1301`
- [ ] `web_search` 是否出现 `1301`
- [ ] 是否出现异常重试过多、单任务耗时显著拉长
- [ ] 是否出现 provider 失败但错误语义不明确的情况

### 4.2 终态分布

- [ ] `task.failed` 是否异常升高
- [ ] `task.terminated` 是否异常升高
- [ ] `task.expired` 是否异常升高
- [ ] 若升高，是否集中在某个 phase 或 provider

### 4.3 下载与 artifact

- [ ] 是否出现 `401 access_token_invalid` 后无法通过 `GET /tasks/{id}` 刷新恢复
- [ ] 是否出现 artifact 文件已删但 DB 仍存在，或反之
- [ ] 是否出现 PDF / ZIP 生成成功但下载失败

### 4.4 生命周期

- [ ] 是否出现 heartbeat 超时误杀
- [ ] 是否出现 disconnect 后任务未终止
- [ ] 是否出现 cleanup_pending 长时间堆积
- [ ] 是否出现 feedback 后 revision 切换异常

## 5. 发布负责人填写区

| 项目 | 结果 |
| --- | --- |
| 发布负责人 |  |
| 执行日期 |  |
| Web 域名 |  |
| API 域名 |  |
| 是否支持 Preview 访问 API |  |
| CORS 白名单策略 |  |
| 是否允许 production stub fallback |  |
| Railway Volume artifact 保留策略 |  |
| 最终结论 (`go` / `no-go`) |  |
| 备注 |  |
