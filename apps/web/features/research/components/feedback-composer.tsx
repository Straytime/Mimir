"use client";

import type { FormEvent } from "react";

import { useFeedbackSubmit } from "../hooks/use-feedback-submit";
import { useResearchSessionStore } from "../providers/research-workspace-providers";
import { selectCanSubmitFeedback } from "../store/selectors";

const MAX_FEEDBACK_LENGTH = 1000;

export function FeedbackComposer() {
  const feedbackDraft = useResearchSessionStore((state) => state.ui.feedbackDraft);
  const feedbackFieldError = useResearchSessionStore(
    (state) => state.ui.feedbackFieldError,
  );
  const feedbackSubmitError = useResearchSessionStore(
    (state) => state.ui.feedbackSubmitError,
  );
  const pendingAction = useResearchSessionStore((state) => state.ui.pendingAction);
  const revisionTransition = useResearchSessionStore(
    (state) => state.ui.revisionTransition,
  );
  const setFeedbackDraft = useResearchSessionStore((state) => state.setFeedbackDraft);
  const canSubmitFeedback = useResearchSessionStore(selectCanSubmitFeedback);
  const submitFeedback = useFeedbackSubmit();

  const isSubmitting = pendingAction === "submitting_feedback";
  const isDisabled = isSubmitting || !canSubmitFeedback;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await submitFeedback();
  }

  return (
    <section
      aria-label="反馈输入"
      className="rounded-[2rem] border border-slate-200/70 bg-white/82 p-6 shadow-sm backdrop-blur"
      role="region"
    >
      <div className="space-y-2">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
          Feedback
        </p>
        <h3 className="text-xl font-semibold text-slate-950">继续迭代当前任务</h3>
        <p className="text-sm leading-6 text-slate-600">
          提交后会保留旧报告，直到下一轮 revision 的首个 SSE 事件到达并接管工作台。
        </p>
      </div>

      <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <label
            className="text-sm font-medium text-slate-800"
            htmlFor="feedback-text"
          >
            反馈意见
          </label>
          <textarea
            aria-describedby="feedback-help feedback-counter"
            aria-invalid={feedbackFieldError !== null}
            className="min-h-32 w-full rounded-3xl border border-slate-300 bg-slate-50/80 px-4 py-4 text-base leading-7 text-slate-950 outline-none transition focus:border-sky-500 focus:bg-white disabled:cursor-not-allowed disabled:opacity-70"
            disabled={isDisabled}
            id="feedback-text"
            maxLength={MAX_FEEDBACK_LENGTH}
            onChange={(event) => setFeedbackDraft(event.target.value)}
            placeholder="例如：请强化竞品对比、补充商业化分析，并解释结论背后的证据。"
            value={feedbackDraft}
          />
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span id="feedback-help">
              最多 1000 字。进入下一 revision 等待态后会锁定当前输入区。
            </span>
            <span id="feedback-counter">
              {feedbackDraft.length}/{MAX_FEEDBACK_LENGTH}
            </span>
          </div>
          {feedbackFieldError !== null ? (
            <p className="text-sm text-rose-600" role="alert">
              {feedbackFieldError}
            </p>
          ) : null}
        </div>

        {feedbackSubmitError !== null ? (
          <div
            className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
            role="alert"
          >
            {feedbackSubmitError}
          </div>
        ) : null}

        {revisionTransition.status !== "idle" ? (
          <p className="text-sm leading-6 text-slate-600">
            正在等待第 {revisionTransition.pendingRevisionNumber ?? "?"} 轮研究接管。
          </p>
        ) : null}

        <div className="flex items-center justify-between gap-4">
          <p className="text-sm text-slate-600">
            仅在 `task.awaiting_feedback` 阶段开放；终态事件一旦到达，旧动作会立即禁用。
          </p>
          <button
            className="rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
            disabled={isDisabled || feedbackDraft.trim().length === 0}
            type="submit"
          >
            {isSubmitting ? "正在提交..." : "提交反馈"}
          </button>
        </div>
      </form>
    </section>
  );
}
