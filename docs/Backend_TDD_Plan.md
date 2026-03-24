# Mimir Backend TDD Plan

## 1. 文档目的

本文档定义 Mimir 后端在进入正式编码前的 TDD 实施方案，目标是把 [Architecture.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Architecture.md) 与 [OpenAPI_v1.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/OpenAPI_v1.md) 转换成一套可执行、可验收、可持续推进的后端开发计划。

本文档回答四个问题：

1. 后端测试如何分层。
2. 每层测试应该覆盖什么，不应该覆盖什么。
3. 实施阶段按什么顺序推进，才能保证风险最小。
4. 每个阶段达到什么标准，才能进入下一阶段。

## 2. 输入与不可违背约束

后端实施必须同时满足以下前置设计约束：

- 以前后端解耦为前提，后端必须具备独立对外提供 API 的能力。
- 使用 `FastAPI + Pydantic v2 + SQLAlchemy 2.0 + PostgreSQL`。
- LLM 编排必须手工实现，不引入 LangChain / LangGraph。
- 接口契约以 `REST + SSE` 为准。
- 研究任务相关数据遵循“短期保存、到期清理、失败/终止立即清理”。
- v1 全局同一时刻仅允许一个活动任务。
- 反馈后保留已搜集信息，按 `Task / Revision / SubTask / Event` 模型推进。
- 所有影响外部行为的实现变更都必须先反映到文档与测试，再进入代码。

## 3. TDD 工作原则

## 3.1 Red-Green-Refactor 的执行粒度

Mimir 后端不采用“整阶段写完再补测试”的伪 TDD。每个最小业务增量必须按以下顺序推进：

1. 先写失败测试。
2. 只写让该测试通过的最小实现。
3. 重构实现，但不得放宽行为约束。
4. 再写下一条失败测试。

最小增量示例：

- 一个 schema
- 一个状态流转
- 一个接口的成功路径
- 一个错误码分支
- 一个 SSE 事件 payload
- 一个 adapter 的风控识别逻辑

## 3.2 Contract-First 规则

以下行为一律视为“对外契约”：

- REST 请求/响应字段
- 鉴权方式
- SSE 事件名
- SSE envelope 结构
- 错误码
- 终态事件顺序
- 下载链接与 access token 语义

规则：

1. 如需修改外部行为，先更新 `docs/OpenAPI_v1.md`。
2. 如需修改状态机或数据语义，先更新 `docs/Architecture.md`。
3. 文档未更新前，不允许修改实现来“偷偷改变”行为。

## 3.3 决定性优先

所有测试都应尽量避免真实时间、真实随机数和真实网络带来的不稳定性。

必须注入的可控依赖：

- `Clock`
- `IdGenerator`
- `TaskTokenSigner`
- `AccessTokenSigner`
- `LLMAdapter`
- `WebSearchClient`
- `WebFetchClient`
- `E2BSandboxClient`
- `ArtifactStore`

测试中禁止：

- `time.sleep`
- 真实外部 API 调用
- 依赖真实系统当前时间判断 TTL
- 用 monkeypatch 到处劫持内部函数来代替合理的依赖注入

## 3.4 CI 中禁止真实外部依赖

CI 中不允许直接调用：

- 智谱 LLM
- 智谱 `web_search`
- Jina `web_fetch`
- E2B Sandbox

CI 只能使用：

- fake adapter
- stub adapter
- `respx` HTTP mock
- disposable PostgreSQL
- 临时 artifact 目录

真实外部依赖只允许出现在“手动 smoke 检查”中，不属于 PR 必过门禁。

## 4. 测试分层

建议后端测试目录结构：

```text
services/api/tests/
├─ unit/
│  ├─ domain/
│  ├─ application/
│  ├─ parsers/
│  ├─ policies/
│  └─ prompts/
├─ contract/
│  ├─ rest/
│  ├─ sse/
│  └─ openapi/
├─ integration/
│  ├─ api/
│  ├─ workflows/
│  ├─ db/
│  └─ cleanup/
├─ smoke/
│  └─ external/
└─ fixtures/
```

## 4.1 Unit Tests

目标：

- 验证纯业务规则、parser、policy、状态机与 prompt builder
- 不触及真实 DB、真实网络、真实 FastAPI server

必须覆盖：

- `TaskStateMachine`
- `RequirementDetail` parser
- 选单澄清 parser 与 fallback
- `CollectPlan` 限次规则
- 风控识别逻辑
- 同源去重逻辑
- access token / task token payload 语义
- prompt builder 的关键约束

不应覆盖：

- HTTP 路由
- SQLAlchemy 持久化细节
- SSE 文本输出格式
- 真实流式网络交互

质量要求：

- 运行快
- 错误定位精确
- 使用最少依赖

## 4.2 Contract Tests

目标：

- 验证 FastAPI 暴露的 REST 和 SSE 契约与 `docs/OpenAPI_v1.md` 一致
- 尽可能早发现“实现正确但契约漂移”的问题

必须覆盖：

- OpenAPI schema 快照
- 关键 REST 接口的 request / response schema
- 错误响应 schema
- 鉴权缺失/错误时的错误码
- SSE event name 与 payload schema
- 终态事件顺序约束

实现方式：

- 启动 FastAPI app
- 使用 fake service / fake orchestrator
- 通过 `httpx.AsyncClient` 或 FastAPI test client 调用

## 4.3 Integration Tests

目标：

- 验证 API、数据库、仓储、编排器、清理、SSE、文件制品之间的协作正确性
- 使用 mocked 上游，而不是纯 in-memory stub

必须覆盖：

- 创建任务 + 建立 SSE + 首轮澄清
- 选单澄清超时自动推进
- master/sub collect loop
- 风控 1301 分支
- 通用重试 3 次分支
- writer + E2B artifact 链路
- access token 刷新
- 反馈新 revision
- disconnect / 显式终止 / expiry cleanup

依赖边界：

- 数据库使用真实 PostgreSQL
- 文件系统使用临时目录
- 外部 HTTP 使用 `respx`
- E2B 使用 fake client

## 4.4 Manual Smoke Tests

目标：

- 在非 CI 环境下，用真实外部服务验证关键接入是否工作
- 不追求全覆盖，只验证“接线正确”

建议覆盖：

- 智谱 LLM streaming
- 智谱 `web_search`
- Jina `web_fetch`
- E2B sandbox 创建与销毁

规则：

- smoke 测试不能阻塞普通开发 CI
- 必须显式通过环境变量或 marker 启用

最小 smoke 清单：

1. 智谱 LLM streaming 能完成一轮请求/响应。
2. 智谱 `web_search` 能返回至少一条结构化结果。
3. Jina `web_fetch` 能返回非空 markdown 内容。
4. E2B sandbox 能创建、执行一段 Python 代码并返回 stdout。
5. E2B sandbox 能生成一个 png 文件并完成 artifact 上传。
6. 至少验证一次风控 1301 错误结构能够被 adapter 正确识别。

## 5. 测试工具与基础设施

建议工具：

- `pytest`
- `pytest-asyncio`
- `httpx.AsyncClient`
- `respx`
- `pytest-mock`
- `pytest-xdist`（可选）
- `pytest-timeout`
- `testcontainers` 或 CI PostgreSQL service

静态质量门禁建议：

- `ruff check`
- `ruff format --check`
- `mypy`

说明：

- 静态检查不是 TDD 的替代品，但应作为实现阶段的并行门禁
- 时间控制优先通过可注入的 `Clock` / `FakeClock` 完成，而不是依赖 `freezegun`

## 6. 测试夹具与测试替身设计

## 6.1 必备 Fixtures

必须在 `tests/fixtures/` 中提供以下可复用夹具：

- `fake_clock`
- `fake_id_generator`
- `fake_task_token_signer`
- `fake_access_token_signer`
- `event_sink`
- `temp_artifact_dir`
- `db_engine`
- `db_session`
- `app_client`
- `sse_test_client`

组织约定：

- `tests/fixtures/` 存放 fixture 的实现模块
- `tests/conftest.py` 负责导入并注册这些 fixture，向 pytest 暴露统一入口

## 6.2 Scripted Adapter 策略

对 LLM 和工具调用，不推荐在测试中临时 patch SDK 内部方法；应提供脚本化 fake adapter。

建议接口形态：

```python
class ScriptedLLMAdapter(LLMAdapter):
    def __init__(self, script: list[LLMStep]) -> None: ...
```

`LLMStep` 可表达：

- streaming content delta
- streaming reasoning delta
- tool call
- stop finish reason
- upstream error
- risk control error

同理，为以下依赖提供 scripted fake：

- `ScriptedWebSearchClient`
- `ScriptedWebFetchClient`
- `ScriptedE2BClient`

好处：

- 测试能精确控制事件顺序
- 不依赖 patch 内部实现
- 更容易复现复杂 workflow

## 6.3 Repository Test Strategy

Repository 层测试分两类：

1. unit 层只测 repository 的查询条件与 mapper 时，允许使用 lightweight db fixture
2. integration 层必须用真实 PostgreSQL 跑关键 CRUD 与事务/清理逻辑

不建议：

- mock SQLAlchemy session
- mock ORM model 实例行为

## 6.4 Prompt Builder 与 External Invocation Contract Test Strategy

prompt 相关测试不建议滥用整段 snapshot，因为过于脆弱；但对外部调用契约又必须锁住会导致 provider 漂移的关键信号。

建议按两层锁定：

### 6.4.1 Prompt source-of-truth 锁定

`literal lock`：

- 自然语言澄清 prompt
- 选单澄清 prompt
- 需求分析 prompt
- 反馈需求分析 prompt

要求：

1. 以上四类 prompt 的模型可见文本，以 PRD 原文约束为准。
2. 测试必须断言 PRD 要求的关键语句逐字存在；允许变化只有运行时变量插值、空白规范化和动态 JSON 值替换。
3. `clarification natural` 与 `clarification options` 必须断言 system prompt 为空，不允许由 adapter 私加 system prompt。
4. `requirement analysis` 与 `feedback analysis` 必须断言 system prompt / user prompt 分工与 PRD 一致。

`semantic lock`：

- master planning prompt
- 搜集目标执行 prompt
- 目标执行总结 prompt
- 研究输出准备 prompt
- 研究输出撰写 prompt

要求：

1. 允许等价改写，但测试必须锁定角色语义、tool 可见范围、次数上限、输出 schema 约束、transcript 注入规则。
2. planner / collector / writer 必须断言完整 transcript 被按顺序注入，而不是只注入摘要。
3. 任何 prompt 都必须断言：必须字段、枚举映射、时间变量、PRD 约束语句。

仅在少量关键 prompt 上保留 normalized snapshot：

- 需求分析 prompt
- master planning prompt
- writer prompt

snapshot 规则：

1. 先做时间、ID、动态 JSON 的占位符规范化，再 snapshot。
2. snapshot 只用于锁定高价值骨架，不替代对参数、tool schema 与 request shape 的单独断言。

### 6.4.2 Invocation profile 与 tool contract 锁定

所有真实 provider adapter 都必须有独立 contract tests，至少锁定：

1. 每个阶段的 `model`、`temperature`、`top_p`、`max_tokens`、`thinking`、`clear_thinking`、`stream`
2. no-tool 阶段不应意外挂载 tool schema
3. `collect_agent`、`web_search`、`web_fetch`、`python_interpreter` 的名称与参数名
4. planner / collector / writer 的 transcript 回放顺序
5. `func_7` / `func_8` 的 system prompt 与 tools description 关键句必须与 PRD 0.4 对齐

其中必须重点锁定的 request construction：

1. 智谱 `web_search`：
   - `POST .../web_search`
   - body 固定包含 `search_engine="search_prime"`、`query_rewrite=false`、`count=10`
   - body 动态字段只允许 `search_query` 与 `search_recency_filter`
2. Jina Reader `web_fetch`：
   - `GET https://r.jina.ai/{url}`
   - `Authorization: Bearer ...`（仅当 `JINA_API_KEY` 非空时携带；为空时不携带，以免费无认证模式调用）
   - `Accept: text/plain`
   - 不再接受”POST + JSON body”作为正式契约
   - contract test 拆分为两个 case：key 非空时携带 header / key 为空时不携带 header
3. `python_interpreter`：
   - tool request 只允许 `code`
   - tool result 不得回灌 raw binary
   - tool result 必须包含 `success`、`summary`、`stdout`
   - 失败时必须包含 `stderr` 或等价错误摘要，以及 `error_type`、`error_message`、`traceback_excerpt`
   - tool result 可选携带 `artifacts[]`
   - `artifacts[]` 中必须锁定 `artifact_id`、`filename`、`mime_type`、`canonical_path=mimir://artifact/{artifact_id}`
   - tool description 必须锁定“中文图表优先使用 `Noto Sans CJK SC`”
4. `collect_agent`：
   - 模型可见参数只允许 `collect_target`、`additional_info`、`freshness_requirement`
   - `freshness_requirement` 继续锁定为枚举语义 `low | high`
   - `tool_call_id`、`revision_id`、`subtask_id` 只能在后端内部补齐

结果清洗 contract tests 还必须锁定：

1. `web_search` tool result 只保留 `search_result` 的核心字段，剔除 `icon`、`media` 等展示性字段
2. `web_fetch` 正文截断到前 `5000` 字符，标题提取规则稳定；adapter 与 collection service 若存在双重截断，必须共用同一个配置源
3. `python_interpreter` 只返回文本摘要与 artifact 元数据，不把二进制内容写入 transcript
4. provider 风控、超时、空内容、4xx、5xx 都会被映射到统一异常或统一 tool result envelope
5. E2B `execute` 成功返回但 `execution.error != null` 时，必须映射成 writer 可消费的结构化失败 tool result，而不是 `RetryableOperationError`
6. 自定义 E2B template 的结构测试必须锁定：模板定义文件存在、字体资产存在、模板 build 步骤会安装 `Noto Sans CJK SC` 并刷新字体缓存

E2B template / 字体能力相关测试还必须覆盖：

1. `Settings` 能读取 `MIMIR_E2B_TEMPLATE`
2. provider runtime 在 real E2B mode 下会把 template 传给 `E2BRealSandboxClient`
3. `E2BRealSandboxClient.create()` 会调用 `AsyncSandbox.create(template=...)`
4. template 未配置时，real E2B adapter 保持兼容，不隐式传递其他 template 值

阶段映射：

- Stage 4:
  - 自然语言澄清 prompt
  - 选单澄清 prompt
  - 需求分析 prompt
- Stage 5:
  - 搜集调度 prompt
  - 搜集目标执行 prompt
  - 目标执行总结 prompt
- Stage 6:
  - 研究输出准备 prompt
  - 研究输出撰写 prompt
- Stage 7:
  - 反馈需求分析 prompt

要求：

- 每个阶段的 prompt builder 与真实 provider adapter，在实现前都应先有对应 contract tests
- prompt tests 锁语义，adapter tests 锁真实 request shape，两者不能相互替代

## 6.5 Test Data Builder 策略

随着 workflow 复杂度上升，测试中必须使用 test data builder，而不是在每条测试里手写完整对象。

建议提供以下 builder：

- `build_task_snapshot(...)`
- `build_revision_summary(...)`
- `build_requirement_detail(...)`
- `build_collect_plan(...)`
- `build_collect_result(...)`
- `build_collect_summary(...)`
- `build_formatted_source(...)`
- `build_outline_package(...)`
- `build_event_envelope(...)`

原则：

1. 测试只覆盖自己关心的字段，其余字段使用稳定默认值。
2. builder 生成的数据必须与文档契约一致。
3. builder 本身应尽量无业务逻辑，仅负责构造可读、可复用的测试数据。

## 7. 外部依赖 Mock / Fake 策略

| 依赖 | Unit | Contract | Integration | Smoke |
| --- | --- | --- | --- | --- |
| 智谱 LLM | scripted fake | scripted fake | scripted fake | real |
| 智谱 `web_search` | fake result | fake result | `respx` mock | real |
| Jina `web_fetch` | fake result | fake result | `respx` mock | real |
| E2B sandbox | fake client | fake client | fake client | real |
| PostgreSQL | no | optional lightweight db | real | real |
| Artifact store | temp dir | temp dir | temp dir | temp dir |

说明：

1. 集成测试优先验证“我们的编排器是否正确处理上游响应”，而不是验证第三方服务是否可用。
2. E2B 在 CI 中不接真实服务，避免成本和不稳定性。
3. `web_search` / `web_fetch` 的风控、超时、空内容都应在 integration 层有覆盖。
4. `web_search` 与 Jina `web_fetch` 的 request construction contract，必须至少在一层测试里直接断言 HTTP method、path、headers 与 body，而不是只断言最终解析结果。
5. 智谱 LLM adapter 必须使用 recording fake / spy client 直接断言阶段 profile、system prompt、user prompt 和 tool schema，避免只测 prompt builder 却漏掉 adapter 默认值漂移。

## 8. CI 流程设计

建议拆成四段门禁：

### 8.1 Fast Gate

目标：

- 给开发者最快反馈

内容：

- `ruff check`
- `ruff format --check`
- `mypy`
- `pytest tests/unit`

目标时长：

- 2 分钟内

### 8.2 Contract Gate

内容：

- `pytest tests/contract`
- OpenAPI schema 快照检查
- SSE event schema 检查

目标时长：

- 3 分钟内

### 8.3 Integration Gate

内容：

- `pytest tests/integration`
- Alembic migration 升级检查
- 真实 PostgreSQL workflow 测试

目标时长：

- 10 分钟内

### 8.4 单测试超时约束

为避免异步测试挂起拖垮整段门禁，建议定义单测试超时：

- unit test: `5s`
- contract test: `10s`
- integration test: `30s`

实现方式：

- 优先使用 `pytest-timeout`
- 对局部复杂 async 流程可辅以 `asyncio.timeout`

### 8.5 Optional Smoke Gate

内容：

- 带真实 secrets 的手动 smoke suite

规则：

- 默认不进 PR 门禁
- release 前必须人工执行一次

## 9. 阶段化实施计划

与 [Architecture.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Architecture.md) 中开发阶段的映射关系如下：

| Architecture 阶段 | Backend TDD Stage |
| --- | --- |
| 第一阶段：契约与领域测试 | Stage 0 + Stage 1 |
| 第二阶段：任务框架 | Stage 2 + Stage 3 |
| 第三阶段：需求阶段 | Stage 4 |
| 第四阶段：搜集引擎 | Stage 5 |
| 第五阶段：输出引擎 | Stage 6 + Stage 7 |

## 9.1 Stage 0: Harness 与基础测试设施

目标：

- 先搭起测试执行骨架，再进入业务

先写失败测试：

- `pytest` 能发现并运行异步测试
- `tests/fixtures/` 可提供 fake clock / fake id / temp dir
- app 能启动最小 health endpoint

实现内容：

- `pyproject.toml`
- pytest 配置
- async test 基础设施
- db fixture
- basic app factory

DoD：

- `tests/unit` 和 `tests/contract` 可独立运行
- 能启动最小 FastAPI app
- 有统一 fixture 模块，后续阶段不重复造轮子

## 9.2 Stage 1: Core Schema 与状态机

目标：

- 固化领域模型和状态机

先写失败测试：

- `TaskSnapshot` schema
- `RevisionSummary` schema
- `RequirementDetail` schema
- `CollectPlan` / `CollectSummary` / `EventEnvelope` schema
- `TaskStateMachine` 合法/非法流转
- `status × phase` 组合矩阵
- `RetryPolicy` 的等待/次数/超限策略

实现内容：

- Pydantic DTO
- domain enums
- `TaskStateMachine`
- 基础 token signer payload model
- `RetryPolicy` 的纯策略实现

DoD：

- 所有核心 schema 都有 unit tests
- 非法状态流转会抛明确领域异常
- schema 与 `Architecture.md` / `OpenAPI_v1.md` 一致
- `RetryPolicy` 在 unit 层已可独立验证，不依赖具体 adapter

## 9.3 Stage 2: API Shell、鉴权与任务骨架

目标：

- 先实现“创建任务 + 查询任务 + 鉴权 + 基础策略”，不引入 SSE 生命周期依赖

先写失败测试：

- `POST /tasks`
- `GET /tasks/{id}`
- 鉴权失败错误码
- 单活动任务锁
- 同 IP 配额与 `Retry-After`
- disconnect 使用 header 鉴权成功
- disconnect 使用 body 鉴权成功
- disconnect 使用 `text/plain` body 鉴权成功
- disconnect 在 header 与 body 同时存在时优先使用 header
- CORS 允许白名单 origin
- CORS 拒绝非白名单 origin
- `OPTIONS` preflight 返回 `Authorization`
- 响应头包含 `X-Request-ID`
- 客户端传入 `X-Request-ID` 时原样回传
- 任务相关接口响应包含 `X-Trace-ID`

实现内容：

- task repository
- task token / access token signer
- create task use case
- activity lock policy
- IP quota policy
- CORS middleware
- request / trace id middleware
- disconnect 鉴权解析
- Stage 2 所需 Alembic migration：
  - `research_tasks`
  - `task_revisions`
  - `system_locks`
  - `ip_usage_counters`

DoD：

- `OpenAPI_v1` 中所有基础资源接口可运行
- 返回的错误码与 detail 匹配契约
- contract tests 覆盖创建、查询、鉴权、quota、CORS 与响应头
- Stage 2 的 Alembic migration 可正向和反向迁移
- `RetryPolicy` 已能被 Stage 4 之后的 adapter 直接复用

## 9.4 Stage 3: SSE Broker 与生命周期事件

目标：

- 先打通任务级流式框架，再接入 LLM

先写失败测试：

- `GET /events`
- 任务创建后立即启动 orchestrator
- 首个 SSE 连接只影响观察流，不影响任务是否继续运行
- `task.created`
- `heartbeat`
- `phase.changed`
- `task.failed`
- `task.terminated`
- `task.expired`
- 终态事件顺序
- `awaiting_feedback` 期间保持 SSE 打开
- `awaiting_feedback` 期间 `heartbeat` 与 `disconnect` 仍可调用
- 对无历史 `task_events` 的 seeded task，首次 `/events` 连接仍能 bootstrap `task.created`

说明：

- Stage 3 中涉及 `awaiting_feedback` 与 `task.expired` 的测试，不依赖完整 feedback 业务链路
- 测试可直接通过 factory / repository 预置一个 `delivered + awaiting_feedback` 的 task/revision 状态，再验证 SSE 生命周期行为

实现内容：

- SSE broker
- event persistence
- event serialization
- 显式终止 lifecycle
- SSE 观察流与 expiry lifecycle
- Stage 3 所需 Alembic migration：
  - `task_events`

DoD：

- 前端可稳定消费统一 SSE envelope
- 事件顺序可通过测试确定
- 终态后任务正确触发清理或进入待清理状态
- 首个 SSE 连接、SSE 断开不终止、显式 disconnect 终止具备 integration tests
- Stage 3 的 Alembic migration 可正向和反向迁移

## 9.5 Stage 4: 澄清与需求分析

目标：

- 完成从初始需求到 `RequirementDetail` 的全链路

先写失败测试：

- 自然语言澄清流
- `clarification.natural.ready`
- 选单解析成功
- 问题超过 5 个时截断
- 缺少选项的问题被跳过
- 选项格式不规范时的容错
- 问题之间夹杂非预期文本时的容错
- 选单解析失败 fallback 到自然语言
- 15 秒倒计时事件
- 60 秒后端兜底超时
- 需求分析 JSON parser
- 自然语言澄清 prompt invariant tests
- 选单澄清 prompt invariant tests
- 需求分析 prompt invariant tests
- 澄清 / 需求分析调用 profile contract tests
- 自然语言 / 选单澄清的空 system prompt contract tests

实现内容：

- clarification orchestrator
- clarification parsers
- requirement analyzer adapter
- clarification / analyzer prompt builders
- `POST /clarification`

DoD：

- 自然语言与选单两条路径都可进入 `analyzing_requirement`
- `RequirementDetail` parser 对 malformed JSON 有明确失败行为
- ready 事件与 `available_actions` 时序正确
- parser edge case 都有 unit tests
- Stage 4 使用的 LLM 调用已接入 `RetryPolicy`

## 9.6 Stage 5: 搜集引擎

目标：

- 完成 `func_7` 到 `func_11` 的核心研究引擎

先写失败测试：

- planner 发起单/多 `CollectPlan`
- 单 Revision 最多 5 次 `collect_agent`
- sub agent 最多 10 次工具调用
- 3 个 sub-agent 并发且全部成功
- 3 个 sub-agent 并发时，1 个风控、2 个成功
- barrier 必须等待全部分支完成后再返回 master
- `collector.search.started/completed`
- `collector.fetch.started/completed`
- `summary.completed`
- barrier 回传多个 tool messages
- same-source merge
- 风控 1301 在 collect 阶段转为 `risk_blocked`
- 搜集调度 prompt invariant tests
- 搜集目标执行 prompt invariant tests
- 目标执行总结 prompt invariant tests
- planner / collector / summary 调用 profile contract tests
- 所有 `thinking=True` stage 的 `clear_thinking` 必须显式为 `false`
- planner 第 2 轮及以后必须回灌历史 reasoning content + tool_calls + tool_results，且顺序稳定
- `collect_agent` / `web_search` / `web_fetch` request construction contract tests
- 安全 JSON 提取 tests：仅允许提取首个完整 top-level JSON block；collector stop output、summary `_complete_json()`、outline parser 对“说明文字 + 合法 JSON”兼容，但对非法 JSON 仍明确失败

实现内容：

- planner orchestrator
- collect subtask orchestrator
- summary orchestrator
- planner / collector / summarizer prompt builders
- web_search / web_fetch adapter
- merge service
- Stage 5 所需 Alembic migration：
  - `task_tool_calls`
  - `collected_sources`
  - `agent_runs`

DoD：

- 能在 integration 测试中跑完至少一条完整 collect loop
- 风控与通用重试逻辑全部具备回归测试
- merge 后 refer 编号稳定、可预测
- 并发 sub-agent 场景具备 integration tests
- planner 多轮 replay 时，历史 reasoning content 与历史 tool messages 会一起进入下一轮 transcript
- collector 必须按 PRD `func_8` 进行多轮 tool-calling；第 2 轮及以后，历史 reasoning content、历史 tool_calls 与对应 tool results 必须按原始时序回灌
- Stage 5 的 Alembic migration 可正向和反向迁移

## 9.7 Stage 6: 撰写、E2B 与交付

目标：

- 完成大纲、writer、artifact、下载

先写失败测试：

- `outline.delta`
- `outline.completed`
- `writer.delta`
- `writer.tool_call.requested/completed`
- `artifact.ready`
- `report.completed`
- access token 生成与刷新
- markdown zip 下载
- pdf 下载
- `build_pdf()` 产物必须可被真实 PDF 解析器打开并抽取基本正文
- `report.pdf` 下载接口返回的二进制必须是可解析 PDF，而不是伪造 header
- 含 `mimir://artifact/{artifact_id}` 图片引用时，PDF 导出必须能消费图片资源并完成渲染，不得因导出器本身报错
- PDF renderer 的 block spacer 不能复用同一个 `Spacer` flowable；多段正文、多列表、多图片场景下不得触发 `LayoutError`
- 研究输出准备 prompt invariant tests
- 研究输出撰写 prompt invariant tests
- outline / writer 调用 profile contract tests
- `python_interpreter` tool request / tool result contract tests
- writer transcript tool result 不再退化为固定成功文案
- `markdown zip` 会把正文中的 `mimir://artifact/{artifact_id}` 重写为 `artifacts/{filename}`
- 无图片的 `python_interpreter` 结果仍返回 `summary`，且 zip 不误改写非图片正文
- E2B artifact discovery 必须覆盖受控目录白名单；当前至少验证 `.` 与 `/tmp` 下新增 `.png` 会被采集
- 执行前已存在的 `.png` 与非 `.png` 文件不得误采集为本次 `python_interpreter` artifacts
- provider 返回独立 writer reasoning 字段时，`agent_runs.reasoning_text` 会落库，且不混入最终 markdown
- writer 多轮 `content`（round1/2/3）会按顺序组装成交付 markdown，不能只取 terminal round
- Zhipu non-stream / stream 调用都会提取并传递 provider `finish_reason` 与 `usage`
- `agent_runs.finish_reason` 保持应用层语义；provider 原始 `finish_reason` 与 `usage` 必须分别落到独立字段
- planner / collector / summary / outline / writer / feedback_analysis 的持久化测试必须覆盖 `provider_finish_reason` 与 `provider_usage_json`
- 所有 `thinking=True` stage 的 `clear_thinking` 必须显式为 `false`
- writer 第 2 轮及以后必须回灌历史 reasoning content + tool_calls + tool_results，且顺序稳定
- writer 达到 `MIMIR_WRITER_MAX_ROUNDS` 后若仍有 `tool_calls`，必须 `task.failed`，不能继续 `report.completed`
- writer 最终 markdown 为空白时必须 `task.failed`，不能交付 `0 字 / 0 配图` 空报告
- `Settings` 必须能正确读取 `MIMIR_WRITER_MAX_ROUNDS`，默认值保持 `5`
- E2B 基础设施失败 / destroy 失败 / artifact upload-store 失败仍走后端重试与失败收口
- sandbox 内部 Python 执行失败会产出 `writer.tool_call.completed(success=false)`，并把结构化失败结果写入 writer transcript，允许下一轮继续决策
- delivery export observability 必须区分 `markdown_zip`、`pdf`、`upload` 三个失败子阶段；重试耗尽后仍走既有 `task.failed` 收口，但日志里必须带 `export_kind`、原始异常类型与基础上下文字段

实现内容：

- outline orchestrator
- writer orchestrator
- outline / writer prompt builders
- E2B sandbox lifecycle
- artifact store
- download endpoints
- Stage 6 所需 Alembic migration：
  - `artifacts`

DoD：

- `outline.delta` 与 `outline.completed` 都有 contract / integration 覆盖
- `writer.tool_call.requested/completed` 事件顺序具备回归测试
- writer 首次调用 `python_interpreter` 时才创建 sandbox
- Revision 结束时 sandbox 会被销毁
- 自定义 E2B template 能通过显式配置接线到 real sandbox create 路径
- 下载链接与 artifact URL 都符合契约
- 生成在 `/tmp/*.png` 的图表文件会进入 `python_interpreter` tool result 与最终 `delivery.artifacts`
- `build_markdown_zip`、`build_pdf`、最终 download artifact upload 三段失败都能被独立观察，不再混成单一模糊导出失败
- 多段正文 + 多图的 PDF 仍能成功导出，且 story 中 block spacer 不会复用同一对象
- 正文 markdown 只保存 canonical artifact path，在线渲染与 zip 导出各自完成映射
- writer reasoning content 仅进入 `agent_runs.reasoning_text` / 调试持久化，不进入最终 `report.md`
- writer 成功交付时，最终 markdown 必须包含所有 round 的正文片段，顺序与 round 顺序一致
- writer 多轮 replay 时，历史 reasoning content、历史正文和历史 tool messages 都会进入下一轮 transcript
- writer 成功交付的前提是：无剩余 `tool_calls` 且最终 markdown 非空白
- sandbox 代码执行失败不应直接触发 `task.failed`；只有 infra / upload / store 路径仍可直接失败收口
- PDF / ZIP 均能从 temp artifact store 正常生成
- Stage 6 的 Alembic migration 可正向和反向迁移

## 9.8 Stage 7: 反馈、清理与 hardening

目标：

- 完成闭环，进入可演示状态

先写失败测试：

- `POST /feedback` 创建新 revision
- 新 revision 复用旧搜集结果
- 新 revision 创建后 `collect_agent` 计数器归零
- 新 revision 仍受单 Revision 最多 5 次 `collect_agent` 上限约束
- `awaiting_feedback` 期间 heartbeat 与 disconnect
- expiry 后清理
- failed / terminated 立即清理
- `CleanupExpiredTasks`
- access token 过期后重新 `GET /tasks/{id}` 能刷新 URL
- 反馈需求分析 prompt invariant tests
- feedback analysis 调用 profile contract tests

实现内容：

- feedback analyzer
- feedback prompt builder
- revision rollover
- cleanup worker
- final observability hooks
- 若 feedback / cleanup 引入新字段或索引，则在 Stage 7 同步提交对应 Alembic migration

DoD：

- 主链路、反馈链路、终止链路都具备 integration 测试
- 新旧 revision 切换后的 `collect_agent` 配额重置具备回归测试
- 数据删除策略与 PRD 对齐
- 至少完成一轮人工 smoke 检查清单

## 10. 每阶段通用 Definition of Done

任何阶段完成前必须同时满足：

1. 对应失败测试先写、再变绿。
2. unit / contract / integration 中该阶段相关测试全部通过。
3. 无新增未解释的 flaky test。
4. 需要变更契约时，文档已先更新。
5. 无跳过的关键异常分支。
6. 日志、事件、错误码与契约一致。

## 11. 高风险点与专项测试要求

## 11.1 时间相关行为

高风险行为：

- 显式 disconnect / beforeunload
- 30 分钟 expiry
- access token TTL

要求：

- 一律使用 fake clock 驱动
- 禁止真实等待

## 11.2 流式行为

高风险行为：

- SSE 事件顺序
- streaming delta 拼接
- tool-call 期间 UI 状态事件

要求：

- integration 测试必须显式断言事件顺序
- 至少一条测试覆盖“终态事件是最后一个业务事件”

## 11.3 清理行为

高风险行为：

- 终止即清理
- cleanup_pending 补偿
- artifact 删除与 DB 删除顺序

要求：

- integration 测试必须断言：
  - DB 标记变化
  - 文件删除
  - 二次补偿重试

## 11.4 风控与异常

高风险行为：

- 风控 1301 分支
- collect 阶段与非 collect 阶段行为差异
- 通用重试 3 次

要求：

- 至少各有一条 integration 测试覆盖
- 必须断言错误码、状态变化和最终事件

## 12. 不建议的反模式

以下做法在实施阶段应主动避免：

- 先写大段业务代码，再回头补测试
- 用 mock 覆盖掉 orchestrator 的核心逻辑
- 用 snapshot 测整个 prompt 文本
- 用真实 sleep 等待 TTL 或 heartbeat
- 在 CI 中接真实第三方服务
- 把 flaky 测试暂时 `xfail` 后长期不处理
- 为了让测试通过而放宽契约

## 13. 实施阶段的推荐命令

本地开发建议至少具备以下命令：

```bash
pytest tests/unit
pytest tests/contract
pytest tests/integration
pytest -m "smoke"
ruff check
ruff format --check
mypy app
```

阶段性推荐：

- 开始写新行为前：先跑相关 unit / contract tests
- 提交前：至少跑 `unit + contract`
- 合并前：必须跑 `integration`

## 14. 本文档之后的下一步

在本计划 review 通过后，建议继续输出：

1. `docs/Frontend_IA.md`
2. 如需要，再补 `docs/SSE_Event_Examples.md`
3. 全部设计文档通过后，再进入实施阶段
