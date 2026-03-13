# Mimir Frontend TDD Plan

## 1. 文档目的

本文档定义 Mimir 前端在进入正式编码前的 TDD 实施方案，目标是把 [Frontend_IA.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Frontend_IA.md)、[Architecture.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Architecture.md) 与 [OpenAPI_v1.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/OpenAPI_v1.md) 收敛成一套可执行、可验收、可持续推进的前端开发计划。

本文档回答四个问题：

1. 前端测试如何分层。
2. 每层测试应该覆盖什么，不应该覆盖什么。
3. 前端应按什么顺序推进，才能最小化流式交互与状态管理风险。
4. 每个阶段达到什么标准，才能进入下一阶段。

## 2. 输入与不可违背约束

前端实施必须同时满足以下前置设计约束：

- 使用 `Next.js App Router + TailwindCSS + shadcn/ui`。
- 浏览器直连 Railway API，不引入 Next.js BFF、Route Handler 代理或自定义 websocket 层。
- 前端业务真相源只有 `TaskSnapshot` / `TaskDetailResponse` / `EventEnvelope`。
- 接口契约以 `REST + SSE` 为准，且 v1 不支持自动重连、刷新恢复或断点续跑。
- `task_token` 只保存在页面内存，不写入 `localStorage` / `IndexedDB`。
- 页面刷新、关闭、SSE 中断都视为任务放弃；前端必须优先展示终止态，而不是尝试恢复。
- 选单澄清只消费后端输出的结构化 `ClarificationQuestionSet`，前端不解析 LLM 原始 markdown。
- 下载、图片访问与 feedback 的启用条件一律以 `available_actions`、`status`、`phase` 为准。
- 所有影响外部行为的实现变更都必须先反映到文档与测试，再进入代码。

## 3. TDD 工作原则

## 3.1 Red-Green-Refactor 的执行粒度

前端同样不采用“整页写完再补测试”的伪 TDD。最小增量示例：

- 一个 selector
- 一个 reducer 分支
- 一个组件状态切换
- 一个错误态分支
- 一个 SSE 事件映射
- 一个按钮是否可用的 gating 规则
- 一个滚动或倒计时行为

每个增量都按以下顺序推进：

1. 先写失败测试。
2. 只写让该测试通过的最小实现。
3. 重构实现，但不得改变既定契约。
4. 再写下一条失败测试。

## 3.2 Contract-First 规则

以下行为一律视为前端不可擅改的外部契约：

- REST 请求与响应字段
- SSE 事件名与 payload
- `available_actions` 的语义
- `task_token` / `access_token` 的使用方式
- 终态后的 UI 行为
- 下载刷新与 `access_token_invalid` 的处理约定

规则：

1. 若要修改接口、事件或错误码，先更新 [OpenAPI_v1.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/OpenAPI_v1.md)。
2. 若要修改页面信息架构、状态来源或 UI 生命周期，先更新 [Frontend_IA.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Frontend_IA.md)。
3. 文档未更新前，不允许通过实现“偷偷改变”行为。

## 3.3 决定性优先

所有前端测试都必须尽量避免真实网络、真实时间和不可控浏览器行为带来的不稳定性。

必须可控的依赖：

- `Clock` / fake timers
- `TaskApiClient`
- `TaskEventSource`
- `navigator.sendBeacon`
- `beforeunload` / `pagehide`
- `ResizeObserver`
- `IntersectionObserver`
- `matchMedia`
- `scrollTo` / scroll container metrics

测试中禁止：

- 真实调用后端 API
- 真实等待 15 秒倒计时
- 用整页 DOM snapshot 代替语义断言
- 依赖浏览器默认重连或默认滚动行为

## 3.4 语义断言优先于快照

不建议对以下内容做大范围 snapshot：

- 整页 DOM
- 长 markdown 正文
- 长时间线列表
- 整个 Zustand store

应优先断言：

- 按钮是否 enabled / disabled
- 文案是否出现
- 某个 timeline item 是否进入 `running / completed`
- 某个 `revision_id` 切换后旧内容是否被清空
- 某个 SSE 事件是否触发预期 state patch

仅在少量稳定场景保留 snapshot：

- 静态空态布局
- 终态 banner 的骨架结构

## 3.5 CI 中禁止真实后端依赖

CI 中不允许：

- 调用真实 Railway 后端
- 依赖真实 SSE 流
- 依赖真实下载文件生成

CI 只能使用：

- `MSW` mock REST
- `ScriptedTaskEventSource`
- Playwright 下的 lightweight mock API server
- fake browser APIs

真实后端联调只允许出现在手动 smoke 检查中。

## 4. 测试分层

建议前端测试目录结构：

```text
apps/web/tests/
├─ unit/
│  ├─ reducers/
│  ├─ selectors/
│  ├─ mappers/
│  └─ utils/
├─ contract/
│  ├─ api/
│  ├─ sse/
│  └─ types/
├─ component/
│  ├─ panels/
│  ├─ timeline/
│  ├─ report/
│  └─ delivery/
├─ integration/
│  ├─ workspace/
│  ├─ stream/
│  └─ revision/
├─ e2e/
│  ├─ fixtures/
│  └─ specs/
├─ smoke/
│  └─ preview/
└─ fixtures/
```

目录职责约定：

- `tests/fixtures/`：Vitest 层共享的 render helper、store factory、browser API mock、builder
- `tests/e2e/fixtures/`：Playwright 层共享的 page objects、mock server 启停脚本、SSE 剧本装载器

## 4.1 Unit Tests

目标：

- 验证纯前端规则，不触及真实 DOM 或只触及最小 DOM
- 尽早固化 store、selector、mapper 与 reducer 的行为

必须覆盖：

- `event-reducer`
- `task-snapshot-merger`
- timeline mapper
- `available_actions` gating selectors
- `revisionTransition` 流转
- markdown artifact URL 解析
- auto-scroll 判定逻辑
- countdown deadline 计算

不应覆盖：

- 组件布局细节
- 真正的 SSE 订阅
- Playwright 浏览器行为

## 4.2 Contract Tests

目标：

- 保证前端消费的契约与 [OpenAPI_v1.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/OpenAPI_v1.md) 一致
- 尽可能早发现字段漂移、事件缺失或 mapper 假设错误

必须覆盖：

- `TaskSnapshot` / `TaskDetailResponse` fixture 与 TypeScript 类型兼容
- `EventEnvelope` fixture 与事件 union 对齐
- `clarification.options.ready` / `task.awaiting_feedback` / `report.completed` 等关键 payload 形状
- [Frontend_IA.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Frontend_IA.md) §8 事件映射表中的每个 SSE event 都至少有一条 fixture 测试

实现方式：

- 使用 `lib/contracts/` 中的类型
- 使用稳定 fixture + builder
- 必要时对关键 event payload 增加运行时 schema

## 4.3 Component Tests

目标：

- 验证单个组件或单个面板在给定 state 下的行为正确
- 覆盖交互、禁用态、倒计时、滚动和错误提示

必须覆盖：

- `ResearchInputPanel`
- `ResearchConfigPanel`
- `ClarificationPanel`
- `ClarificationCountdown`
- `LiveTimelinePanel`
- `ReportCanvas`
- `DeliveryActions`
- `FeedbackComposer`
- `TerminalBanner`

重点行为：

- `o_auto` 默认选中
- 倒计时重置
- auto-scroll 暂停 / 恢复
- markdown 图片错误占位
- 下载按钮 loading / disabled
- feedback overlay

## 4.4 Integration Tests

目标：

- 在“真实 React 树 + store + mocked REST + scripted SSE”下验证工作台级协作
- 优先覆盖最容易出错的跨组件状态同步

必须覆盖：

- 创建任务后立即启动 SSE，而不是额外先 `GET /tasks`
- SSE `task.created` 覆盖初始化 snapshot
- `heartbeat` loop 的启动 / 停止
- stream 中断后立即进入终止态
- `report.completed` 与 `task.awaiting_feedback` 的先后约束
- `access_token_invalid` 刷新 `delivery`
- feedback 新 revision 切换
- `beforeunload` / `sendBeacon` 注册与触发

依赖边界：

- REST 通过 `MSW` mock
- SSE 通过 `ScriptedTaskEventSource`
- 浏览器 API 通过 fake/mock

## 4.5 E2E Tests

目标：

- 在真实浏览器中验证最小主链路可用
- 不追求覆盖所有状态分支

必须覆盖：

1. 创建任务
2. 完成澄清
3. 观察时间线与正文流式变化
4. 报告交付后下载按钮可用
5. 提交 feedback 并进入新 revision
6. 页面断连触发终止

实现方式：

- 使用 `Playwright`
- 启动 Next.js 前端
- 通过 lightweight mock API server 提供 REST + SSE + download 响应

不建议在 E2E 中直接依赖真实 FastAPI 或真实外部服务。

## 4.6 Manual Smoke Tests

目标：

- 在接近真实部署环境下验证前端与后端的接线正确
- 不进 PR 必过门禁

最小 smoke 清单：

1. 创建任务后 10 秒内可成功建立 SSE。
2. 自然语言澄清能完成一轮提交。
3. 选单澄清能自动倒计时提交。
4. 时间线能展示 `collect_target`。
5. 报告中的 artifact 图片能正常加载。
6. 下载 `markdown zip` 与 `pdf` 至少各成功一次。
7. feedback 后能进入新 revision。
8. 页面关闭或刷新会终止任务。

## 5. 测试工具与基础设施

建议工具：

- `vitest`
- `jsdom`
- `@testing-library/react`
- `@testing-library/user-event`
- `@testing-library/jest-dom`
- `msw`
- `playwright`
- `typescript`
- `eslint`
- `vitest-axe` 或等价 a11y 检查工具（推荐）

静态质量门禁建议：

- `eslint`
- `tsc --noEmit`

说明：

- 静态检查不是 TDD 的替代品，但应作为实现阶段并行门禁
- 时间相关行为优先用 `vi.useFakeTimers()`，不要真实等待
- Playwright 只覆盖最关键主链路，不代替 component / integration tests
- a11y 断言优先使用 `vitest-axe`；若未启用，则至少补 `role`、`aria-*`、键盘可达性断言

## 6. 测试夹具与测试替身设计

## 6.1 必备 Fixtures

必须在 `tests/fixtures/` 中提供以下可复用夹具：

- `render_with_store`
- `make_test_store`
- `fake_clock`
- `mock_send_beacon`
- `mock_beforeunload`
- `mock_match_media`
- `mock_resize_observer`
- `mock_intersection_observer`
- `mock_scroll_container`
- `msw_server`
- `scripted_task_event_source`
- `mock_download_trigger`

组织约定：

- `tests/fixtures/` 存放 fixture 的实现模块
- `tests/setup.ts` 负责注册全局 DOM mock 与 `jest-dom`
- `vitest.config.ts` 中显式区分 `unit / component / integration`
- `tests/e2e/fixtures/` 只存放 Playwright 侧 fixture、page object 与 mock server 脚本，不复用 Vitest render helper

## 6.2 Scripted SSE 策略

前端不应直接在测试中 mock `@microsoft/fetch-event-source` 的内部实现；应先封装 `TaskEventSource` 抽象，再提供脚本化 fake。

建议接口形态：

```ts
type TaskEventSource = {
  connect(args: {
    url: string;
    token: string;
    onOpen: () => void;
    onEvent: (event: EventEnvelope) => void;
    onError: (error: unknown) => void;
    onClose: () => void;
  }): () => void;
};
```

`ScriptedTaskEventSource` 可表达：

- open
- event
- delay
- hang
- error
- close

好处：

- 精确控制事件顺序
- 不依赖第三方库内部实现细节
- 更容易复现 `task.created -> phase.changed -> report.completed -> task.awaiting_feedback` 等时序问题

## 6.3 REST Mock 策略

组件与集成测试中的 REST 调用统一通过 `MSW` 拦截。

至少覆盖：

- `POST /tasks`
- `GET /tasks/{id}`
- `POST /clarification`
- `POST /feedback`
- `POST /heartbeat`
- `POST /disconnect`
- 下载 / artifact 请求的 `200` 与 `401 access_token_invalid`

E2E 中不建议复用 `MSW` 作为唯一 mock；应使用更接近真实网络行为的 mock API server，避免 `SSE + download` 行为与浏览器层偏差过大。

E2E mock server 方案：

- 采用“独立 Node.js 轻量 HTTP server”方案，推荐 `Hono` 或 `Express`
- 由 Playwright `globalSetup` 或 worker fixture 启停
- 统一提供 REST、SSE、artifact、zip、pdf 响应
- 每条 Playwright spec 通过 scenario id 或脚本文件向 mock server 注册本轮事件剧本
- SSE 推送按剧本顺序与延迟执行，确保测试脚本能精确等待特定 UI 状态

说明：

- `page.route()` 可用于个别 fault injection，但不作为主方案
- 之所以不选纯 `page.route()`，是因为 `SSE + download + 二进制响应` 的浏览器行为更适合由独立 server 模拟

## 6.4 Browser API Mock 策略

必须提供可复用 mock：

- `navigator.sendBeacon`
- `window.confirm` 或等价离开确认桩
- `Element.scrollTo`
- `HTMLElement.scrollHeight / clientHeight / scrollTop`
- `ResizeObserver`
- `IntersectionObserver`
- `matchMedia`

要求：

- 每个 mock 都应支持在测试内显式断言是否被调用
- 不允许在测试里零散 patch 全局对象

响应式断点测试策略：

- `mock_match_media` 必须支持模拟 `< 768px`、`768px - 1279px`、`>= 1280px` 三类 breakpoint
- 组件测试通过切换 `matchMedia` 返回值验证移动端、平板、桌面布局差异
- breakpoint 切换后，组件需要重新触发媒体查询订阅回调，而不是只在首次 render 生效

## 6.5 Test Data Builder 策略

随着状态复杂度上升，测试中必须使用 builder，而不是手写大对象。

建议提供以下 builder：

- `build_task_snapshot(...)`
- `build_create_task_response(...)`
- `build_task_detail_response(...)`
- `build_revision_summary(...)`
- `build_requirement_detail(...)`
- `build_delivery_summary(...)`
- `build_artifact_summary(...)`
- `build_question_set(...)`
- `build_event_envelope(...)`
- `build_timeline_item(...)`

原则：

1. 测试只声明自己关心的字段，其余字段用稳定默认值。
2. builder 生成的数据必须与 [OpenAPI_v1.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/OpenAPI_v1.md) 一致。
3. builder 本身不承担业务逻辑，只负责构造可读测试数据。

## 7. 外部依赖 Mock / Fake 策略

| 依赖 | Unit | Contract | Component | Integration | E2E | Smoke |
| --- | --- | --- | --- | --- | --- | --- |
| REST API | no | fixture | MSW | MSW | mock server | real |
| SSE source | no | fixture | scripted fake | scripted fake | mock server | real |
| `sendBeacon` | fake | fake | fake | fake | browser spy | real |
| 下载行为 | no | fixture | fake trigger | fake trigger | real browser download | real |
| Browser observers | fake | fake | fake | fake | real browser | real |

说明：

1. 前端测试重点是“我们如何消费后端契约”，不是验证后端本身可用。
2. `SSE` 与 download 在浏览器级行为差异较大，因此 Playwright 需要独立 mock server。
3. 所有断连、倒计时、auto-scroll 测试都应基于 fake timers 或可控 scroll metrics。

## 8. CI 流程设计

建议拆成五段门禁：

### 8.1 Fast Gate

内容：

- `eslint`
- `tsc --noEmit`
- `vitest tests/unit`
- `vitest tests/contract`

目标时长：

- `2 分钟` 内

### 8.2 Component Gate

内容：

- `vitest tests/component`

目标时长：

- `3 分钟` 内

### 8.3 Integration Gate

内容：

- `vitest tests/integration`

目标时长：

- `5 分钟` 内

### 8.4 E2E Gate

内容：

- `playwright test`

目标时长：

- `8 分钟` 内

### 8.5 Optional Smoke Gate

内容：

- 连接真实预览环境或 staging 后端的手动 smoke suite

规则：

- 默认不进 PR 门禁
- 发布前至少人工执行一次

## 8.6 单测试超时约束

为避免流式测试挂起拖垮整段门禁，建议定义单测试超时：

- unit test: `3s`
- contract test: `3s`
- component test: `5s`
- integration test: `10s`
- e2e test: `30s`

实现方式：

- Vitest 使用 `testTimeout`
- Playwright 使用项目级与单 spec 级 timeout

## 9. 阶段化实施计划

与 [Architecture.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Architecture.md) 中开发阶段的映射关系如下：

| Architecture 阶段 | Frontend TDD Stage |
| --- | --- |
| 第一阶段：契约与领域测试 | Stage 0 + Stage 1 |
| 第二阶段：任务框架 | Stage 2 + Stage 3 |
| 第三阶段：需求阶段 | Stage 4 |
| 第四阶段：搜集引擎 | Stage 5 |
| 第五阶段：输出引擎 | Stage 6 + Stage 7 |

与 [Frontend_IA.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Frontend_IA.md) 的对应关系如下：

| Frontend_IA 章节 | Frontend TDD Stage |
| --- | --- |
| 路由与状态模型 | Stage 1 + Stage 2 |
| SSE / heartbeat / disconnect | Stage 3 |
| 澄清面板 | Stage 4 |
| 时间线 | Stage 5 |
| 报告 / 下载 / feedback | Stage 6 + Stage 7 |

前后端对齐约定：

1. 前后端共享的契约类型优先收敛到 `packages/contracts/` 或前端 `lib/contracts/` 的同源生成物，前端 mock 不手写与契约冲突的字段。
2. 后端 contract tests 若更新了 REST 或 SSE payload，前端对应 fixture / builder / scripted SSE 剧本必须在同一 PR 或同一阶段内同步更新。
3. 每个 Architecture 阶段结束时，至少做一次“前端 mock 对照后端 contract 文档”的自检；任务框架、澄清、输出三个大阶段结束时各做一次前后端 smoke 联调。

## 9.1 Stage 0: Harness 与测试基础设施

目标：

- 先搭好前端测试骨架，再进入业务

先写失败测试：

- `vitest` 能运行 React + jsdom 测试
- `@testing-library/react` 能渲染最小 client component
- `tests/setup.ts` 能注册 `jest-dom`
- `ScriptedTaskEventSource` 最小 open / event / close 场景可用
- Playwright 最小空 spec 能在 CI 配置下启动并通过
- E2E mock server 最小 health route 可被 Playwright 访问

实现内容：

- `vitest` 配置
- Playwright 基础配置
- `tests/setup.ts`
- 基础 DOM mocks
- render helper
- scripted SSE driver
- E2E mock server skeleton

DoD：

- `unit / contract / component` 测试可独立运行
- Playwright 有最小可运行基线，后续阶段不再从零接入
- 全局 mocks 有统一入口
- 后续阶段不需要重复造测试基础设施

## 9.2 Stage 1: 契约类型、Store 与 Reducer

目标：

- 固化前端状态模型与事件映射骨架

先写失败测试：

- `TaskSnapshot` fixture 与 contracts 类型兼容
- `EventEnvelope` fixture 与关键 event union 对齐
- `task-snapshot-merger` 的初始化覆盖规则
- `event-reducer` 处理 `task.created`
- `event-reducer` 处理 `phase.changed`
- `event-reducer` 处理 `heartbeat`
- `event-reducer` 处理终态事件
- `event-reducer` 遇到当前阶段未支持的 event 分支时保持 no-op
- `available_actions` selectors

实现内容：

- `lib/contracts/` 类型接入
- Zustand store skeleton
- selectors
- reducers / mappers
- builders

DoD：

- 关键 store slice 已固定
- reducers 对通用事件与终态事件有 unit tests
- revision 切换相关 reducer 分支留到 Stage 7 补齐
- 不存在“组件内临时拼业务状态”的实现借口

## 9.3 Stage 2: 页面 Shell、输入与创建任务

目标：

- 先打通首页工作台与创建任务入口

先写失败测试：

- `Idle` 空态渲染
- `ResearchInputPanel` 字数限制与提交交互
- `ResearchConfigPanel` 默认 `natural`
- `POST /tasks` 成功后写入 `task_id/task_token/urls`
- `POST /tasks` 返回 `422 validation_error` 时字段就地标红且保留输入内容
- 创建任务后立即启动 SSE 连接
- 请求发出时 `pendingAction = creating_task`
- 创建任务成功或失败后 `pendingAction` 清回 `null`
- `409 resource_busy` 提示
- `429 ip_quota_exceeded` 提示与时间文案
- 创建中禁用输入与配置
- 不在 `POST /tasks` 成功后额外调用 `GET /tasks`

实现内容：

- `ResearchPageClient`
- workspace shell
- create task hook
- create task REST client
- input / config panel

DoD：

- 能从空态进入活跃工作台
- 错误态提示与 PRD / OpenAPI 契约一致
- `creating_task` 的 pendingAction 生命周期有测试保护
- “创建后立即建连”的行为有 integration tests

## 9.4 Stage 3: SSE 生命周期、Heartbeat 与终止态

目标：

- 打通前端最关键的流式生命周期

先写失败测试：

- `task.created` 覆盖初始化 snapshot
- SSE 连接在 `connect_deadline_at` 前未触发 `onOpen` 时，客户端主动超时并进入终止态
- `heartbeat` loop 仅在允许状态下启动
- `heartbeat` 返回 `409/404` 时停止并进入终态
- SSE 中断后立即进入终止态
- 不发生自动重连
- 活跃任务期间注册 `beforeunload`
- 终态事件到达后移除 `beforeunload`
- `pagehide` 触发 `sendBeacon`
- 手动点击“终止任务”调用普通 `POST /disconnect`
- 发起手动终止时 `pendingAction = disconnecting`
- 终止请求完成后 `pendingAction` 清回 `null`
- `task.failed` / `task.terminated` / `task.expired` 禁用所有旧操作

实现内容：

- `use-task-stream`
- `use-heartbeat-loop`
- `use-disconnect-guard`
- 顶栏连接状态
- `TerminalBanner`

DoD：

- 断连、终止、过期三条路径都有 integration tests
- `connect_deadline_at` 的客户端超时逻辑具备测试
- `sendBeacon` 与普通 disconnect 的鉴权调用方式都有测试
- v1 “不恢复、不重连”的约束已被测试钉死

## 9.5 Stage 4: 澄清流程

目标：

- 完成自然语言与选单澄清两条路径

先写失败测试：

- `clarification.delta` 渲染
- `clarification.natural.ready` 后启用输入框
- `clarification.options.ready` 初始化 `optionAnswers = o_auto`
- 选单问题渲染与单选切换
- `clarification.countdown.started` 启动倒计时
- 任一选项变化后倒计时重置
- 倒计时结束自动提交 `submitted_by_timeout = true`
- 手动提交会取消当前倒计时
- 提交澄清时 `pendingAction = submitting_clarification`
- 澄清提交成功或失败后 `pendingAction` 清回 `null`
- `POST /clarification` 返回 `422 validation_error` 时字段错误展示且保留输入
- `clarification.fallback_to_natural` 清空选单并切到自然语言模式
- 移动端澄清阶段把 `报告` 分段替换为 `澄清详情`

实现内容：

- clarification panels
- countdown hook
- clarification submit hook
- mobile clarification layout

DoD：

- 两种澄清模式都可从 UI 成功提交
- 倒计时行为完全由 fake timers 覆盖
- `submitting_clarification` 的 pendingAction 生命周期有测试保护
- 前端没有任何“自己解析选单 markdown”的逻辑

## 9.6 Stage 5: 时间线与研究中透明度

目标：

- 落实 PRD 对“让用户知道系统正在做什么”的要求

先写失败测试：

- `analysis.delta` / `analysis.completed`
- `planner.reasoning.delta`
- `planner.tool_call.requested` 显示 `collect_target`
- `collector.reasoning.delta`
- `collector.search.*` / `collector.fetch.*`
- `collector.completed`
- `summary.completed`
- `sources.merged`
- `outline.delta` 只显示“正在构思”，不渲染 raw delta
- 并发 sub-agent 事件交错时，timeline item 仍带正确 `collectTarget`
- 时间线默认自动滚动到底部

实现内容：

- timeline mapper
- timeline panel
- requirement summary card
- analysis / planning / collection status copy

DoD：

- 核心研究阶段的透明度事件全部可见
- `collect_target` 展示行为具备 component / integration tests
- 并发 sub-agent 的时间线标签不会串线

## 9.7 Stage 6: Report Canvas、Artifact 与交付

目标：

- 完成报告正文、图片与下载动作

先写失败测试：

- `outline.completed` 显示章节概览
- `writer.delta` 追加正文
- `writer.reasoning.delta` 只进时间线，不进正文
- `writer.tool_call.requested` 显示“正在生成配图”
- `writer.tool_call.completed` 结束对应 tool call 的进行中状态
- auto-scroll 默认跟随
- 用户上滚后暂停 auto-scroll
- 点击“回到底部”恢复 auto-scroll
- 自定义 markdown `img` renderer 只允许当前 task artifact URL
- `artifact.ready` 后图片可在 gallery 中可见
- 图片返回 `401 access_token_invalid` 时刷新 `delivery`
- `refreshingDelivery = true` 时下载按钮 disabled
- `refreshingDelivery = true` 时图片重试按钮 disabled
- 刷新完成后相关按钮恢复 enabled
- 刷新后按 `artifact_id` 使用新 URL 重渲染
- `report.completed` 更新下载区
- `report.completed` 到达但尚未 `task.awaiting_feedback` 时不显示 feedback
- `markdown zip` / `pdf` 下载 loading state

实现内容：

- `ReportCanvas`
- `ArtifactGallery`
- `DeliveryActions`
- `use-delivery-refresh`
- markdown renderer
- auto-scroll hook

DoD：

- 正文、图片、下载三类交付能力均有 component / integration tests
- writer tool-call 状态切换具备回归测试
- `access_token_invalid` 刷新链路有回归测试
- 报告渲染不允许原始 HTML

## 9.8 Stage 7: Feedback、Revision 切换与 Hardening

目标：

- 完成闭环，进入可演示状态

先写失败测试：

- `task.awaiting_feedback` 才显示 feedback 输入区
- `POST /feedback` 返回后进入 overlay 等待态
- 提交 feedback 时 `pendingAction = submitting_feedback`
- feedback 提交成功或失败后 `pendingAction` 清回 `null`
- `POST /feedback` 返回 `422 validation_error` 时字段错误展示且保留输入
- `phase.changed(to_phase = processing_feedback)` 时顶栏与时间线显示“正在处理反馈”
- `processing_feedback` 阶段的 `analysis.delta` 正确进入时间线或阶段详情文案
- 新 `revision_id` 首个事件到达后插入分隔项
- 新 revision 的 `analysis.completed` 更新 `currentRevision.requirement_detail`
- `phase.changed(to_phase = planning_collection)` 时时间线进入新一轮研究阶段
- revision 切换时清空旧 `analysisText / reportMarkdown / outline / artifacts / delivery`
- 旧报告在等待下一 revision 期间保持可见
- 新 revision 稳定后 overlay 消失
- `task.failed` / `task.expired` 时 feedback 与下载动作被禁用
- 移动端 `操作 / 报告 / 进度` 切换可正常工作
- 关键组件具备基本 a11y 断言
- 最小 Playwright 主链路通过

实现内容：

- `FeedbackComposer`
- revision transition handling
- responsive shell hardening
- a11y polish
- Playwright specs

DoD：

- feedback 闭环具备 integration tests
- `submitting_feedback` 的 pendingAction 生命周期有测试保护
- 最小主链路具备 Playwright coverage
- 移动端与桌面端核心交互都能通过测试运行

## 10. 每阶段通用 Definition of Done

任何阶段完成前必须同时满足：

1. 对应失败测试先写、再变绿。
2. 该阶段相关的 unit / contract / component / integration 测试全部通过。
3. 没有新增未解释的 flaky test。
4. 需要变更契约时，文档已先更新。
5. 关键按钮 gating、终态禁用、revision 切换没有跳过异常分支。

## 11. 高风险点与专项测试要求

## 11.1 流式与时序

高风险行为：

- 创建任务后立即建 SSE
- `task.created` 覆盖 `POST /tasks` 初始化 snapshot
- `report.completed` 与 `task.awaiting_feedback` 的先后
- stream 中断后立即终止

要求：

- 必须使用 scripted SSE 精确控制事件顺序
- 至少一条 integration test 覆盖“终态事件后禁止所有旧交互”

## 11.2 时间相关行为

高风险行为：

- 15 秒选单倒计时
- 20 秒 heartbeat
- auto-scroll 恢复逻辑

要求：

- 一律使用 fake timers
- 禁止真实等待

## 11.3 Revision 切换

高风险行为：

- feedback 后旧报告残留
- 旧 delivery / old artifact URL 泄漏到新 revision
- overlay 状态卡死

要求：

- 必须有 integration tests 覆盖从 `POST /feedback 202` 到新 `revision_id` 首个事件的完整过渡

## 11.4 Artifact 与下载

高风险行为：

- markdown 图片用旧 `access_token`
- 刷新 `delivery` 后图片不更新
- 下载按钮重复点击

要求：

- 至少一条 component test 和一条 integration test 覆盖 `401 access_token_invalid -> GET /tasks -> retry`

## 12. 反模式清单

以下做法应在 code review 中直接拦截：

1. 组件内部直接拼业务状态，不走 selector / reducer。
2. 用整页 snapshot 断言复杂页面。
3. 用真实 `setTimeout` / `sleep` 等待倒计时。
4. 在测试里直接 patch 第三方 SSE 库内部实现，而不是通过 `TaskEventSource` 抽象。
5. 将 `task_token` 写入 localStorage 以便测试“更方便”。
6. 依赖真实后端或真实预览环境让组件测试通过。
