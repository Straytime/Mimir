"use client";

import type { FormEvent, KeyboardEvent } from "react";

import { useCreateTask } from "../hooks/use-create-task";
import { useResearchSessionStore } from "../providers/research-workspace-providers";

const MAX_QUERY_LENGTH = 500;

export function ResearchInputPanel() {
  const initialPromptDraft = useResearchSessionStore(
    (state) => state.ui.initialPromptDraft,
  );
  const createTaskUi = useResearchSessionStore((state) => state.ui.createTask);
  const pendingAction = useResearchSessionStore((state) => state.ui.pendingAction);
  const setInitialPromptDraft = useResearchSessionStore(
    (state) => state.setInitialPromptDraft,
  );
  const createTask = useCreateTask();

  const isSubmitting = pendingAction === "creating_task";
  const hasPrompt = initialPromptDraft.trim().length > 0;

  async function submitTask(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    await createTask();
  }

  async function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      await createTask();
    }
  }

  return (
    <form
      className="space-y-4 rounded-[2rem] border border-slate-200/70 bg-white/85 p-6 shadow-sm backdrop-blur"
      onSubmit={submitTask}
    >
      <div className="space-y-2">
        <h2 className="text-lg font-semibold text-primary">输入研究主题</h2>
        <p className="text-sm leading-6 text-secondary">
          最多 500 字或单词。按 <kbd>Enter</kbd> 提交，<kbd>Shift + Enter</kbd>{" "}
          换行。
        </p>
      </div>

      <div className="space-y-2">
        <label
          className="text-sm font-medium text-primary"
          htmlFor="initial-query"
        >
          研究主题
        </label>
        <textarea
          aria-describedby="initial-query-help initial-query-counter"
          aria-invalid={createTaskUi.initialQueryError !== null}
          className="min-h-40 w-full border-0 bg-surface-container-lowest px-4 py-4 text-base leading-7 text-primary placeholder:text-tertiary outline-none transition focus:bg-surface-container-high focus:shadow-[inset_2px_0_0_0_theme(colors.surface-tint)] disabled:cursor-not-allowed disabled:opacity-70"
          disabled={isSubmitting}
          id="initial-query"
          maxLength={MAX_QUERY_LENGTH}
          onChange={(event) => setInitialPromptDraft(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="例如：帮我研究中国 AI 搜索产品的竞争格局、主要玩家和未来机会"
          value={initialPromptDraft}
        />
        <div className="flex items-center justify-between text-xs text-tertiary">
          <span id="initial-query-help">允许换行，创建中会暂时锁定输入。</span>
          <span id="initial-query-counter">
            {initialPromptDraft.length}/{MAX_QUERY_LENGTH}
          </span>
        </div>
        {createTaskUi.initialQueryError !== null ? (
          <p className="text-sm text-[#FF6B6B]" role="alert">
            {createTaskUi.initialQueryError}
          </p>
        ) : null}
      </div>

      {createTaskUi.submitError !== null ? (
        <div
          className="bg-surface-container-high px-4 py-3 text-sm text-[#FFB86C]"
          role="alert"
        >
          <p>{createTaskUi.submitError}</p>
          {createTaskUi.nextAvailableAt !== null ? (
            <p className="mt-1">下次可创建时间：{createTaskUi.nextAvailableAt}</p>
          ) : null}
          {createTaskUi.retryAfterLabel !== null ? (
            <p className="mt-1">{createTaskUi.retryAfterLabel}</p>
          ) : null}
        </div>
      ) : null}

      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-secondary">
          创建成功后将进入工作台，依次完成澄清与需求分析。
        </p>
        <button
          className="bg-primary px-5 py-3 text-sm font-semibold text-on-primary transition hover:shadow-[0_2px_0_0_theme(colors.surface-tint)] disabled:cursor-not-allowed disabled:bg-tertiary disabled:text-surface"
          disabled={isSubmitting || !hasPrompt}
          type="submit"
        >
          {isSubmitting ? "正在创建..." : "开始研究"}
        </button>
      </div>
    </form>
  );
}
