# Mimir Architecture

## 1. 文档目的

本文档基于 [PRD 0.3](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Mimir_v1.0.0_prd_0.3.md) 输出正式开发前的技术与架构设计，目标是把产品需求收敛为可执行的工程方案，覆盖以下内容：

- 前后端解耦方式与整体系统结构
- 后端目录结构与模块职责
- 核心 Agent 之间传递的数据结构（Schema）
- 前后端 API 接口契约与流式事件协议
- 数据存储、清理、风控、断连、限流等关键非功能设计
- TDD 开发顺序与测试边界

本文档只做架构与技术规划，不进入业务代码实现。

## 2. 架构原则

### 2.1 总体原则

1. 严格前后端解耦。
2. 后端必须可以在未来独立对外提供完整 API 服务。
3. 不使用 LangChain、LangGraph 或其他 Agent 编排框架，所有 Agent loop 手工实现。
4. 采用 contract-first + TDD 开发方式。
5. 所有长耗时阶段都必须可流式输出到前端。
6. 所有研究相关数据默认短期存活，严格执行删除策略。
7. 当前版本只支持“全局同一时刻一个研究任务”，优先保证行为确定性和可观测性，而不是横向扩展。

### 2.2 技术选型

#### 前端

- `Next.js`（App Router）
- `TailwindCSS`
- `shadcn/ui`
- `react-markdown` + `rehype-sanitize` 用于安全渲染报告
- `@microsoft/fetch-event-source` 或等价 `fetch + ReadableStream` 方案，用于带 Header 的 SSE 连接
- 浏览器直连后端 API 与 SSE，不引入 Next.js BFF

#### 后端

- `Python 3.12+`
- `FastAPI`
- `Pydantic v2`
- `SQLAlchemy 2.0` + `Alembic`
- `PostgreSQL` 作为主存储
- `httpx` 作为底层 HTTP 客户端
- 智谱官方 SDK 作为主 LLM 访问方式
- `E2B Sandbox API` 用于 `python_interpreter`

#### 部署

- 前端部署到 `Vercel`
- 后端部署到 `Railway`
- 后端默认挂载 Railway Volume 作为临时制品目录

### 2.3 关键决策

#### 决策 A: 流式协议使用 SSE，而不是 WebSocket

原因：

- PRD 的核心交互是单向流式展示，不需要频繁双向实时通信
- 浏览器接入简单，和 FastAPI 集成成本低
- 对前后端完全解耦更友好
- 更利于“事件日志 + 回放”的实现

#### 决策 B: 后端采用显式状态机 + 显式编排器

原因：

- PRD 中 func_7~func_10、func_15 有明确循环、分支、限次、回退与异常处理
- 手工编排比通用 Agent 框架更容易保证精确实现
- 更易测试、回放、调试和做风控处理

#### 决策 C: 任务使用 Task / Revision 二层模型

原因：

- 一次“研究任务”在交付后还能接受多轮反馈
- 反馈后需要重新生成需求详情并继续搜集与撰写
- PRD 0.3 明确要求反馈后不删除已搜集信息

因此：

- `Task` 表示从首次输入到最终过期/删除的整段生命周期
- `Revision` 表示首次输出或每次反馈后的一轮重跑

补充说明：

- PRD 0.3 的版本历史写明“反馈重启逻辑不删除已收集信息”
- 架构实现以 2026-03-12 更新的 PRD 0.3 版本历史和 `func_15` 详细说明为准

## 3. 建议仓库结构

建议将仓库整理为 Monorepo，但前后端边界保持明确：

```text
Mimir/
├─ apps/
│  └─ web/                      # Next.js 前端
├─ services/
│  └─ api/                      # FastAPI 后端
├─ packages/
│  └─ contracts/                # OpenAPI / JSON Schema / TS types
├─ docs/
│  ├─ Mimir_v1.0.0_prd_0.3.md
│  └─ Architecture.md
└─ scripts/
```

### 3.1 前端目录建议

```text
apps/web/
├─ app/
├─ components/
├─ features/
│  └─ research/
│     ├─ components/
│     ├─ hooks/
│     ├─ schemas/
│     └─ stores/
├─ lib/
│  ├─ api/
│  ├─ sse/
│  └─ utils/
├─ styles/
└─ tests/
```

前端职责只包括：

- 研究输入与配置
- 澄清交互
- 流式事件渲染
- 报告 markdown / 图片展示
- 下载与反馈入口

前端不承担：

- 业务编排
- Prompt 拼接
- 工具调用
- 数据持久化

### 3.2 后端目录建议

```text
services/api/
├─ app/
│  ├─ main.py
│  ├─ api/
│  │  ├─ deps.py
│  │  ├─ error_handlers.py
│  │  └─ v1/
│  │     ├─ router.py
│  │     ├─ health.py
│  │     ├─ tasks.py
│  │     ├─ events.py
│  │     └─ downloads.py
│  ├─ application/
│  │  ├─ dto/
│  │  ├─ commands/
│  │  ├─ services/
│  │  ├─ use_cases/
│  │  ├─ orchestrators/
│  │  └─ policies/
│  ├─ domain/
│  │  ├─ enums.py
│  │  ├─ models/
│  │  ├─ value_objects/
│  │  └─ services/
│  ├─ infrastructure/
│  │  ├─ db/
│  │  │  ├─ models/
│  │  │  ├─ repositories/
│  │  │  └─ migrations/
│  │  ├─ llm/
│  │  │  ├─ zhipu_client.py
│  │  │  ├─ parsers/
│  │  │  └─ prompts/
│  │  ├─ tools/
│  │  │  ├─ web_search_client.py
│  │  │  ├─ web_fetch_client.py
│  │  │  └─ e2b_client.py
│  │  ├─ storage/
│  │  ├─ streaming/
│  │  ├─ security/
│  │  └─ observability/
│  └─ core/
│     ├─ config.py
│     ├─ clock.py
│     ├─ ids.py
│     ├─ json.py
│     └─ retry.py
├─ tests/
│  ├─ unit/
│  ├─ contract/
│  ├─ integration/
│  └─ e2e/
└─ pyproject.toml
```

## 4. 运行时架构

```mermaid
flowchart LR
    U["Browser"] --> W["Next.js Web (Vercel)"]
    U -->|REST + SSE| A["FastAPI API (Railway)"]
    W -->|静态资源| U

    A --> O["Workflow Orchestrator"]
    O --> L["Zhipu LLM Adapter"]
    O --> S["Web Search Adapter"]
    O --> F["Jina Web Fetch Adapter"]
    O --> E["E2B Sandbox Adapter"]
    O --> D["PostgreSQL"]
    O --> R["Artifact Store (Railway Volume)"]
```

### 4.1 核心模块

#### API Layer

- 提供 REST 接口
- 提供 SSE 事件流
- 负责请求校验、鉴权、状态检查、错误映射

#### Workflow Orchestrator

- 驱动整个任务状态机
- 管理 revision 生命周期
- 驱动 master/sub agent loop
- 负责取消、重试、风控回退、断连终止

#### External Adapters

- 智谱 LLM 调用
- 智谱 `web_search`
- Jina `web_fetch`
- E2B `python_interpreter`

#### Persistence

- 存储任务状态、事件流、Agent loop、搜集结果、报告与制品元数据

#### Artifact Store

- 临时保存图片、markdown zip、pdf
- 随任务清理一起删除

## 5. 任务模型与状态机

## 5.1 核心实体

### Task

表示单次研究会话，含首次输入、交付、反馈、过期、删除等完整生命周期。

### Revision

表示 Task 内的一轮产出版本：

- `rev_1`: 初始需求产生的首轮版本
- `rev_n`: 基于用户反馈产生的后续版本

实现约束：

- 对外暴露的 `revision_id` 使用不可枚举的 opaque id，例如 `rev_01H...`
- Task 内部另存一个单调递增的 `revision_number`
- 文档中使用 `rev_1` 的地方仅作为阅读示意，不作为最终 ID 生成规则

### SubTask

表示 master agent 一次工具调用创建的单个搜集目标执行单元，对应 PRD 中的 `collect_agent`。

### Event

表示发往前端的流式 UI 事件，也是后端的可回放事件日志。

## 5.2 Task 状态

建议将 `status` 和 `phase` 分离。

### status

- `running`
- `awaiting_user_input`
- `awaiting_feedback`
- `terminated`
- `failed`
- `expired`
- `purged`

### phase

- `clarifying`
- `analyzing_requirement`
- `planning_collection`
- `collecting`
- `summarizing_collection`
- `merging_sources`
- `preparing_outline`
- `writing_report`
- `delivered`
- `processing_feedback`

### 5.2.1 `status × phase` 合法组合

| status | 合法 phase | 说明 |
| --- | --- | --- |
| `awaiting_user_input` | `clarifying` | 仅在澄清问题已生成、等待用户输入或选单提交时出现 |
| `running` | `clarifying`, `analyzing_requirement`, `planning_collection`, `collecting`, `summarizing_collection`, `merging_sources`, `preparing_outline`, `writing_report`, `processing_feedback` | 所有活跃执行阶段 |
| `awaiting_feedback` | `delivered` | 报告已交付，等待用户反馈 |
| `expired` | `delivered` | 报告交付后 30 分钟未继续操作而过期 |
| `terminated` | 任一活跃 phase 或 `delivered` | 保留终止发生时的 phase 以便调试与审计 |
| `failed` | 任一活跃 phase 或 `delivered` | 保留失败发生时的 phase 以便调试与审计 |
| `purged` | 不对前端暴露 | 数据已物理清理，仅作为内部清理终态 |

补充规则：

1. `clarifying` 既可能是 `running`，也可能是 `awaiting_user_input`。前者表示系统正在生成澄清内容，后者表示已生成完毕并等待用户。
2. `processing_feedback` 不再拆分新 phase；其内部显式包含“反馈需求分析 LLM -> 生成新的 RequirementDetail -> 切换 revision 编排”的子步骤。
3. `delivered` 不是运行态。到达 `delivered` 后，`status` 只能是 `awaiting_feedback`、`expired`、`terminated` 或 `failed`。

## 5.3 状态流转

```mermaid
stateDiagram-v2
    [*] --> clarifying
    clarifying --> analyzing_requirement
    analyzing_requirement --> planning_collection
    planning_collection --> collecting
    collecting --> summarizing_collection
    summarizing_collection --> planning_collection
    planning_collection --> merging_sources
    merging_sources --> preparing_outline
    preparing_outline --> writing_report
    writing_report --> delivered
    delivered --> processing_feedback
    processing_feedback --> planning_collection
    delivered --> expired
    clarifying --> terminated
    analyzing_requirement --> failed
    planning_collection --> failed
    merging_sources --> failed
    preparing_outline --> failed
    collecting --> failed
    processing_feedback --> failed
    writing_report --> failed
```

补充说明：

1. 为避免状态图过于拥挤，图中未逐一画出所有通用边。实际上所有活跃 phase 在前端断连时都允许流转到 `terminated`。
2. 同样地，所有活跃 phase 在通用异常重试耗尽时都允许流转到 `failed`。
3. `processing_feedback` 内部先完成 feedback analyzer LLM 调用，生成新的 `RequirementDetail` 后，才进入下一轮 `planning_collection`。

### 5.4 关键规则

1. Task 创建后立即占用“全局唯一活动任务锁”。
2. 交付后的 Task 进入 `awaiting_feedback`，最多保留 30 分钟。
3. 用户提交反馈时，创建新 Revision，不删除已有搜集结果。
4. 用户刷新、关闭页面或前端断连时，Task 直接 `terminated` 并立即清理。
5. 任一阶段遇到非风控异常，按统一重试策略处理；超限后 `failed`。
6. 任何终止态都必须触发清理作业。

## 6. 后端模块职责

### 6.1 Application 层

负责业务编排，不直接操作具体 SDK。

建议包含以下 Use Cases：

- `CreateTask`
- `StreamTaskEvents`
- `SubmitClarification`
- `SubmitFeedback`
- `TerminateTaskOnDisconnect`
- `GenerateMarkdownZip`
- `GeneratePdf`

建议包含以下 Orchestrators：

- `TaskOrchestrator`
- `RevisionOrchestrator`
- `ClarificationOrchestrator`
- `MasterPlanningOrchestrator`
- `CollectSubTaskOrchestrator`
- `ReportWritingOrchestrator`

建议包含以下 Policies：

- `RetryPolicy`
- `RiskControlPolicy`
- `TaskQuotaPolicy`
- `DisconnectPolicy`
- `CleanupPolicy`

### 6.2 Domain 层

只放纯业务规则与领域对象，不依赖 FastAPI 或 SDK。

重点对象：

- `ResearchTask`
- `TaskRevision`
- `RequirementDetail`
- `ClarificationForm`
- `CollectPlan`
- `CollectResult`
- `CollectSummary`
- `FormattedSource`
- `OutlinePackage`
- `ReportBundle`
- `TaskEvent`

重点领域服务：

- `TaskStateMachine`
- `SameSourceMergeService`
- `OutputFormatMapper`
- `FreshnessPolicyMapper`
- `ArtifactManifestBuilder`

### 6.3 Infrastructure 层

负责所有外部系统交互。

#### LLM Adapter

- 调智谱官方 SDK
- 统一封装流式 token、reasoning token、finish reason、tool calls
- 解析 PRD 要求的 JSON 输出

#### Tool Adapters

- `WebSearchClient`
- `WebFetchClient`
- `E2BSandboxClient`

#### Persistence

- SQLAlchemy models
- repositories
- migrations

#### Streaming

- SSE broker
- event serialization

#### Security

- task token 签发与校验
- IP 限流
- 来源校验与 CORS
- 短期下载签名与 artifact 访问签名

## 7. 核心 Schema 设计

说明：

1. LLM 输出格式严格遵循 PRD。
2. LLM 原始输出进入 parser 后，转换为后端内部规范化 schema。
3. Agent 之间传递的一律使用内部规范化 schema，避免直接依赖 LLM 原始 JSON 形态。

## 7.1 TaskSnapshot

前后端共享的任务快照。

```json
{
  "task_id": "tsk_01H...",
  "status": "running",
  "phase": "clarifying",
  "active_revision_id": "rev_01H...",
  "active_revision_number": 1,
  "clarification_mode": "natural",
  "created_at": "2026-03-13T14:30:00+08:00",
  "updated_at": "2026-03-13T14:30:05+08:00",
  "expires_at": null,
  "available_actions": ["submit_clarification"]
}
```

## 7.2 ResearchConfig

```json
{
  "clarification_mode": "natural"
}
```

字段说明：

- `clarification_mode`: `natural | options`

## 7.3 ClarificationQuestionSet

选单澄清使用。

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

说明：

- `o_auto` 不依赖 LLM 生成，由后端统一追加
- 前端默认全选 `o_auto`
- 选单解析必须在后端 parser 层完成，前端只渲染结构化 `questions`
- 若 LLM 输出无法被稳定解析为问题-选项结构，后端应回退到自然语言澄清，并发出 `clarification.fallback_to_natural` 事件

## 7.4 ClarificationSubmission

### 自然语言模式

```json
{
  "mode": "natural",
  "answer_text": "重点看中国市场，偏商业分析，最好覆盖近两年变化。"
}
```

### 选单模式

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

## 7.5 RequirementDetail

这是后续所有 Agent 的标准输入。

```json
{
  "research_goal": "分析中国 AI 搜索产品的竞争格局与机会",
  "domain": "互联网 / AI 产品",
  "requirement_details": "偏商业报告，关注中国市场，重点覆盖近两年变化，输出语言为中文。",
  "output_format": "business_report",
  "freshness_requirement": "high",
  "language": "zh-CN",
  "raw_llm_output": {
    "研究目标": "分析中国 AI 搜索产品的竞争格局与机会",
    "所属垂域": "互联网 / AI 产品",
    "需求明细": "偏商业报告，关注中国市场，重点覆盖近两年变化，输出语言为中文。",
    "适用形式": "商业报告",
    "时效需求": "是"
  }
}
```

说明：

- `output_format` 内部统一枚举：
  - `general`
  - `research_report`
  - `business_report`
  - `academic_paper`
  - `deep_article`
  - `guide`
  - `shopping_recommendation`
- `freshness_requirement` 内部统一枚举：
  - `high`
  - `normal`
- `language` 虽不在 PRD LLM JSON 顶层字段中，但应在 parser 阶段强制抽取并结构化

## 7.6 CollectPlan

master agent 发给 sub agent 的标准结构。

```json
{
  "tool_call_id": "call_01H...",
  "revision_id": "rev_01H...",
  "collect_target": "收集 2024-2026 年中国 AI 搜索产品的主要厂商、产品定位与公开进展",
  "additional_info": "优先官方发布、主流媒体、行业研究；关注时效性；中文输出。",
  "freshness_requirement": "high"
}
```

约束：

- 单轮最多 3 个 `CollectPlan`
- 单个 Revision 累计最多 5 次 `collect_agent` 调用

## 7.7 CollectResult

sub agent 结束后产生的原始搜集结果。

```json
{
  "subtask_id": "sub_01H...",
  "tool_call_id": "call_01H...",
  "collect_target": "收集 2024-2026 年中国 AI 搜索产品的主要厂商、产品定位与公开进展",
  "status": "completed",
  "search_queries": [
    "中国 AI 搜索 产品 2025",
    "AI 搜索 中国 厂商 2024 2026"
  ],
  "tool_call_count": 4,
  "items": [
    {
      "info": "某产品在 2025 年发布企业版能力，主要面向金融和政企客户。",
      "title": "某公司发布会回顾",
      "link": "https://example.com/article"
    }
  ]
}
```

字段说明：

- `status`: `completed | partial | risk_blocked`
- `tool_call_count`: sub agent 内部工具调用次数，最大 10

## 7.8 CollectSummary

sub agent 给 master 的压缩摘要。

```json
{
  "tool_call_id": "call_01H...",
  "subtask_id": "sub_01H...",
  "collect_target": "收集 2024-2026 年中国 AI 搜索产品的主要厂商、产品定位与公开进展",
  "status": "completed",
  "search_queries": [
    "中国 AI 搜索 产品 2025",
    "AI 搜索 中国 厂商 2024 2026"
  ],
  "key_findings_markdown": "- 市场上已有多家产品进入垂直场景。\n- 官方披露更多集中在 2025 年后。"
}
```

如果触发 func_17 指定风控异常，则统一转换为：

```json
{
  "tool_call_id": "call_01H...",
  "subtask_id": "sub_01H...",
  "status": "risk_blocked",
  "message": "触发风控敏感，请重新规划"
}
```

## 7.9 FormattedSource

搜集结果汇总后的标准信息源结构。

```json
{
  "refer": "ref_1",
  "title": "某公司发布会回顾",
  "link": "https://example.com/article",
  "info": "某产品在 2025 年发布企业版能力，主要面向金融和政企客户。\n同源页面中补充的另一条关键信息。"
}
```

说明：

- `refer` 在去重后重新顺序编号
- `info` 为同源聚合后的文本
- Writer 只能引用 `FormattedSource.refer`

## 7.10 OutlinePackage

研究输出准备阶段产物。

内部结构建议使用“有序数组”，不要直接使用动态 key 的字典，便于前端和测试处理。

```json
{
  "title": "中国 AI 搜索产品竞争格局研究",
  "sections": [
    {
      "section_id": "section_1",
      "title": "研究背景与问题定义",
      "description": "界定研究范围，说明市场背景、问题边界与分析框架。",
      "order": 1
    },
    {
      "section_id": "section_2",
      "title": "主要参与者与产品定位",
      "description": "分析代表性产品的定位、能力侧重点与目标用户。",
      "order": 2
    }
  ],
  "entities": ["AI 搜索产品", "中国市场", "厂商竞争格局"],
  "raw_llm_output": {}
}
```

说明：

- Prompt 仍按 PRD 的 JSON 结构输出
- Parser 将其转换为 `title + sections[] + entities[]`

## 7.11 PythonArtifact

`python_interpreter` 工具返回的图片制品结构。

```json
{
  "artifact_id": "art_01H...",
  "filename": "chart_market_share.png",
  "mime_type": "image/png",
  "storage_key": "tasks/tsk_x/rev_01H/artifacts/chart_market_share.png",
  "download_path": "/api/v1/tasks/tsk_x/artifacts/art_01H...?access_token=***",
  "markdown_ref": "![chart_market_share](/api/v1/tasks/tsk_x/artifacts/art_01H...?access_token=***)",
  "access_expires_at": "2026-03-13T14:55:00+08:00"
}
```

## 7.12 ReportBundle

Writer 阶段最终交付结构。

```json
{
  "revision_id": "rev_01H...",
  "markdown": "# 中国 AI 搜索产品竞争格局研究\n...",
  "artifacts": [
    {
      "artifact_id": "art_01H...",
      "filename": "chart_market_share.png",
      "mime_type": "image/png"
    }
  ],
  "word_count": 6800
}
```

## 7.13 AgentTranscriptMessage

这是“完整 agent loop 信息”的标准落库结构，用于下一轮调用时重建上下文。

```json
{
  "message_id": "msg_01H...",
  "task_id": "tsk_01H...",
  "revision_id": "rev_01H...",
  "subtask_id": "sub_01H...",
  "agent_type": "planner",
  "role": "assistant",
  "content_type": "reasoning",
  "content": "需要先覆盖市场格局，再补充代表性产品信息。",
  "tool_name": null,
  "tool_call_id": null,
  "created_at": "2026-03-13T14:35:10+08:00"
}
```

字段说明：

- `agent_type`: `clarifier | analyzer | planner | collector | summarizer | outliner | writer | feedback_analyzer`
- `role`: `system | user | assistant | tool`
- `content_type`: `prompt | reasoning | content | tool_call | tool_result`

要求：

1. planner / collector / writer 三类 loop 必须完整保存 transcript。
2. 后续回合重新调用 LLM 时，必须按原始顺序回放 transcript。
3. UI 事件与 transcript 分离存储，避免把前端展示协议直接耦合到 LLM 输入协议。
4. transcript 大字段应使用 `TEXT` 列独立存储，不应塞进单个大 JSON。
5. 考虑到 v1 同时只允许一个活动任务、且任务默认 30 分钟内清理，完整 transcript 存储在容量上可接受；当单条 `reasoning/content` 超过 64KB 时，允许在应用层做透明压缩存储。

## 7.14 EventEnvelope

所有 SSE 事件统一使用此结构。

```json
{
  "seq": 41,
  "event": "planner.tool_call.requested",
  "task_id": "tsk_01H...",
  "revision_id": "rev_01H...",
  "phase": "planning_collection",
  "timestamp": "2026-03-13T14:35:18+08:00",
  "payload": {
    "tool_call_id": "call_01H...",
    "collect_target": "收集 2024-2026 年中国 AI 搜索产品的主要厂商、产品定位与公开进展"
  }
}
```

## 8. Agent Loop 设计

## 8.1 Master Agent Loop

输入：

- `RequirementDetail`
- 当前 Revision 已有的 `CollectSummary[]`
- 历史 master agent reasoning / tool messages

输出二选一：

1. `stop`
2. `CollectPlan[]`

后端职责：

- 按 Revision 维度累计 `collect_agent` 总调用次数
- 校验同轮并发数不超过 3
- 把每个 tool call 映射为一个 `SubTask`

## 8.2 Sub Agent Loop

输入：

- `CollectPlan`
- 当前 SubTask 的完整历史 reasoning / tool messages

工具：

- `web_search`
- `web_fetch`

输出：

- `CollectResult`

后端职责：

- 累计工具调用次数，达到 10 次则强制 stop
- 保存 `search_query_list`
- 截断 `web_fetch` 返回内容到前 10000 字符
- 工具 adapter 必须返回标准化成功/失败结果，避免 sub agent 因超时、空响应或非法响应而挂起
- `search_recency_filter` 内部统一枚举值使用 `noLimit`；若上游或 prompt 历史中出现 `nolimit`，由 adapter 层做兼容映射

## 8.3 Summary Loop

输入：

- `CollectPlan`
- `CollectResult`

输出：

- `CollectSummary`

## 8.4 Writer Loop

输入：

- `RequirementDetail`
- `FormattedSource[]`
- `OutlinePackage`
- 当前 writer 历史 reasoning / tool messages

工具：

- `python_interpreter`

输出：

- `ReportBundle`

E2B 生命周期约束：

1. 不在进入 `writing_report` 时立即创建沙箱，而是在 writer 首次真正触发 `python_interpreter` 工具时惰性创建。
2. 同一 Revision 内的多次 `python_interpreter` 调用复用同一个 E2B sandbox。
3. Revision 完成、任务终止、任务失败或任务过期时，必须显式销毁该 Revision 对应的 sandbox。
4. E2B sandbox 创建失败、执行失败或上传 artifact 失败时，适用 PRD 的通用重试策略；重试耗尽后该 Revision 失败，不做“静默跳过图表”的降级。
5. 由于 v1 全局只允许一个活动任务，一个 Revision 持有一个活动 sandbox 的成本是可接受的。

## 8.5 外部调用契约与 PRD 收敛

本节用于把 PRD 中对第三方模型与工具服务的调用要求，正式收敛为后续实现修正的唯一设计口径。

适用范围：

- 智谱 LLM chat / tool-calling
- 智谱 `web_search`
- Jina Reader `web_fetch`
- E2B `python_interpreter`

总原则：

1. 除本节显式说明的设计层调整外，PRD `func_4`、`func_5`、`func_6`、`func_7`、`func_8`、`func_9`、`func_12`、`func_13`、`func_15` 的调用定义仍是 source of truth。
2. 后续实现不得再以“adapter 默认值”替代阶段级调用配置；若要调整模型、采样参数、tool schema 或 request shape，必须先同步更新 PRD、本文档和测试计划。
3. 本节约束的是后端对外 provider/tool 调用，不改变已有 `TaskSnapshot`、`EventEnvelope` 与 REST/SSE 公共契约，因此 `docs/OpenAPI_v1.md` 不需要同步改动。

### 8.5.1 LLM 阶段调用 profile

下表是所有真实 LLM 调用必须遵守的阶段 profile。实现可以通过配置注入这些值，但配置项本身不构成新的 source of truth。

| 阶段 | PRD 对应 | `model` | `temperature` | `top_p` | `max_tokens` | `thinking` | `stream` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| clarification natural | `func_4` | `glm-5` | `0.5` | `0.8` | `98304` | `false` | `true` |
| clarification options | `func_5` | `glm-5` | `0.5` | `0.8` | `98304` | `false` | `true` |
| requirement analysis | `func_6` | `glm-5` | `0.5` | `0.8` | `98304` | `false` | `true` |
| planner | `func_7` | `glm-5` | `1` | `1` | `98304` | `true` | `true` |
| collector | `func_8` | `glm-5` | `1` | `1` | `98304` | `true` | `true` |
| summary | `func_9` | `glm-5` | `0.6` | `0.8` | `98304` | `false` | `true` |
| outline | `func_12` | `glm-5` | `1` | `1` | `98304` | `true` | `true` |
| writer | `func_13` | `glm-5` | `1` | `1` | `98304` | `true` | `true` |
| feedback analysis | `func_15` | `glm-5` | `0.5` | `0.8` | `98304` | `false` | `true` |

补充约束：

1. `planner`、`collector`、`outline`、`writer` 四类 thinking-enabled 调用，还必须显式传递 `clear_thinking=false`，不得依赖 SDK 默认值。
2. 未在上表列出的任意 LLM 调用，都不能绕过本表自行选择新的模型 profile。
3. `stream=true` 是真实 provider 调用契约的一部分；即使后端内部最终把结果聚合后再持久化或发事件，也不能把上游请求默认为非流式。

### 8.5.2 Prompt source of truth 与组织规则

按 drift 风险把 prompt 分成两类。

第一类：逐字继承 PRD

- `clarification natural`
- `clarification options`
- `requirement analysis`
- `feedback analysis`

约束：

1. 以上四类 prompt 的模型可见文本，以 PRD 原文为准逐字落实；允许的变化只有运行时变量插值、空白规范化和 JSON 示例中的动态值替换。
2. `clarification natural` 与 `clarification options` 必须保持 PRD 的“空 system prompt”约束，不能再由 adapter 私自补一个新的 system prompt。
3. `requirement analysis` 与 `feedback analysis` 的 system prompt / user prompt 边界，以 PRD 为准；不得把 PRD 中模型可见的角色说明挪到 adapter 不可见的默认字符串里。

第二类：允许等价改写，但语义必须与 PRD 一致

- `planner`
- `collector`
- `summary`
- `outline`
- `writer`

允许的设计层抽象：

1. 可以把 PRD 的稳定角色说明收口到 system prompt，把运行时数据放到 user prompt。
2. 可以把“只输出合法 JSON”这类结构化输出指令抽成统一后缀或 adapter wrapper。
3. 可以把 transcript 以多条 message 注入，而不是把全部历史拼成单个长字符串。

不可改变的语义：

1. tool 可见范围、tool 名称、tool 参数名不能改。
2. 并发上限、`collect_agent` 次数上限、sub-agent 工具调用上限不能改。
3. planner / collector / writer 的完整 transcript 必须按原始顺序回放，不能只注入摘要。
4. 不得新增 PRD 未定义的模型可见字段、工具或输出 schema。

system / user prompt 组织规则：

1. system prompt 负责稳定角色、硬性边界、tool 使用约束。
2. user prompt 负责当前 `RequirementDetail`、`CollectPlan`、`CollectResult`、`FormattedSource[]`、反馈文本等运行时输入。
3. 若 PRD 明确要求 system prompt 为空，则设计也必须保持为空；这类调用不能为了“统一封装”而额外加 system prompt。

### 8.5.3 Tool schema 契约

| tool | 可用阶段 | 模型可见 request schema | 设计约束 |
| --- | --- | --- | --- |
| `collect_agent` | planner | `collect_target`、`additional_info`、`freshness_requirement` | 对模型暴露的 schema 以 PRD 为准，不额外暴露 `tool_call_id`、`revision_id`、`subtask_id`；这些内部元数据由后端在解析后补齐。 |
| `web_search` | collector | `search_query`、`search_recency_filter` | `search_recency_filter` 的规范值为 `day | week | month | year | noLimit`；若历史 transcript 中出现 `nolimit`，只允许 adapter 做兼容归一化。 |
| `web_fetch` | collector | `url` | 只允许模型传目标 URL，不对模型暴露 header、timeout、parser 等实现细节。 |
| `python_interpreter` | writer | `code` | 只允许模型提交待执行 Python 代码；sandbox 创建、复用、上传 artifact、下载签名 URL 都由后端 orchestrator / adapter 负责。 |

tool result 归一化规则：

1. `collect_agent` 返回给 planner 的是后端综合后的 subtask 摘要，不是原始 `web_search` / `web_fetch` provider payload。
2. `web_search` 与 `web_fetch` 的 tool result 都必须在 adapter 层标准化为“成功但内容为空”或“失败但可继续”的统一 envelope，避免 collector loop 因 provider 响应形态差异挂起。
3. `python_interpreter` tool result 只允许返回文本摘要与 artifact 元数据，不能把二进制文件内容直接放进 transcript 或 SSE payload。

### 8.5.4 Tool request construction 与结果清洗

#### 智谱 `web_search`

真实 HTTP 请求必须构造成：

- `POST https://open.bigmodel.cn/api/paas/v4/web_search`
- `Authorization: Bearer {ZHIPU_API_KEY}`
- 请求体固定字段：
  - `search_engine: "search_prime"`
  - `query_rewrite: false`
  - `count: 10`
  - `search_query: <tool call 中的 search_query>`
  - `search_recency_filter: <tool call 中的 search_recency_filter>`

额外约束：

1. `search_engine`、`query_rewrite`、`count` 属于固定 provider contract，不允许由 planner / collector prompt 或 adapter 默认值自由漂移。
2. tool result 回灌给 collector 时，只保留 `search_result` 列表中的核心字段；`icon`、`media` 及其他展示性厂商字段一律剔除。
3. provider 如果返回 `results`、`data.search_result` 等兼容形态，adapter 负责归一到同一内部结构，再返回给上层。

#### Jina Reader `web_fetch`

PRD 当前把 `web_fetch` 写成 `POST https://r.jina.ai/` + JSON body `{"url": ...}`。设计层在此做一处有意识调整：

- 正式请求形态采用 `GET https://r.jina.ai/{url}`
- Header:
  - `Authorization: Bearer {JINA_API_KEY}`（当 `JINA_API_KEY` 非空时携带；为空时不携带，以免费无认证模式调用，受 RPM 限制）
  - `Accept: text/plain`

调整理由：

1. Jina Reader 的稳定接入方式是“把目标 URL 直接拼到 reader base URL 后面”，这与现有 real adapter 和上游产品形态一致。
2. 使用 path-based GET 比起自定义 POST body 更少歧义，也更适合通过 `respx` 与 contract tests 明确锁定。

结果处理规则：

1. 把响应视为 markdown / plaintext 文本，不做 HTML 二次抓取。
2. 以首个 markdown 标题或首行文本生成 `title`，原始 `url` 仍作为主键。
3. 返回给 collector transcript、数据库与 summary loop 的正文，统一截断到前 `10000` 个字符。
4. 空内容、上游 4xx、拒绝访问、非文本体都转成标准化“失败但可继续”的 tool result；超时与 5xx 仍按可重试异常处理。

#### `python_interpreter`

1. writer 发出的 tool request 只包含 `code`。
2. adapter / orchestrator 负责把执行结果拆成：
   - 文本执行摘要
   - artifact 元数据
   - 失败错误摘要
3. raw binary、压缩包内容或图片字节不进入 transcript；它们只能进入 artifact store。

### 8.5.5 Port / adapter 责任边界

必须通过端口层显式传递的内容：

1. LLM 阶段标识，以及对应的 `model`、`temperature`、`top_p`、`max_tokens`、`thinking`、`clear_thinking`、`stream`
2. system prompt / user prompt 的最终模型可见内容
3. transcript message 列表及其顺序
4. tool schema 列表，以及期望的输出模式（纯文本 / 结构化 JSON / tool-calling）
5. `web_search` 的 `search_query` 与 `search_recency_filter`
6. `web_fetch` 的 `url`
7. `python_interpreter` 的 `code`

可由 adapter 默认值承接的内容：

1. API key、base URL、HTTP timeout、连接池、User-Agent、`Accept` 等传输层细节
2. 智谱 `web_search` 的固定字段：`search_engine="search_prime"`、`query_rewrite=false`、`count=10`
3. Jina Reader 的 base URL 与鉴权 header 组织方式
4. 结果截断长度、标题提取、厂商字段清洗、错误映射、request id 采集
5. `RetryPolicy`、风控异常映射与日志埋点

禁止由 adapter 私自决定的内容：

1. 阶段模型 profile
2. prompt 文本语义
3. tool 名称、tool 参数名、tool 可见字段
4. transcript 是否完整回放
5. planner 并发上限、`collect_agent` 总配额、sub-agent 工具调用上限

后续实现修正应优先把当前“只传 prompt 字符串”的薄端口，提升为显式携带调用 profile 与 prompt bundle 的端口；在该修正完成前，任何真实 provider 适配都不得再新增隐式默认值。

## 9. API 契约

约定：

- 所有业务接口前缀统一为 `/api/v1`
- 除二进制下载与图片访问外，所有需要访问任务内容的接口都通过 `Authorization: Bearer {task_token}` 传递鉴权
- 二进制下载与图片访问使用短期 `access_token` query 参数，而不是直接暴露 `task_token`
- `task_token` 在创建任务时只返回一次，后端只保存其哈希值
- 前端使用浏览器直连 Railway API

### 通用连接约定

1. 前端创建任务成功后，必须在 10 秒内建立 SSE 连接。
2. 后端只在“首个有效 SSE 连接建立完成”后启动 orchestrator，因此不会出现 `POST /tasks` 返回后早期事件丢失的问题。
3. SSE 建立时，后端先回放当前任务已经持久化但尚未发出的事件，然后切换到实时流。
4. 一旦活动 SSE 流中断，即视为前端断连，不支持基于 `Last-Event-ID` 的任务恢复；`seq` 和 `id:` 字段主要用于事件排序、审计和首连回放。
5. 前端应使用支持自定义 Header 的 SSE 客户端，不使用浏览器原生 `EventSource`。
6. 若创建任务后 10 秒内始终没有建立首个有效 SSE 连接，后端直接终止并清理该任务，避免悬空任务占用全局锁。

### CORS 约定

- `allow_origins` 使用显式白名单，从环境变量注入
- 默认只允许生产前端域名、预览域名和本地开发域名
- 允许方法：`GET`, `POST`, `OPTIONS`
- 允许请求头：`Authorization`, `Content-Type`, `Last-Event-ID`, `X-Request-ID`
- 不使用 cookie，会话鉴权不依赖 `credentials`

## 9.1 创建任务

`POST /api/v1/tasks`

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

响应体：

```json
{
  "task_id": "tsk_01H...",
  "task_token": "secret_***",
  "snapshot": {
    "task_id": "tsk_01H...",
    "status": "running",
    "phase": "clarifying",
    "active_revision_id": "rev_01H...",
    "active_revision_number": 1,
    "clarification_mode": "natural",
    "created_at": "2026-03-13T14:30:00+08:00",
    "updated_at": "2026-03-13T14:30:00+08:00",
    "expires_at": null,
    "available_actions": ["submit_clarification"]
  },
  "events_url": "/api/v1/tasks/tsk_01H.../events"
}
```

状态码：

- `201` 创建成功
- `409` 当前已有全局活动任务
- `429` 同 IP 24 小时内超过 3 次创建上限

## 9.2 查询任务快照

`GET /api/v1/tasks/{task_id}`

返回：

- 当前 `TaskSnapshot`
- 若已交付，则返回当前 revision 的报告元信息与可下载项

## 9.3 订阅任务事件流

`GET /api/v1/tasks/{task_id}/events`

响应类型：

- `text/event-stream`

SSE 事件格式：

```text
id: 41
event: planner.tool_call.requested
data: {"seq":41,"event":"planner.tool_call.requested","task_id":"tsk_01H...","revision_id":"rev_01H...","phase":"planning_collection","timestamp":"2026-03-13T14:35:18+08:00","payload":{"tool_call_id":"call_01H...","collect_target":"收集 2024-2026 年中国 AI 搜索产品的主要厂商、产品定位与公开进展"}}
```

建议支持的事件类型：

- `task.created`
- `phase.changed`
- `heartbeat`
- `clarification.delta`
- `clarification.options.ready`
- `clarification.countdown.started`
- `clarification.fallback_to_natural`
- `analysis.delta`
- `analysis.completed`
- `planner.reasoning.delta`
- `planner.tool_call.requested`
- `collector.reasoning.delta`
- `collector.search.started`
- `collector.search.completed`
- `collector.fetch.started`
- `collector.completed`
- `summary.completed`
- `sources.merged`
- `outline.delta`
- `outline.completed`
- `writer.reasoning.delta`
- `writer.delta`
- `artifact.ready`
- `report.completed`
- `task.awaiting_feedback`
- `task.failed`
- `task.terminated`

SSE 保活与断连判定：

1. 后端每 15 秒发送一个 `heartbeat` 事件。
2. 前端在任务活跃期间每 20 秒调用一次轻量 `heartbeat` 接口，刷新 `last_client_seen_at`。
3. 后端若连续 45 秒未收到客户端心跳，视为前端断连并终止任务。
4. 若 SSE 写入失败、客户端主动断开或 `sendBeacon` 上报断连，后端也立即执行同样的终止逻辑。
5. 鉴于 PRD 明确“断连即放弃任务”，v1 不做 SSE 自动重连与断点续跑。

### 心跳保活接口

`POST /api/v1/tasks/{task_id}/heartbeat`

请求体：

```json
{
  "client_time": "2026-03-13T14:35:30+08:00"
}
```

响应：

- `204 No Content`

## 9.4 提交澄清

`POST /api/v1/tasks/{task_id}/clarification`

请求体：

- 自然语言模式用 `ClarificationSubmission(mode=natural)`
- 选单模式用 `ClarificationSubmission(mode=options)`

响应体：

```json
{
  "accepted": true,
  "snapshot": {
    "task_id": "tsk_01H...",
    "status": "running",
    "phase": "analyzing_requirement",
    "active_revision_id": "rev_01H...",
    "active_revision_number": 1,
    "clarification_mode": "natural",
    "created_at": "2026-03-13T14:30:00+08:00",
    "updated_at": "2026-03-13T14:31:10+08:00",
    "expires_at": null,
    "available_actions": []
  }
}
```

状态码：

- `202` 已接受
- `409` 当前状态不允许提交
- `422` 参数不合法

选单澄清计时策略：

1. 面向用户的 15 秒倒计时由前端负责展示和重置。
2. `clarification.countdown.started` 事件只提供“开始倒计时”的 UI 信号，不作为后端精确计时器。
3. 后端额外保存一个 60 秒的兜底超时，防止任务永久卡在 `awaiting_user_input`。
4. 若兜底超时触发且仍未收到提交，后端按默认全选 `auto` 的选单状态自动推进到 `analyzing_requirement`。

## 9.5 提交反馈

`POST /api/v1/tasks/{task_id}/feedback`

请求体：

```json
{
  "feedback_text": "补充比较各家产品在 B 端场景的落地情况，并删掉不够确定的推测。"
}
```

响应体：

```json
{
  "accepted": true,
  "revision_id": "rev_01J...",
  "revision_number": 2
}
```

状态码：

- `202` 已接受
- `409` 当前不处于可反馈状态

## 9.6 断连终止

`POST /api/v1/tasks/{task_id}/disconnect`

说明：

- 前端在 `pagehide` / `beforeunload` 中通过 `sendBeacon` 调用
- 后端收到后立即终止任务并清理

请求体：

```json
{
  "reason": "pagehide"
}
```

响应体：

```json
{
  "accepted": true
}
```

此外，后端还应在 SSE 连接非正常断开时触发同样的终止逻辑，作为 `sendBeacon` 失败时的兜底。

更准确地说，后端的断连兜底来源包括三类：

1. `sendBeacon` 主动上报断连
2. SSE 写入失败或连接主动关闭
3. heartbeat 超时

## 9.7 下载 markdown zip

`GET /api/v1/tasks/{task_id}/downloads/markdown.zip?access_token=...`

返回：

- `application/zip`
- 内容包含：
  - `report.md`
  - `artifacts/*.png`

## 9.8 下载 PDF

`GET /api/v1/tasks/{task_id}/downloads/report.pdf?access_token=...`

返回：

- `application/pdf`

实现建议：

- 由后端负责 `markdown -> HTML -> PDF` 渲染
- v1 推荐在 Railway 后端内实现 `ReportExportService`
- PDF 与 markdown zip 都属于短期制品，纳入统一 Artifact 清理策略

## 9.9 获取图片制品

`GET /api/v1/tasks/{task_id}/artifacts/{artifact_id}?access_token=...`

返回：

- 对应图片二进制流

## 9.10 错误响应格式

```json
{
  "error": {
    "code": "resource_busy",
    "message": "当前已有研究任务在执行，请稍后再试。",
    "detail": {},
    "request_id": "req_01H..."
  }
}
```

建议错误码：

- `resource_busy`
- `ip_quota_exceeded`
- `invalid_task_state`
- `validation_error`
- `risk_control_triggered`
- `upstream_service_error`
- `task_not_found`
- `task_token_invalid`
- `access_token_invalid`

## 10. 数据存储与清理策略

## 10.1 数据表建议

### `research_tasks`

- 任务主表
- 保存状态、阶段、配置、IP 哈希、token 哈希、过期时间等

### `task_revisions`

- 每轮 revision 一行
- 保存需求详情、当前报告、当前大纲、当前状态
- 推荐额外字段：
  - `revision_number`
  - `collect_agent_calls_used`
  - `sandbox_id`
  - `clarification_deadline_at`

### `task_events`

- SSE 事件日志
- 保存 `seq / event / payload / phase / created_at`

### `agent_runs`

- 保存各 Agent 每轮调用的 metadata
- 推荐字段：
  - `agent_type`
  - `revision_id`
  - `subtask_id`
  - `prompt_name`
  - `reasoning_text`
  - `content_text`
  - `finish_reason`
  - `tool_calls_json`
  - `compressed`

### `task_tool_calls`

- 保存外部工具调用记录
- 便于重试、调试、统计

### `collected_sources`

- 保存 `CollectResult.items`
- 保存去重前和去重后结果

### `artifacts`

- 保存图片、zip、pdf 的元数据

### `ip_usage_counters`

- 记录同 IP 24 小时内创建任务次数

### `system_locks`

- 保存全局唯一活动任务锁

## 10.2 清理策略

严格对齐 PRD：

1. 用户开启新任务前，先清理所有旧任务数据与制品。
2. 被终止或失败的任务，立即清理数据与制品。
3. 已交付且未开启新任务的任务，保留 30 分钟后清理。
4. E2B 沙箱在 revision 结束或任务终止时必须显式销毁。
5. Artifact Store 中的图片、zip、pdf 必须与数据库删除保持事务一致性或补偿一致性。

建议实现：

- 创建任务前主动执行一次 `CleanupExpiredTasks`
- 后端启动后常驻一个轻量清理协程，每 60 秒扫描一次过期任务
- 删除顺序：
  1. 标记任务终态
  2. 取消后台执行
  3. 删除制品文件
  4. 删除数据库记录

一致性策略：

- 由于 Railway Volume 无法与 PostgreSQL 共享事务，v1 明确采用“补偿一致性”方案，而不是伪事务
- 具体顺序为：
  1. 数据库标记 `cleanup_pending`
  2. 删除 artifact / sandbox / 临时文件
  3. 删除数据库业务记录
  4. 最终标记或物理清除清理记录
- 清理协程应持续重试处于 `cleanup_pending` 的残留任务，直到文件和数据库都被清掉

额外清理：

- `ip_usage_counters` 删除 48 小时之前的历史记录，避免长期膨胀

## 10.3 日志约束

日志中禁止保留：

- API key（`ZHIPU_API_KEY`、`JINA_API_KEY`、`E2B_API_KEY`）
- 签名密钥（`MIMIR_TASK_TOKEN_SECRET`、`MIMIR_ACCESS_TOKEN_SECRET`）
- `task_token`、`access_token` 的明文值

日志中允许保留：

- `task_id`、`revision_id`、`subtask_id`
- 状态变化、phase 流转
- 时长、上游 request id、错误码
- 用户完整原始输入
- LLM 调用完整入参（prompt）与完整出参（response）
- 网页抓取内容
- 报告全文
- 图片文件名和 metadata（不含二进制内容）

## 10.4 运行配置与环境变量

敏感配置全部通过环境变量注入：

- `DATABASE_URL`
- `ZHIPU_API_KEY`
- `JINA_API_KEY`（optional；为空时 web_fetch 降级为免费无认证模式，受 RPM 限制）
- `E2B_API_KEY`
- `ALLOWED_ORIGINS`
- `ARTIFACT_SIGNING_SECRET`
- `TASK_TOKEN_SIGNING_SECRET`

约束：

1. 生产环境使用 Railway / Vercel 的环境变量管理。
2. 本地开发使用 `.env` 文件，但 `.env` 必须加入 `.gitignore`。
3. 所有密钥读取统一收口到 `app/core/config.py`。

## 11. 异常、风控、限流、断连设计

## 11.1 通用异常处理

按 PRD func_16：

- 固定等待 3 秒
- 最多重试 3 次
- 成功则继续
- 超限则终止任务，并允许前端查看原始错误摘要

实现建议：

- `RetryPolicy` 只包裹幂等或可安全重试的调用
- 对 LLM streaming 已经部分输出的场景，不做中途续传，直接整轮重试

## 11.2 风控异常处理

识别条件：

- HTTP `400`
- 响应体业务错误码 `1301`

仅对以下调用做特殊识别：

- LLM 调用
- `web_search`

接入边界：

- 智谱官方 SDK 仅用于 LLM chat / tool-calling 能力
- 智谱 `web_search` 使用 `httpx` 直接访问 `open.bigmodel.cn` 的独立 HTTP API
- `web_search` 与 LLM 的风控识别逻辑统一收口在 adapter 层，向上抛出统一的 `RiskControlTriggered` 异常

处理逻辑：

1. 若处于 `collecting / summarizing_collection` 阶段：
   - 终止当前 subtask
   - 向 master 注入一条 `CollectSummary(status=risk_blocked)` 风格的 tool message
   - 当前 task 累计达到 2 次后，直接终止整个任务
2. 其他阶段触发风控：
   - 直接终止整个任务

## 11.3 使用限制

按 PRD func_21：

1. 全局同一时刻只允许一个活动任务。
2. 同一 IP 24 小时最多创建 3 个任务。

实现建议：

- 用 `system_locks` 表实现全局活动任务锁
- 用 `ip_usage_counters` 做 24 小时窗口统计
- 前端收到 `409 / 429` 后给出明确提示

## 11.4 断连策略

按 PRD func_22：

- 关闭页面
- 刷新页面
- 其他前端断连

统一视为放弃任务。

实现建议：

1. 前端在 `pagehide` 触发 `sendBeacon`
2. 后端以客户端 heartbeat 超时和 SSE 写入失败作为双重兜底判据
3. 一旦判定断连，立即：
   - 取消 orchestrator
   - 关闭 E2B 沙箱
   - 删除任务与制品
   - 写入 `task.terminated` 事件

## 11.5 外部工具容错

### `web_fetch`

`WebFetchClient` 应定义明确的容错边界：

- 默认总超时建议 30 秒
- 对空内容、非文本内容、上游拒绝访问、超时、5xx 响应统一转换为标准化 tool error
- tool error 以“失败但可继续”的 tool result 返回给 sub agent，由 sub agent 自主决定是否换源、换 query 或停止

### `python_interpreter`

- sandbox 内代码执行、文件读取、artifact 上传都应设置独立超时
- 所有失败都通过统一 tool error envelope 返回给 writer loop

## 11.6 可观测性与追踪

最少需要采集以下指标：

- `task_created_total`
- `task_completed_total`
- `task_failed_total`
- `task_terminated_total`
- `task_phase_duration_seconds`
- `llm_call_latency_seconds`
- `llm_call_fail_total`
- `tool_call_latency_seconds`
- `tool_call_fail_total`
- `risk_control_triggered_total`

追踪约定：

1. 每个 HTTP 请求生成 `request_id`，返回给客户端。
2. 每个 Task 生成一个贯穿生命周期的 `trace_id`，用于串联内部编排日志。
3. 所有上游请求都记录对方返回的 `request_id`，并与本地 `trace_id` 关联。

## 12. 前后端交互约束

## 12.1 前端页面模型

前端建议按以下区域组织：

- `ResearchInputPanel`
- `ResearchConfigPanel`
- `ClarificationPanel`
- `LiveTimelinePanel`
- `ReportViewer`
- `DownloadActions`
- `FeedbackComposer`

## 12.2 前端状态来源

前端状态只来源于两类输入：

1. REST 响应中的 `TaskSnapshot`
2. SSE 的 `EventEnvelope`

前端不自行推断业务状态机，不维护独立业务真相源。

补充约束：

1. 前端不解析 LLM 的原始选单 markdown；选单只消费后端输出的 `ClarificationQuestionSet`。
2. 前端不缓存 `task_token` 到 localStorage / IndexedDB，只保存在当前页面内存。
3. 前端收到 `task.terminated`、`task.failed` 或 SSE 流中断后，应立即切换到终止态 UI，不再尝试恢复任务。

## 12.3 Markdown 与图片渲染

前端渲染约束：

- 使用安全白名单渲染 markdown
- 禁止渲染任意原始 HTML
- 只允许加载本任务的 artifact URL
- 所有下载按钮都基于后端生成的制品

## 13. TDD 开发策略

## 13.1 测试分层

### 后端 Unit Tests

覆盖：

- 状态机流转
- Prompt builder
- LLM 输出 parser
- 同源去重算法
- 限次策略
- 风控识别逻辑
- 输出格式映射

### 后端 Contract Tests

覆盖：

- FastAPI OpenAPI 输出快照
- 请求/响应 schema
- SSE 事件 schema
- 错误响应 schema

### 后端 Integration Tests

覆盖：

- API + 数据库
- API + mocked 智谱 / Jina / E2B
- 任务创建、澄清、搜集、汇总、撰写、反馈完整流程
- 风控与重试分支

### 前端 Component Tests

覆盖：

- 研究输入与配置表单
- 选单澄清 15 秒倒计时
- SSE 事件渲染
- markdown 报告展示
- 下载与反馈入口状态

### E2E Tests

覆盖最小主链路：

1. 创建任务
2. 完成澄清
3. 观察搜集与撰写流式过程
4. 报告成功交付
5. 提交反馈并产出新 revision
6. 页面断连触发任务终止

## 13.2 建议测试工具

后端：

- `pytest`
- `pytest-asyncio`
- `httpx.AsyncClient`
- `respx`
- `pytest-mock`

前端：

- `vitest`
- `@testing-library/react`
- `playwright`
- `msw`

## 13.3 推荐开发顺序

### 第一阶段：先写契约与领域测试

1. `TaskSnapshot / RequirementDetail / CollectPlan / CollectSummary / EventEnvelope` schema 测试
2. `TaskStateMachine` 测试
3. OpenAPI contract 测试

### 第二阶段：实现任务框架

1. 创建任务
2. SSE 事件流
3. 任务锁与 IP 限制
4. 断连终止

### 第三阶段：实现需求阶段

1. 自然语言澄清
2. 选单澄清
3. 需求分析 parser

### 第四阶段：实现搜集引擎

1. master planning
2. sub agent collect
3. summary + barrier
4. source merge

### 第五阶段：实现输出引擎

1. outline preparation
2. writer + E2B
3. markdown zip / pdf 下载
4. feedback revision

## 14. 当前版本的最终建议

1. 架构上采用“单 FastAPI 服务 + 显式编排器 + PostgreSQL + SSE + Railway Volume”的简单稳定方案。
2. 领域上引入 `Task / Revision / SubTask / Event` 四个核心实体，足以覆盖 PRD 0.3 的全流程。
3. 契约上坚持 REST + SSE，前端只消费 `TaskSnapshot` 与 `EventEnvelope`。
4. 实现上先做 schema、状态机、契约测试，再落基础设施和业务编排，严格遵循 TDD。

如果后续开始正式开发，建议下一份文档直接进入：

- `docs/Backend_TDD_Plan.md`
- `docs/OpenAPI_v1.md`
- `docs/Frontend_IA.md`
