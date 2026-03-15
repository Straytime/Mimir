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
        <h2 className="text-lg font-semibold text-slate-950">输入研究主题</h2>
        <p className="text-sm leading-6 text-slate-600">
          最多 500 字或单词。按 <kbd>Enter</kbd> 提交，<kbd>Shift + Enter</kbd>{" "}
          换行。
        </p>
      </div>

      <div className="space-y-2">
        <label
          className="text-sm font-medium text-slate-800"
          htmlFor="initial-query"
        >
          研究主题
        </label>
        <textarea
          aria-describedby="initial-query-help initial-query-counter"
          aria-invalid={createTaskUi.initialQueryError !== null}
          className="min-h-40 w-full rounded-3xl border border-slate-300 bg-slate-50/80 px-4 py-4 text-base leading-7 text-slate-950 outline-none transition focus:border-sky-500 focus:bg-white disabled:cursor-not-allowed disabled:opacity-70"
          disabled={isSubmitting}
          id="initial-query"
          maxLength={MAX_QUERY_LENGTH}
          onChange={(event) => setInitialPromptDraft(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="例如：帮我研究中国 AI 搜索产品的竞争格局、主要玩家和未来机会"
          value={initialPromptDraft}
        />
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span id="initial-query-help">允许换行，创建中会暂时锁定输入。</span>
          <span id="initial-query-counter">
            {initialPromptDraft.length}/{MAX_QUERY_LENGTH}
          </span>
        </div>
        {createTaskUi.initialQueryError !== null ? (
          <p className="text-sm text-rose-600" role="alert">
            {createTaskUi.initialQueryError}
          </p>
        ) : null}
      </div>

      {createTaskUi.submitError !== null ? (
        <div
          className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
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
        <p className="text-sm text-slate-600">
          创建任务后会立即请求建立 SSE 连接；真正的生命周期消费留到 Stage 3。
        </p>
        <button
          className="rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          disabled={isSubmitting || !hasPrompt}
          type="submit"
        >
          {isSubmitting ? "正在创建..." : "开始研究"}
        </button>
      </div>
    </form>
  );
}
