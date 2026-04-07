# Mimir Execution Log

`docs/Execution_Log.md` is the single global implementation history for this repository.

## Usage Rules

- Maintain this file as append-only history for completed implementation sessions.
- The repository currently follows single-threaded serial development: only one active task package should be in flight at a time.
- After each development session completes, append a new entry before handing off or requesting the next task package.
- Leader release decisions should use both this log and the per-session completion report.

## Entry Template

Copy the template below for each completed session:

```md
## <Task Package> <Short Title>

- 日期时间: YYYY-MM-DD HH:MM:SS TZ (+offset)
- 任务包编号: <task id>
- session 标识: <session id>
- 目标摘要: <one-paragraph summary>
- 修改文件:
  - <path>
  - <path>
- 测试/验证:
  - 已运行: <commands or checks>
  - 未运行: <tests not run and why>
- 验收结论: <accepted / not accepted + short reason>
- blocker / 风险:
  - <item>
  - <item>
- 下一步建议:
  - <item>
  - <item>
```

## Compressed Historical Summary

- Coverage: 2026-03-13 through 2026-03-30. The detailed raw history for this period was compacted on 2026-04-07 to keep this file operational; the most recent raw entries remain verbatim below.
- Foundation / M0-M4: established the monorepo skeleton, `pnpm` / `uv` readiness, FastAPI and Next.js Stage 0 harnesses, shared contracts and stores, task creation + SSE lifecycle, clarification + requirement analysis, planner / collector loops, outline / writer / E2B / delivery, feedback revision, cleanup, and the corresponding integration closures.
- Release hardening / R1 backend: aligned real provider adapters and invocation contracts, normalized web fetch + search behavior, hardened writer rounds / timeout / failure finalization / abort lifecycle, captured reasoning + trace retention, stabilized seeded SSE bootstrap and provider finish reasons, and added production smoke / regression verification around collecting, delivery, artifacts, feedback revision, and Railway deployment readiness.
- Export / rendering stabilization: iterated on PDF and web delivery quality through footnote handling, GFM rendering rules, Chromium export hardening, E2B artifact discovery, spacer/layout fixes, human-readable delivery prompts, and explicit observability around export and LLM usage.
- Frontend design / UX wave: introduced the `Lab Terminal` visual system, tightened idle hero and clarification UX, refactored the unified input bar and workspace card order, moved `Collection Trace` to the hierarchical tree model, unified page-level card anchoring and shared long-card height caps, and repeatedly simplified report / outline / status / example prompt presentation without changing task semantics.
- Documentation / governance: repeatedly refreshed `Frontend_IA`, `DESIGN`, prompt-contract docs, production debugging playbooks, and repository execution guidance so docs stayed aligned with shipped behavior.

## Recent Raw Entries

## TP-FIX01~03: 脚注渲染修复 + 输入框草稿清空

- 日期: 2026-03-30
- 分支: `tp/unified-input-card-reorder`（追加提交）
- 目标: 修复 PDF/Web 脚注渲染问题 + 任务创建后输入框残留文本

### TP-FIX01: 清空任务创建后的输入框草稿
- 根因: `bootstrapCreateTaskIntoState()` 未清空 `initialPromptDraft`，禁用态 textarea 仍显示原始输入
- 修复: 在 `bootstrapCreateTaskIntoState()` 的 `ui` 分支中增加 `initialPromptDraft: ""`
- 变更: `research-session-store.ts`, `unified-input-bar.spec.tsx`（+1 test case）
- 验证: 82 component tests passed

### TP-FIX02: PDF 末尾参考来源使用序号替代 ref key
- 根因: `_extract_footnote_label()` 从 `<li id="fn:ref_1">` 提取 suffix `ref_1` 作为 label，LLM 使用 `[^ref_n]` 命名时显示 `[ref_1]` 而非 `[1]`
- 修复: `_extract_footnote_label()` 改为始终返回 `str(fallback_index)`（顺序序号）
- 变更: `services/api/app/infrastructure/delivery/local.py`, `tests/unit/infrastructure/test_local_report_export.py`（+1 test case）
- 验证: 16 backend tests passed

### TP-FIX03: Web 端 markdown 预览支持脚注渲染
- 根因: `react-markdown` 未配置 `remark-gfm` 插件，`[^ref_n]` 语法原样输出
- 修复: 安装 `remark-gfm`，在 `ReportCanvas` 的 ReactMarkdown 上配置 `remarkPlugins={[remarkGfm]}`。`rehype-sanitize` 的 `defaultSchema` 已包含脚注所需全部标签/属性，无需扩展
- 变更: `report-canvas.tsx`, `report-canvas.spec.tsx`（+1 test case），`package.json`, `pnpm-lock.yaml`
- 验证: 83 component tests passed, typecheck 0 error

- 验收结论: accepted — 三个修复全部通过

---

## TP-FIX04: Markdown 脚注预处理 — 顺序编号归一化

- 日期: 2026-03-30
- 分支: main（追加提交）
- 目标: 解决 Web 端 markdown 预览中脚注编号异常（显示 49、162、1112 等原始 ref key）和末尾来源缺失的问题

### 根因分析
- remark-gfm 要求 footnote ref 和 definition 的 key 完全匹配才渲染为脚注
- LLM 使用的 `[^ref_N]` key 中 N 来自 collector 的大编号池（可达 200+），非顺序
- LLM 可能存在 ref/def key 拼写不一致（`ref_49` vs `ref49`）或漏写 definition
- 无匹配 definition 的 ref 被 remark-gfm 原样输出为文本 `[^ref_49]`
- 经 6 组边界测试验证：remark-gfm 在 ref-def 匹配时渲染完全正确（始终顺序编号 1,2,3）

### 修复方案
新增纯函数 `normalizeFootnotes(md)` 在 ReactMarkdown 渲染前预处理 markdown：
1. 扫描正文中所有 `[^ref_N]` inline ref（按首次出现顺序），分配顺序编号
2. key 归一化：去下划线+小写，使 `ref_49` 与 `ref49` 匹配
3. 替换 inline ref 为 `[^1]`, `[^2]`, ...
4. 移除原始 definition 行，按顺序追加新的 definition
5. 丢弃无 inline ref 的孤立 definition，为无 def 的 ref 生成占位 `(来源缺失)`

### 变更文件
- 新建: `features/research/utils/normalize-footnotes.ts`
- 新建: `tests/unit/normalize-footnotes.spec.ts`（9 test cases）
- 修改: `features/research/components/report-canvas.tsx`（import + 调用 normalizeFootnotes）

### 验证
- `pnpm test:unit` — 68 passed (13 files)
- `pnpm test:component` — 83 passed (21 files)
- `pnpm typecheck` — 0 error

### 边界 case 处理
- 无脚注 / 空字符串 → 原样返回（快速路径）
- 重复 inline ref（同一 key 多次引用）→ 共享同一编号
- 孤立 definition → 丢弃
- 孤立 ref → 占位 def `(来源缺失)`
- 非脚注内容（加粗、链接、代码块）→ 原样保留

- 验收结论: accepted

---

## TP-FIX04-RB01 Web Footnote Preprocessor Rollback

- 日期: 2026-03-30
- 分支: `codex/rollback-tp-fix04-web-footnotes`
- 目标: 回滚 `TP-FIX04` 的 web 端 footnote 预处理层，恢复 `ReportCanvas` 对 `remark-gfm` 的原始 markdown 语义消费方式，保留 `TP-FIX01~03` 中 PDF 端脚注标签与 Web 端 GFM 接线修复

### 回滚内容
- 删除 `apps/web/features/research/utils/normalize-footnotes.ts`
- 删除 `apps/web/tests/unit/normalize-footnotes.spec.ts`
- 从 `apps/web/features/research/components/report-canvas.tsx` 移除 `normalizeFootnotes()` 接线，改为直接传递 `deferredReportMarkdown`

### 文档收口
- 更新 `docs/Frontend_IA.md` 的 `ReportCanvas` 渲染约束，明确 Web 预览不得重编号、不得删除 definition、不得合成占位来源

### 回归测试
- 新增 `apps/web/tests/component/report-canvas.spec.tsx` 覆盖以下场景：
  - `[^ref_1]` 与 `[^ref1]` 并存时保持独立脚注
  - 缺失 definition 时不伪造 `(来源缺失)`
  - 多行 footnote definition 的 continuation line 不泄漏到正文
  - 标准 `[^ref_n]` 脚注渲染仍然正常

### 验证
- `pnpm typecheck` — 0 error
- `pnpm test:unit` — 59 passed (12 files)
- `pnpm test:component` — 86 passed (21 files)

### 验收结论
- accepted

---

## PROMPT-IMPACT Preserve Manual Planner/Summary Prompt Update

- 日期: 2026-04-01
- 分支: `prompt-update-04011445`
- 目标: 保留当前分支手动更新的 planner / summary prompt 文案，补齐语义锁测试，并清理 summary prompt 不再消费 `result_status` 后留下的死实现链

### 变更内容
- 保留 `services/api/app/application/prompts/collection.py` 中当前分支的 prompt 文案更新，不回退到旧文案或 PRD 文案
- 更新 `services/api/tests/unit/application/test_collection_prompts.py`，锁定 summary prompt 的新语义：强调客观信息压缩、禁止指引/建议、要求 markdown 无序列表输出、用户 prompt 中不再注入 `<搜集状态>`；同时补充 planner prompt 对“补充描述信息和背景 / 预设上下文” wording 的断言
- 删除 `services/api/app/application/dto/research.py`、`services/api/app/application/services/collection.py` 与相关测试中仅用于 summary prompt 的 `result_status` 死字段，保持运行时行为不变

### 验证
- `cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit/application/test_collection_prompts.py -q`
- `cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit/infrastructure/test_zhipu_adapters.py -k "planner or summary" -q`

### 验收结论
- accepted

---

## CT-GUARD Plan Round Multi-Collect Guard

- 日期: 2026-04-01
- 分支: `codex/collection-trace-multi-collect-guard`
- 目标: 锁定 `Collection Trace` 对“单轮 planner 最多同时挂 3 个 collect group” 的前端设计预期与回归测试

### 变更内容
- 更新 `docs/Frontend_IA.md`，明确单个 `plan round` 下可同时保留多个 `collect group`，且当前前端设计预期 planner 单轮一次最多发起 `3` 个 collect，并按请求顺序显示
- 更新 `apps/web/tests/unit/mappers/timeline-mapper.spec.ts`，新增单轮 planner 连续发起 `3` 个 `tool_call_id` 仍保留在同一 `plan round` 的 mapper 回归测试，并锁定各自 collector / summary 事件按 `tool_call_id` 正确回填，不发生串组
- 更新 `apps/web/tests/component/timeline-panel.spec.tsx`，新增一个 `plan round` 下完整渲染 `3` 个 `Collect` 块的 component 回归测试

### 验证
- `cd apps/web && pnpm typecheck`
- `cd apps/web && pnpm test:unit`
- `cd apps/web && pnpm test:component`

### 验收结论
- accepted

## FE-DELIVERY-STATUS-POLISH Report Delivery Status Polish

- 日期时间: 2026-04-01 11:04:20 CST (+0800)
- 任务包编号: FE-DELIVERY-STATUS-POLISH
- session 标识: codex/report-delivery-status-polish
- 目标摘要: 收敛交付态前端文案与入口职责，移除 `Report Canvas` 中的轮次标题，调整 `writing_report` 顶栏文案为“正在生成研究内容”，并把 `delivered` 后的新研究入口从 `DeliveryActions` 移到 `SessionStatusBar`，保持非交付态 disconnect 行为不变。
- 修改文件:
  - `apps/web/features/research/components/report-canvas.tsx`
  - `apps/web/features/research/components/session-status-bar.tsx`
  - `apps/web/features/research/components/delivery-actions.tsx`
  - `apps/web/tests/component/report-canvas.spec.tsx`
  - `apps/web/tests/component/session-status-bar.spec.tsx`
  - `apps/web/tests/component/delivery-new-research.spec.tsx`
  - `apps/web/tests/integration/report-delivery-flow.spec.tsx`
  - `docs/Frontend_IA.md`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm test:component -- report-canvas.spec.tsx session-status-bar.spec.tsx delivery-new-research.spec.tsx`；`cd apps/web && pnpm test:integration -- report-delivery-flow.spec.tsx`；`cd apps/web && pnpm typecheck`；`cd apps/web && pnpm test:component`；`cd apps/web && pnpm test:integration`
  - 未运行: 无
- 验收结论: accepted；文档、测试、实现与最终验证顺序符合要求，且改动限制在任务包指定组件、文档与必要测试范围内。
- blocker / 风险:
  - `pnpm test:integration` 期间 `tests/integration/report-delivery-flow.spec.tsx` 仍会输出未匹配 `POST /api/v1/tasks/tsk_stage0/heartbeat` 的 MSW warning；当前测试结果为通过，但该 warning 不是本任务范围内修复项。
- 下一步建议:
  - 如需进一步清理测试输出，可单独下发一个小任务包为 `report-delivery-flow` 增补 heartbeat handler

---

## TP-WORKSPACE-CARD-ANCHOR-05 Shared Card Anchor and Inner Scroll Decoupling

- 日期: 2026-03-31
- 分支: `codex/workspace-card-anchor-alignment`
- 目标: 将内容卡片自动定位收敛为工作台级共享定义，并将 `Collection Trace` / `Report Canvas` 的内容刷新改为仅滚动卡片内部容器

### 变更内容
- 更新 `docs/Frontend_IA.md`，明确内容卡片出现时使用工作台级共享 card anchor，对齐到顶栏下方统一留白；长内容卡片刷新只允许内部滚动，不驱动页面滚动
- 新增 `apps/web/features/research/hooks/use-workspace-card-anchor.ts`，由工作台统一管理页面级卡片定位
- 修改 `apps/web/features/research/components/research-workspace-shell.tsx`，给澄清、需求摘要、Collection Trace、Outline、Report 卡片接入统一 anchor 管理
- 移除 `apps/web/features/research/components/clarification-panels.tsx` 中澄清卡片的局部页面滚动特例
- 修改 `apps/web/features/research/components/timeline-panel.tsx` 与 `apps/web/features/research/hooks/use-report-auto-scroll.ts` / `apps/web/features/research/components/report-canvas.tsx`，将内容刷新改为容器 `scrollTo(...)`，不再依赖 `scrollIntoView`
- 更新 component / integration tests，覆盖共享 page anchor 与 inner-scroll-only 行为

### 验证
- `cd apps/web && pnpm typecheck` - 0 error
- `cd apps/web && pnpm test:component` - 89 passed
- `cd apps/web && pnpm test:integration` - 37 passed

### 验收结论
- accepted

---

## TP-CARD-HEIGHT-RECOMPUTE-04 Recompute Card Height Token on Workspace Activation

- 日期: 2026-03-31
- 分支: `codex/card-level-height-cap`
- 目标: 修正 `idle -> active workspace` 切换时 card-level height token 不重算的问题

### 变更内容
- 更新 `docs/Frontend_IA.md`，明确 active workspace 挂载后必须重新计算并写入动态卡片高度 token
- 更新 `apps/web/tests/component/research-page-client.spec.tsx`，覆盖 `Idle -> active workspace` 路径上 `--research-card-max-h` 从空值变为计算值的回归场景

### 验证
- `cd apps/web && pnpm typecheck` - 0 error
- `cd apps/web && pnpm test:component` - 88 passed
- `cd apps/web && pnpm test:integration` - 37 passed

### 验收结论
- accepted

## TP-FRONTEND-CLARIFICATION-WORKSPACE-TIGHTEN Clarification Workspace Tighten

- 日期时间: 2026-03-30 18:52:47 CST (+0800)
- 任务包编号: frontend-clarification-workspace-tighten
- session 标识: codex-execute-agent-frontend-clarification-workspace-tighten
- 目标摘要: 收口前端工作台澄清体验与阶段展示逻辑，将澄清详情文案改为更自然的反馈请求，提交初始需求后自动滚动到澄清详情区，未开始的工作台卡片改为按阶段出现，同时让顶栏下半部只显示 `taskId`，不再展示阶段补充小字、搜集进度或 `analysisText`。
- 修改文件:
  - `docs/Frontend_IA.md`
  - `docs/Execution_Log.md`
  - `apps/web/features/research/components/clarification-panels.tsx`
  - `apps/web/features/research/components/research-workspace-shell.tsx`
  - `apps/web/features/research/components/session-status-bar.tsx`
  - `apps/web/tests/component/session-status-bar.spec.tsx`
  - `apps/web/tests/component/research-page-client.spec.tsx`
  - `apps/web/tests/component/collect-progress-display.spec.tsx`
  - `apps/web/tests/integration/create-task-flow.spec.tsx`
  - `apps/web/tests/integration/clarification-flow.spec.tsx`
- 测试/验证:
  - 已运行: `pnpm test:component -- --runInBand apps/web/tests/component/session-status-bar.spec.tsx apps/web/tests/component/research-page-client.spec.tsx apps/web/tests/component/collect-progress-display.spec.tsx`
  - 已运行: `pnpm test:integration -- --runInBand apps/web/tests/integration/create-task-flow.spec.tsx apps/web/tests/integration/clarification-flow.spec.tsx`
  - 已运行: `pnpm test:component`
  - 已运行: `pnpm test:integration`
  - 已运行: `pnpm typecheck`
  - 未运行: 无
- 验收结论: accepted
- blocker / 风险:
  - `pnpm test:integration` 过程中仍会看到来自无关 `report-delivery-flow` 的现有 MSW heartbeat 警告，但不会影响测试结果
- 下一步建议:
  - 如需进一步优化，可在不改变阶段 gating 的前提下，再细化 timeline / outline 的视觉密度
  - 当前任务可直接进入收尾与后续任务分派

---

## TP-WEB-FOOTNOTE-01 Hide Footnote Backrefs

- 日期: 2026-03-30
- 分支: `codex/hide-web-footnote-backrefs`
- 目标: 仅在 Web 端 `ReportCanvas` 中隐藏 `remark-gfm` 生成的 footnote backref 可见符号与编号，保留正文 superscript 引用、脚注编号列表和来源链接

### 变更内容
- 更新 `docs/Frontend_IA.md`，补充 Web 预览可以隐藏 footnote backref，但不得改写脚注正文或 definition
- 在 `apps/web/features/research/components/report-canvas.tsx` 中增加局部 `a` renderer，屏蔽 `data-footnote-backref` 链接
- 新增 `apps/web/tests/component/report-canvas.spec.tsx` 回归测试，覆盖 backref 隐藏、正文 superscript 保留与来源链接保留

### 验证
- `pnpm typecheck` — 0 error
- `pnpm test:component` — 87 passed (21 files)

### 验收结论
- accepted

---

## TP-COLLECTION-TRACE-HEIGHT-01 Collection Trace Scope and Shared Body Height Cap

- 日期: 2026-03-30
- 分支: `codex/collection-trace-height-cap`
- 目标: 将右栏 `Live Timeline` 收缩为仅展示信息检索阶段的 `Collection Trace`，并为 `Collection Trace` 与 `ReportBody` 引入共享的动态 body height token

### 变更内容
- 更新 `docs/Frontend_IA.md`，明确 `Collection Trace` 只展示 `planning_collection` 到 `merging_sources` 之间的检索信息，不再承载 analysis / outline / writer / artifact / report 信息
- 新增 `apps/web/features/research/hooks/use-workspace-body-max-height.ts` 与 `apps/web/features/research/utils/layout-vars.ts`，由工作台根节点测量顶栏与底部输入区之间的可视高度并写入共享 CSS 变量
- 修改 `apps/web/features/research/components/timeline-panel.tsx`、`apps/web/features/research/components/report-canvas.tsx`，改为消费共享 body height token，移除写死 `34rem`
- 修改 `apps/web/features/research/components/research-workspace-shell.tsx`，让 `Collection Trace` 只在 collection 阶段可见
- 为 `session-status-bar.tsx` 与 `unified-input-bar.tsx` 增加布局测量标记，供共享高度 hook 使用
- 收窄 `apps/web/features/research/mappers/timeline-mapper.ts` 的展示映射，仅保留 collection 相关事件进入 `Collection Trace`，同时保留 `outlineReady` 状态更新
- 更新相关 component / unit / integration tests，覆盖文案、显示时机、事件过滤与共享高度 token

### 验证
- `pnpm typecheck` - 0 error
- `pnpm test:unit` - 58 passed
- `pnpm test:component` - 88 passed
- `pnpm test:integration` - 37 passed

### 验收结论
- accepted

---

## TP-COLLECTION-TRACE-LIFECYCLE-02 Collection Trace Lifetime Correction

- 日期: 2026-03-30
- 分支: `codex/collection-trace-height-cap`
- 目标: 修正 `Collection Trace` 的可见生命周期，确保其在 collection 阶段之后继续作为历史卡片保留并上推显示

### 变更内容
- 更新 `docs/Frontend_IA.md`，明确 `Collection Trace` 自进入 `planning_collection` 起出现，并在后续 `preparing_outline` / `writing_report` / `delivered` 阶段继续保留
- 调整 `apps/web/features/research/components/research-workspace-shell.tsx`，移除 `Collection Trace` 在 `preparing_outline` 之后隐藏的限制
- 更新 `apps/web/tests/component/collect-progress-display.spec.tsx`、`apps/web/tests/component/research-page-client.spec.tsx`、`apps/web/tests/integration/research-transparency.spec.tsx`、`apps/web/tests/integration/report-delivery-flow.spec.tsx` 中与生命周期相关的断言

### 验证
- `pnpm typecheck` - 0 error
- `pnpm test:component` - 88 passed
- `pnpm test:integration` - 37 passed

### 验收结论
- accepted

---

## TP-COLLECTION-TRACE-CARD-HEIGHT-03 Collection Trace and Report Canvas Card-Level Height Cap

- 日期: 2026-03-30
- 分支: `codex/card-level-height-cap`
- 目标: 将 `Collection Trace` 与 `Report Canvas` 的高度约束从 body 级纠正为 card 级，确保卡片本身限高、内部内容滚动

### 变更内容
- 更新 [docs/Frontend_IA.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Frontend_IA.md)，明确长内容卡片的动态上限作用于卡片容器本身，卡片头部固定可见，内部 body 负责滚动
- 调整 [apps/web/features/research/components/timeline-panel.tsx](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/apps/web/features/research/components/timeline-panel.tsx) 与 [apps/web/features/research/components/report-canvas.tsx](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/apps/web/features/research/components/report-canvas.tsx)，将共享动态高度 token 挂到外层卡片容器，并让内部 body 变成 flex 滚动区
- 将共享 token 重命名为 card-level 语义，更新 [apps/web/features/research/utils/layout-vars.ts](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/apps/web/features/research/utils/layout-vars.ts) 与 [apps/web/features/research/hooks/use-workspace-body-max-height.ts](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/apps/web/features/research/hooks/use-workspace-body-max-height.ts)
- 更新 [apps/web/tests/component/timeline-panel.spec.tsx](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/apps/web/tests/component/timeline-panel.spec.tsx)、[apps/web/tests/component/report-canvas.spec.tsx](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/apps/web/tests/component/report-canvas.spec.tsx)、[apps/web/tests/component/research-page-client.spec.tsx](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/apps/web/tests/component/research-page-client.spec.tsx) 以覆盖 card-level 限高与内部滚动行为

### 验证
- `cd apps/web && pnpm typecheck` - 0 error
- `cd apps/web && pnpm test:component` - 88 passed
- `cd apps/web && pnpm test:integration` - 37 passed

### 验收结论
- accepted

---

## CT-DATA Collection Trace Tree Data Model

- 日期: 2026-03-31
- 分支: `codex/collection-trace-tree-data`
- 目标: 将 `Collection Trace` 的底层数据从扁平 `TimelineItem[]` 收敛为能表达 `plan round -> collect group -> collect events / summary` 与 `sources merged` 的树状结构，同时保留最小 `timeline` 兼容层，不提前重做 UI

### 变更内容
- 更新 `docs/Frontend_IA.md`，把 `Collection Trace` 定义为卡片级根节点，并明确独立 `plan round`、`collect group`、同级 `summary`、一级 `sources merged` 与前端 round inference 规则
- 在 `apps/web/features/research/store/research-session-store.types.ts` 中新增 `CollectionTraceRoot`、`CollectionPlanRoundNode`、`CollectionCollectGroup`、`CollectionCollectEntry`、`CollectionSummaryNode`、`CollectionSourcesMergedNode` 等类型，并将 `stream.collectionTrace` 纳入权威状态
- 新增 `apps/web/features/research/mappers/collection-trace-builder.ts`，用显式规则处理 planner loop 切分、collect reasoning burst 切分、4 类工具事件落位、summary sibling 挂接与 `sources merged` 顶层终点节点
- 修改 `apps/web/features/research/mappers/timeline-mapper.ts` 与 `apps/web/features/research/reducers/event-reducer.ts`，在保留现有 `timeline` 兼容层的同时，把 collection 相关事件同步写入新的 `collectionTrace`
- 更新 `apps/web/tests/unit/mappers/timeline-mapper.spec.ts`，覆盖多轮 planner loop、collect group 内时间顺序、summary sibling、sources merged 顶层节点与 collection-only 过滤回归

### 验证
- `cd apps/web && pnpm typecheck` - 0 error
- `cd apps/web && pnpm test:unit` - 59 passed
- `cd apps/web && pnpm test:component` - 89 passed

### 验收结论
- accepted

---

## CT-UI Collection Trace Hierarchical Rendering

- 日期: 2026-03-31
- 分支: `codex/collection-trace-tree-data`
- 目标: 将 `Collection Trace` 的前端渲染切到权威的 `stream.collectionTrace` 树状模型，准确呈现 `plan round -> collect / summary -> sources merged` 的层级与折叠预览交互

### 变更内容
- 更新 `docs/Frontend_IA.md`，补充 `Collection Trace` 的 UI 呈现规则，明确 `stream.collectionTrace` 是面板主数据源、`Plan Round N` 顶层 section、`collect` / `summary` 同级、reasoning 与 summary 默认单行预览且独立展开、`Sources Merged` 直接完整显示
- 重写 `apps/web/features/research/components/timeline-panel.tsx`，将渲染输入从扁平 `TimelineItem[]` 切到 `CollectionTraceRoot`，新增 plan round、collect group、tool event、summary、sources merged 的层级化展示与独立展开控制，同时保留卡片级限高与内部自动滚动
- 修改 `apps/web/features/research/components/research-workspace-shell.tsx`，让工作台将 `stream.collectionTrace` 作为 `Collection Trace` 卡片的唯一主数据输入
- 扩展 `apps/web/tests/fixtures/builders.ts`，新增 collection trace 树结构的测试夹具
- 更新 `apps/web/tests/component/timeline-panel.spec.tsx`、`apps/web/tests/component/collect-progress-display.spec.tsx`、`apps/web/tests/component/copy-cleanup.spec.tsx`、`apps/web/tests/component/research-page-client.spec.tsx` 与 `apps/web/tests/integration/research-transparency.spec.tsx`，覆盖多轮 plan、collect / summary 同级、tool event 顺序、独立展开与 sources merged 终点渲染

### 验证
- `cd apps/web && pnpm typecheck` - 0 error
- `cd apps/web && pnpm test:component` - 91 passed
- `cd apps/web && pnpm test:integration` - 37 passed

### 验收结论
- accepted

---

## CT-CLEANUP Remove Legacy Collection Timeline Compatibility Layer

- 日期: 2026-03-31
- 分支: `codex/collection-trace-tree-data`
- 目标: 移除 web 前端中为旧 `timeline` 保留的 collection 兼容层，让 collection 相关前端逻辑只依赖 `stream.collectionTrace`

### 变更内容
- 更新 `docs/Frontend_IA.md`，明确 `collectionTrace` 是 collection 相关前端逻辑的唯一权威流，删除 `stream.timeline` / `TimelineItem` 兼容层的文档定义
- 修改 `apps/web/features/research/store/selectors.ts`，让 `selectCollectProgress` 从 `collectionTrace` 推导搜集进度，不再依赖旧 timeline 投影
- 修改 `apps/web/features/research/store/research-session-store.types.ts`、`apps/web/features/research/store/research-session-store.ts`，删除 `stream.timeline`、`TimelineItem` 与 `revision-divider` 死代码，并在 revision switch 时显式清空 `collectionTrace`
- 重写 `apps/web/features/research/mappers/timeline-mapper.ts` 与 `apps/web/features/research/reducers/event-reducer.ts`，保留文件边界但移除 collection timeline 兼容写入，只维护 `collectionTrace` 与 `outlineReady`
- 更新 `apps/web/tests/unit/collect-progress.spec.ts`、`apps/web/tests/unit/mappers/timeline-mapper.spec.ts`、新增 `apps/web/tests/unit/research-session-store.spec.ts`，并同步收口 `apps/web/tests/component/session-status-bar.spec.tsx` 与 `apps/web/tests/fixtures/builders.ts`

### 验证
- `cd apps/web && pnpm typecheck`
- `cd apps/web && pnpm test:unit`
- `cd apps/web && pnpm test:component`
- `cd apps/web && pnpm test:integration`

### 验收结论
- accepted

---

## CT-DENSITY Compact Collection Trace Tool Events

- 日期: 2026-04-01
- 分支: `codex/collection-trace-tool-event-density`
- 目标: 将 `Collection Trace` 内 `search/fetch started/completed` 四类工具事件从大块嵌套卡片收敛为紧凑日志行，并消除长 fetch URL 的横向溢出风险

### 变更内容
- 更新 `docs/Frontend_IA.md`，补充 `Collection Trace` 的 tool-event 密度规则，明确四类工具事件必须保留独立事件语义，但展示上降级为遵循 `DESIGN.md` 的 compact row；同时锁定 `fetch` 事件优先显示 `hostname + 截断 path`、完整 URL 保留在可访问属性中、内容区必须使用 `min-w-0` 与单行截断
- 修改 `apps/web/features/research/components/timeline-panel.tsx`，新增 `ToolEventRow` 与 fetch URL 格式化逻辑，将 `search/fetch started/completed` 改为紧凑三段式日志行，保留 reasoning / summary / collect completed 的原有层级权重
- 更新 `apps/web/tests/component/timeline-panel.spec.tsx`，补充 compact tool row 与长 URL 可访问/截断回归，并验证四类工具事件仍按原顺序独立显示

### 验证
- `cd apps/web && pnpm test:component -- timeline-panel.spec.tsx` - 102 passed

### 验收结论
- accepted

---

## DOCS-AGENT Role Split Guidance

- 日期: 2026-04-01
- 分支: `codex/agent-role-guidance-split`
- 目标: 将仓库级 agent 规则拆分为 `for-master-agent` 与 `for-execute-agent` 两个章节，保留通用纪律在公共区，并新增 master-agent 创建 execute-agent 时禁止 `fork_context: true` 的约束；同步更新 `CLAUDE.md`

### 变更内容
- 更新 `AGENTS.md`，将角色相关规则从原 `agent 规则` 拆分为 `通用规则`、`for-master-agent` 与 `for-execute-agent` 三部分；保留单线程串行开发、`docs-first / tests-first / implementation` 等通用纪律在公共区
- 在 `for-master-agent` 中新增：创建 `execute-agent` 时禁止使用 `fork_context: true`，要求以干净上下文开始，只传递当前任务包所需的最小必要信息
- 在 `for-execute-agent` 中收口执行侧职责与任务包执行原则
- 同步更新 `CLAUDE.md`，保持与仓库级 agent 规范一致

### 验证
- 人工校对 `AGENTS.md` 与 `CLAUDE.md` 的角色章节结构与措辞一致
- 人工确认通用规则仍留在公共区，未被错误拆分到角色章节

### 验收结论
- accepted

---

## CLARIFICATION Anchor Countdown Polish

- 日期: 2026-04-01
- 分支: `codex/clarification-anchor-countdown-polish`
- 目标: 修正 clarification / requirement summary 共享 anchor 可视位置，新增 options clarification 全局 sticky 倒计时，将前端默认倒计时文案调整为 30 秒，并固定底部 submit 按钮宽高

### 变更内容
- 更新 `docs/Frontend_IA.md`，补充 clarification ready re-anchor、Requirement Summary 可视锚点、独立 sticky 倒计时 surface、30 秒默认倒计时与输入按钮固定宽度约束
- 更新 `apps/web/tests/component/research-page-client.spec.tsx`、`apps/web/tests/component/clarification-countdown.spec.tsx`、`apps/web/tests/component/unified-input-bar.spec.tsx` 与 `apps/web/tests/integration/clarification-flow.spec.tsx`，先锁定 clarification / requirement summary re-anchor、全局倒计时可见性、30 秒倒计时文案与 submit 按钮固定尺寸回归；同步把测试 fixtures / reducer 断言中的默认 countdown duration 调整为 30 秒
- 修改 `apps/web/features/research/hooks/use-workspace-card-anchor.ts`，支持按卡片解析内部 anchor target；并在 `apps/web/features/research/components/clarification-panels.tsx`、`apps/web/features/research/components/requirement-summary-card.tsx` 与 `apps/web/features/research/components/research-workspace-shell.tsx` 中把 clarification 标题与 requirement summary 内容区接入共享 anchor，同时新增独立的 options clarification sticky countdown surface
- 修改 `apps/web/features/research/hooks/use-workspace-body-max-height.ts` 与 `apps/web/features/research/utils/layout-vars.ts`，为全局 sticky countdown surface 写入状态栏高度 CSS 变量，保证其停靠在状态栏下方
- 修改 `apps/web/features/research/components/research-config-panel.tsx` 与 `apps/web/features/research/components/unified-input-bar.tsx`，将 options clarification 默认文案更新为 30 秒，并把 submit 按钮改为固定宽度、固定高度、居中内容的布局

### 验证
- `cd apps/web && pnpm typecheck`
- `cd apps/web && pnpm test:component`
- `cd apps/web && pnpm test:integration`

### 验收结论
- accepted

---

## Workspace Long-Card Height And Outline Polish

- 日期: 2026-04-01
- 分支: `codex/workspace-card-height-outline-polish`
- 目标: 修正工作台长卡高度测量与占位，让 `Collection Trace` / `Report Canvas` 使用同一 viewport content band；交付态报告默认从顶部开始阅读；将 `OutlineCard` 从 plain list 提升为可扫描的编号层级结构；把底部输入托盘改为 docked tonal surface，同时保持现有 anchor 与交互语义不变

### 变更内容
- 更新 `docs/Frontend_IA.md`，补充长卡高度 token 的 viewport content band 口径、`delivered` 态报告首屏顶部规则、`OutlineCard` 结构化层级要求，以及 `UnifiedInputBar` 的 docked surface 视觉约束
- 更新 `apps/web/tests/component/research-page-client.spec.tsx`、`apps/web/tests/component/report-canvas.spec.tsx`、`apps/web/tests/component/outline-card.spec.tsx` 与 `apps/web/tests/component/unified-input-bar.spec.tsx`，先锁定共享长卡高度 token、交付态报告首屏位置、outline 编号分组结构与输入托盘无顶边线语义；同步调整既有 card-height 回归断言以匹配新测量规则
- 修改 `apps/web/features/research/hooks/use-workspace-body-max-height.ts`，将共享长卡高度改为基于 viewport、sticky status bar、高度固定的 input tray 与统一留白推导；并在 `apps/web/features/research/components/timeline-panel.tsx`、`apps/web/features/research/components/report-canvas.tsx` 中让长卡实际占满该内容带高度
- 修改 `apps/web/features/research/hooks/use-report-auto-scroll.ts` 与 `apps/web/features/research/components/report-canvas.tsx`，保留 `writing_report` 阶段的自动贴底与“回到底部”按钮，同时让 `delivered` 首次渲染回到报告起始位置，避免交付态继续被推到底部
- 修改 `apps/web/features/research/components/outline-card.tsx` 与 `apps/web/features/research/components/unified-input-bar.tsx`，将 outline 改为 leading-zero 编号、标题/说明分层的 terminal 式结构，并把底部输入区改为 tonal stacking 的 docked tray，移除原顶边线分隔

### 验证
- `cd apps/web && pnpm typecheck`
- `cd apps/web && pnpm test:component`
- `cd apps/web && pnpm test:integration`

### 验收结论
- accepted

---

## Collection Trace Tool Pair Merge

- 日期: 2026-04-01
- 分支: `codex/collection-trace-tool-pairs`
- 任务包编号: 未提供
- session 标识: codex-20260401-collection-trace-tool-pairs
- 目标: 将 `Collection Trace` 中 search / fetch 的 started-completed 事件在前端渲染层折叠为单行 tool row，统一为低侵入样式；Search 显示 query，Fetch 显示 URL 导向对象，右侧仅显示当前状态，同时移除 search result count 与 fetch completed title 的旧 completed-only 文案

### 变更内容
- 更新 `docs/Frontend_IA.md`，将 `Collection Trace` tool row 规则改为 render-time 成对折叠，明确统一行样式、时序保持与 completed-only 文案隐藏要求
- 更新 `apps/web/tests/component/timeline-panel.spec.tsx`，先锁定 search/fetch 成对折叠、Started/Done 状态、旧 completed-only 文案隐藏、started-only 降级以及统一 row marker 的组件回归
- 修改 `apps/web/features/research/components/timeline-panel.tsx`，新增本地 merge 逻辑，仅基于现有 `collect.entries` 顺序合并相邻 started/completed pair；Search 与 Fetch 共享同一 row treatment，并对没有匹配 started 的 completed 事件做安全降级显示

### 验证
- `cd apps/web && pnpm exec vitest run tests/component/timeline-panel.spec.tsx`
- `cd apps/web && pnpm typecheck`
- `cd apps/web && pnpm test:component`

### 验收结论
- accepted

### 风险
- 目前 render-time merge 只折叠相邻的 started/completed pair；如果后端未来输出非相邻配对事件，前端会安全降级为多行而不是跨事件重排
- `pnpm test:component` 仍会输出既有 MSW 未匹配 artifact 请求告警，但本次任务相关测试均通过，且没有新增失败

---

## Collector Limit Finalize Turn

- 日期时间: 2026-04-01 18:50:10 CST (+0800)
- 任务包编号: 未提供
- session 标识: codex-20260401-collector-limit-finalize-turn
- 目标摘要: 修复 collector subtask 的工具调用上限收口语义，使第 10 次工具调用完成后不再立刻硬停，而是先把第 10 次 tool result 回放进 transcript，允许 collector 再获得一次 finalize 机会；当 collector 继续请求第 11 次工具调用时，仅阻断未执行的调用，并让 summary 输入优先基于最终 `CollectResult.items`。
- 修改文件:
  - `docs/Architecture.md`
  - `services/api/app/application/services/collection.py`
  - `services/api/tests/integration/collection/test_collection_engine.py`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/integration/collection/test_collection_engine.py -k "tool_call_limit"`；`cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit/application/test_collection_prompts.py tests/integration/collection/test_collection_engine.py -k "tool_call_limit or collector"`
  - 未运行: 其余 backend 单元、契约、集成测试；本任务按任务包只覆盖 collector limit 与相关 collector 集成路径
- 验收结论: accepted；已满足“最多执行 10 次工具调用、阻断第 11 次执行、保留 post-limit finalize 轮、summary 输入使用最终 `CollectResult.items`”的任务包验收条件。
- blocker / 风险:
  - 当前超限后的最终一次 stop 依赖 collector 在收到 `tool_call_limit_exceeded` tool message 后收口；若未来 provider 行为持续忽略该提示，orchestrator 仍会按 partial 结果强制收口
  - 为消除现有 Stage 5 测试中的 SSE 时序抖动，本次相关测试改为基于 fake agent invocation 与 DB event 轮询判断完成；该变更不扩大业务行为范围，但后续若要专门验证 SSE 时序，仍建议单独补更稳健的流式测试工具
- 下一步建议:
  - 若后续还有 collector loop 调整，优先补一个更通用的 Stage 5 “等待 collection barrier 完成”测试辅助，减少各测试重复处理 SSE 时序
  - 如需继续收紧 limit 语义，可再评估是否要为“收到 limit notice 后仍继续请求工具”的 forced-partial 路径补独立 observability 事件

## Prompt Update Drift Review

- 日期时间: 2026-04-01 22:25:09 CST (+0800)
- 任务包编号: 未提供
- session 标识: codex-20260401-prompt-update-drift-review
- 目标摘要: 审查 `prompt-update-04012155` 上用户手工修改的 collector 与 outline prompt 文案，判断是否引入契约、测试或运行时漂移；结论为 prompt 语义已变化但未造成直接运行时 breakage，因此仅补齐最小化的语义锁测试与 outline parser fixture，使当前 prompt 行为、测试预期与运行时容错保持一致。
- 修改文件:
  - `services/api/app/application/prompts/collection.py`
  - `services/api/app/application/prompts/delivery.py`
  - `services/api/tests/unit/application/test_collection_prompts.py`
  - `services/api/tests/unit/application/test_delivery_prompts.py`
  - `services/api/tests/unit/infrastructure/test_zhipu_outline_agent.py`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit/application/test_collection_prompts.py tests/unit/application/test_delivery_prompts.py tests/unit/infrastructure/test_zhipu_outline_agent.py`
  - 未运行: 其余 backend unit / contract / integration tests；本任务包仅要求审查 prompt 语义锁与直接受影响的 outline parser 路径
- 验收结论: accepted；collector prompt 的新工具与收口语义已被语义锁测试覆盖，outline prompt 示例移除硬编码 `参考来源` section 后，相关 prompt 测试与直接受影响的 parser fixture 已同步，且 targeted tests 全部通过。
- blocker / 风险:
  - 未重跑更广泛的 delivery / collection 集成链路；当前结论基于 prompt builders 与 directly impacted outline parser tests
  - outline prompt 不再示例化 `参考来源` section 后，模型输出章节结构可能更自由，但当前 parser 已允许任意非 `标题` section key，未发现新增运行时约束
- 下一步建议:
  - 后续如继续人工调整 prompt 文案，同步维护 prompt semantic-lock tests，避免再次出现仅测试层漂移
  - 若线上观察到 outline 章节分布变化，再决定是否需要补充更高层的 delivery integration coverage

## Clarification Countdown + Top Stack Fixes

- 日期时间: 2026-04-01 22:51:36 CST (+0800)
- 任务包编号: 未提供
- session 标识: codex-20260401-clarification-layout-countdown-fixes
- 目标摘要: 修复 options clarification 的真实倒计时默认值仍为 15 秒、顶部倒计时在长问题列表滚动时缺少统一 sticky top stack、澄清标题与 requirement summary anchor 仍只按 status bar 计算，以及顶部状态区 sticky 行为回退的问题；本次仅在既有后端配置路径与前端工作台布局/anchor hooks 上做最小本地修复，不扩展业务功能。
- 修改文件:
  - `services/api/.env.example`
  - `services/api/app/core/config.py`
  - `services/api/tests/unit/core/test_config.py`
  - `services/api/tests/integration/lifecycle/test_clarification_lifecycle.py`
  - `apps/web/features/research/components/clarification-panels.tsx`
  - `apps/web/features/research/components/research-workspace-shell.tsx`
  - `apps/web/features/research/components/session-status-bar.tsx`
  - `apps/web/features/research/hooks/use-workspace-body-max-height.ts`
  - `apps/web/features/research/hooks/use-workspace-card-anchor.ts`
  - `apps/web/features/research/utils/layout-vars.ts`
  - `apps/web/tests/component/clarification-countdown.spec.tsx`
  - `apps/web/tests/component/research-page-client.spec.tsx`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit/core/test_config.py tests/integration/lifecycle/test_clarification_lifecycle.py -q`；`cd apps/web && pnpm test:component -- --run tests/component/clarification-countdown.spec.tsx tests/component/research-page-client.spec.tsx`；`cd apps/web && pnpm exec vitest run tests/integration/clarification-flow.spec.tsx tests/integration/create-task-flow.spec.tsx`
  - 未运行: 更广的 frontend `pnpm test:integration` 全量回归；一次脚本尝试会把目录内无关用例一并拉起，并命中既有 `tests/integration/research-transparency.spec.tsx` 失败，因此本次按任务包只保留 directly impacted integration 用例验收
- 验收结论: accepted；options clarification 的默认倒计时已改为 30 秒并通过后端配置/生命周期测试锁定，前端工作台已恢复为统一 sticky top stack，澄清标题与 requirement summary anchor 均按完整 top stack 高度计算，相关 targeted tests 全部通过。
- blocker / 风险:
  - 当前验证集中在直接受影响的 backend lifecycle、frontend component 与两条前端 integration 链路，未重新执行更大范围的 web 回归集
  - 既有 `tests/integration/research-transparency.spec.tsx` 在全量 integration 脚本下仍失败，但失败点与本次修改范围无关，需单独任务包处理
- 下一步建议:
  - 若 production 需要显式覆盖倒计时时长，可在部署变量中按新增示例配置 `MIMIR_CLARIFICATION_COUNTDOWN_SECONDS`
  - 后续如继续调整 workspace 顶部结构，优先复用 `data-research-top-stack` 这一测量入口，避免再次回退到只按 status bar 计算

## TP-2026-04-01 Planner Stop Reasoning Preserve

- 日期时间: 2026-04-01 23:35:17 CST (+0800)
- 任务包编号: TP-2026-04-01-planner-stop-reasoning-preserve
- session 标识: codex-20260401-planner-stop-reasoning-preserve
- 目标摘要: 修复 planner adapter 在 `provider_finish_reason=stop` 时的停止语义，使其无论 `content` 是非 JSON 文本、非 dict JSON 还是空字符串，都会将 provider 返回的 `reasoning_content` 保留到 `PlannerDecision.reasoning_deltas` 中，并立即结束 planner；同时保持既有 tool_calls 与 JSON plan 解析路径不回归。
- 修改文件:
  - `docs/Architecture.md`
  - `services/api/tests/unit/infrastructure/test_zhipu_adapters.py`
  - `services/api/app/infrastructure/research/real_http.py`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit/infrastructure/test_zhipu_adapters.py -k "planner"`（红测，新增 3 个 stop reasoning 用例失败）；`cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit/infrastructure/test_zhipu_adapters.py -k "planner"`（修复后转绿，9 passed）；`cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit/infrastructure/test_zhipu_adapters.py`（49 passed）
  - 未运行: `tests/integration`；本任务包只涉及 planner adapter 的 unit 级 stop 语义修复，未触及需要新增 integration 覆盖的跨阶段流程
- 验收结论: accepted；`provider_finish_reason=stop` 时 planner 已不再依赖 `content` 的 JSON dict 可解析性来保留 reasoning，且既有 planner tool_call / JSON plan 解析测试保持通过。
- blocker / 风险:
  - 当前 stop 分支优先保留 provider `reasoning_content`；如果某些 provider 未来只在 `content` JSON 里返回 `reasoning_deltas` 且不再提供 `reasoning_content`，仍需单独评估是否要扩展 stop 分支兼容策略
  - 本次未新增 integration 级 coverage；若后续 orchestrator 对 planner transcript 回灌策略再调整，需配套补跨轮集成验证
- 下一步建议:
  - 若近期继续处理 planner / collector transcript 问题，可补一条 integration 测试验证 stop round 的 reasoning 会进入下一轮 transcript
  - 若发现其他 adapter 对 `provider_finish_reason` 仍有“靠 content 猜语义”的分支，可按同样方式单独收敛

## TP-20260401 Collection Trace Input Outline Polish

- 日期时间: 2026-04-01 23:59:08 CST (+0800)
- 任务包编号: TP-20260401
- session 标识: codex-20260401-collection-trace-input-outline-polish
- 目标摘要: 收紧 `Collection Trace`、`UnifiedInputBar` 与 `OutlineCard` 的前端呈现细节：为 plan/collect 头部状态徽标补单行稳定约束，移除 `collect completed` 行的重复完成徽标，调整底部输入区为更贴合页面的单层嵌入式表面，并让大纲卡片只展示章节编号与标题，不再暴露 section description。
- 修改文件:
  - `docs/Frontend_IA.md`
  - `apps/web/tests/component/timeline-panel.spec.tsx`
  - `apps/web/tests/component/outline-card.spec.tsx`
  - `apps/web/tests/component/unified-input-bar.spec.tsx`
  - `apps/web/features/research/components/timeline-panel.tsx`
  - `apps/web/features/research/components/outline-card.tsx`
  - `apps/web/features/research/components/unified-input-bar.tsx`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm exec vitest run tests/component/timeline-panel.spec.tsx tests/component/outline-card.spec.tsx tests/component/unified-input-bar.spec.tsx`；`cd apps/web && pnpm test:component -- --run tests/component/timeline-panel.spec.tsx tests/component/outline-card.spec.tsx tests/component/unified-input-bar.spec.tsx`；`cd apps/web && pnpm typecheck`
  - 未运行: 视觉截图回归或手动浏览器验收；本次任务包仅要求组件测试与类型检查
- 验收结论: accepted；目标 UI 约束均已通过文档、组件测试与类型检查收口，且未改动数据契约、交互语义或输入行为逻辑。
- blocker / 风险:
  - `pnpm test:component` 现有全量组件套件仍会打印若干既有 MSW 未匹配 artifact 请求告警，但命令整体通过，本次改动未新增该问题
  - 输入区的“嵌入式”视觉主要通过表面层级与类约束落地，最终观感仍建议在真实页面做一次人工确认
- 下一步建议:
  - 在真实 workspace 页面做一次桌面端长 collect target 与底部输入区的视觉 spot check
  - 如需进一步削减测试噪音，可单独下发任务处理组件测试中的 MSW 未匹配告警

## Production Collection Trace Playbook Update

- 日期时间: 2026-04-02 00:57:44 CST (+0800)
- 任务包编号: 未提供
- session 标识: codex-20260402-production-collection-trace-playbook
- 目标摘要: 将本次 production 上拉取 collection 阶段完整 LLM 历史的实战经验收敛进 `AGENTS.md` 的 `## Production 排查` 章节，重点减少对 `railway ssh` 交互方式、容器查询、导出回传、本地重定向与 schema 假设的反复试错，并补充 secret 脱敏与容器 `/tmp` 清理约束。
- 修改文件:
  - `AGENTS.md`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `git branch --show-current`（确认当前分支为 `codex/production-debug-playbook`）；`git diff -- AGENTS.md`（人工自检新增条目与既有 `Production 只读排查路径` / `Production 失败任务快速排查约定` 无冲突，且均为可执行命令/流程层面的增补）；`rg -n "payload_json|created_at|task_events|agent_runs|task_tool_calls|artifacts|research_tasks" services/api/app -g '*.py'`（交叉确认文档中引用的关键表/字段命名来自当前仓库实现，而非记忆假设）
  - 未运行: 无自动化测试；本任务包仅允许文档更新，验收依赖针对新增流程条目的人工一致性检查
- 验收结论: accepted；`AGENTS.md` 已补入 production 只读排查中的敏感变量脱敏、交互式 tty 要求、`/tmp` 临时脚本两段式导出、Postgres 交叉确认、schema 轻量确认、`railway ssh ... COMMAND` 叠加重定向/heredoc 的禁忌，以及容器 `/tmp` 清理约束，覆盖任务包要求的 7 条真实经验点且未改动其他章节。
- blocker / 风险:
  - 本次仅做文档收口，没有额外录入可直接复制的长脚本模板；后续若出现高频同类排查，可再单独下发任务包沉淀脚本化 playbook
  - `AGENTS.md` 现有条目较长，后续继续增补 production 规范时需避免把不同故障类型的经验继续堆叠在同一层级
- 下一步建议:
  - 下次做 production 活体导出时，直接按新增的“两段式导出 + Postgres 交叉确认 + `/tmp` 清理”流程执行
  - 若后续再次遇到 schema 误记或 one-shot `railway ssh` quoting 问题，应优先回填具体例子到单独排查文档，而不是继续在主规范里叠加泛化描述

## Sync CLAUDE Production Debugging Playbook

- 日期时间: 2026-04-02 09:02:30 CST (+0800)
- 任务包编号: 未提供
- session 标识: codex-20260402-sync-claude-production-playbook
- 目标摘要: 将 `AGENTS.md` 中新增的 `## Production 排查` 经验同步到 `CLAUDE.md`，补齐只读排查与失败任务快速排查中的脱敏、两段式导出、tty/one-shot 区别、schema 轻量确认、Postgres 交叉确认和 `/tmp` 清理要求，并记录本次执行。
- 修改文件:
  - `CLAUDE.md`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `git branch --show-current`（确认当前分支为 `codex/production-debug-playbook`）；`sed -n '303,390p' AGENTS.md` 与 `sed -n '296,380p' CLAUDE.md`（编辑前人工比对缺失项）；编辑后将再次执行段落 diff/人工核对，确认 `CLAUDE.md` 已覆盖 secret 脱敏、两段式导出、tty/one-shot 区别、schema 轻量确认、Postgres 交叉确认、`/tmp` 清理等要求
  - 未运行: 无自动化测试；本任务包仅要求文档同步与人工自检
- 验收结论: accepted；`CLAUDE.md` 的 `## Production 排查` 已对齐 `AGENTS.md` 当前同主题内容，且本次变更仅限目标章节与 `docs/Execution_Log.md`
- blocker / 风险:
  - 本次为文档同步，未额外引入脚本模板或示例命令封装；后续若继续迭代 production 排查流程，仍需同步维护两份文档避免再次漂移
- 下一步建议:
  - 后续凡是继续增补 `AGENTS.md` 的 production 排查经验，应在同一任务里同步检查 `CLAUDE.md`，避免知识分叉

## Prompt Update 04021059 Planner Collector Lock + Jina Web Fetch Params

- 日期时间: 2026-04-02 15:00:37 CST (+0800)
- 任务包编号: 未提供
- session 标识: codex-20260402-prompt-update-04021059
- 目标摘要: 吸收当前分支上用户已手工修改的 planner / collector prompt 与 tool description 文案，修正文档中仍然漂移的 Jina `web_fetch` GET-only 设计，并将 real-mode Jina Reader 请求改为按 PRD 0.6 固定携带 `retainLinks="none"` 与 `retainImages="none"`，同时补齐相关 unit tests 与执行记录。
- 修改文件:
  - `docs/Architecture.md`
  - `services/api/tests/unit/application/test_invocation_contracts.py`
  - `services/api/tests/unit/application/test_collection_prompts.py`
  - `services/api/tests/unit/infrastructure/test_jina_web_fetch.py`
  - `services/api/tests/unit/infrastructure/test_zhipu_adapters.py`
  - `services/api/app/infrastructure/research/jina.py`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit/application/test_invocation_contracts.py tests/unit/application/test_collection_prompts.py tests/unit/infrastructure/test_jina_web_fetch.py tests/unit/infrastructure/test_zhipu_adapters.py -k 'jina_web_fetch or semantic_lock or tool_schemas_match_current_architecture_contract'`（先红后绿；红测确认旧实现仍使用 GET contract，修复后 19 passed）
  - 已运行: `rg -n "GET https://r\\.jina\\.ai|10000|retainLinks|retainImages|POST https://r\\.jina\\.ai/" docs/Architecture.md services/api/app/infrastructure/research/jina.py services/api/tests/unit/infrastructure/test_jina_web_fetch.py services/api/tests/unit/infrastructure/test_zhipu_adapters.py`（确认设计与实现中无旧 GET/10000 漂移残留）
  - 未运行: 其余 `services/api` unit / contract / integration 全量测试；本任务包仅要求最小相关单测与文档一致性校验
- 验收结论: accepted；当前 prompt/tool 测试已锁定分支上的手工文案，`web_fetch` 对模型仍仅暴露 `url`，real Jina adapter 已固定发送 `retainLinks=none` 与 `retainImages=none`，目标单测全部通过。
- blocker / 风险:
  - 本次只覆盖了与 Jina `web_fetch` contract 直接相关的 unit tests，未重新跑更大范围的 provider / orchestrator 回归
  - `test_jina_web_fetch.py` / `test_zhipu_adapters.py` 目前通过精确 request body 字节串锁 contract，后续若仅调整 JSON 序列化细节也会触发测试更新
- 下一步建议:
  - 若后续继续调整 PRD 0.6 相关 prompt 文案，应同步优先更新 `docs/Architecture.md` 与 semantic lock tests，避免再次出现设计漂移
  - 在下一次相关后端改动中可顺带跑更大范围的 `services/api/tests/unit/infrastructure`，补一轮 provider 侧回归信心

## Workspace Visibility + Status + Input Polish

- 日期时间: 2026-04-02 16:39:10 CST (+0800)
- 任务包编号: 未提供
- session 标识: codex-20260402-workspace-visibility-status-input-polish
- 目标摘要: 按 `docs/DESIGN.md` 的 The Lab Terminal / Surgical Minimalism 风格，收紧工作台卡片的空内容显隐规则，增强顶栏当前阶段的状态辨识度并弱化 `taskId`，同时将底部输入区改为单层嵌入式 surface，并为 `textarea` 增加带上限的动态高度。
- 修改文件:
  - `docs/Frontend_IA.md`
  - `apps/web/features/research/components/research-workspace-shell.tsx`
  - `apps/web/features/research/components/session-status-bar.tsx`
  - `apps/web/features/research/components/unified-input-bar.tsx`
  - `apps/web/features/research/components/clarification-panels.tsx`
  - `apps/web/features/research/components/requirement-summary-card.tsx`
  - `apps/web/features/research/components/outline-card.tsx`
  - `apps/web/features/research/components/delivery-actions.tsx`
  - `apps/web/features/research/components/timeline-panel.tsx`
  - `apps/web/tests/component/research-workspace-shell.spec.tsx`
  - `apps/web/tests/component/session-status-bar.spec.tsx`
  - `apps/web/tests/component/unified-input-bar.spec.tsx`
  - `apps/web/tests/component/delivery-actions-visibility.spec.tsx`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm exec vitest run tests/component/research-workspace-shell.spec.tsx tests/component/session-status-bar.spec.tsx tests/component/unified-input-bar.spec.tsx`（目标红测转绿，27 passed）
  - 已运行: `cd apps/web && pnpm exec vitest run tests/component/research-workspace-shell.spec.tsx tests/component/session-status-bar.spec.tsx tests/component/unified-input-bar.spec.tsx tests/component/research-page-client.spec.tsx tests/component/clarification-detail-display.spec.tsx tests/component/delivery-actions-visibility.spec.tsx tests/component/outline-card.spec.tsx`（受影响组件回归，49 passed）
  - 未运行: `apps/web` 其余 component/integration/e2e 全量测试；本任务包按最小必要范围回归
- 验收结论: accepted；工作台主卡片已统一改为“内容 ready 后才出现”，顶栏改为更强的阶段主状态块且 `taskId` 降为弱 metadata，底部输入区改为单层嵌入式无边界 surface，并支持有上限的多行自动增高。
- blocker / 风险:
  - 本次只跑了与工作台显隐、顶栏、输入区直接相关的组件测试，未重跑更大范围的 integration / e2e
  - `ReportCanvas` 仍保留自身内部 skeleton 能力，但当前工作台 shell 已不会在空 markdown 时挂载该卡片；若未来其他入口直接使用该组件，需要继续遵守同样的显隐口径
- 下一步建议:
  - 若后续继续细调工作台视觉，优先在 `docs/Frontend_IA.md` 与组件测试里锁定显隐和层级语义，避免再次回到 phase-only 占位
  - 若要继续打磨输入区交互，可补一组针对真实 `scrollHeight` 与移动端视口的 component / e2e 测试

## Prompt Update 04021815 Prompt Contract Sync

- 日期时间: 2026-04-02 18:15:00 CST (+0800)
- 任务包编号: 未提供
- session 标识: codex-20260402-prompt-update-04021815
- 目标摘要: 对齐当前分支上用户已手工修改的 `planner` / `collector` / `writer` prompt 与 `python_interpreter` tool description 文案，只补最小必要文档与 unit semantic-lock 测试，不改动现有实现文案。
- 修改文件:
  - `docs/Execution_Log.md`
  - `services/api/tests/unit/application/test_invocation_contracts.py`
  - `services/api/tests/unit/application/test_collection_prompts.py`
  - `services/api/tests/unit/application/test_delivery_prompts.py`
- 测试/验证:
  - 已运行: `cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit/application/test_invocation_contracts.py tests/unit/application/test_collection_prompts.py tests/unit/application/test_delivery_prompts.py -q`（目标单测；验证 prompt/tool contract 当前文案）
  - 未运行: 其余 `services/api` unit / contract / integration 测试；本任务包仅涉及 prompt/tool wording 的最小同步
- 验收结论: accepted；目标 unit tests 已对齐当前实现中的 planner/collector 停止语义、writer 篇幅约束与 `python_interpreter` tool description，新文案未再出现旧断言漂移。
- blocker / 风险:
  - 本次未新增 adapter / orchestrator 级验证；若后续 provider 侧对 prompt 拼接方式再调整，仍需补更高层回归
  - 当前只同步了实现直接依赖的 unit semantic-lock 测试，其他二级文档若存在转述，后续仍可能单独漂移

## UI-2026-04-02 Status Bar Thin Ellipsis Polish

- 日期时间: 2026-04-02 21:51:01 CST (+0800)
- 任务包编号: UI-2026-04-02-status-bar-thin-ellipsis
- session 标识: codex-20260402-status-bar-thin-ellipsis
- 目标摘要: 按 `docs/DESIGN.md` 与 `docs/Frontend_IA.md` 将工作台顶栏收紧为更薄的单层状态条，移除原有大号中文阶段标题，把阶段展示收敛为 chip，并为所有进行中的阶段补充循环尾随省略号动效，同时把 `taskId` 重排为更弱的同排元信息且保持现有 disconnect / 新研究行为不变。
- 修改文件:
  - `docs/Frontend_IA.md`
  - `apps/web/features/research/components/session-status-bar.tsx`
  - `apps/web/tests/component/session-status-bar.spec.tsx`
  - `apps/web/tests/component/session-status-bar-terminal.spec.tsx`
  - `apps/web/tests/integration/research-transparency.spec.tsx`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm exec vitest run tests/component/session-status-bar.spec.tsx tests/component/session-status-bar-terminal.spec.tsx tests/integration/research-transparency.spec.tsx`
  - 已运行: `cd apps/web && pnpm typecheck`
  - 未运行: `pnpm lint`、其余 component / integration / e2e 测试；本任务包只要求状态栏相关聚焦验证与类型检查
- 验收结论: accepted；状态栏已无第二排大号中文阶段标题，进行中阶段显示 chip + 循环省略号，`taskId` 保持弱化且重新排布，聚焦测试与类型检查通过。
- blocker / 风险:
  - 省略号动效通过组件内联 `<style>` 注入，后续若状态栏被服务端化或抽到共享样式层，需要同步迁移动画定义
  - 本次未运行全量前端测试，仍存在未覆盖区域的回归风险
- 下一步建议:
  - 若后续继续打磨顶栏，可补一条视觉回归截图用例，锁定 chip 与 `taskId` 的最终层级
  - 在下一个前端 polish 任务中统一复查工作台其余 sticky surface 的高度节奏

## TP-20260402 Options Countdown Dock Tight

- 日期时间: 2026-04-02 22:07:39 CST (+0800)
- 任务包编号: TP-20260402
- session 标识: codex-20260402-countdown-dock-tight
- 目标摘要: 收紧 options clarification 模式下的顶部 sticky stack，使选单澄清倒计时作为独立 surface 继续停靠在全局 top stack 内，但与 `SessionStatusBar` 直接贴合无可见间隙，同时保持澄清详情卡片锚点行为不变，并将该布局约束补入前端 IA 文档与聚焦组件测试。
- 修改文件:
  - `docs/Frontend_IA.md`
  - `apps/web/tests/component/clarification-countdown.spec.tsx`
  - `apps/web/features/research/components/research-workspace-shell.tsx`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm test:component -- --run apps/web/tests/component/clarification-countdown.spec.tsx`（命令实际会跑完整 component suite；其中本次新增 countdown 结构断言按预期先失败，同时暴露仓库内既有无关失败：`tests/component/copy-cleanup.spec.tsx`、`tests/component/timeline-panel.spec.tsx`）
  - 已运行: `cd apps/web && pnpm exec vitest run tests/component/clarification-countdown.spec.tsx tests/component/research-page-client.spec.tsx`
  - 未运行: 完整前端 test matrix；本任务包只要求聚焦顶部堆叠布局修复与相关锚点回归验证
- 验收结论: accepted；文档、聚焦测试与实现均已对齐，倒计时保留在全局 sticky top stack 中并直接 dock 在状态栏下方，聚焦测试通过。
- blocker / 风险:
  - `pnpm test:component` 当前存在与本任务无关的既有失败，尚未在本次任务范围内处理
  - 终态 `TerminalBanner` 的垂直间距现在由其外层 `pt-3` 单独承担；若后续 top stack 再加入新 surface，需要继续显式管理相邻间距
- 下一步建议:
  - 如需恢复 component suite 全绿，可单独下发任务修复 `copy-cleanup` 与 `timeline-panel` 的空态测试漂移
  - 若后续继续收紧顶部堆叠规则，可考虑为 top stack 相邻 surface 增加更明确的语义化 data attributes 以便测试

## TP-20260402 Frontend Branding Polish

- 日期时间: 2026-04-02 23:08:50 CST (+0800)
- 任务包编号: TP-20260402
- session 标识: codex-20260402-branding-polish
- 目标摘要: 收紧首页与工作台顶部品牌表达，将旧的 `AI 研究工作台` hero 替换为大号 `Mimir` wordmark 与 `Draw from depth.` slogan，同时将 `SessionStatusBar` 中的任务标识改为仅显示原始 `taskId` 值，并在 Next App Router 标准 icon 路径下补入给定黑白 SVG favicon；本次实现严格停留在品牌文案、弱化 task id 呈现与图标资源接入，不涉及任务流转、工作台排序或其他壳层改造。
- 修改文件:
  - `docs/Frontend_IA.md`
  - `apps/web/tests/component/research-page-client.spec.tsx`
  - `apps/web/tests/component/session-status-bar.spec.tsx`
  - `apps/web/tests/integration/report-delivery-flow.spec.tsx`
  - `apps/web/tests/e2e/specs/harness.spec.ts`
  - `apps/web/tests/unit/app-icon.spec.ts`
  - `apps/web/features/research/components/research-page-client.tsx`
  - `apps/web/features/research/components/session-status-bar.tsx`
  - `apps/web/app/icon.svg`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm exec vitest run tests/component/research-page-client.spec.tsx tests/component/session-status-bar.spec.tsx tests/integration/report-delivery-flow.spec.tsx tests/unit/app-icon.spec.ts`
  - 已运行: `cd apps/web && pnpm typecheck`
  - 未运行: `pnpm test:e2e`；本任务包验收只要求聚焦测试与类型检查，e2e 规格已同步更新但未在本回合执行
- 验收结论: accepted；文档、聚焦测试与实现已对齐，idle / reset 后 hero 均切换为 `Mimir` + `Draw from depth.`，状态栏去除 `taskId:` 前缀，且 favicon 资源已落在 `app/icon.svg`。
- blocker / 风险:
  - 聚焦 integration test 仍打印既有 heartbeat MSW 未命中告警，但不影响本次断言通过
  - 本次未执行 e2e，浏览器层对 favicon 实际暴露路径的最终验证留待后续全量回归
- 下一步建议:
  - 若需要收紧品牌一致性，可在后续任务中补充 favicon/head 层的浏览器级断言
  - 若要消除测试噪音，可单独下发任务为 `heartbeat` 请求补 MSW handler

## TP-2026-04-03 Example Prompts Polish

- 日期时间: 2026-04-03 00:23:38 CST (+0800)
- 任务包编号: TP-2026-04-03-example-prompts
- session 标识: codex-20260403-example-prompts-polish
- 目标摘要: 更新 idle 态示例研究主题前两条文案，保持第三条不变，并按 `DESIGN.md` 将 ExamplePrompts 的 hover / focus 收紧为 recessed / docked 的低幅 tonal shift，去除生硬的 glow、shadow 与漂浮感。
- 修改文件:
  - `docs/Frontend_IA.md`
  - `apps/web/tests/component/example-prompts.spec.tsx`
  - `apps/web/features/research/components/example-prompts.tsx`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm exec vitest run tests/component/example-prompts.spec.tsx`；`cd apps/web && pnpm typecheck`
  - 未运行: 全量 `pnpm test:component`、`pnpm lint` 与其余前端测试未重跑；本任务包验收仅要求 ExamplePrompts 组件测试与类型检查
- 验收结论: accepted；前两条示例文案保持目标值，第三条保持现状，hover / focus contract 已明确限制为 `surface-container-lowest -> surface-container-low` 的低幅 tonal lift，并排除 glow、shadow、整块亮到 `surface` 与 `translateY` 漂浮感。
- blocker / 风险:
  - 最终视觉判断仍主要依赖 class contract 与测试，未在真实浏览器中补充人工目测截图
  - `docs/Execution_Log.md` 现有同主题历史条目较多，后续若继续打磨同一区域，建议由 master-agent 合并为更小、更清晰的任务包
- 下一步建议:
  - 若需进一步验证观感，可在独立任务中做一次浏览器级 hover / focus 人工验收
  - 若要统一 idle 区微交互语义，单独下发任务校准相邻组件，不在本组件内顺手扩散

## TP-2026-04-03 Prompt Date Format UTC+8

- 日期时间: 2026-04-03 16:00 CST (+0800)
- 任务包编号: TP-2026-04-03-prompt-date-format-utc8
- session 标识: fix/prompt-date-format-utc8
- 目标摘要: 将所有 LLM prompt 中的时间变量注入从完整 ISO 8601 格式统一为 UTC+8 时区的 YYYY-MM-DD 日期字符串
- 修改文件:
  - `services/api/app/core/date_utils.py` — 新增辅助函数 `format_date_cn(dt) -> str`
  - `services/api/app/application/prompts/clarification.py` — 2 处 `.isoformat()` 替换为 `format_date_cn()`
  - `services/api/app/application/prompts/requirement.py` — 1 处替换
  - `services/api/app/application/prompts/collection.py` — 3 处替换
  - `services/api/app/application/prompts/delivery.py` — 3 处替换（含参数重命名 `now_iso` -> `now_date`）
  - `services/api/app/application/prompts/feedback.py` — 1 处替换
  - `services/api/tests/unit/core/test_date_utils.py` — 新增辅助函数单元测试（6 个）
  - `services/api/tests/unit/application/test_prompts.py` — 更新 3 处时间断言
  - `services/api/tests/unit/application/test_collection_prompts.py` — 更新 1 处时间断言
  - `services/api/tests/unit/application/test_delivery_prompts.py` — 更新 2 处时间断言
  - `services/api/tests/unit/application/test_feedback_prompts.py` — 更新 1 处时间断言
  - `docs/execution_log.md` — 本条目
- 测试/验证:
  - `uv run --group dev pytest tests/unit` — 223 passed
- 验收结论: accepted；所有 prompt 文件中不再有 `.isoformat()` 用于时间注入，时间格式统一为 YYYY-MM-DD，时区固定 UTC+8
- blocker / 风险: 无
- 下一步建议: 无

## TP-2026-04-03 Frontend TopBar Alignment & Submit Button Style

- 日期时间: 2026-04-03 16:06 CST (+0800)
- 任务包编号: TP-2026-04-03-frontend-style-fix
- session 标识: fix/prompt-date-format-utc8
- 目标摘要: 修复顶栏元素多余内边距导致与内容区不对齐的问题；优化提交按钮为紧凑终端风格并实现设计宪法要求的 hover 反色效果
- 修改文件:
  - `apps/web/features/research/components/session-status-bar.tsx` — 去掉根 `<section>` 的 `px-4`，消除与内容区的 16px 内缩偏差
  - `apps/web/features/research/components/unified-input-bar.tsx` — 按钮样式：去掉 `h-12 w-[120px]`，改用 `px-6 py-2.5` 紧凑内边距；字体改为 `font-ui text-xs font-medium uppercase tracking-[0.08em]`；hover 从 `hover:bg-primary/90` 改为 `hover:bg-surface hover:text-primary`（反色）；过渡改为 `transition-colors`
  - `apps/web/tests/component/unified-input-bar.spec.tsx` — 更新 3 处按钮 class 断言，去掉对已移除的 `h-12` / `w-[120px]` 的检查
  - `docs/Execution_Log.md` — 本条目
- 测试/验证:
  - `pnpm typecheck` — passed
  - `pnpm test:unit` — 63 passed
  - `pnpm test:component` — 124 passed, 3 failed (pre-existing failures in copy-cleanup.spec.tsx / timeline-panel.spec.tsx，与本次变更无关)
- 验收结论: accepted；顶栏与内容区对齐，按钮符合设计宪法终端风格及 hover 反色规则
- blocker / 风险: 无
- 下一步建议: 无

## Active Task Package 1 Idle Clarification Terminal Polish

- 日期时间: 2026-04-03 18:06:14 CST (+0800)
- 任务包编号: Active Task Package 1
- session 标识: codex/home-shell-clarification-terminal-polish
- 目标摘要: 重做 idle 首页主舞台与输入提交流程，将示例主题和输入区上移到视觉中心，改为 `options` 默认澄清模式，删除旧的“研究配置”与“示例研究主题”文案，改成吸附在输入框下方的轻量配置组件，并将澄清详情标题统一为“需求澄清”，同时保持 active workspace 底部 fixed 输入托盘与现有任务流转语义。
- 修改文件:
  - `docs/Frontend_IA.md`
  - `apps/web/features/research/components/research-page-client.tsx`
  - `apps/web/features/research/components/example-prompts.tsx`
  - `apps/web/features/research/components/research-config-panel.tsx`
  - `apps/web/features/research/components/unified-input-bar.tsx`
  - `apps/web/features/research/components/clarification-panels.tsx`
  - `apps/web/features/research/components/research-workspace-shell.tsx`
  - `apps/web/features/research/store/research-session-store.types.ts`
  - `apps/web/tests/component/research-page-client.spec.tsx`
  - `apps/web/tests/component/research-config-panel.spec.tsx`
  - `apps/web/tests/component/unified-input-bar.spec.tsx`
  - `apps/web/tests/component/clarification-detail-display.spec.tsx`
  - `apps/web/tests/integration/create-task-flow.spec.tsx`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm exec vitest run tests/component/research-page-client.spec.tsx tests/component/research-config-panel.spec.tsx tests/component/unified-input-bar.spec.tsx tests/component/clarification-detail-display.spec.tsx tests/integration/create-task-flow.spec.tsx`
  - 已运行: `cd apps/web && pnpm typecheck`
  - 未运行: 其余 `apps/web` 全量测试；本任务包验收只要求指定 component/integration 集合与 typecheck
- 验收结论: accepted；idle 态输入区已回到主舞台中央、active workspace 恢复底部 fixed 托盘、默认澄清模式切为 `options`、配置文案与 hover 提示落地、澄清标题与旧引导文案替换完成。
- blocker / 风险:
  - `apps/web/features/research/components/research-workspace-shell.tsx` 为直接相关补充变更，不在原始清单内，但为了让任务创建后立即渲染“需求澄清”卡片占位而最小化引入
  - 当前仅验证了任务包要求的 targeted tests；若后续有依赖旧 copy 的快照或 e2e，需要在下一轮全量回归中确认
- 下一步建议:
  - 如需继续 polish，可在独立任务包中补 idle 主舞台的视觉微调与移动端 spacing 回归
  - 合并前执行一次 `apps/web` 更大范围组件回归，确认没有遗漏旧文案依赖

## Active Task Package 1 ResearchConfigPanel Hint Scope Rework

- 日期时间: 2026-04-03 18:06:14 CST (+0800)
- 任务包编号: Active Task Package 1
- session 标识: codex/home-shell-clarification-terminal-polish
- 目标摘要: 收紧 `ResearchConfigPanel` 的 hover / focus 提示范围，改为只显示当前悬浮或聚焦选项对应的一条说明，避免同时展开两种模式说明，保持 idle 配置组件的低存在感。
- 修改文件:
  - `docs/Frontend_IA.md`
  - `apps/web/features/research/components/research-config-panel.tsx`
  - `apps/web/tests/component/research-config-panel.spec.tsx`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm exec vitest run tests/component/research-config-panel.spec.tsx`
  - 未运行: 其余前端测试；本次返工仅覆盖单组件提示行为
- 验收结论: accepted；提示区已按当前 hover / focus 目标单条切换，不再同时显示两种模式说明。
- blocker / 风险:
  - 无当前 blocker
- 下一步建议:
  - 无

## Active Task Package 2 Terminated Banner Copy + Risk Control Reason Alignment

- 日期时间: 2026-04-03 18:33:40 CST (+0800)
- 任务包编号: Active Task Package 2
- session 标识: codex/home-shell-clarification-terminal-polish
- 目标摘要: 收紧 `task.terminated` 终态提示，统一 banner 主标题为“任务已终止”，将次要文案改为按后端 `termination reason` 的稳定产品化映射并补缺省回退，同时修复 collection 风控终止事件 reason 与前端/contracts 的契约漂移，统一为 `risk_control_limit`。
- 修改文件:
  - `docs/Frontend_IA.md`
  - `apps/web/features/research/components/terminal-banner.tsx`
  - `apps/web/tests/component/terminal-banner.spec.tsx`
  - `apps/web/tests/component/terminal-banner-detail.spec.tsx`
  - `apps/web/tests/integration/task-stream-lifecycle.spec.tsx`
  - `services/api/app/application/services/collection.py`
  - `services/api/tests/integration/collection/test_collection_engine.py`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm exec vitest run tests/component/terminal-banner.spec.tsx tests/component/terminal-banner-detail.spec.tsx tests/integration/task-stream-lifecycle.spec.tsx`
  - 已运行: `cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/integration/collection/test_collection_engine.py -k risk_control -q`
  - 未运行: 其余前后端测试；本任务包验收仅要求上述 targeted verification
- 验收结论: accepted；`terminated` banner 已改为固定主标题并按 reason 输出稳定 detail，reason 缺失时会回退到通用说明，collection 风控终止事件 payload 已统一为 `risk_control_limit`。
- blocker / 风险:
  - `packages/contracts/src/index.ts` 本轮未修改，因为仓库内前端/contracts 已经是 `risk_control_limit`；漂移点仅在后端 collection 终止 reason
  - 当前只验证了任务包要求的 targeted tests；若其他前端用例仍对旧终止 copy 有隐式依赖，需要在后续更大范围回归中确认
- 下一步建议:
  - 如需继续 polish，可在独立任务包中检查其他终态相关 UI 是否仍残留“旧任务操作已禁用”旧文案
  - 合并前执行更大范围前后端回归，确认没有遗漏旧 reason 文案依赖

## Active Task Package Research Config Panel Refine

- 日期时间: 2026-04-03 18:58:06 CST (+0800)
- 任务包编号: Active Task Package
- session 标识: codex/research-config-panel-refine
- 目标摘要: 将需求沟通方式文案统一为 `问答式` / `选项式`，把 `ResearchConfigPanel` 收紧为低存在感、轻量、矩形 terminal selector，并修复 hover / focus 提示在指针移向提示区时的闪烁消失问题。
- 修改文件:
  - `docs/Frontend_IA.md`
  - `apps/web/features/research/components/research-config-panel.tsx`
  - `apps/web/tests/component/research-config-panel.spec.tsx`
  - `apps/web/tests/component/research-page-client.spec.tsx`
  - `apps/web/tests/integration/create-task-flow.spec.tsx`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm exec vitest run tests/component/research-config-panel.spec.tsx tests/component/research-page-client.spec.tsx tests/integration/create-task-flow.spec.tsx`
  - 已运行: `cd apps/web && pnpm typecheck`
  - 未运行: 其余 `apps/web` 测试；本任务包验收仅要求上述 targeted tests 与 typecheck
- 验收结论: accepted；`问答式` / `选项式` 文案已落地，默认选中仍为 `options`，selector 已收紧为低存在感矩形终端风格，tooltip 在 hover / focus 期间只显示当前项提示且指针移向提示区时保持稳定可见。
- blocker / 风险:
  - tooltip 预留了固定底部空间以保证 attached panel 稳定显示；若后续文案继续增长，需要单独回归更窄视口下的垂直节奏
- 下一步建议:
  - 如需继续 polish，可在独立任务包中补更大范围 idle 页面对齐检查，确认该 selector 与输入区、示例主题在多断点下的整体密度一致

## UI-20260404 Idle Research Config Hint + Hero Slogan Polish

- 日期时间: 2026-04-04 12:18:25 CST (+0800)
- 任务包编号: UI-20260404-idle-hover-hero
- session 标识: codex-20260404-idle-hover-hero
- 目标摘要: 收口 Idle 首页 `ResearchConfigPanel` 的模式提示交互与 hero slogan 视觉层级；先在 `Frontend_IA` 固化 attached hint 与弱化 slogan 契约，再以组件测试锁住 hover 稳定性、弱化样式和 terminal cursor 表现，最后仅在 web 侧实现去除底部硬编码留白的 docked hint 与更紧凑、更低对比的 slogan。
- 修改文件:
  - `docs/Frontend_IA.md`
  - `apps/web/tests/component/research-config-panel.spec.tsx`
  - `apps/web/tests/component/research-page-client.spec.tsx`
  - `apps/web/features/research/components/research-config-panel.tsx`
  - `apps/web/features/research/components/research-page-client.tsx`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm exec vitest run tests/component/research-config-panel.spec.tsx tests/component/research-page-client.spec.tsx`；`cd apps/web && pnpm typecheck`
  - 未运行: 浏览器级人工视觉回归；本任务包验收命令仅要求组件测试与 `typecheck`
- 验收结论: accepted；组件测试已锁住 hint 附着位置与 hover 保持逻辑，Idle hero 仍显示 `Mimir` 与 slogan，且 slogan 已降为元信息层并带 terminal 风格下划线后缀。
- blocker / 风险:
  - 未做截图或真实浏览器像素级比对，跨断点的最终观感仍依赖后续人工 spot check
  - slogan 的 terminal 感通过 pseudo-element cursor 表达，若后续文案改动需同步关注其可读性与间距
- 下一步建议:
  - 在桌面与移动端各做一次人工 hover / focus 巡检，确认 hint 与输入区、示例区之间的垂直节奏
  - 若后续继续微调 Idle hero，可在不改文案主体的前提下统一 wordmark 与 slogan 的 tracking token

## UI-20260405 Idle Hint Overlay + Real Underscore Fix

- 日期时间: 2026-04-05 15:50:10 CST (+0800)
- 任务包编号: UI-20260405-idle-overlay-underscore
- session 标识: codex/fix-web-overlay-slogan
- 目标摘要: 修复生产已复现的两个 Idle 页面问题：将 `ResearchConfigPanel` 的模式提示从正常文档流节点改为 selector region 内的 attached absolute overlay，消除 hint 显示时把 idle 主舞台整体上顶的位移；同时把 hero slogan 从生产未生效的 pseudo-element 方案改为真实 DOM 文本 + underscore 节点，确保弱化颜色与 terminal 结尾在实际渲染中稳定可见。
- 修改文件:
  - `docs/DESIGN.md`
  - `docs/Frontend_IA.md`
  - `apps/web/tests/component/research-config-panel.spec.tsx`
  - `apps/web/tests/component/research-page-client.spec.tsx`
  - `apps/web/features/research/components/research-config-panel.tsx`
  - `apps/web/features/research/components/research-page-client.tsx`
  - `apps/web/tests/integration/report-delivery-flow.spec.tsx`
  - `apps/web/tests/e2e/specs/harness.spec.ts`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm exec vitest run tests/component/research-config-panel.spec.tsx tests/component/research-page-client.spec.tsx`
  - 已运行: `cd apps/web && pnpm typecheck`
  - 已运行: `cd apps/web && pnpm exec vitest run tests/integration/report-delivery-flow.spec.tsx`
  - 未运行: `apps/web` 其余测试与浏览器级人工回归；本返工包验收要求仅包含两个组件 spec 与 `typecheck`
- 验收结论: accepted；`research-config-selector-region` 已成为 `relative` 锚点，hint `note` 已改为 `absolute` attached panel，不再参与正常文档流；hero slogan 已改为弱化文本加真实 underscore 节点，去除了生产未生效的 pseudo-element 依赖。
- blocker / 风险:
  - 未在真实浏览器中重新测量 hover 前后容器几何值；当前“不会撑高页面”的证明来自代码结构与组件测试约束，而非新的生产像素测量
  - `tests/integration/report-delivery-flow.spec.tsx` 运行时仍有既存的 MSW heartbeat 未匹配警告，但测试本身通过，本次未扩范围处理该警告
- 下一步建议:
  - 在生产页或预发页做一次桌面 hover / focus spot check，确认 hint overlay 不再推动首页主舞台
  - 如需扩大回归，再补跑 `apps/web` 的 e2e/harness 用例，确认 hero slogan 新结构在真实浏览器可见

## UI-20260405 Hero Tone + Hint Gap Rework

- 日期时间: 2026-04-05 16:11:48 CST (+0800)
- 任务包编号: UI-20260405-hero-tone-hint-gap
- session 标识: codex/hero-hint-gap-tune
- 目标摘要: 对 Idle 页做一次小范围返工：将 hero slogan 主体的弱化样式改为更稳妥的显式文本色阶加独立透明度类，避免生产环境出现“类名存在但颜色未生效”时 `Draw from depth` 仍过亮；同时保持 `ResearchConfigPanel` 的 hint 为 selector region 内的 absolute attached overlay，并通过 overlay 自身偏移补出克制的小间距，消除 selector 下沿贴边与覆盖感。
- 修改文件:
  - `docs/Frontend_IA.md`
  - `apps/web/tests/component/research-page-client.spec.tsx`
  - `apps/web/tests/component/research-config-panel.spec.tsx`
  - `apps/web/features/research/components/research-page-client.tsx`
  - `apps/web/features/research/components/research-config-panel.tsx`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm exec vitest run tests/component/research-config-panel.spec.tsx tests/component/research-page-client.spec.tsx`
  - 已运行: `cd apps/web && pnpm typecheck`
  - 未运行: 浏览器级人工视觉回归；本返工包验收命令仅要求目标组件测试与 `typecheck`
- 验收结论: accepted；hero slogan 仍保留独立 underscore 节点，且 `Draw from depth` 主体已通过稳定的 `text-secondary` + `opacity` 组合弱化；config hint 仍为 `absolute` overlay，不参与文档流，并与 selector 下沿保留明确小间距。
- blocker / 风险:
  - 本次未做生产页人工像素比对，最终亮度层级与 gap 观感仍建议在真实浏览器做一次桌面 spot check
  - gap 当前固定为小间距 utility，若后续 selector 高度或字号继续调整，需要一并复核 docked overlay 的节奏
- 下一步建议:
  - 在预发或生产页人工检查一次 hero 与 selector hint 的实际视觉层级
  - 若后续继续调整 idle hero，仅在不改变文案与 underscore 结构的前提下微调 tracking 或 opacity

## UI-20260405 Collection Trace Reanchor Fix

- 日期时间: 2026-04-05 16:35:58 CST (+0800)
- 任务包编号: UI-20260405-collection-trace-reanchor
- session 标识: codex/collection-trace-anchor-fix
- 目标摘要: 修复检索阶段工作台页面级自动锚点错误停留在 `Requirement Summary` 的问题。文档层明确 `planning_collection`、`collecting`、`summarizing_collection`、`merging_sources` 阶段应以 `Collection Trace` 作为页面级主锚点，并在 trace 内容更新时重新定位到 trace 自身；前端以最小改动将 `collectionTrace` 的 anchor signal 从只看 `nodes.length` 扩展为反映 trace 内容签名的信号，从而覆盖“节点数不变但内容更新”的流式场景。
- 修改文件:
  - `docs/Frontend_IA.md`
  - `apps/web/tests/component/research-page-client.spec.tsx`
  - `apps/web/features/research/components/research-workspace-shell.tsx`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm exec vitest run tests/component/research-page-client.spec.tsx`
  - 已运行: `cd apps/web && pnpm typecheck`
  - 未运行: 其余 `apps/web` 测试与真实浏览器手动滚动回归；本返工包验收只要求目标 spec 与 `typecheck`
- 验收结论: accepted；collection 相关阶段中，`Collection Trace` 内容更新即使 `nodes.length` 不变，也会重新触发页面级锚点并停靠在 `Collection Trace`，不再停留在更早的 `Requirement Summary`。
- blocker / 风险:
  - 当前实现使用 `collectionTrace.nodes` 的序列化内容签名驱动重锚；若未来 trace 规模显著增大，可能需要单独下发性能优化包，把内容签名收敛为更轻量的版本号或稳定摘要
  - 本次未做真实浏览器人工滚动 spot check，最终体验验证仍依赖组件测试与类型检查
- 下一步建议:
  - 在桌面工作台做一次人工 collection phase spot check，确认真实滚动体验与预期一致
  - 若后续发现 trace 体量继续增长，再评估把 anchor signal 切换为更轻量的 collection-specific version 信号

## UI-20260405 Hero Wordmark + OutlineCard Light Redesign

- 日期时间: 2026-04-05 17:21:22 CST (+0800)
- 任务包编号: UI-20260405-hero-outline-redesign
- session 标识: codex/hero-outline-redesign
- 目标摘要: 按小范围前端重设计任务包收紧 Idle hero 与 `OutlineCard` 的视觉契约。文档层将首页主 wordmark 固定为纯白 uppercase `MIMIR`，并明确 `OutlineCard` 必须转为更轻、更干净、以 tonal layering 为主的阅读引导卡片；测试层先锁定 `MIMIR` + slogan、章节顺序、description 不暴露，以及 neutral layered surface 合同；实现层仅调整 `research-page-client` 与 `outline-card`，去掉原先偏重的 amber 主导表达，同时保持现有数据与状态语义不变。
- 修改文件:
  - `docs/Frontend_IA.md`
  - `apps/web/tests/component/research-page-client.spec.tsx`
  - `apps/web/tests/component/outline-card.spec.tsx`
  - `apps/web/features/research/components/research-page-client.tsx`
  - `apps/web/features/research/components/outline-card.tsx`
  - `apps/web/tests/integration/report-delivery-flow.spec.tsx`
  - `apps/web/tests/e2e/specs/harness.spec.ts`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm exec vitest run tests/component/research-page-client.spec.tsx tests/component/outline-card.spec.tsx`
  - 已运行: `cd apps/web && pnpm typecheck`
  - 未运行: 更广的 `apps/web` integration / e2e / 浏览器人工视觉回归；本任务包验收只要求目标组件 spec 与 `typecheck`
- 验收结论: accepted；Idle hero 现为纯白 uppercase `MIMIR` 且 slogan 仍保留真实 DOM underscore，`OutlineCard` 维持 ordered section titles 与隐藏 descriptions 的行为，同时整体表面语言已切换为更轻的 neutral layered stack，不再由 amber 大面积主导。
- blocker / 风险:
  - 本次未做真实浏览器的人工视觉 spot check，最终观感仍建议在桌面与移动端各确认一次
  - 已同步更新直接引用旧 hero 文案的 integration / e2e 断言，但未在本任务内重新跑这些套件
- 下一步建议:
  - 在真实页面确认 `MIMIR` 的 tracking、白度与 slogan 层级是否满足预期
  - 若后续继续微调工作台卡片，保持 amber 仅作 accent，不回退到大面积暖色填充

## UI-20260405 Example Prompt Cards Visual Enhancement

- 日期时间: 2026-04-05 17:41:00 CST (+0800)
- 任务包编号: UI-20260405-example-prompt-cards-visual
- session 标识: codex/example-prompt-cards-visual
- 目标摘要: 优化首页示例研究问题卡片的视觉表现，使其从黑色背景中清晰可辨。将卡片默认背景从 `bg-surface-container-lowest` (#000000) 提升至 `bg-surface-container` (#1a1919)，hover/focus 背景提升至 `bg-surface-container-high` (#2c2c2c)，移除所有 outline 类以遵循设计宪法 No-Line Rule，并为 focus-visible 状态添加 amber shadow 作为无障碍指示器。
- 修改文件:
  - `apps/web/features/research/components/example-prompts.tsx`
  - `apps/web/tests/component/example-prompts.spec.tsx`
  - `docs/execution_log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm typecheck` -- 通过
  - 已运行: `cd apps/web && npx vitest run tests/component/example-prompts.spec.tsx` -- 3/3 通过
- 验收结论: accepted；卡片默认状态背景色高于 base layer，无 border/outline 线条分隔，hover 保持左侧 amber 竖线 + 背景提亮，focus-visible 使用 amber shadow ring 作为无障碍指示。
- blocker / 风险:
  - 纯视觉修改，建议在真实浏览器确认最终观感
- 下一步建议:
  - 在桌面与移动端浏览器确认卡片从背景中的视觉区分度

## UI-20260407 Workspace Card Anchor Strategy Fix

- 日期时间: 2026-04-07 10:41:17 CST (+0800)
- 任务包编号: UI-20260407-workspace-card-anchor-strategy-fix
- session 标识: codex/workspace-anchor-strategy-fix
- 目标摘要: 修复工作台共享 card anchor 行为，使页面级自动滚动不再依赖反向 phase 优先级，而是只在“本轮新出现或内容变化的卡片”里按既定卡片顺序选择最早目标；覆盖 `Collection Trace` 首次出现、`Outline` 首次 ready、同轮多卡同时变更以及 later changed card 仍可成为锚点的回归场景。
- 修改文件:
  - `docs/Frontend_IA.md`
  - `apps/web/tests/component/research-page-client.spec.tsx`
  - `apps/web/features/research/components/research-workspace-shell.tsx`
  - `apps/web/features/research/hooks/use-workspace-card-anchor.ts`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm exec vitest run tests/component/research-page-client.spec.tsx` -- 18/18 通过
  - 已运行: `cd apps/web && pnpm typecheck` -- 通过
- 验收结论: accepted；共享 anchor 现在按工作台既有卡片顺序从 changed cards 中选取目标，`Collection Trace` 首次出现会正确锚定到自身，`Requirement Summary` 与 `Collection Trace` 同轮变化时会优先锚到更靠前的需求摘要，而未变化的早卡不会抢走 later changed card 的锚点。
- blocker / 风险:
  - 当前回归集中在 component 层；尚未在真实浏览器中手动确认长页面、实际 sticky top stack 高度和 smooth scroll 体感
  - `report` 卡片的页面级 anchor 仍只覆盖首次 ready，不会因后续正文 delta 持续触发页面滚动；这与当前文档“正文刷新只滚内部容器”的约束保持一致，但若后续产品预期变化需单独补文档和测试
- 下一步建议:
  - 在真实工作台流程中确认从需求摘要进入 `Collection Trace`、再进入 `Outline` 的滚动体验是否符合预期

## UI-20260407 Workspace Card Anchor Strategy Fix Follow-up

- 日期时间: 2026-04-07 10:46:40 CST (+0800)
- 任务包编号: UI-20260407-workspace-card-anchor-strategy-fix-followup
- session 标识: codex/workspace-anchor-strategy-fix
- 目标摘要: 将共享 card anchor 规则从 `Collection Trace` / `Outline` 的局部修复收紧为适用于全部内容卡片的统一策略。文档层明确“任一卡片出现或内容更新都可成为候选锚点，若同轮多卡变化则按工作台顺序选最早者”；实现层把 `DeliveryActions` 纳入 shared anchor order，并让 `Report Canvas` 在后续正文内容更新时也能触发页面级锚定；测试层补齐 report content update 与 delivery-only appearance 两个回归。
- 修改文件:
  - `docs/Frontend_IA.md`
  - `apps/web/tests/component/research-page-client.spec.tsx`
  - `apps/web/features/research/components/research-workspace-shell.tsx`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm exec vitest run tests/component/research-page-client.spec.tsx` -- 19/19 通过
  - 已运行: `cd apps/web && pnpm typecheck` -- 通过
- 验收结论: accepted；共享 anchor 现在对所有内容卡片统一按 changed-cards 规则工作，`Report Canvas` 的正文更新可在未改变的早卡存在时重新成为页面锚点，`DeliveryActions` 也能在单独出现时成为该轮锚点；若 report 与 delivery 同轮变化，仍按既定顺序优先锚到 report。
- blocker / 风险:
  - 仍未做真实浏览器下的人工滚动体验确认，尤其是 delivered 阶段 report / delivery 切换时的页面观感
- 下一步建议:
  - 在真实任务流里验证 report 流式增量、delivered 切换和 delivery 单独出现三种场景的滚动体感

## UI-20260407 Execution Log Compression + Hero Signature + OutlineCard Simplify

- 日期时间: 2026-04-07 11:18:55 CST (+0800)
- 任务包编号: UI-20260407-log-hero-outline
- session 标识: codex/log-outline-site-link
- 目标摘要: 按 docs-first -> tests-first -> implementation 收紧一组前端/文档返工：将 `docs/Execution_Log.md` 从全量原始历史压缩为“保留说明头部 + 历史摘要 + 最近 50 条原始记录”的可维护结构；在 `Frontend_IA` 固化 hero 附近的低存在感 `robiniflore.com` 外部署名链接与更紧凑的 `OutlineCard` 契约；随后以 targeted component tests 锁定 hero 链接、章节顺序、description 隐藏与旧重型 outline sublabel/summary block 的移除，最后只调整 `research-page-client` 与 `outline-card` 的表现层实现。
- 修改文件:
  - `docs/Execution_Log.md`
  - `docs/Frontend_IA.md`
  - `apps/web/features/research/components/research-page-client.tsx`
  - `apps/web/features/research/components/outline-card.tsx`
  - `apps/web/tests/component/research-page-client.spec.tsx`
  - `apps/web/tests/component/outline-card.spec.tsx`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm exec vitest run tests/component/research-page-client.spec.tsx tests/component/outline-card.spec.tsx`
  - 已运行: `cd apps/web && pnpm typecheck`
  - 未运行: 更大范围 `apps/web` component / integration / e2e 与真实浏览器视觉回归；本任务包验收仅要求上述 targeted tests 与 `typecheck`
- 验收结论: accepted；`Execution_Log.md` 已显著压缩并在当前 session 追加后保留最近 50 条原始记录，Idle hero 现包含低存在感外部署名链接，`OutlineCard` 收紧为更轻的目录板式结构，且测试已锁定章节顺序与旧重型结构不再出现。
- blocker / 风险:
  - `robiniflore.com` 链接的最终弱化程度尚未做真实浏览器人工 spot check；不同屏幕亮度下可能还需要极小的 opacity / tracking 微调
  - `OutlineCard` 的视觉收紧目前通过 component 测试与类型检查保证结构正确，尚未做桌面/移动端像素级人工验收
- 下一步建议:
  - 在真实浏览器桌面与移动端各检查一次 hero 元信息层级，确认外链不会被误读为主 CTA
  - 若后续继续微调 `OutlineCard`，保持“目录板”方向，不再引回独立 summary slab、重复 sublabel 或更重的 amber stack

## FE-HERO-METADATA-ROW-POLISH Hero Alignment + Signature Row

- 日期时间: 2026-04-07 11:40:27 CST (+0800)
- 任务包编号: FE-HERO-METADATA-ROW-POLISH
- session 标识: codex/hero-alignment-signature-row
- 目标摘要: 按 docs-first -> tests-first -> implementation 收紧 Idle hero 的元信息层布局。文档先明确 hero metadata row 必须把 slogan 与 `robiniflore.com` 放在同一行、左侧与 `MIMIR` 视觉左缘收齐、右侧签名保持弱化；随后更新组件测试，锁定新 row 结构并拒绝旧的 slogan 下方独立链接布局；最后仅在 `research-page-client` 中把 slogan 和签名链接合并到同一 metadata row，去掉旧的左侧补偿与堆叠结构。
- 修改文件:
  - `docs/Frontend_IA.md`
  - `apps/web/tests/component/research-page-client.spec.tsx`
  - `apps/web/features/research/components/research-page-client.tsx`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm exec vitest run tests/component/research-page-client.spec.tsx` -- 19/19 通过
  - 已运行: `cd apps/web && pnpm typecheck` -- 通过
  - 未运行: 真实浏览器人工视觉验收；本任务包验收命令仅要求 targeted component spec 与 `typecheck`
- 验收结论: accepted；hero 现在以单行 metadata row 呈现 slogan 与签名链接，链接保持弱化并右对齐，旧的下方独立链接契约已由测试锁死不再回退。
- blocker / 风险:
  - 尚未做真实浏览器下的人工视觉 spot check，不同字重渲染或窄屏下仍可能需要极小 spacing 微调
- 下一步建议:
  - 在桌面与移动端各做一次人工视觉确认，重点看 `MIMIR` 与 slogan 左缘是否已自然收齐、签名是否保持“弱元信息”而非 CTA 感
