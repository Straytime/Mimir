# Mimir Frontend IA

## 1. 文档目的

本文档基于 [PRD 0.3](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Mimir_v1.0.0_prd_0.3.md)、[Architecture.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Architecture.md) 与 [OpenAPI_v1.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/OpenAPI_v1.md)，定义 Mimir 前端在正式开发前必须收敛的设计：

- Next.js App Router 下的页面与路由策略
- 前端信息架构与主要交互区块
- `TaskSnapshot` / `EventEnvelope` 驱动的客户端状态模型
- REST / SSE 消费方式、断连策略、下载刷新策略
- 组件边界、目录组织与视觉方向

本文档不进入业务代码实现，也不替代后续的前端测试计划。

## 2. 设计原则

1. 前端只负责输入、澄清交互、流式展示、下载与反馈，不承担业务编排。
2. 前端业务真相源只有两类：REST 返回的 `TaskSnapshot` / `TaskDetailResponse` 与 SSE `EventEnvelope`。
3. v1 不支持刷新恢复、断线重连、任务续跑，因此前端必须优先降低导航与刷新导致的状态丢失风险。
4. 浏览器直连 Railway API，不引入 Next.js BFF、Server Action 代理或自定义 websocket 层。
5. UI 优先服务“透明感”和“研究进行中”的可感知性，而不是堆叠过多调试信息。
6. 视觉风格采用极简科技风，桌面优先，但移动端必须可完成完整流程。

## 3. 路由与导航策略

### 3.1 路由结论

v1 推荐采用“单主路由工作台”：

| 路由 | 用途 | 说明 |
| --- | --- | --- |
| `/` | 首页 + 研究工作台 | 同一页面承载 idle、运行中、交付后、终态 |
| `/error` | 全局错误页 | Next.js 框架级错误兜底 |

不建议在 v1 为活跃任务使用 `/tasks/[taskId]` 之类的动态路由。

原因：

1. 当前版本不支持页面刷新后恢复任务，URL 中暴露 `task_id` 不带来真正的恢复能力。
2. `task_token` 只保存在内存，不持久化到 `localStorage` / `IndexedDB`；跨路由跳转只会增加状态丢失面。
3. v1 仍不支持刷新后恢复任务，单路由能最大化避免误触导航；若用户确认刷新或关闭页面，则通过显式断连语义放弃任务。

### 3.2 App Router 结构建议

```text
apps/web/
├─ app/
│  ├─ layout.tsx
│  ├─ page.tsx
│  ├─ loading.tsx
│  ├─ error.tsx
│  └─ globals.css
├─ features/
│  └─ research/
│     ├─ components/
│     ├─ hooks/
│     ├─ stores/
│     ├─ reducers/
│     ├─ mappers/
│     └─ schemas/
├─ lib/
│  ├─ api/
│  ├─ sse/
│  ├─ contracts/
│  └─ utils/
└─ components/ui/
```

实现边界建议：

- `app/page.tsx` 保持为薄壳，渲染 `ResearchPageClient`
- 所有任务交互逻辑都放在 client components 内
- 不使用 Next.js route handler 代理后端接口

`lib/contracts/` 用途建议：

- 存放与 [OpenAPI_v1.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/OpenAPI_v1.md) 对齐的 TypeScript 契约类型
- 至少包含：`TaskSnapshot`、`TaskDetailResponse`、`RevisionSummary`、`DeliverySummary`、`EventEnvelope`、`ClarificationQuestionSet`
- 前端内部 `features/research/schemas/` 可基于这些契约类型再补本地 UI schema，但不能改写后端字段语义

## 4. 页面信息架构

### 4.1 顶层页面状态

同一页面包含三种顶层视图模式：

1. `Idle`
   - 尚未创建任务
   - 展示输入区、配置区、产品价值说明
2. `ActiveWorkspace`
   - 已创建任务，正在澄清 / 分析 / 搜集 / 撰写 / 等待反馈
   - 展示工作台三栏布局
3. `Terminal`
   - 任务 `terminated` / `failed` / `expired`
   - 展示终态说明、清理提示、重新开始入口

### 4.2 Desktop 布局

桌面端采用 `3 / 6 / 3` 三栏工作台：

| 区域 | 主要内容 | 设计目标 |
| --- | --- | --- |
| 左栏 `Control Rail` | 输入、配置、澄清、反馈、下载、任务状态 | 承担所有可操作区 |
| 中栏 `Report Canvas` | 流式报告、图片、交付态结果 | 作为视觉中心与主要阅读区 |
| 右栏 `Live Timeline` | 当前阶段、事件时间线、轻量调试摘要 | 提供“系统正在做什么”的透明度 |

顶栏固定显示：

- `Mimir` 标识
- 当前连接状态
- 当前 phase / status
- 终止任务按钮

### 4.3 Tablet / Mobile 布局

移动端不保留三栏并列，改为单列 + 分段切换：

| 视口 | 布局 |
| --- | --- |
| `>= 1280px` | 三栏并列 |
| `768px - 1279px` | 左栏折叠为抽屉，中栏主内容，右栏可切换抽屉 |
| `< 768px` | 顶部状态条 + `操作 / 报告 / 进度` 三段切换 |

移动端原则：

1. 报告阅读优先。
2. 澄清与反馈输入始终可触达。
3. 时间线不与报告同时抢占主视口。

补充规则：

1. 当 `snapshot.phase === clarifying` 时，移动端将 `报告` 分段临时替换为 `澄清详情`。
2. `操作` 分段只保留输入与提交控件；流式追问文本、选单问题与倒计时移到 `澄清详情` 分段。
3. 当任务进入 `writing_report` 及之后阶段，再恢复 `报告` 分段。

## 5. 主要面板设计

### 5.1 `ResearchInputPanel`

职责：

- 输入初始研究需求
- 限制 `500` 字/单词
- 支持换行
- 提交后立即进入任务创建流程

显示时机：

- `Idle`

交互规则：

- `Enter` 提交，`Shift + Enter` 换行
- 任务创建中禁用输入与配置切换
- `409 resource_busy`、`429 ip_quota_exceeded` 直接在面板内提示

### 5.2 `ResearchConfigPanel`

职责：

- 切换澄清模式：`natural` / `options`

显示时机：

- `Idle`

交互规则：

- 默认 `natural`
- 任务创建后锁定，不允许在当前 Task 中变更

### 5.3 `ClarificationPanel`

根据 `clarification_mode` 分两种子模式：

1. `NaturalClarificationComposer`
   - 展示 `clarification.delta` 流式文本
   - 在 ready 后启用输入框
   - 提交 `answer_text`
2. `OptionsClarificationForm`
   - 只消费 `clarification.options.ready.question_set`
   - 每题默认选中 `o_auto`
   - 维护 15 秒倒计时
   - 支持手动提交与超时自动提交

前端约束：

1. 不解析原始 markdown 选单。
2. 倒计时仅为 UI 定时器；每次改选任意题目后重新开始 15 秒。
3. 发生 `clarification.fallback_to_natural` 后，应清空选单状态并切到自然语言模式。

### 5.4 `ReportCanvas`

职责：

- 渲染 `writer.delta` 拼接出的 markdown 正文
- 渲染 markdown 中引用的任务图片
- 在撰写前阶段提供占位态

子区域：

1. `ReportHeader`
   - 当前 revision 编号
   - 当前阶段说明
   - 交付后显示字数与图片数量
2. `ReportBody`
   - 流式 markdown 内容
3. `ArtifactGallery`
   - 展示已生成图片缩略图与标题

渲染约束：

- 使用 `react-markdown` + `rehype-sanitize`
- 禁止原始 HTML
- 只允许后端返回的 artifact URL
- `outline.delta` 不直接渲染为正文

### 5.4.1 Markdown 图片渲染策略

`ReportBody` 必须使用自定义 `img` renderer，而不是直接信任 markdown 中的原始 `src`。

规则：

1. 正文 markdown 的唯一 canonical 图片引用格式是 `mimir://artifact/{artifact_id}`；前端不把 `delivery.artifacts[].url` 直接当作正文 source of truth。
2. 渲染前先从 markdown `src` 中解析 `artifact_id`；若能解析出 `artifact_id`，优先使用 `stream.artifacts` 与 `remote.delivery.artifacts` 中该 `artifact_id` 对应的最新 URL，而不是直接使用正文里的旧 `access_token` URL。
3. 图片加载期间显示 skeleton，占位尺寸使用固定宽高比卡片，避免正文跳动。
4. 图片请求若返回 `401 access_token_invalid`，组件触发一次 `use-delivery-refresh`；刷新成功后通过 `artifact_id -> latest url` 映射重渲染，不直接修改 `reportMarkdown` 原文。
5. 若 `src` 不是 canonical artifact path，或刷新后仍无法加载，显示错误占位和“交付链接已失效”提示，不无限重试。
6. `markdown zip` 的离线重写由后端导出层负责；前端在线渲染不消费 `artifacts/{filename}` 这种离线路径。

### 5.4.2 Report Canvas 滚动与渲染策略

滚动行为：

1. 默认跟随最新内容自动滚动到底部。
2. 当用户手动上滚且距底部超过 `80px` 时，暂停自动滚动。
3. 暂停期间显示“回到底部”浮动按钮。
4. 用户点击按钮或重新滚到底部后，恢复自动滚动。

渲染性能策略：

1. `writer.delta` 先累积到内存 buffer，再以 `requestAnimationFrame` 或不高于 `100ms` 的节流频率刷新 markdown 渲染。
2. 报告渲染层使用 `useDeferredValue` 或等价方式降低长文本持续 parse 带来的卡顿。
3. v1 不对正文做虚拟列表；一万字量级优先通过增量节流解决。

### 5.5 `LiveTimelinePanel`

职责：

- 将复杂 SSE 事件归一为用户可理解的时间线
- 展示“正在做什么”
- 作为调试与排障的第一入口

展示策略：

- 用户主视图显示归一后的 timeline item，不直接暴露原始 event name
- 对 `analysis.delta`、`outline.delta`、`writer.reasoning.delta` 这类调试价值高、用户价值低的事件，仅保留轻量状态文案
- 本节文案表只定义时间线展示文案；事件写入 store 的权威规则见 §8

建议的用户可读阶段文案：

| 事件组 | 用户文案 |
| --- | --- |
| `clarification.*` | 正在确认研究范围 |
| `analysis.*` | 正在分析你的研究需求 |
| `planner.*` | 正在规划研究路径 |
| `collector.*` | 正在搜索与读取资料 |
| `summary.completed` | 正在整理阶段结论 |
| `sources.merged` | 正在去重并整理引用 |
| `outline.*` | 正在构思报告结构 |
| `writer.*` | 正在撰写报告 |
| `artifact.ready` | 已生成配图 |
| `report.completed` | 报告已完成 |

并发 sub-agent 展示策略：

1. v1 采用“线性时间线 + 明确标注所属搜集目标”的方案，不做多列并排。
2. 每个 `planner.tool_call.requested` 生成一条父级 timeline item，主标题直接展示 `collect_target`。
3. 后续 `collector.*` / `summary.completed` / `collector.completed` 事件，若携带 `subtask_id` 或 `tool_call_id`，都挂接到对应父级 item 下或显示统一标签。
4. `TimelineItem` 必须保留 `revisionId`、`subtaskId`、`toolCallId`、`collectTarget` 字段，为未来分组渲染留出余地。
5. 时间线默认始终自动滚动到最新事件，不提供手动暂停。

### 5.6 `DeliveryActions`

职责：

- 提供 `markdown zip` 和 `pdf` 下载
- 展示 access token 过期后的刷新反馈

显示时机：

- `awaiting_feedback + delivered`

交互规则：

1. 仅在 `available_actions` 包含 `download_markdown` / `download_pdf` 时启用。
2. 下载或图片请求若返回 `401 access_token_invalid`，前端先调用 `GET /tasks/{id}` 刷新 `delivery`，再重试一次。
3. 若重试后仍失败，提示“交付链接已失效或任务已清理”。
4. `pdf` 下载按钮需要 loading 状态，因为后端可能存在惰性 PDF 渲染延迟。
5. `markdown zip` 与 `pdf` 使用独立 loading state，避免重复点击与互相阻塞。
6. 当 `refreshingDelivery === true` 时，下载按钮与图片重试按钮统一禁用。

### 5.7 `FeedbackComposer`

职责：

- 输入反馈文本
- 提交新 revision

显示时机：

- `awaiting_feedback + delivered`

交互规则：

- 最长 `1000` 字/单词
- 提交后立即清空当前输入框并锁定操作区，等待新 revision 事件流
- 反馈提交成功后，先保留旧报告；当检测到新的 `revision_id` 成为活动 revision 时，再重置报告 buffer 并开始接收新正文
- 从 `POST /feedback` 返回到新 revision 首个事件到达之间，旧报告上方显示半透明 overlay，文案为“正在处理反馈并准备新一轮研究...”
- 时间线不清空；当新 revision 成为活动 revision 时，插入“第 N 轮研究开始”的分隔项

### 5.8 `Skeleton` 与占位态

最小占位策略：

1. 任务创建成功但 SSE 尚未建立时，工作台显示三栏 skeleton。
2. 澄清 LLM 正在生成时，`ClarificationPanel` 显示文本行 skeleton。
3. 进入 `writing_report` 前，`ReportCanvas` 显示段落 skeleton，而不是空白区。
4. 时间线收到 phase 切换但尚无后续细节时，插入一条轻量 skeleton row。

### 5.9 `TerminalBanner`

职责：

- 承接 `task.terminated`、`task.failed`、`task.expired`
- 阻断一切旧任务操作
- 提供“开启新研究”入口

文案要求：

- `terminated`: 明确告知因用户显式终止或确认离开页面导致任务结束
- `failed`: 明确显示错误摘要
- `expired`: 明确告知报告已过期并被清理

## 6. 客户端状态模型

## 6.1 状态分层

前端状态分为两层：

1. `Remote Authoritative State`
   - 来自 `TaskSnapshot`、`TaskDetailResponse`、`EventEnvelope`
   - 决定按钮是否可用、当前 phase、当前 revision、交付链接等
2. `Ephemeral UI State`
   - 只服务本地交互
   - 例如输入框草稿、倒计时截止时间、抽屉开关、toast

禁止把本地 UI 状态反向当作业务真相。

### 6.2 Store 建议

推荐使用一个不持久化的 `Zustand` store，按 slice 拆分：

```ts
type ResearchSessionStore = {
  session: {
    taskId: string | null;
    taskToken: string | null;
    traceId: string | null;
    requestId: string | null;
    eventsUrl: string | null;
    heartbeatUrl: string | null;
    disconnectUrl: string | null;
    connectDeadlineAt: string | null;
    sseState: "idle" | "connecting" | "open" | "closed" | "failed";
  };
  remote: {
    snapshot: TaskSnapshot | null;
    currentRevision: RevisionSummary | null;
    delivery: DeliverySummary | null;
  };
  stream: {
    analysisText: string;
    clarificationText: string;
    questionSet: ClarificationQuestionSet | null;
    reportMarkdown: string;
    outline: ResearchOutline | null;
    outlineReady: boolean;
    timeline: TimelineItem[];
    artifacts: ArtifactSummary[];
    lastEventSeq: number | null;
  };
  ui: {
    initialPromptDraft: string;
    clarificationDraft: string;
    feedbackDraft: string;
    optionAnswers: Record<string, string>;
    clarificationCountdownDeadlineAt: string | null;
    pendingAction:
      | "creating_task"
      | "submitting_clarification"
      | "submitting_feedback"
      | "disconnecting"
      | null;
    revisionTransition: {
      status: "idle" | "waiting_next_revision" | "switching";
      pendingRevisionId: string | null;
      pendingRevisionNumber: number | null;
    };
    reportAutoScrollEnabled: boolean;
    terminalReason: "terminated" | "failed" | "expired" | null;
  };
  deliveryUi: {
    refreshingDelivery: boolean;
    markdownDownloadState: "idle" | "loading" | "error";
    pdfDownloadState: "idle" | "loading" | "error";
  };
};
```

`TimelineItem` 建议最小结构：

```ts
type TimelineItem = {
  id: string;
  revisionId: string | null;
  kind: "phase" | "reasoning" | "collect" | "summary" | "tool_call" | "system";
  label: string;
  detail?: string;
  status: "running" | "completed" | "failed";
  occurredAt: string;
  subtaskId?: string;
  toolCallId?: string;
  collectTarget?: string;
};
```

规则：

1. `taskToken` 只保存在内存，不做 persistence middleware。
2. `writer.delta` 与 `clarification.delta` 直接累积到字符串 buffer，不把每个 delta 都塞入 timeline。
3. timeline 存归一后的 `TimelineItem`，而不是全量原始 event 副本。
4. 当 `active_revision_id` 发生切换时，必须清空上一轮的 `analysisText`、`clarificationText`、`questionSet`、`reportMarkdown`、`outline`、`artifacts` 与旧 `delivery`，避免跨 revision 污染。
5. `optionAnswers` 只在 `clarification.options.ready` 到达后初始化为“每题 -> o_auto”的映射，不能在 ready 前乐观创建。
6. 下载与交付刷新状态独立于 `pendingAction`，因为它们可与阅读或反馈输入并存。

### 6.3 派生状态

通过 selector 派生，不单独持久化：

- `isAwaitingClarification`
- `isResearchRunning`
- `isAwaitingFeedback`
- `canSubmitClarification`
- `canSubmitFeedback`
- `canDownloadMarkdown`
- `canDownloadPdf`
- `shouldShowCountdown`

派生规则必须完全基于：

- `snapshot.status`
- `snapshot.phase`
- `snapshot.available_actions`

## 7. REST 与 SSE 编排

### 7.1 创建任务

前端流程：

1. 用户提交初始需求与澄清模式。
2. 调用 `POST /tasks`。
3. 成功后立刻把 `task_id`、`task_token`、`trace_id`、`urls.*`、`connect_deadline_at` 写入 store。
4. 立刻启动 SSE 连接，不能等待额外用户动作。
5. 等待 `task.created` 作为首个权威快照。

前端不应在 `POST /tasks` 成功后再额外调用 `GET /tasks/{id}` 做初始化。

### 7.2 SSE 连接

实现建议：

- 使用 `@microsoft/fetch-event-source`
- 使用 `Authorization: Bearer {task_token}`
- 设置 `Accept: text/event-stream`
- 不使用浏览器原生 `EventSource`

规则：

1. 创建任务后应立即发起首个 SSE 连接，但超过 `connect_deadline_at` 不会再导致后端自动终止。
2. v1 不支持跨刷新恢复，但支持同一页面生命周期内的 SSE 自动重连。
3. 自动重连只在 `task_token` 仍在内存、页面未刷新/关闭、任务未终态、且用户未显式终止时生效。
4. 若连接失败、流中断或解析异常，只更新连接状态并在页内安排重连；不本地硬终止旧任务，也不跨刷新恢复旧任务。

### 7.3 心跳

前端在以下状态可持续发送 `POST /heartbeat`：

- `awaiting_user_input`
- `running`
- `awaiting_feedback`

调度规则：

1. 默认每 `20 秒` 发送一次。
2. 仅在 `sseState === "open"` 时运行。
3. heartbeat 用于活跃遥测，不再承担“保命”职责；若返回 `409 invalid_task_state` 或 `404 task_not_found`，前端停止轮询并按服务端已收口的状态进入终态提示。

### 7.4 断连与主动终止

分两类：

1. 用户点击“终止任务”
   - 走普通 `POST /disconnect`
   - 使用 header 鉴权
2. 页面关闭 / 刷新 / `pagehide`
   - 使用 `navigator.sendBeacon`
   - body 携带 `task_token`

浏览器端约束：

1. 当存在 `snapshot` 且 `status` 不属于 `terminated / failed / expired` 时注册 `beforeunload` 提示。
2. 自定义提示文案不可靠，应按浏览器默认行为处理。
3. `pagehide` 时尽量触发 `sendBeacon`，但 UI 不能假设 beacon 一定成功；若 beacon 未送达，任务可能继续在后端运行。

### 7.5 交付链接刷新

以下场景调用 `GET /tasks/{id}`：

1. `awaiting_feedback` 阶段主动刷新下载 / artifact URL
2. 下载或图片访问返回 `401 access_token_invalid`
3. 用户手动触发“刷新交付链接”

不用于：

- 页面刷新恢复旧任务
- SSE 中断后的断点续跑

### 7.6 Snapshot 合并规则

`task-snapshot-merger.ts` 的合并原则：

1. `POST /tasks` 返回的 `snapshot` 只用于初始化会话，不视为最终权威状态。
2. 首个 SSE `task.created.snapshot` 到达后，应整体覆盖初始化 snapshot。
3. 后续 SSE 事件优先更新 `snapshot.phase`、`snapshot.status`、`snapshot.available_actions` 与 `active_revision_id`。
4. `GET /tasks/{id}` 主要用于刷新 `current_revision` 与 `delivery`；若其 `snapshot.updated_at` 早于本地已有值，则只合并 `delivery`，不回滚更晚的 SSE 状态。
5. 任一终态事件 `task.failed` / `task.terminated` / `task.expired` 一旦到达，优先级最高，后续旧快照不得覆盖。

### 7.7 Feedback 后的 Revision 切换

前端处理规则：

1. `POST /feedback` 返回 `202` 后，立即写入 `revisionTransition.status = waiting_next_revision`，并记录 `pendingRevisionId` / `pendingRevisionNumber`。
2. 在等待阶段继续展示旧报告，但禁用反馈输入与下载动作。
3. 当收到新 `revision_id` 的首个 SSE 事件时，切换到 `revisionTransition.status = switching`，插入“第 N 轮研究开始”时间线分隔项。
4. 进入 `switching` 时，清空上一轮的流式 buffer、artifact 列表与旧 `delivery`。
5. 当新 revision 进入稳定活跃阶段后，回到 `revisionTransition.status = idle`。

## 8. 事件到 UI 的映射

本节是前端事件处理的权威映射；§5.5 的事件组文案只用于时间线展示。

| SSE 事件 | Store 更新 | 主 UI 行为 |
| --- | --- | --- |
| `task.created` | 覆盖 `snapshot` | 工作台进入活跃态 |
| `phase.changed` | 更新 `snapshot.phase/status` | 顶栏与时间线更新 |
| `heartbeat` | 更新连接健康时间 | 不额外打断用户 |
| `clarification.delta` | 追加 `clarificationText` | 展示追问流 |
| `clarification.options.ready` | 写入 `questionSet`、可用动作，并初始化 `optionAnswers` 为每题 `o_auto` | 展示选单并默认全选 `o_auto` |
| `clarification.natural.ready` | 标记可提交 | 启用澄清输入框 |
| `clarification.countdown.started` | 更新倒计时截止时间 | 启动 15 秒倒计时 |
| `clarification.fallback_to_natural` | 清空选单状态 | 切换为自然语言澄清 |
| `analysis.delta` | 追加 `analysisText` | 展示“正在分析需求”过程文本 |
| `analysis.completed` | 更新 `currentRevision.requirement_detail`，清空 `analysisText` | 在侧栏显示需求摘要 |
| `planner.reasoning.delta` | 追加到当前规划 timeline item 的 detail | 展示规划思考过程 |
| `planner.tool_call.requested` | 新增带 `collectTarget` 的 timeline item | 展示“正在搜集：{collect_target}” |
| `collector.reasoning.delta` | 追加到对应 `subtaskId` timeline item 的 detail | 展示子任务搜索思考 |
| `collector.search.*` / `collector.fetch.*` | 写入对应 `subtaskId` timeline item | 展示“正在搜索/读取资料” |
| `collector.completed` | 将对应 subtask timeline item 标记为完成 | 展示该搜集目标已完成 |
| `summary.completed` | 写入 timeline | 展示阶段结论已完成 |
| `sources.merged` | 写入 timeline | 展示来源去重结果 |
| `outline.delta` | `outlineReady = false` | 只显示“正在构思” |
| `outline.completed` | 写入 `outline`，`outlineReady = true` | 可在侧栏显示章节概览 |
| `writer.tool_call.requested` | timeline 增加工具调用项 | 显示“正在生成配图” |
| `writer.tool_call.completed` | 更新对应 `toolCallId` timeline item 为完成态 | 结束“正在生成配图”状态 |
| `writer.reasoning.delta` | 追加到当前写作 timeline item 的 detail | 展示轻量写作思考 |
| `writer.delta` | 追加 `reportMarkdown` | 实时渲染正文 |
| `artifact.ready` | 追加 artifact | 在报告与图库中可见 |
| `report.completed` | 更新 `delivery` | 下载区准备就绪 |
| `task.awaiting_feedback` | 更新 `snapshot` 与 `expires_at` | 展示反馈输入与下载按钮 |
| `task.failed` | 设置 `terminalReason = failed` | 切换失败态 |
| `task.terminated` | 设置 `terminalReason = terminated` | 切换终止态 |
| `task.expired` | 设置 `terminalReason = expired` | 切换过期态 |

额外约束：

1. `task.failed` / `task.terminated` / `task.expired` 一旦到达，必须禁用所有旧任务按钮。
2. `report.completed` 到达不等于一定可反馈；是否显示反馈区仍以后续 `task.awaiting_feedback` 与 `available_actions` 为准。

## 9. 组件边界与目录建议

### 9.1 `features/research/components`

建议组件：

- `research-page-client.tsx`
- `research-workspace-shell.tsx`
- `session-status-bar.tsx`
- `research-input-panel.tsx`
- `research-config-panel.tsx`
- `clarification-stream.tsx`
- `clarification-natural-composer.tsx`
- `clarification-options-form.tsx`
- `clarification-countdown.tsx`
- `requirement-summary-card.tsx`
- `timeline-panel.tsx`
- `report-canvas.tsx`
- `artifact-gallery.tsx`
- `delivery-actions.tsx`
- `feedback-composer.tsx`
- `terminal-banner.tsx`

### 9.2 `features/research/hooks`

建议 hooks：

- `use-create-task`
- `use-task-stream`
- `use-heartbeat-loop`
- `use-disconnect-guard`
- `use-clarification-submit`
- `use-feedback-submit`
- `use-delivery-refresh`
- `use-report-auto-scroll`
- `use-timeline-auto-scroll`

### 9.3 `features/research/reducers`

建议职责：

- `event-reducer.ts`
  - 把 `EventEnvelope` 归一为 store patch
- `timeline-mapper.ts`
  - 把事件映射为用户可读 timeline item
- `task-snapshot-merger.ts`
  - 统一处理 `POST /tasks`、`GET /tasks`、SSE snapshot 覆盖规则

## 10. 视觉与交互风格

### 10.1 风格方向

采用“浅色极简科技风”：

- 背景：冷白 + 很浅的蓝灰渐变，不做纯白平铺
- 强调色：青蓝 / 冰蓝
- 文字：深石墨灰
- 边框：细线、低对比、带轻微透明度
- 动效：只保留阶段切换、时间线插入、报告首屏淡入三类关键动效

### 10.2 字体建议

- 展示标题：`Space Grotesk`
- 正文：`IBM Plex Sans`
- 代码 / 时间线元数据：`IBM Plex Mono`

字体加载策略：

- 使用 `next/font` 加载字体，而不是运行时 CDN 注入
- 统一启用 `font-display: swap`
- 在 `app/layout.tsx` 里定义 CSS variables，并交给 Tailwind token 消费

### 10.3 主题范围

- v1 仅支持浅色主题
- 暗色模式不在当前版本范围内，避免在实现阶段引入额外状态与配色分叉

### 10.4 shadcn/ui 组件建议

优先使用：

- `Button`
- `Textarea`
- `Card`
- `RadioGroup`
- `Badge`
- `Alert`
- `Dialog`
- `ScrollArea`
- `Separator`
- `Tooltip`
- `Skeleton`

自定义视觉组件：

- `PhasePill`
- `ConnectionIndicator`
- `TimelineItemCard`
- `ArtifactThumb`

## 11. 错误态与边界行为

| 场景 | 前端处理 |
| --- | --- |
| `409 resource_busy` | 输入区内提示“当前系统正处理另一项研究，请稍后重试” |
| `429 ip_quota_exceeded` | 显示 `next_available_at` 与倒计时文案 |
| `422 validation_error` | 就地标红字段，不丢失已输入内容 |
| `401 task_token_invalid` | 视为当前会话失效，进入终止提示 |
| `401 access_token_invalid` | 先刷新 `delivery`，再重试一次 |
| SSE 中断 | 标记连接已关闭或失败，并在当前页面会话内自动重连；不本地硬终止任务 |
| `invalid_task_state` | 立即同步禁用按钮，并提示“任务状态已变更” |

额外说明：

1. 状态栏中的活跃性信号应展示“最近事件”或“最近服务端活动”，而不是“最近心跳”。
2. heartbeat 仍可用于活跃遥测，但不是任务是否仍在推进的唯一权威指标。

## 12. 可访问性与可测试性约束

1. 时间线区域使用 `aria-live="polite"`，但报告正文不做全量朗读。
2. 倒计时与终止确认必须可键盘操作。
3. 所有主要按钮都要有稳定的 `data-testid` 或语义 role。
4. 组件设计应允许用 scripted SSE 事件序列做测试，不依赖真实网络。

## 13. 与契约文档的边界

本文档补足的是“前端如何组织与消费契约”。

不在本文档展开的内容：

- OpenAPI 字段定义与错误码明细：见 [OpenAPI_v1.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/OpenAPI_v1.md)
- 后端状态机、Schema 与清理策略：见 [Architecture.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Architecture.md)
- 后端测试分层与阶段实施：见 [Backend_TDD_Plan.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Backend_TDD_Plan.md)

建议下一步继续输出独立的前端测试与实施计划文档，使页面状态设计与 TDD 顺序对齐。
