# Mimir Implementation Playbook

## 1. 文档目的

本文档用于回答“设计已经完成后，如何按设计进入实施阶段”。

它不是新的架构设计文档，也不是某一端的 TDD 计划补充，而是实施总控文档，解决四个问题：

1. 当前版本应该按什么顺序落地。
2. 哪些工作可以并行，哪些必须串行。
3. 每次给 Codex 或工程师下达任务时，任务包应该怎么写。
4. 每个阶段完成后，如何做收口、联调与验收。

本文档与以下文档配套使用：

- [Architecture.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Architecture.md)
- [OpenAPI_v1.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/OpenAPI_v1.md)
- [Backend_TDD_Plan.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Backend_TDD_Plan.md)
- [Frontend_IA.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Frontend_IA.md)
- [Frontend_TDD_Plan.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Frontend_TDD_Plan.md)

## 2. 实施阶段的总原则

1. 先文档，后测试，再实现。
2. 先契约与骨架，后业务细节。
3. 单次只下发一个“足够小且能验收”的任务包，不下发大而泛的“把某端做完”。
4. 每个任务包都必须显式写清：输入文档、范围边界、验收标准、禁止事项。
5. 前后端始终以同一套契约为中心推进，不允许各自“先写一个差不多的 mock”。
6. 每个 Architecture 阶段结束后，都要做一次阶段收口，而不是无限连续编码。

### 2.1 当前执行纪律

从 `2026-03-13` 起，Mimir 仓库的实施执行采用以下固定纪律：

1. 当前默认采用单线程串行开发，同一时刻只推进一个活跃任务包。
2. 每个开发 session 完成后，必须先更新 [`docs/Execution_Log.md`](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Execution_Log.md)，再提交本次 session 回报。
3. leader 是否放行下一任务包，以 [`docs/Execution_Log.md`](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Execution_Log.md) 与该 session 的完成回报为共同依据。

## 3. 总体落地顺序

建议按 5 个里程碑推进，而不是把 Backend / Frontend 完全拆开各走各的。

| 里程碑 | 对应 Architecture 阶段 | 后端 | 前端 | 目标 |
| --- | --- | --- | --- | --- |
| M0 | 契约与领域测试 | Stage 0 + Stage 1 | Stage 0 + Stage 1 | 搭起 monorepo 骨架、contracts、测试基础设施 |
| M1 | 任务框架 | Stage 2 + Stage 3 | Stage 2 + Stage 3 | 创建任务、SSE、heartbeat、disconnect、终止态 |
| M2 | 需求阶段 | Stage 4 | Stage 4 | 自然语言澄清、选单澄清、需求分析 |
| M3 | 搜集引擎 | Stage 5 | Stage 5 | timeline、collect_target、透明度、搜集主循环 |
| M4 | 输出引擎 | Stage 6 + Stage 7 | Stage 6 + Stage 7 | 报告、artifact、下载、feedback revision、hardening |

结论：

- 不建议“后端先全部做完，再做前端”。
- 建议按里程碑推进，同阶段内前后端协同完成。

## 4. 每个里程碑的交付口径

### 4.1 M0: 契约与基础设施

必须交付：

- `apps/web`、`services/api`、`packages/contracts` 目录骨架
- 前后端各自的 Stage 0 / Stage 1 测试基础设施
- `packages/contracts` 或等价同源契约产物的接入方式
- 最小 CI 骨架

不得进入下一里程碑的情形：

- 契约类型仍然散落在多处手写
- 前端没有 scripted SSE 基础设施
- 后端没有 fake adapter / fake clock 基础设施

### 4.2 M1: 任务框架

必须交付：

- `POST /tasks`
- `GET /tasks/{id}`
- `GET /events`
- `POST /heartbeat`
- `POST /disconnect`
- 前端 Idle -> ActiveWorkspace -> Terminal 最小流转

阶段验收重点：

- 创建任务后前端立即建 SSE
- 10 秒 connect deadline
- SSE 中断即终止
- `sendBeacon` 与普通 disconnect 都能工作

### 4.3 M2: 需求阶段

必须交付：

- 自然语言澄清
- 选单澄清
- 15 秒倒计时
- 需求分析结果进入 `RequirementDetail`

阶段验收重点：

- 前端不解析原始选单 markdown
- `422 validation_error` 路径具备可视回归保护
- ready 事件与 `available_actions` gating 一致

### 4.4 M3: 搜集引擎

必须交付：

- planner / collector / summary 主链路
- 前端时间线能展示 `collect_target`
- 并发 sub-agent 的透明度展示

阶段验收重点：

- 前端 timeline 不串线
- 后端并发搜集与 barrier 正常
- 风控与 retry 路径有测试保护

### 4.5 M4: 输出引擎

必须交付：

- writer 流式正文
- artifact 图片
- markdown zip / pdf 下载
- feedback 进入新 revision
- 基本 hardening

阶段验收重点：

- `access_token_invalid -> GET /tasks -> retry`
- revision 切换不污染旧数据
- feedback analyzer -> 新 revision -> 新一轮研究链路完整

## 5. 并行策略

说明：

- 以下并行策略描述的是能力边界，不是当前默认执行方式。
- 当前仓库仍按 §2.1 的单线程串行开发规则推进。

## 5.1 可并行

以下工作可以并行，但必须以同一里程碑为边界：

1. 同一里程碑内，前端和后端各自的 Stage 开发。
2. 同一里程碑内，contracts 接入与测试基础设施完善。
3. 同一里程碑内，文档型收口和代码型实现并行推进。

## 5.2 不可并行

以下工作不应并行推进：

1. 未完成 M0 时，不进入 M1 业务编码。
2. 未完成 M1 时，不进入澄清和需求分析实现。
3. 未完成 M2 时，不进入搜集主循环。
4. 未完成 M3 时，不进入 writer / feedback 闭环。
5. 同一 session 内不要同时领两个不同里程碑的任务包。

## 5.3 推荐并行颗粒度

每个活跃 session 最好只承担以下三类之一：

1. `backend-only` 任务包
2. `frontend-only` 任务包
3. `contracts / glue` 任务包

不要让同一 session 同时做：

- 后端业务实现
- 前端组件实现
- contracts 变更

这三者放在一个任务包里会显著提高漂移概率。

## 6. “发号施令”的任务包规范

每次下发任务时，建议使用固定模板，不要口头化、抽象化。

### 6.1 必备字段

每个任务包都必须包含：

1. `目标`
2. `输入文档`
3. `范围`
4. `非目标`
5. `必须先写的测试`
6. `实现约束`
7. `交付物`
8. `验收标准`
9. `回报格式`

### 6.2 标准任务包模板

```md
任务名称：

目标：
- 

输入文档：
- docs/Architecture.md
- docs/OpenAPI_v1.md
- docs/Backend_TDD_Plan.md
- docs/Frontend_IA.md
- docs/Frontend_TDD_Plan.md

范围：
- 

非目标：
- 不修改未列出的接口契约
- 不提前实现下一阶段功能

必须先写的测试：
- 

实现约束：
- 严格按 TDD
- 若发现契约冲突，先停下并更新文档
- 不引入设计文档未批准的新框架

交付物：
- 代码文件：
- 测试文件：
- 如需更新文档：

验收标准：
- 

回报格式：
- 修改了哪些文件
- 跑了哪些测试
- 还剩什么风险 / blocker
```

### 6.3 好任务包的标准

一个好任务包应满足：

- 最多覆盖一个 Stage 内的一个清晰子目标
- 能在一次 session 内闭环
- 不需要实施者自行猜测边界
- 验收标准是“可证明的”，不是“差不多”

### 6.4 坏任务包的典型问题

以下指令要避免：

- “先把后端搭起来”
- “把前端页面都做了”
- “把 SSE 流式交互接上”
- “按文档全部实现这一阶段”

这些任务过大、边界不清，最终一定会绕开 TDD。

## 7. 给 Codex 的任务下达模板

## 7.1 实现型指令模板

适用于新功能落地：

```md
按 docs/Implementation_Playbook.md 执行一个小任务包，不要跨阶段扩张。

本次只做：
- [这里写明确范围]

必须遵守：
- 先写失败测试，再写实现
- 只改和本任务直接相关的文件
- 若发现 docs 冲突，先指出并停下，不自行发明新契约

输入文档：
- [列出文档]

完成后请只汇报：
1. 改了哪些文件
2. 跑了哪些测试
3. 是否达到任务包验收标准
4. 还剩哪些 blocker
```

## 7.2 修复型指令模板

适用于 review 后返工：

```md
只修复以下问题，不扩展范围：

- [问题 1]
- [问题 2]

约束：
- 不重构无关代码
- 不改变既有契约
- 如需改文档，先说明原因并最小修改

完成后请按“问题 -> 修改 -> 验证”格式汇报。
```

## 7.3 收口型指令模板

适用于某里程碑末尾：

```md
现在不做新功能，只做本里程碑收口。

请检查：
- 文档、contracts、mock、实现是否一致
- 本阶段 DoD 是否全部满足
- 是否缺少联调 / smoke / 回归测试

输出：
1. 已满足项
2. 未满足项
3. 建议的下一批任务包
```

## 8. 推荐的任务拆解方式

## 8.1 M0 推荐拆解

1. `packages/contracts` 骨架与类型生成策略
2. `services/api` Stage 0
3. `apps/web` Stage 0
4. 后端 Stage 1
5. 前端 Stage 1

## 8.2 M1 推荐拆解

1. 后端 `POST /tasks + GET /tasks`
2. 前端输入页 + create task hook
3. 后端 `GET /events + heartbeat + disconnect`
4. 前端 SSE / heartbeat / terminate
5. 前后端任务框架联调与 smoke

## 8.3 M2 推荐拆解

1. 后端自然语言澄清链路
2. 前端自然语言澄清 UI
3. 后端选单澄清链路
4. 前端选单澄清与倒计时
5. 需求分析与结果回填联调

## 8.4 M3 推荐拆解

1. 后端 planner
2. 后端 collector + summary
3. 前端 timeline mapper
4. 前端 timeline UI 与并发 subtask 展示
5. 搜集阶段联调与风控回归

## 8.5 M4 推荐拆解

1. 后端 writer / artifact / downloads
2. 前端 ReportCanvas / ArtifactGallery / DeliveryActions
3. 后端 feedback revision
4. 前端 FeedbackComposer / revision transition
5. 全链路 hardening 与 demo smoke

## 9. 回报与验收机制

## 9.1 每次实施完成后的回报格式

要求实施者统一按以下格式回报：

```md
完成内容：
- 

修改文件：
- 

测试：
- 已运行：
- 未运行：

结果：
- 是否达到任务包验收标准：

风险 / blocker：
- 
```

补充要求：

- 在提交上述回报前，先完成 [`docs/Execution_Log.md`](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Execution_Log.md) 的本次 session 追加记录。

## 9.2 验收时只看四件事

1. 是否严格在任务包范围内。
2. 是否先有测试，再有实现。
3. 是否满足对应 Stage 的 DoD。
4. 是否引入了文档漂移。

## 9.3 不通过时的处理

如果任务不通过，不要说“继续补一补”。

应重新生成一个更小的返工任务包，明确写：

- 哪些点未达标
- 本次只修什么
- 不允许顺手扩展什么

## 9.4 放行依据

leader 放行下一任务包时，只看两份材料：

1. [`docs/Execution_Log.md`](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Execution_Log.md) 中最新的实施记录是否完整。
2. 当前 session 回报是否与任务包验收标准一致。

## 10. 建议的实施启动顺序

如果现在正式进入开发，建议从下面这组任务包开始：

1. 创建 monorepo 骨架：`apps/web`、`services/api`、`packages/contracts`
2. 落 `packages/contracts` 的最小同源类型策略
3. 后端 Stage 0
4. 前端 Stage 0
5. 后端 Stage 1
6. 前端 Stage 1

只有这 6 步完成，才进入业务功能编码。

## 11. 最终结论

Mimir 的实施不应该靠“连续对 Codex 说继续”推进，而应该靠“小任务包 + 明确输入文档 + 明确验收标准”推进。

换句话说，真正的“发号施令”方式不是：

- “把这一阶段做完”

而是：

- “按哪份文档、在什么边界内、先写哪些测试、交付哪些文件、跑哪些验证、达到什么标准后停止”

如果后续你准备正式开工，建议下一步直接按本文档生成第一批实施任务包，而不是继续补抽象设计。
