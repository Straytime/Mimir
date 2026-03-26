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
      className="bg-surface-container-low p-6"
      role="region"
    >
      <div className="space-y-2">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-tertiary">
          Feedback
        </p>
        <h3 className="text-xl font-semibold text-primary">继续迭代当前任务</h3>
        <p className="text-sm leading-6 text-secondary">
          提交后将保留旧报告，直到新一轮研究就绪后接管。
        </p>
      </div>

      <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <label
            className="text-sm font-medium text-primary"
            htmlFor="feedback-text"
          >
            反馈意见
          </label>
          <textarea
            aria-describedby="feedback-help feedback-counter"
            aria-invalid={feedbackFieldError !== null}
            className="min-h-32 w-full border-0 bg-surface-container-lowest px-4 py-4 text-base leading-7 text-primary placeholder:text-tertiary outline-none transition focus:bg-surface-container-high focus:shadow-[inset_2px_0_0_0_theme(colors.surface-tint)] disabled:cursor-not-allowed disabled:opacity-70"
            disabled={isDisabled}
            id="feedback-text"
            maxLength={MAX_FEEDBACK_LENGTH}
            onChange={(event) => setFeedbackDraft(event.target.value)}
            placeholder="例如：请强化竞品对比、补充商业化分析，并解释结论背后的证据。"
            value={feedbackDraft}
          />
          <div className="flex items-center justify-between text-xs text-tertiary">
            <span id="feedback-help">
              最多 1000 字。进入下一轮修订后会锁定当前输入。
            </span>
            <span id="feedback-counter">
              {feedbackDraft.length}/{MAX_FEEDBACK_LENGTH}
            </span>
          </div>
          {feedbackFieldError !== null ? (
            <p className="text-sm text-[#FF6B6B]" role="alert">
              {feedbackFieldError}
            </p>
          ) : null}
        </div>

        {feedbackSubmitError !== null ? (
          <div
            className="bg-surface-container-high px-4 py-3 text-sm text-[#FFB86C]"
            role="alert"
          >
            {feedbackSubmitError}
          </div>
        ) : null}

        {revisionTransition.status !== "idle" ? (
          <p className="text-sm leading-6 text-secondary">
            正在等待第 {revisionTransition.pendingRevisionNumber ?? "?"} 轮研究接管。
          </p>
        ) : null}

        <div className="flex items-center justify-between gap-4">
          <p className="text-sm text-secondary">
            仅在交付后的反馈阶段开放，终态事件到达后会自动禁用。
          </p>
          <button
            className="bg-primary px-5 py-3 text-sm font-semibold text-on-primary transition hover:shadow-[0_2px_0_0_theme(colors.surface-tint)] disabled:cursor-not-allowed disabled:bg-tertiary disabled:text-surface"
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
