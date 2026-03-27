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
      className="space-y-3 bg-surface-container-low p-6"
      disabled={isDisabled}
    >
      <legend className="px-2 text-[11px] font-ui font-semibold uppercase tracking-[0.15em] text-tertiary">
        研究配置
      </legend>
      <p className="text-sm leading-6 text-secondary">
        任务创建后配置会锁定。当前阶段会按这里选择的模式进入自然语言或选单澄清 UI。
      </p>

      <label className="flex cursor-pointer items-start gap-3 bg-surface-container-lowest px-4 py-3 transition hover:bg-surface-container-high">
        <input
          checked={clarificationModeDraft === "natural"}
          className="mt-1 accent-surface-tint"
          name="clarification_mode"
          onChange={() => setClarificationModeDraft("natural")}
          type="radio"
          value="natural"
        />
        <span>
          <span className="block text-sm font-semibold text-primary">
            自然澄清
          </span>
          <span className="block text-sm text-secondary">
            默认模式。系统先用自然语言追问，再等待用户回答。
          </span>
        </span>
      </label>

      <label className="flex cursor-pointer items-start gap-3 bg-surface-container-lowest px-4 py-3 transition hover:bg-surface-container-high">
        <input
          checked={clarificationModeDraft === "options"}
          className="mt-1 accent-surface-tint"
          name="clarification_mode"
          onChange={() => setClarificationModeDraft("options")}
          type="radio"
          value="options"
        />
        <span>
          <span className="block text-sm font-semibold text-primary">
            选单澄清
          </span>
          <span className="block text-sm text-secondary">
            系统生成结构化问题并预选默认答案，15 秒倒计时后自动提交。
          </span>
        </span>
      </label>
    </fieldset>
  );
}
