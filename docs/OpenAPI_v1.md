# Mimir OpenAPI v1

## 1. 文档目的

本文档是 Mimir v1 后端 API 的正式契约草案，基于以下文档收敛而来：

- [PRD 0.3](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Mimir_v1.0.0_prd_0.3.md)
- [Architecture.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Architecture.md)

目标：

1. 为前后端联调提供稳定接口契约。
2. 为后端 `contract tests`、前端 mock、SSE 事件消费逻辑提供统一基线。
3. 为后续 machine-readable OpenAPI YAML/JSON 生成提供源文档。

说明：

- 本文档是 human-readable contract，不是最终的 OpenAPI YAML。
- 进入实施阶段后，应使用 FastAPI + Pydantic model 生成实际 OpenAPI 文档，并用 contract tests 对齐本文档。

## 2. API 设计原则

### 2.1 基本约定

- Base path: `/api/v1`
- 默认请求/响应格式：`application/json; charset=utf-8`
- 时间字段统一使用 ISO 8601，带时区偏移，例如 `2026-03-13T14:35:18+08:00`
- 所有 ID 使用 opaque string，不暴露数据库主键
- 所有非文件响应默认返回 `Cache-Control: no-store`

### 2.2 ID 命名约定

| 资源 | 前缀 | 示例 |
| --- | --- | --- |
| Task | `tsk_` | `tsk_01J1ABC...` |
| Revision | `rev_` | `rev_01J1XYZ...` |
| SubTask | `sub_` | `sub_01J1QWE...` |
| Tool Call | `call_` | `call_01J1RTY...` |
| Artifact | `art_` | `art_01J1UIO...` |
| Request | `req_` | `req_01J1PAS...` |
| Trace | `trc_` | `trc_01J1DFG...` |

### 2.3 鉴权模型

#### Task Token

- 创建任务时返回一次 `task_token`
- 仅服务端保存其哈希值
- 除下载/图片资源外，所有任务相关接口都使用：

```http
Authorization: Bearer {task_token}
```

#### Access Token

- 用于 markdown zip / PDF / 图片等二进制或 `<img>` 资源访问
- 通过 query parameter 传递：

```text
?access_token=...
```

- `access_token` 必须短期有效，且过期时间不得晚于任务 `expires_at`
- `access_token` 应绑定 `task_id`、资源类型、资源范围与过期时间

生命周期约定：

1. 首次获取通过 `artifact.ready`、`report.completed` 事件和 `GET /api/v1/tasks/{task_id}` 的 `delivery` 字段返回。
2. 若前端发现 `access_token` 过期，应重新调用 `GET /api/v1/tasks/{task_id}` 获取新的下载/制品 URL。
3. v1 不提供单独的 access token 刷新端点。
4. 单个 access token 的建议 TTL 为 `10 分钟`，但实际有效期取 `min(10 分钟, task.expires_at - now)`。

### 2.4 请求追踪

客户端可选传入：

```http
X-Request-ID: req_client_123
```

服务端必须在响应头中返回：

```http
X-Request-ID: req_01J...
X-Trace-ID: trc_01J...
```

约束：

- 每个 HTTP 请求有唯一 `request_id`
- 每个 Task 生命周期内有稳定的 `trace_id`

## 3. 资源模型

### 3.1 Task

代表单次研究会话的完整生命周期。

### 3.2 Revision

代表 Task 内的一轮研究版本：

- `revision_number = 1` 表示首轮研究
- `revision_number >= 2` 表示基于反馈生成的新版本

### 3.3 Artifact

代表 writer 阶段产生的图片等文件制品。

## 4. 通用 Schema

## 4.1 枚举

### TaskStatus

```text
running | awaiting_user_input | awaiting_feedback | terminated | failed | expired | purged
```

### TaskPhase

```text
clarifying | analyzing_requirement | planning_collection | collecting | summarizing_collection | merging_sources | preparing_outline | writing_report | delivered | processing_feedback
```

### ClarificationMode

```text
natural | options
```

### OutputFormat

```text
general | research_report | business_report | academic_paper | deep_article | guide | shopping_recommendation
```

### FreshnessRequirement

```text
high | normal
```

### AvailableAction

```text
submit_clarification | submit_feedback | download_markdown | download_pdf
```

### RevisionStatus

```text
in_progress | completed | failed | terminated
```

## 4.2 ErrorResponse

```json
{
  "error": {
    "code": "resource_busy",
    "message": "当前已有研究任务在执行，请稍后再试。",
    "detail": {},
    "request_id": "req_01J...",
    "trace_id": "trc_01J..."
  }
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `error.code` | string | 是 | 稳定错误码 |
| `error.message` | string | 是 | 面向调用方的简要描述 |
| `error.detail` | object | 是 | 附加结构化错误细节，默认 `{}` |
| `error.request_id` | string | 是 | 本次请求 ID |
| `error.trace_id` | string | 否 | 若已绑定任务，则返回任务 trace ID |

错误码全集：

- `resource_busy`
- `ip_quota_exceeded`
- `invalid_task_state`
- `validation_error`
- `risk_control_triggered`
- `upstream_service_error`
- `task_not_found`
- `task_token_invalid`
- `access_token_invalid`

## 4.3 TaskSnapshot

```json
{
  "task_id": "tsk_01J...",
  "status": "running",
  "phase": "clarifying",
  "active_revision_id": "rev_01J...",
  "active_revision_number": 1,
  "clarification_mode": "natural",
  "created_at": "2026-03-13T14:30:00+08:00",
  "updated_at": "2026-03-13T14:30:05+08:00",
  "expires_at": null,
  "available_actions": []
}
```

## 4.4 RevisionSummary

```json
{
  "revision_id": "rev_01J...",
  "revision_number": 1,
  "revision_status": "in_progress",
  "started_at": "2026-03-13T14:30:00+08:00",
  "finished_at": null,
  "requirement_detail": null
}
```

说明：

- `revision_status` 是 Revision 自身状态，不等于 Task 级 `status`
- `requirement_detail` 仅在需求分析完成后可用
- 该字段允许为空，避免接口在不同 phase 下返回结构不一致

## 4.5 RequirementDetail

```json
{
  "research_goal": "分析中国 AI 搜索产品的竞争格局与机会",
  "domain": "互联网 / AI 产品",
  "requirement_details": "偏商业报告，关注中国市场，重点覆盖近两年变化，输出语言为中文。",
  "output_format": "business_report",
  "freshness_requirement": "high",
  "language": "zh-CN"
}
```

## 4.6 ClarificationQuestionSet

```json
{
  "questions": [
    {
      "question_id": "q_1",
      "question": "这次研究更偏向哪个方向？",
      "options": [
        { "option_id": "o_1", "label": "行业现状与趋势" },
        { "option_id": "o_2", "label": "主要参与者与格局" },
        { "option_id": "o_3", "label": "商业机会与风险" },
        { "option_id": "o_auto", "label": "自动" }
      ]
    }
  ]
}
```

## 4.7 ArtifactSummary

```json
{
  "artifact_id": "art_01J...",
  "filename": "chart_market_share.png",
  "mime_type": "image/png",
  "url": "/api/v1/tasks/tsk_01J.../artifacts/art_01J...?access_token=***",
  "access_expires_at": "2026-03-13T15:00:00+08:00"
}
```

## 4.8 DeliverySummary

```json
{
  "revision_id": "rev_01J...",
  "revision_number": 1,
  "word_count": 6800,
  "artifact_count": 1,
  "markdown_zip_url": "/api/v1/tasks/tsk_01J.../downloads/markdown.zip?access_token=***",
  "pdf_url": "/api/v1/tasks/tsk_01J.../downloads/report.pdf?access_token=***",
  "artifacts": [
    {
      "artifact_id": "art_01J...",
      "filename": "chart_market_share.png",
      "mime_type": "image/png",
      "url": "/api/v1/tasks/tsk_01J.../artifacts/art_01J...?access_token=***",
      "access_expires_at": "2026-03-13T15:00:00+08:00"
    }
  ]
}
```

## 4.9 TaskDetailResponse

```json
{
  "task_id": "tsk_01J...",
  "snapshot": {
    "task_id": "tsk_01J...",
    "status": "awaiting_feedback",
    "phase": "delivered",
    "active_revision_id": "rev_01J...",
    "active_revision_number": 1,
    "clarification_mode": "natural",
    "created_at": "2026-03-13T14:30:00+08:00",
    "updated_at": "2026-03-13T14:55:00+08:00",
    "expires_at": "2026-03-13T15:25:00+08:00",
    "available_actions": ["submit_feedback", "download_markdown", "download_pdf"]
  },
  "current_revision": {
    "revision_id": "rev_01J...",
    "revision_number": 1,
    "revision_status": "completed",
    "started_at": "2026-03-13T14:30:00+08:00",
    "finished_at": "2026-03-13T14:55:00+08:00",
    "requirement_detail": {
      "research_goal": "分析中国 AI 搜索产品的竞争格局与机会",
      "domain": "互联网 / AI 产品",
      "requirement_details": "偏商业报告，关注中国市场，重点覆盖近两年变化，输出语言为中文。",
      "output_format": "business_report",
      "freshness_requirement": "high",
      "language": "zh-CN"
    }
  },
  "delivery": {
    "revision_id": "rev_01J...",
    "revision_number": 1,
    "word_count": 6800,
    "artifact_count": 1,
    "markdown_zip_url": "/api/v1/tasks/tsk_01J.../downloads/markdown.zip?access_token=***",
    "pdf_url": "/api/v1/tasks/tsk_01J.../downloads/report.pdf?access_token=***",
    "artifacts": [
      {
        "artifact_id": "art_01J...",
        "filename": "chart_market_share.png",
        "mime_type": "image/png",
        "url": "/api/v1/tasks/tsk_01J.../artifacts/art_01J...?access_token=***",
        "access_expires_at": "2026-03-13T15:00:00+08:00"
      }
    ]
  }
}
```

说明：

- `GET /tasks/{task_id}` 不返回完整 markdown 正文
- 报告正文以 SSE 流式交付为主
- `delivery` 仅在报告已生成后可用，否则为 `null`

## 5. 接口列表

| 方法 | 路径 | 用途 | 鉴权 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/health` | 健康检查 | 无 |
| `POST` | `/api/v1/tasks` | 创建研究任务 | 无 |
| `GET` | `/api/v1/tasks/{task_id}` | 查询任务快照与交付摘要 | `task_token` |
| `GET` | `/api/v1/tasks/{task_id}/events` | 订阅任务 SSE 事件流 | `task_token` |
| `POST` | `/api/v1/tasks/{task_id}/heartbeat` | 客户端保活 | `task_token` |
| `POST` | `/api/v1/tasks/{task_id}/clarification` | 提交澄清 | `task_token` |
| `POST` | `/api/v1/tasks/{task_id}/feedback` | 提交反馈 | `task_token` |
| `POST` | `/api/v1/tasks/{task_id}/disconnect` | 主动终止任务 | `task_token` |
| `GET` | `/api/v1/tasks/{task_id}/downloads/markdown.zip` | 下载 markdown zip | `access_token` |
| `GET` | `/api/v1/tasks/{task_id}/downloads/report.pdf` | 下载 PDF | `access_token` |
| `GET` | `/api/v1/tasks/{task_id}/artifacts/{artifact_id}` | 获取图片制品 | `access_token` |

## 6. 详细接口契约

## 6.1 `GET /api/v1/health`

用途：

- Railway liveness probe
- 本地和 CI 基础可用性检查

可选查询参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `check` | string | 否 | 仅支持 `readiness` |

响应 `200`：

```json
{
  "status": "ok",
  "service": "mimir-api",
  "version": "v1"
}
```

当 `check=readiness` 时，后端应额外检查数据库连接和基础依赖初始化状态后再返回 `status: ok`。

## 6.2 `POST /api/v1/tasks`

用途：

- 创建 Task
- 分配 `task_id`、`task_token`、`trace_id`
- 预占全局活动任务锁
- 等待客户端在 10 秒内建立首个 SSE 连接

请求体：

```json
{
  "initial_query": "帮我研究中国 AI 搜索产品竞争格局和未来机会",
  "config": {
    "clarification_mode": "natural"
  },
  "client": {
    "timezone": "Asia/Shanghai",
    "locale": "zh-CN"
  }
}
```

字段约束：

| 字段 | 类型 | 必填 | 约束 |
| --- | --- | --- | --- |
| `initial_query` | string | 是 | 最长 500 字/单词，允许换行 |
| `config.clarification_mode` | enum | 是 | `natural` 或 `options` |
| `client.timezone` | string | 是 | IANA timezone |
| `client.locale` | string | 否 | 默认 `zh-CN` |

响应 `201`：

```json
{
  "task_id": "tsk_01J...",
  "task_token": "secret_***",
  "trace_id": "trc_01J...",
  "snapshot": {
    "task_id": "tsk_01J...",
    "status": "running",
    "phase": "clarifying",
    "active_revision_id": "rev_01J...",
    "active_revision_number": 1,
    "clarification_mode": "natural",
    "created_at": "2026-03-13T14:30:00+08:00",
    "updated_at": "2026-03-13T14:30:00+08:00",
    "expires_at": null,
    "available_actions": []
  },
  "urls": {
    "events": "/api/v1/tasks/tsk_01J.../events",
    "heartbeat": "/api/v1/tasks/tsk_01J.../heartbeat",
    "disconnect": "/api/v1/tasks/tsk_01J.../disconnect"
  },
  "connect_deadline_at": "2026-03-13T14:30:10+08:00"
}
```

错误：

| 状态码 | 错误码 | 说明 |
| --- | --- | --- |
| `409` | `resource_busy` | 当前已有活动任务 |
| `429` | `ip_quota_exceeded` | 同 IP 24 小时配额耗尽 |
| `422` | `validation_error` | 入参不合法 |

`429 ip_quota_exceeded` 示例：

响应头：

```http
Retry-After: 37800
```

响应体：

```json
{
  "error": {
    "code": "ip_quota_exceeded",
    "message": "24 小时内创建任务次数已达上限，请稍后再试。",
    "detail": {
      "quota_limit": 3,
      "quota_used": 3,
      "next_available_at": "2026-03-14T02:15:00+08:00"
    },
    "request_id": "req_01J...",
    "trace_id": null
  }
}
```

## 6.3 `GET /api/v1/tasks/{task_id}`

请求头：

```http
Authorization: Bearer {task_token}
```

响应 `200`：

- 返回 `TaskDetailResponse`

使用场景：

- 前端初始化后获取当前权威状态
- 交付后刷新下载链接与制品链接
- 后续前端 bug 排查时的人类可读状态检查

补充说明：

- 若下载或图片 URL 中的 `access_token` 过期，前端应重新调用此接口获取新的 `delivery` 内容
- 该接口返回的 `delivery` URL 始终以“最近一次仍有效的 access token”覆盖旧值

错误：

| 状态码 | 错误码 | 说明 |
| --- | --- | --- |
| `401` | `task_token_invalid` | token 无效或不匹配 |
| `404` | `task_not_found` | task 不存在或已清理 |

## 6.4 `GET /api/v1/tasks/{task_id}/events`

请求头：

```http
Authorization: Bearer {task_token}
Accept: text/event-stream
```

响应头：

```http
Content-Type: text/event-stream
Cache-Control: no-store
Connection: keep-alive
```

SSE 格式：

```text
id: 41
event: phase.changed
data: {"seq":41,"event":"phase.changed","task_id":"tsk_01J...","revision_id":"rev_01J...","phase":"analyzing_requirement","timestamp":"2026-03-13T14:31:11+08:00","payload":{"from_phase":"clarifying","to_phase":"analyzing_requirement","status":"running"}}

```

SSE 约束：

1. 服务端每 15 秒至少发送一个 `heartbeat`
2. `id` 与 `seq` 必须单调递增
3. v1 不支持断线恢复，不保证重新连接后续跑
4. 一旦活动流断开，后端将按断连策略终止任务
5. 当 Task 进入 `awaiting_feedback` 时，当前 SSE 连接保持打开，直到收到反馈、发生断连、或触发过期

错误：

| 状态码 | 错误码 | 说明 |
| --- | --- | --- |
| `401` | `task_token_invalid` | token 无效 |
| `404` | `task_not_found` | task 不存在 |

## 6.5 `POST /api/v1/tasks/{task_id}/heartbeat`

请求头：

```http
Authorization: Bearer {task_token}
```

请求体：

```json
{
  "client_time": "2026-03-13T14:35:30+08:00"
}
```

响应：

- `204 No Content`

错误：

| 状态码 | 错误码 | 说明 |
| --- | --- | --- |
| `401` | `task_token_invalid` | token 无效 |
| `404` | `task_not_found` | task 不存在 |
| `409` | `invalid_task_state` | 当前已不接受 heartbeat |

## 6.6 `POST /api/v1/tasks/{task_id}/clarification`

请求头：

```http
Authorization: Bearer {task_token}
```

### 自然语言模式请求体

```json
{
  "mode": "natural",
  "answer_text": "重点看中国市场，偏商业分析，最好覆盖近两年变化。"
}
```

字段约束：

- `answer_text` 最长 `500` 字/单词

### 选单模式请求体

```json
{
  "mode": "options",
  "submitted_by_timeout": true,
  "answers": [
    {
      "question_id": "q_1",
      "selected_option_id": "o_2",
      "selected_label": "主要参与者与格局"
    }
  ]
}
```

响应 `202`：

```json
{
  "accepted": true,
  "snapshot": {
    "task_id": "tsk_01J...",
    "status": "running",
    "phase": "analyzing_requirement",
    "active_revision_id": "rev_01J...",
    "active_revision_number": 1,
    "clarification_mode": "natural",
    "created_at": "2026-03-13T14:30:00+08:00",
    "updated_at": "2026-03-13T14:31:10+08:00",
    "expires_at": null,
    "available_actions": []
  }
}
```

错误：

| 状态码 | 错误码 | 说明 |
| --- | --- | --- |
| `401` | `task_token_invalid` | token 无效 |
| `404` | `task_not_found` | task 不存在 |
| `409` | `invalid_task_state` | 当前状态不允许提交澄清 |
| `422` | `validation_error` | 入参格式错误 |

## 6.7 `POST /api/v1/tasks/{task_id}/feedback`

请求头：

```http
Authorization: Bearer {task_token}
```

请求体：

```json
{
  "feedback_text": "补充比较各家产品在 B 端场景的落地情况，并删掉不够确定的推测。"
}
```

字段约束：

- `feedback_text` 最长 `1000` 字/单词

响应 `202`：

```json
{
  "accepted": true,
  "revision_id": "rev_01J...",
  "revision_number": 2
}
```

错误：

| 状态码 | 错误码 | 说明 |
| --- | --- | --- |
| `401` | `task_token_invalid` | token 无效 |
| `404` | `task_not_found` | task 不存在 |
| `409` | `invalid_task_state` | 当前状态不允许提交反馈 |
| `422` | `validation_error` | 反馈内容不合法 |

## 6.8 `POST /api/v1/tasks/{task_id}/disconnect`

鉴权方式：

方案 A，普通请求使用 header：

```http
Authorization: Bearer {task_token}
```

方案 B，`sendBeacon` 使用 body：

```json
{
  "reason": "pagehide",
  "task_token": "secret_***"
}
```

`reason` 枚举建议：

```text
pagehide | beforeunload | client_manual_abort | network_lost
```

响应 `202`：

```json
{
  "accepted": true
}
```

说明：

- 普通前端请求优先使用 `Authorization: Bearer {task_token}`
- 若通过 `sendBeacon` 调用，允许在 body 中附带 `task_token`
- 推荐前端优先使用：

```javascript
navigator.sendBeacon(
  url,
  new Blob([JSON.stringify(body)], { type: 'application/json' })
);
```

- 若浏览器 `sendBeacon` 只支持 `text/plain`，后端需兼容 JSON string body
- 若 header 与 body 中同时存在 token，服务端应优先校验 header

错误：

| 状态码 | 错误码 | 说明 |
| --- | --- | --- |
| `401` | `task_token_invalid` | header/body token 缺失或无效 |
| `404` | `task_not_found` | task 不存在 |

## 6.9 `GET /api/v1/tasks/{task_id}/downloads/markdown.zip`

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `access_token` | string | 是 | 短期访问签名 |

成功响应：

- `200 application/zip`

关键响应头：

```http
Content-Type: application/zip
Content-Disposition: attachment; filename="mimir-report.zip"
Cache-Control: no-store
```

错误：

| 状态码 | 错误码 | 说明 |
| --- | --- | --- |
| `401` | `access_token_invalid` | access token 无效或过期 |
| `404` | `task_not_found` | task 不存在或制品已清理 |

## 6.10 `GET /api/v1/tasks/{task_id}/downloads/report.pdf`

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `access_token` | string | 是 | 短期访问签名 |

成功响应：

- `200 application/pdf`

关键响应头：

```http
Content-Type: application/pdf
Content-Disposition: attachment; filename="mimir-report.pdf"
Cache-Control: no-store
```

错误：

| 状态码 | 错误码 | 说明 |
| --- | --- | --- |
| `401` | `access_token_invalid` | access token 无效或过期 |
| `404` | `task_not_found` | task 不存在或制品已清理 |

## 6.11 `GET /api/v1/tasks/{task_id}/artifacts/{artifact_id}`

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `access_token` | string | 是 | 短期访问签名 |

成功响应：

- `200 image/png`

关键响应头：

```http
Content-Type: image/png
Cache-Control: no-store
```

约束：

- v1 writer 仅支持产出 png 图表

错误：

| 状态码 | 错误码 | 说明 |
| --- | --- | --- |
| `401` | `access_token_invalid` | access token 无效或过期 |
| `404` | `task_not_found` | task 不存在、artifact 不存在或制品已清理 |

## 7. SSE 事件契约

## 7.1 统一 Envelope

```json
{
  "seq": 41,
  "event": "planner.tool_call.requested",
  "task_id": "tsk_01J...",
  "revision_id": "rev_01J...",
  "phase": "planning_collection",
  "timestamp": "2026-03-13T14:35:18+08:00",
  "payload": {}
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `seq` | integer | 是 | Task 维度单调递增事件号 |
| `event` | string | 是 | 事件名称 |
| `task_id` | string | 是 | Task ID |
| `revision_id` | string | 否 | 当前 revision ID，任务级事件可为空 |
| `phase` | enum | 是 | 事件所属 phase |
| `timestamp` | string | 是 | 事件产生时间 |
| `payload` | object | 是 | 事件特定负载 |

## 7.2 事件列表

### `task.created`

payload:

```json
{
  "snapshot": {
    "task_id": "tsk_01J...",
    "status": "running",
    "phase": "clarifying",
    "active_revision_id": "rev_01J...",
    "active_revision_number": 1,
    "clarification_mode": "natural",
    "created_at": "2026-03-13T14:30:00+08:00",
    "updated_at": "2026-03-13T14:30:00+08:00",
    "expires_at": null,
    "available_actions": []
  }
}
```

说明：

- `task.created.snapshot` 是 SSE 建立后的权威初始状态
- 若与 `POST /tasks` 的 201 响应存在重复，前端应以后到达者覆盖先到达者

### `phase.changed`

payload:

```json
{
  "from_phase": "clarifying",
  "to_phase": "analyzing_requirement",
  "status": "running"
}
```

### `heartbeat`

payload:

```json
{
  "server_time": "2026-03-13T14:35:30+08:00"
}
```

### `clarification.delta`

用途：

- 自然语言澄清流式输出
- 选单澄清原始 LLM 输出流式展示

payload:

```json
{
  "delta": "1. 你更想聚焦行业现状还是竞争格局？"
}
```

### `clarification.options.ready`

payload:

```json
{
  "status": "awaiting_user_input",
  "available_actions": ["submit_clarification"],
  "question_set": {
    "questions": [
      {
        "question_id": "q_1",
        "question": "这次研究更偏向哪个方向？",
        "options": [
          { "option_id": "o_1", "label": "行业现状与趋势" },
          { "option_id": "o_2", "label": "主要参与者与格局" },
          { "option_id": "o_3", "label": "商业机会与风险" },
          { "option_id": "o_auto", "label": "自动" }
        ]
      }
    ]
  }
}
```

### `clarification.natural.ready`

payload:

```json
{
  "status": "awaiting_user_input",
  "available_actions": ["submit_clarification"]
}
```

### `clarification.countdown.started`

payload:

```json
{
  "duration_seconds": 15,
  "started_at": "2026-03-13T14:30:20+08:00"
}
```

说明：

- 选单倒计时的重置与最终截止时间由前端自行维护
- 该事件不提供权威 `auto_submit_at`

### `clarification.fallback_to_natural`

payload:

```json
{
  "reason": "parse_failed"
}
```

### `analysis.delta`

payload:

```json
{
  "delta": "{\n  \"研究目标\": \"...\""
}
```

### `analysis.completed`

payload:

```json
{
  "requirement_detail": {
    "research_goal": "分析中国 AI 搜索产品的竞争格局与机会",
    "domain": "互联网 / AI 产品",
    "requirement_details": "偏商业报告，关注中国市场，重点覆盖近两年变化，输出语言为中文。",
    "output_format": "business_report",
    "freshness_requirement": "high",
    "language": "zh-CN"
  }
}
```

### `planner.reasoning.delta`

payload:

```json
{
  "delta": "当前还缺少代表性玩家与市场趋势信息。"
}
```

### `planner.tool_call.requested`

payload:

```json
{
  "tool_call_id": "call_01J...",
  "collect_target": "收集 2024-2026 年中国 AI 搜索产品的主要厂商、产品定位与公开进展",
  "additional_info": "优先官方发布与高可信媒体。"
}
```

### `collector.reasoning.delta`

payload:

```json
{
  "subtask_id": "sub_01J...",
  "tool_call_id": "call_01J...",
  "delta": "先做高时效搜索，再读取官方来源。"
}
```

### `collector.search.started`

payload:

```json
{
  "subtask_id": "sub_01J...",
  "tool_call_id": "call_01J...",
  "search_query": "中国 AI 搜索 产品 2025",
  "search_recency_filter": "noLimit"
}
```

### `collector.search.completed`

payload:

```json
{
  "subtask_id": "sub_01J...",
  "tool_call_id": "call_01J...",
  "search_query": "中国 AI 搜索 产品 2025",
  "result_count": 10,
  "titles": [
    "某公司发布会回顾",
    "2025 中国 AI 搜索市场观察"
  ]
}
```

### `collector.fetch.started`

payload:

```json
{
  "subtask_id": "sub_01J...",
  "tool_call_id": "call_01J...",
  "url": "https://example.com/article"
}
```

### `collector.fetch.completed`

payload:

```json
{
  "subtask_id": "sub_01J...",
  "tool_call_id": "call_01J...",
  "url": "https://example.com/article",
  "success": true,
  "title": "某公司发布会回顾"
}
```

### `collector.completed`

payload:

```json
{
  "subtask_id": "sub_01J...",
  "tool_call_id": "call_01J...",
  "status": "completed",
  "item_count": 4,
  "search_queries": [
    "中国 AI 搜索 产品 2025",
    "AI 搜索 中国 厂商 2024 2026"
  ]
}
```

### `summary.completed`

payload:

```json
{
  "subtask_id": "sub_01J...",
  "tool_call_id": "call_01J...",
  "status": "completed",
  "key_findings_markdown": "- 官方披露更多集中在 2025 年后。\n- 已出现多个垂直场景产品。"
}
```

### `sources.merged`

payload:

```json
{
  "source_count_before_merge": 18,
  "source_count_after_merge": 11,
  "reference_count": 11
}
```

### `outline.delta`

payload:

```json
{
  "delta": "{\n  \"research_outline\": {"
}
```

说明：

- `outline.delta` 主要用于调试和时间线透明度，不要求前端原样展示
- 面向用户的主界面可仅显示“正在构思”

### `outline.completed`

payload:

```json
{
  "outline": {
    "title": "中国 AI 搜索产品竞争格局研究",
    "sections": [
      {
        "section_id": "section_1",
        "title": "研究背景与问题定义",
        "description": "界定研究范围，说明市场背景、问题边界与分析框架。",
        "order": 1
      }
    ],
    "entities": ["AI 搜索产品", "中国市场", "厂商竞争格局"]
  }
}
```

### `writer.reasoning.delta`

payload:

```json
{
  "delta": "先完成市场格局章节，再决定是否需要图表支撑。"
}
```

### `writer.tool_call.requested`

payload:

```json
{
  "tool_call_id": "call_01J...",
  "tool_name": "python_interpreter"
}
```

### `writer.tool_call.completed`

payload:

```json
{
  "tool_call_id": "call_01J...",
  "tool_name": "python_interpreter",
  "success": true
}
```

### `writer.delta`

payload:

```json
{
  "delta": "## 一、研究背景与问题定义\n"
}
```

### `artifact.ready`

payload:

```json
{
  "artifact": {
    "artifact_id": "art_01J...",
    "filename": "chart_market_share.png",
    "mime_type": "image/png",
    "url": "/api/v1/tasks/tsk_01J.../artifacts/art_01J...?access_token=***",
    "access_expires_at": "2026-03-13T15:00:00+08:00"
  }
}
```

### `report.completed`

payload:

```json
{
  "delivery": {
    "revision_id": "rev_01J...",
    "revision_number": 1,
    "word_count": 6800,
    "artifact_count": 1,
    "markdown_zip_url": "/api/v1/tasks/tsk_01J.../downloads/markdown.zip?access_token=***",
    "pdf_url": "/api/v1/tasks/tsk_01J.../downloads/report.pdf?access_token=***",
    "artifacts": [
      {
        "artifact_id": "art_01J...",
        "filename": "chart_market_share.png",
        "mime_type": "image/png",
        "url": "/api/v1/tasks/tsk_01J.../artifacts/art_01J...?access_token=***",
        "access_expires_at": "2026-03-13T15:00:00+08:00"
      }
    ]
  }
}
```

### `task.awaiting_feedback`

payload:

```json
{
  "expires_at": "2026-03-13T15:25:00+08:00",
  "available_actions": ["submit_feedback", "download_markdown", "download_pdf"]
}
```

说明：

- `awaiting_feedback` 期间 SSE 流保持打开
- 后端继续发送 SSE `heartbeat`，前端继续调用 `POST /heartbeat`
- 断连判定逻辑在 `awaiting_feedback` 期间同样生效

### `task.expired`

payload:

```json
{
  "expired_at": "2026-03-13T15:25:00+08:00"
}
```

说明：

- 后端应先发送 `task.expired`，再关闭 SSE 流并进入清理流程

### `task.failed`

payload:

```json
{
  "error": {
    "code": "upstream_service_error",
    "message": "上游服务异常"
  }
}
```

### `task.terminated`

payload:

```json
{
  "reason": "client_disconnected"
}
```

`reason` 枚举：

```text
client_disconnected | heartbeat_timeout | sendbeacon_received | risk_control_limit | sse_connect_timeout | server_shutdown
```

### 终态事件顺序

统一规则：

1. 正常流转到 `delivered` 时，先发送 `phase.changed`，再发送 `task.awaiting_feedback`
2. 发生 `failed` / `terminated` / `expired` 时，对应终态事件始终是该 Task 生命周期内的最后一个业务事件
3. `task.failed`、`task.terminated`、`task.expired` 不再额外重复发送同一次终态对应的 `phase.changed`

## 8. 状态与接口行为约束

### 8.1 允许调用矩阵

| 当前 status | 当前 phase | 可调用接口 |
| --- | --- | --- |
| `awaiting_user_input` | `clarifying` | `GET /tasks/{id}`, `GET /events`, `POST /heartbeat`, `POST /clarification`, `POST /disconnect` |
| `running` | 任一活跃 phase | `GET /tasks/{id}`, `GET /events`, `POST /heartbeat`, `POST /disconnect` |
| `awaiting_feedback` | `delivered` | `GET /tasks/{id}`, `GET /events`, `POST /heartbeat`, `POST /feedback`, `POST /disconnect`, `GET /downloads/*`, `GET /artifacts/*` |

补充说明：

- `failed`、`terminated`、`expired` 三类终态不保证还能通过 `GET /tasks/{id}` 读取到数据，因为 PRD 要求失败/终止立即清理、到期后立即清理
- 客户端对终态的主感知来源应是 SSE 终止事件，而不是事后查询

### 8.2 明确不支持的行为

v1 不支持：

- 多任务并行
- 页面刷新后恢复未完成任务
- SSE 断线重连继续消费
- 下载接口使用 `task_token`
- 前端自行解析选单 markdown

## 9. Contract Test 建议

进入实施阶段后，至少应覆盖以下 contract tests：

1. `POST /tasks` 成功、资源冲突、IP 配额耗尽三条路径。
2. 所有任务相关接口在缺失或错误 `Authorization` 时返回 `401 task_token_invalid`。
3. 下载和 artifact 接口在 `access_token` 失效时返回 `401 access_token_invalid`。
4. `GET /events` 的首条事件、心跳事件、终止事件的 envelope 结构。
5. 自然语言澄清与选单澄清的 ready 事件结构，包括 `clarification.natural.ready` 与 `clarification.options.ready`。
6. `POST /clarification` 的 `natural` / `options` 两种 body schema 和字段长度约束。
7. writer 工具调用事件与 collector fetch completed 事件的 payload 结构。
8. `POST /feedback` 仅在 `awaiting_feedback + delivered` 组合下可用。
9. `awaiting_feedback` 状态下 `GET /events`、`POST /heartbeat`、`POST /disconnect` 仍可调用。
10. `GET /tasks/{id}` 在 delivered 前后返回的 `delivery` 字段可空性，以及 access token 过期后通过重新获取 task detail 刷新 URL。

## 10. 本文档之后的下一步

在本文档 review 通过后，建议继续输出：

1. `docs/Backend_TDD_Plan.md`
2. `docs/Frontend_IA.md`
3. 如有必要，再补 `docs/SSE_Event_Examples.md`
