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
   - 展示居中的主舞台输入区、示例研究主题、轻量澄清模式配置
   - 顶部 hero 固定为大号纯白 uppercase `MIMIR` wordmark 与 slogan `Draw from depth.`，不再使用“小号品牌 overline + AI 研究工作台”组合
   - `MIMIR` 必须作为当前屏首最强视觉信号：字形全大写、纯白、不混入 amber 主色填充；允许通过 tracking 与尺寸建立压迫感，但不能依赖 glow、描边或多色渐变
   - slogan 属于弱信号元信息层：与 `MIMIR` 保持更紧的垂直间距，颜色低于主标题对比度；`Draw from depth` 主体必须持续明显弱于 `MIMIR`，且弱化效果应通过稳定的文本色阶与独立透明度类组合实现，不依赖在生产环境可能失效的单一 slash opacity 颜色写法；结尾句点以 terminal 风格下划线光标表现
   - terminal underscore 必须作为真实可见的 DOM 文本节点渲染，不得依赖 pseudo-element `content`、opacity 组合或仅存在 class 名而未实际出字的实现
2. `ActiveWorkspace`
   - 已创建任务，正在澄清 / 分析 / 搜集 / 撰写 / 等待反馈
   - 展示工作台三栏布局
   - 工作台卡片按统一的“phase + content readiness”规则渲染：只有内容已就绪的卡片才出现；空内容卡片不得仅因 phase 已推进就提前占位
3. `Terminal`
   - 任务 `terminated` / `failed` / `expired`
   - 展示终态说明、清理提示、重新开始入口

### 4.2 Desktop 布局

桌面端采用 `3 / 6 / 3` 三栏工作台：

| 区域 | 主要内容 | 设计目标 |
| --- | --- | --- |
| 左栏 `Control Rail` | 输入、配置、澄清、反馈、下载、任务状态 | 承担所有可操作区 |
| 中栏 `Report Canvas` | 流式报告、图片、交付态结果 | 作为视觉中心与主要阅读区 |
| 右栏 `Collection Trace` | 研究信息检索阶段的事件时间线 | 提供“系统正在搜集什么”的透明度 |

顶栏固定显示：

- `Mimir` 标识
- 当前连接状态
- 当前 phase / status，其中阶段主文案必须是顶栏最强信息
- 当前 `taskId` 原始值，但仅作为弱化的附属标识，不再附带 `taskId:` 前缀标签
- 任务控制按钮（运行中为“终止任务”，`delivered` 后切为“新研究”）

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
2. `操作` 分段只保留输入与提交控件；流式追问文本与选单问题移到 `澄清详情` 分段。
3. 选单澄清倒计时必须保留为工作台级全局可见 sticky surface，并固定停靠在顶栏下方；移动端与桌面端都不能把倒计时只埋在长问题列表内部，避免用户滚动时丢失剩余时间感知。
4. 当任务进入 `writing_report` 及之后阶段，再恢复 `报告` 分段。

## 5. 主要面板设计

### 5.1 `ResearchInputPanel`

职责：

- 输入初始研究需求
- 限制 `500` 字/单词
- 支持换行
- 提交后立即进入任务创建流程
- 提供 3 个可一键写入输入框的示例研究主题

显示时机：

- `Idle`

交互规则：

- `Enter` 提交，`Shift + Enter` 换行
- 任务创建中禁用输入与配置切换
- `409 resource_busy`、`429 ip_quota_exceeded` 直接在面板内提示
- Idle 态输入区必须位于主舞台视觉中心，placeholder 固定为 `想研究些什么？`
- 提交按钮不再显示文字 label，改为终端感回车符或抽象 icon，但必须保留可访问名称
- 输入区下方直接停靠轻量配置组件；配置组件与输入区属于同一主舞台堆叠，不再出现独立的“研究配置”大块
- 任务创建成功并进入 active workspace 后，输入区整体回到底部 fixed 输入托盘
- 示例研究主题固定为：
  - `从心理学角度解析 openclaw 爆火的原因`
  - `一级方程式赛车 26 年新规的争议与影响`
  - `新能源汽车电池技术路线对比：磷酸铁锂 vs 三元锂 vs 固态电池`
- 示例区域不再显示 `示例研究主题` 标题文案，仅保留主题按钮本身
- Idle 态示例卡片默认保持 recessed / docked 的低对比表面，基底固定为 `surface-container-lowest`；hover / focus 仅允许抬到 `surface-container-low` 一档，并配合左缘 `surface-tint` 细线 accent 与极轻 outline。
- ExamplePrompts 禁止使用 `shadow-glow-*`、`shadow-ghost`、整块亮到 `surface`、大幅 `translateY` 或任何看起来像漂浮 CTA slab 的 hover / focus 写法。

### 5.2 `ResearchConfigPanel`

职责：

- 切换澄清模式：`natural` / `options`

显示时机：

- `Idle`

交互规则：

- 配置组件直接可见文案固定为 `你喜欢什么样的需求沟通方式？`
- 选项名称固定为 `问答式`、`选项式`
- 默认 `options`
- hover / focus 到某个模式时，只显示该模式自己的提示文案：
  - `问答式`: `通过自然对话，开放式地向我反馈需求细节，适合复杂、需要详细说明的研究任务`
  - `选项式`: `通过自动生成的选单直接向我提供预设建议，适合快速启动`
- 选项 UI 必须保持低存在感、轻量、矩形 terminal selector，不得回退为大块卡片式入口；遵守 DESIGN.md 的 0px 硬边、无阴影、以 tonal change 而非漂浮感表达选中态
- 提示区必须作为 selector 容器的紧邻 attached hint / panel 渲染，不得依赖给父容器增加硬编码底部留白来“腾位置”
- selector region 必须作为 `relative` 锚点，hint panel 必须作为该区域内的 `absolute` attached overlay；hint 进入显示态时不得参与正常文档流、不得撑高容器、不得把 idle 主舞台整体向上顶
- hint panel 与 selector 下沿之间必须保留一个克制但明确的小间距，用于避免贴边和下沿遮挡感；该间距必须由 hint 自身的 overlay offset 提供，不能通过恢复到文档流或给外围容器补占位实现
- 提示区在 hover / focus 期间必须稳定可见；指针从选项移动到提示区本体时不得闪烁、提前消失或变得难以触发
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
   - 维护 30 秒倒计时
   - 支持手动提交与超时自动提交

前端约束：

1. 不解析原始 markdown 选单。
2. 倒计时仅为 UI 定时器；每次改选任意题目后重新开始 30 秒。
3. 发生 `clarification.fallback_to_natural` 后，应清空选单状态并切到自然语言模式。
4. 澄清详情标题固定为“需求澄清”，不再显示“在开始之前，有一些问题需要你的反馈”引导文案。
5. `ClarificationDetailPanel` 在进入 `clarifying` phase 后即渲染，至少显示标题与生成中占位；当 `clarificationText` 或 `questionSet` 就绪后再补齐具体内容。
6. 提交初始需求后，页面必须通过工作台级共享 card anchor 规则滚动到澄清详情卡片，不依赖单个卡片自身的局部滚动逻辑。
7. `clarification.delta` 文本或 `clarification.options.ready.question_set` 首次就绪时，即使仍处于同一 `clarifying` anchor key，也必须重新定位到澄清详情标题，使标题落在状态栏下方的统一留白区内。
8. 选单澄清倒计时不得并入 `SessionStatusBar` 的 taskId-only 下排；若需要保持全局可见，必须作为独立的工作台级 sticky surface。
9. 当 `clarification_mode === "options"` 且倒计时可见时，倒计时 surface 必须作为 `SessionStatusBar` 的紧邻下方 docked block 出现在同一全局 sticky top stack 中，两者之间不得再插入额外的留白 wrapper、stack gap 或分隔带；`TerminalBanner` 若存在，仍保持在该 top stack 的更下方。

### 5.4 `ReportCanvas`

职责：

- 渲染 `writer.delta` 拼接出的 markdown 正文
- 渲染 markdown 中引用的任务图片
- 作为报告正文首次就绪后的主阅读卡片

子区域：

1. `ReportHeader`
   - 固定显示 `Report Canvas` 区块标签
   - 当前阶段说明
   - 交付后只显示图片数量，不显示 revision 编号或报告轮次标题
2. `ReportBody`
   - 流式 markdown 内容

渲染约束：

- 使用 `react-markdown` + `rehype-sanitize`
- 禁止原始 HTML
- 只允许后端返回的 artifact URL
- `outline.delta` 不直接渲染为正文
- `ReportCanvas` 仅在 `reportMarkdown` 非空时挂载；`writing_report` / `delivered` phase 本身不足以触发空卡片占位
- Web 预览必须保留原始 footnote 语义，不得重编号、不得删除 definition、不得合成占位来源；如需修复 `ref` / `def` 别名，仅允许保守修复确认为同一来源的 alias，不得改写已正常匹配的正文或文末列表
- Web 预览可以隐藏 footnote backref 的可见符号与编号，但必须保留脚注编号列表、来源链接，以及正文中的 superscript 引用
- 工作台内的卡片采用阶段驱动渲染，未开始的卡片不提前渲染为空占位卡片；仅在对应阶段或内容准备好后才出现。

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

1. `writing_report` 流式阶段默认跟随最新内容自动滚动到底部，以保证写作过程可读。
2. 当用户手动上滚且距底部超过 `80px` 时，暂停自动滚动。
3. 暂停期间显示“回到底部”浮动按钮。
4. 用户点击按钮或重新滚到底部后，恢复自动滚动。
5. 当任务进入 `delivered` 且首次以交付态渲染 `Report Canvas` 时，正文滚动位置必须回到报告起始处，不得沿用流式阶段的“贴底”默认位置。
6. `delivered` 态仍允许用户自由滚动阅读，但不再因为交付态自身挂载或 metadata 更新而自动把正文推回底部。

渲染性能策略：

1. `writer.delta` 先累积到内存 buffer，再以 `requestAnimationFrame` 或不高于 `100ms` 的节流频率刷新 markdown 渲染。
2. 报告渲染层使用 `useDeferredValue` 或等价方式降低长文本持续 parse 带来的卡顿。
3. v1 不对正文做虚拟列表；一万字量级优先通过增量节流解决。

### 5.5 `CollectionTracePanel`

职责：

- 仅将信息检索阶段的 SSE 事件归一为用户可理解的结构化 trace
- 展示从 `planning_collection` 到 `merging_sources` 之间的搜集进展
- 作为检索过程的轻量透明度视图，不承载后续写作/交付阶段信息

展示策略：

- `Collection Trace` 卡片自身是根节点；卡片内部只展示一级 `plan round` 节点与一级终点 `sources merged` 节点
- 只消费 collection 相关事件：`planner.*`、`collector.*`、`summary.completed`、`sources.merged`
- `phase.changed` 只用于驱动阶段语义，不得单独作为空 `Collection Trace` 卡片的出现条件；卡片仅在 `stream.collectionTrace.nodes.length > 0` 时出现
- 本节只定义结构与展示语义；事件写入 store 的权威规则见 §8

建议的用户可读阶段文案：

| 事件组 | 用户文案 |
| --- | --- |
| `planner.*` | 正在规划研究路径 |
| `collector.*` | 正在搜索与读取资料 |
| `summary.completed` | 正在整理阶段结论 |
| `sources.merged` | 正在去重并整理引用 |

层级结构：

1. 每轮 planner loop 必须生成一个独立一级 `plan round` 节点，不能把后续轮次 reasoning 继续拼接到第一轮 plan 上。
2. `sources merged` 是整个 `Collection Trace` 的一级终点节点，与任意 `plan round` 同级。
3. 每个 `plan round` 下可以有多个 `collect group`；每个 group 以 `planner.tool_call.requested.tool_call_id` 为主键。
4. 当前前端设计预期中，planner 单轮一次最多同时发起 `3` 个 collect；若同一轮连续收到 `3` 个不同 `tool_call_id`，它们必须保留在同一个 `plan round` 内并按请求顺序显示。
5. 每个 `collect group` 内必须包含两个同级块：`collect` 与 `summary`。`summary` 是 `collect` 的延续，但不是 `collect.entries` 的子项。
6. `collect` 内部按时间顺序保留独立事件，不得把 reasoning、tool call、tool result 无边界地压扁成单个 `detail` 字符串。
7. `Collection Trace` 卡片在 `stream.collectionTrace.nodes.length > 0` 后出现，并在后续 `preparing_outline` / `writing_report` / `delivered` 阶段继续保留，作为历史卡片被上推显示。
8. 时间线默认始终自动滚动到最新事件，不提供手动暂停。

前端轮次推断规则：

1. 后端当前不提供显式 `round_id`，因此 `plan round` 必须在前端推断。
2. 若不存在活动 `plan round`，首个 `planner.reasoning.delta` 创建 `plan round 1`。
3. 若最近一个 `plan round` 已经包含至少一个 `collect group`，随后再次出现 `planner.reasoning.delta`，则必须开启新的 `plan round`，而不是继续追加到旧轮次。
4. 同一 `plan round` 内，连续的 `planner.reasoning.delta` 视为同一个 planner reasoning burst；直到出现 `planner.tool_call.requested` 或下一轮 plan 才结束。
5. `collect` 内的 reasoning round 也必须前端推断：连续的 `collector.reasoning.delta` 属于同一 reasoning round；一旦出现 `collector.search.started`、`collector.search.completed`、`collector.fetch.started`、`collector.fetch.completed` 或 `collector.completed`，当前 reasoning round 立即闭合，下一段 reasoning delta 必须开启新的 round。
6. `summary.completed` 不参与 round 切分；它只挂到对应 `collect group.summary`，并保留自身时间戳与状态。

数据约束：

1. `stream.collectionTrace` 是 `Collection Trace` 的权威数据结构。
2. collection 相关前端逻辑只能从 `stream.collectionTrace` 推导，不再保留旧 `stream.timeline` 兼容投影。
3. `outline.*`、`writer.*`、`artifact.ready`、`report.completed`、`task.awaiting_feedback` 均不得写入 `collectionTrace`。

UI 呈现规则：

1. `Collection Trace` 面板的主渲染输入必须来自 `stream.collectionTrace`。
2. 每个一级 `plan round` 节点使用独立 section 呈现，标题固定为 `Plan Round N`，并以比二级块更强的标题与边框权重表达顶层层级。
3. 每个 `collect group` 在同一 `plan round` 内按发生顺序渲染；组内 `collect` 与 `summary` 必须是两个同级块，不得把 `summary` 塞回 `collect.entries`。
4. `collect` 内部的 `reasoning`、tool event、`collect completed` 必须严格按时间顺序穿插显示；`search` 与 `fetch` 只允许在前端渲染层把同一对象的 `started/completed` 成对事件折叠为一条 tool row，不得改变它们相对 `reasoning` 与 `collect completed` 的时序位置，也不得合并为跨对象的单行摘要。
5. `plan reasoning`、`collect reasoning` 与 `summary` 默认只显示单行预览，并提供独立展开控制；展开状态必须按块隔离，不能通过一个按钮同时展开整张卡片。
6. `Sources Merged` 作为卡片末尾的一级终点节点直接完整显示，不进入折叠预览态。
7. `search` 与 `fetch` tool event 必须使用紧凑日志行呈现；默认以现有 `fetch` 行为基线，前端按 started/completed 成对折叠为单行，左侧只显示 `Search` 或 `Fetch`，中间显示对象，右侧显示当前状态（当前为 `Started` / `Done`，后续若有其他状态可沿用同一区域承载）。
8. 成对折叠必须是纯 UI 层行为：仅基于现有 `collect.entries` 顺序推导，不改 store、不改 mapper、不改 `CollectionTrace` 数据模型；若出现只有 completed 而无 matching started 的异常情况，必须安全降级为单行显示，而不是直接丢弃。
9. `search` 行的对象文本必须显示 query 本身，不再显示命中条数等 completed-only 文案；`fetch` 行的对象文本必须显示 URL 导向对象，优先使用 `hostname + 截断 path`，完整 URL 保留在可访问属性中，且内容容器必须使用 `min-w-0` 与单行截断策略，防止长 URL 向右溢出；completed 返回的标题文本不再显示在该行。
10. 紧凑 tool-event 行必须遵守 `DESIGN.md` 的 `Lab Terminal` 风格：使用统一的低侵入 tonal stacking 区分层级，不引入额外圆角漂移、阴影或 card-in-card 膨胀；`Search` 与 `Fetch` 不应再因为事件类型不同而产生分裂的视觉处理。`reasoning` 仍应明显是思考块，`summary` 仍应明显是阶段结论。
11. `Plan Round` 与 `Collect` 标题区右侧状态徽标必须保持单行、固定内容宽度优先，不得被左侧长标题或长 collect target 挤压到换行、压扁或变形成多行标签；标题区容器必须显式限制 `wrap` 与 `shrink` 行为。
12. `collect completed` 事件行仅保留事件标签与完成详情，不再重复渲染右侧 `已完成` 状态徽标；完成态信息以所在 `collect` 分组头部状态为准，避免同一块内双重完成反馈。

高度约束：

1. 长内容卡片不再使用固定 `34rem`。
2. `Collection Trace` 与 `Report Canvas` 共享同一动态卡片级 max-height token，该 token 由工作台“内容带”高度推导：上边界是 sticky 状态区底部后的统一留白起点，下边界是固定底部输入托盘上缘前的统一留白终点，而不是依据卡片自身当前文档位置推导。
3. 该约束作用于卡片容器本身；卡片头部保持固定可见，内部 body 才是滚动区。
4. 当页面从 `Idle` 进入 active workspace、顶栏挂载完成后，前端必须重新计算并写入该 token，不能只依赖首次挂载或窗口 resize。
5. 内容卡片进入当前关注阶段或首次出现时，页面级自动定位必须使用工作台级共享 card anchor 定义，而不是各卡片自行调用页面滚动。
6. 共享 card anchor 的目标位置是“卡片容器顶端对齐到顶栏下方统一留白”，其 offset 必须基于真实顶栏位置计算。
7. `Collection Trace` 与 `Report Canvas` 的内容刷新只允许滚动卡片内部容器，不得驱动页面级滚动。
8. 共享 card anchor 不能只依赖 anchor key 变化；同一张卡片在当前阶段内从“未就绪”变为“内容首次就绪”时，也必须触发页面定位。
9. 若同一轮状态更新中有多张内容卡片同时变为可见或可锚定，页面必须按既定卡片顺序选择更靠前的卡片作为锚点，例如 `Report Canvas` 与 `DeliveryActions` 同时出现时优先锚到 `Report Canvas`。
10. `澄清详情` 与 `Requirement Summary` 两张卡片的 anchor 目标位置都不是卡片外层容器顶边；前者应让“澄清详情”标题贴合状态栏下方统一留白，后者应让需求摘要内容区默认完整露出，不被卡片标签或过多上边距挤出首屏。
11. 在 `planning_collection`、`collecting`、`summarizing_collection`、`merging_sources` 阶段，只要 `Collection Trace` 已可见，它就是页面级自动锚点的优先目标；同阶段内 trace 内容更新时，即使 `nodes.length` 不变，也必须重新锚定到 `Collection Trace` 自身，不能回退到先前已锚定过的 `Requirement Summary`。
12. 共享 max-height token 的计算必须对 `Collection Trace` 与 `Report Canvas` 一致生效，确保两张长卡都占满同一可视内容带，并与统一 anchor 留白规则兼容。

### 5.5.1 `OutlineCard`

职责：

- 在 `outline.ready` 后提供报告结构预览
- 作为 `Report Canvas` 之前的阅读引导，而不是纯技术占位

展示规则：

1. `OutlineCard` 只在 `outlineReady === true` 且存在 `outline` 时渲染。
2. 视觉结构必须体现 `DESIGN.md` 的 `Lab Terminal` 风格，但本卡片应走更轻、更干净的阅读引导方向：通过 leading-zero 编号、分层 tonal stacking、留白与轻量 ghost outline 建立层次，不得回退到 amber 大面积底色或厚重的高对比堆叠。
3. 卡片头部保留 `Outline` 技术标签、报告标题与章节总数；标题区应以中性 surface 为主，amber 只作为小面积点状 accent，不主导标题、计数块或整卡文本色。
4. 各 section 必须按 `order` 顺序渲染，并显式展示 `01`、`02` 这类编号，强化终端式结构感；每个 section 至少应拆分为“编号 / 标题”两层信息。
5. 若后端提供 `description`，前端在该卡片中仍不展示，避免提前泄露章节展开内容；章节列表只暴露 ordered titles，不额外添加摘要段落。
6. section 之间通过留白、tone shift 与内外 surface 的嵌套形成“薄板叠层”关系，不使用 1px 横线切割，不制造 bloated panel 或 amber-heavy 信息墙。

### 5.11 `UnifiedInputBar`

职责：

- 统一承接初始需求与自然语言澄清输入
- 在 `Idle` 时作为主舞台中央输入区显示；进入 active workspace 后固定停靠底部

视觉与布局规则：

1. `Idle` 态输入区不得以底部 fixed tray 形式出现；active workspace 中才采用 fixed 底部的嵌入式 surface 处理，而不是显式的外层 docked tray 包裹内层输入块。
2. 不使用显式 `border-top` 作为主要分隔手段；若出于可访问性需要保留边界感，只能使用极弱的 ghost boundary、背景过渡或内阴影式处理，不能形成“硬切线”。
3. 输入区在 active workspace 中仍是固定底部的页面级共享区域，`Collection Trace` / `Report Canvas` 的 max-height 计算必须扣除其实际占位与预留留白。
4. `textarea` 高度必须随输入行数增长，但需要设置明确上限；超过上限后改为内部滚动，不继续推高页面级底栏。
5. 提交按钮在单行与多行输入下都必须保持稳定的固定尺寸与对齐方式，不因 `textarea` 增高而塌缩、拉伸或偏离点击热区。
6. 文本输入区与提交按钮必须保持同一视觉表面语言，避免出现“外层底栏 + 内层输入块”的双层托盘感；按钮固定宽高与现有交互语义保持不变，且不显示文字 `提交`。
7. `Idle` 态 placeholder 固定为 `想研究些什么？`；其余 phase 仍按既有任务状态语义切换 placeholder 与禁用状态。
8. 本次视觉调整不改变提交热键、delivered 态新研究确认逻辑或澄清模式切换语义。

### 5.6 `DeliveryActions`

职责：

- 提供 `markdown zip` 和 `pdf` 下载
- 展示 access token 过期后的刷新反馈
- 内嵌展示已生成图片缩略图与标题
- 不展示报告字数

显示时机：

- `awaiting_feedback + delivered`

交互规则：

1. 仅在 `available_actions` 包含 `download_markdown` / `download_pdf` 时启用。
2. 下载或图片请求若返回 `401 access_token_invalid`，前端先调用 `GET /tasks/{id}` 刷新 `delivery`，再重试一次。
3. 若重试后仍失败，提示“交付链接已失效或任务已清理”。
4. `pdf` 下载按钮需要 loading 状态，因为后端可能存在惰性 PDF 渲染延迟。
5. `markdown zip` 与 `pdf` 使用独立 loading state，避免重复点击与互相阻塞。
6. 当 `refreshingDelivery === true` 时，下载按钮与图片重试按钮统一禁用。
7. `delivered` 后不在 `DeliveryActions` 渲染“开始新研究”入口；新研究入口统一由 `SessionStatusBar` 顶栏按钮承接。
8. `Artifact Gallery` 不再作为独立工作台卡片出现；所有配图缩略图、空态文案与 lightbox 入口统一并入 `DeliveryActions` 卡片内部。

### 5.7 `FeedbackComposer`

v1 前端不开放 `FeedbackComposer`。

规则：

- 即使后端进入 `awaiting_feedback + delivered`，前端也只保留下载与报告阅读视图，不渲染反馈输入区。
- `POST /feedback`、revision 切换 overlay 与相关入口在前端全部隐藏；相关后端契约仅保留为未启用能力。
- 若 store 中带有 `feedbackDraft`、`feedbackSubmitError`、`revisionTransition` 等状态，前端必须安全降级，不暴露对应 UI。

### 5.8 `Skeleton` 与占位态

最小占位策略：

1. 任务创建成功但 SSE 尚未建立时，工作台显示三栏 skeleton。
2. 澄清、需求摘要、搜集轨迹、大纲、报告、交付这几类主工作台卡片都遵循“空内容不显示”的统一规则，不因为 phase 已进入就渲染空壳 card。
3. 图片加载或报告正文内部的局部加载态可以使用 skeleton，但不得借此提前挂载尚无正文的 `ReportCanvas`。
4. `Collection Trace` 只有在已有至少一个节点后才可见；若未来需要 skeleton，只能作为已出现卡片内部的局部行状态，而不是空卡片占位。
5. 除以上明确的 skeleton 场景外，未开始的卡片不应以空卡片或占位文案提前占据版面。

### 5.9 `TerminalBanner`

职责：

- 承接 `task.terminated`、`task.failed`、`task.expired`
- 阻断一切旧任务操作
- 提供“开启新研究”入口

文案要求：

- `terminated` 主标题固定为 `任务已终止`
- `terminated` 次要文案必须只根据后端 `payload.reason` 做稳定映射；不得再通过单独标题分支表达不同终止原因
- `terminated` 的 `reason` 映射固定为：
  - `sendbeacon_received`: `系统已收到页面关闭信号，当前任务已停止。旧任务操作不可恢复，请重新创建研究。`
  - `client_disconnected`: `当前页面已主动断开连接，任务已停止。旧任务操作不可恢复，请重新创建研究。`
  - `heartbeat_timeout`: `任务因长时间未收到心跳而停止。旧任务操作不可恢复，请重新创建研究。`
  - `sse_connect_timeout`: `任务因长时间未建立事件连接而停止。旧任务操作不可恢复，请重新创建研究。`
  - `server_shutdown`: `服务端连接已中断，当前任务被终止。旧任务操作不可恢复，请重新创建研究。`
  - `risk_control_limit`: `研究内容触发了平台内容安全策略，当前任务已停止。请调整研究主题后重新创建研究。`
- `terminated` 若缺少 `reason` 或 reason 不在映射表内，回退到通用文案：`当前任务已停止，旧任务操作不可恢复，请重新创建研究。`
- `failed` 当前只展示统一失败 error summary 路径，不新增细粒度 reason 状态
- `expired` 当前只基于 `expired_at` 告知报告已过期并被清理
- 所有“旧任务操作已禁用”类信息只允许出现在次要文案中，不再出现在主标题中

### 5.10 `SessionStatusBar`

职责：

- 承接会话连接状态、当前阶段标题与任务标识
- 作为工作台顶栏的轻量状态条
- 承接顶栏唯一任务控制按钮

展示规则：

1. 状态栏必须收紧为单层、薄而平的 docked terminal header，不再展示第二排的大号中文阶段标题。
2. 当前阶段只以单个 stage chip 呈现；非 terminal 且未进入 `delivered` 的阶段，chip 尾部必须显示循环省略号动效，作为唯一持续活跃信号。
3. `taskId` 只作为弱化的技术标识出现，并与 chip 同排或尾部贴靠排布；不得回退为独立强调行，也不得展示阶段补充小字、`analysisText` 或搜集进度。
4. `taskId` 的可见文案必须直接显示原始 id 值本身，不再追加 `taskId:`、`ID:` 或其他说明性前缀。
5. `writing_report` 阶段的阶段语义仍固定对应“正在生成研究内容”，但该文案不再作为大号独立标题行显示。
6. 当 `snapshot.phase === delivered` 且任务未进入 terminal status 时，顶栏按钮文案切为“新研究”，点击直接调用 `reset`，不走 disconnect。
7. 非 `delivered` 的非 terminal 任务继续显示“终止任务”，并保持原有 disconnect 行为不变。

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
    collectionTrace: CollectionTraceRoot;
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
    terminationDetail:
      | "sendbeacon_received"
      | "client_disconnected"
      | "heartbeat_timeout"
      | "sse_connect_timeout"
      | "server_shutdown"
      | "risk_control_limit"
      | null;
  };
  deliveryUi: {
    refreshingDelivery: boolean;
    markdownDownloadState: "idle" | "loading" | "error";
    pdfDownloadState: "idle" | "loading" | "error";
  };
};
```

`CollectionTraceRoot` 建议结构：

```ts
type CollectionTraceRoot = {
  nodes: CollectionTraceNode[];
};

type CollectionTraceNode = CollectionPlanRoundNode | CollectionSourcesMergedNode;

type CollectionPlanRoundNode = {
  id: string;
  kind: "plan_round";
  revisionId: string | null;
  roundIndex: number;
  label: string;
  status: "running" | "completed" | "failed";
  occurredAt: string;
  reasoningBursts: CollectionReasoningBurst[];
  collectGroups: CollectionCollectGroup[];
};

type CollectionCollectGroup = {
  id: string;
  revisionId: string | null;
  toolCallId: string;
  subtaskId?: string;
  collectTarget?: string;
  occurredAt: string;
  collect: CollectionCollectNode;
  summary: CollectionSummaryNode | null;
};

type CollectionCollectNode = {
  id: string;
  kind: "collect";
  label: string;
  status: "running" | "completed" | "failed";
  occurredAt: string;
  entries: CollectionCollectEntry[];
};

type CollectionCollectEntry =
  | CollectionReasoningBurst
  | CollectionToolEvent
  | CollectionCollectCompletedEvent;

type CollectionReasoningBurst = {
  id: string;
  kind: "reasoning_burst";
  occurredAt: string;
  detail: string;
};

type CollectionToolEvent = {
  id: string;
  kind:
    | "search_started"
    | "search_completed"
    | "fetch_started"
    | "fetch_completed";
  occurredAt: string;
  label: string;
  detail?: string;
};

type CollectionCollectCompletedEvent = {
  id: string;
  kind: "collect_completed";
  occurredAt: string;
  status: "completed" | "failed";
  detail: string;
};

type CollectionSummaryNode = {
  id: string;
  kind: "summary";
  occurredAt: string;
  status: "completed" | "failed";
  detail?: string;
};

type CollectionSourcesMergedNode = {
  id: string;
  kind: "sources_merged";
  occurredAt: string;
  status: "completed";
  sourceCountBeforeMerge: number;
  sourceCountAfterMerge: number;
  referenceCount: number;
  detail: string;
};
```

规则：

1. `taskToken` 只保存在内存，不做 persistence middleware。
2. `writer.delta` 与 `clarification.delta` 直接累积到字符串 buffer，不把每个 delta 都塞入 collection 事件流。
3. collection 相关事件必须写入 `collectionTrace`，而不是压扁为单个 detail 字符串。
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

v1 前端不开放 feedback/revision 交互，因此主流程不进入前端 revision 切换 UI。

约束：

1. 后端仍可保留 `POST /feedback` 与 revision 状态机，但前端不提供提交入口。
2. 若 store 因异常状态带有 `revisionTransition` 数据，前端只做安全降级，不渲染 feedback composer 或 revision overlay。
3. `Collection Trace`、报告正文、交付下载继续按现有只读视图工作。

## 8. 事件到 UI 的映射

本节是前端事件处理的权威映射；§5.5 的事件组文案只用于 `Collection Trace` 展示。

| SSE 事件 | Store 更新 | 主 UI 行为 |
| --- | --- | --- |
| `task.created` | 覆盖 `snapshot` | 工作台进入活跃态 |
| `phase.changed` | 更新 `snapshot.phase/status` | 顶栏更新；进入 `planning_collection` 时开启 `Collection Trace` |
| `heartbeat` | 更新连接健康时间 | 不额外打断用户 |
| `clarification.delta` | 追加 `clarificationText` | 展示追问流 |
| `clarification.options.ready` | 写入 `questionSet`、可用动作，并初始化 `optionAnswers` 为每题 `o_auto` | 展示选单并默认全选 `o_auto` |
| `clarification.natural.ready` | 标记可提交 | 启用澄清输入框 |
| `clarification.countdown.started` | 更新倒计时截止时间 | 启动 30 秒倒计时 |
| `clarification.fallback_to_natural` | 清空选单状态 | 切换为自然语言澄清 |
| `analysis.delta` | 追加 `analysisText` | 只在侧栏显示“正在分析需求”过程文本，不进入 `Collection Trace` |
| `analysis.completed` | 更新 `currentRevision.requirement_detail`，清空 `analysisText` | 在侧栏显示需求摘要，不进入 `Collection Trace` |
| `planner.reasoning.delta` | 追加到当前 `plan round.reasoningBursts`；必要时开启新 `plan round` | 进入 `Collection Trace` 的规划层 |
| `planner.tool_call.requested` | 在当前 `plan round` 下新建 `collect group` | 进入 `Collection Trace` 的搜集层 |
| `collector.reasoning.delta` | 追加到对应 `collect group.collect.entries` 的 reasoning burst；必要时开启新 burst | 进入 `Collection Trace` |
| `collector.search.*` / `collector.fetch.*` | 作为独立工具事件写入对应 `collect group.collect.entries` | 进入 `Collection Trace` |
| `collector.completed` | 作为独立完成事件写入对应 `collect group.collect.entries` 并更新 `collect.status` | 进入 `Collection Trace`，展示该搜集目标已完成 |
| `summary.completed` | 写入对应 `collect group.summary` | 进入 `Collection Trace`，展示阶段结论已完成 |
| `sources.merged` | 追加一级 `sources merged` 终点节点 | 进入 `Collection Trace`，展示来源去重结果 |
| `outline.delta` | `outlineReady = false` | 只影响章节概览预备态，不进入 `Collection Trace` |
| `outline.completed` | 写入 `outline`，`outlineReady = true` | 只影响章节概览可见性，不进入 `Collection Trace` |
| `writer.tool_call.requested` | 更新写作相关状态 | 不进入 `Collection Trace` |
| `writer.tool_call.completed` | 更新写作相关状态 | 不进入 `Collection Trace` |
| `writer.reasoning.delta` | 追加到当前写作 buffer | 不进入 `Collection Trace` |
| `writer.delta` | 追加 `reportMarkdown` | 实时渲染正文 |
| `artifact.ready` | 追加 artifact | 在报告与图库中可见，不进入 `Collection Trace` |
| `report.completed` | 更新 `delivery` | 下载区准备就绪，不进入 `Collection Trace` |
| `task.awaiting_feedback` | 更新 `snapshot` 与 `expires_at` | 保持下载按钮可用，但不展示反馈输入 |
| `task.failed` | 设置 `terminalReason = failed` | 切换失败态；当前只走统一失败摘要路径 |
| `task.terminated` | 设置 `terminalReason = terminated` 与 `terminationDetail = payload.reason ?? null` | 切换终止态，并驱动终止次要文案映射 |
| `task.expired` | 设置 `terminalReason = expired` | 切换过期态 |

额外约束：

1. `task.failed` / `task.terminated` / `task.expired` 一旦到达，必须禁用所有旧任务按钮。
2. `report.completed` 到达不等于一定可反馈；v1 前端不渲染反馈区，即使后端后续进入 `task.awaiting_feedback`。

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

### 9.3 `features/research/reducers`

建议职责：

- `event-reducer.ts`
  - 把 `EventEnvelope` 归一为 store patch
- `timeline-mapper.ts`
  - 把事件映射为 `collectionTrace` 与 `outlineReady`
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
- `CollectionTraceEntryCard`
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

1. `Collection Trace` 区域使用 `aria-live="polite"`，但报告正文不做全量朗读。
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
