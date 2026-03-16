"use client";

import { useResearchSessionStore } from "../providers/research-workspace-providers";

export function ResearchConfigPanel() {
  const clarificationModeDraft = useResearchSessionStore(
    (state) => state.ui.createTask.clarificationModeDraft,
  );
  const pendingAction = useResearchSessionStore((state) => state.ui.pendingAction);
  const setClarificationModeDraft = useResearchSessionStore(
    (state) => state.setCreateTaskClarificationModeDraft,
  );

  const isDisabled = pendingAction === "creating_task";

  return (
    <fieldset
      className="space-y-3 rounded-3xl border border-slate-200/70 bg-white/80 p-6 shadow-sm"
      disabled={isDisabled}
    >
      <legend className="px-2 text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
        研究配置
      </legend>
      <p className="text-sm leading-6 text-slate-600">
        任务创建后配置会锁定。当前阶段会按这里选择的模式进入自然语言或选单澄清 UI。
      </p>

      <label className="flex cursor-pointer items-start gap-3 rounded-2xl border border-slate-200 px-4 py-3">
        <input
          checked={clarificationModeDraft === "natural"}
          className="mt-1"
          name="clarification_mode"
          onChange={() => setClarificationModeDraft("natural")}
          type="radio"
          value="natural"
        />
        <span>
          <span className="block text-sm font-semibold text-slate-900">
            自然澄清
          </span>
          <span className="block text-sm text-slate-600">
            默认模式。系统先用自然语言追问，再等待用户回答。
          </span>
        </span>
      </label>

      <label className="flex cursor-pointer items-start gap-3 rounded-2xl border border-slate-200 px-4 py-3">
        <input
          checked={clarificationModeDraft === "options"}
          className="mt-1"
          name="clarification_mode"
          onChange={() => setClarificationModeDraft("options")}
          type="radio"
          value="options"
        />
        <span>
          <span className="block text-sm font-semibold text-slate-900">
            选单澄清
          </span>
          <span className="block text-sm text-slate-600">
            由后端生成结构化问题集，前端默认把每题初始化为 `o_auto` 并维护 15 秒倒计时。
          </span>
        </span>
      </label>
    </fieldset>
  );
}
