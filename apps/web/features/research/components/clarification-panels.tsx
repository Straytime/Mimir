"use client";

import { useEffect, useState } from "react";

import { useClarificationSubmit } from "../hooks/use-clarification-submit";
import { useResearchSessionStore } from "../providers/research-workspace-providers";
import { selectCanSubmitClarification } from "../store/selectors";
import { extractClarificationIntro } from "../utils/clarification-text";

function getRemainingCountdownSeconds(deadlineAt: string | null) {
  if (deadlineAt === null) {
    return null;
  }

  return Math.max(
    0,
    Math.ceil((new Date(deadlineAt).getTime() - Date.now()) / 1000),
  );
}

function useCountdownSeconds(deadlineAt: string | null) {
  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(() =>
    getRemainingCountdownSeconds(deadlineAt),
  );

  useEffect(() => {
    setRemainingSeconds(getRemainingCountdownSeconds(deadlineAt));

    if (deadlineAt === null) {
      return;
    }

    const intervalId = setInterval(() => {
      setRemainingSeconds(getRemainingCountdownSeconds(deadlineAt));
    }, 1_000);

    return () => {
      clearInterval(intervalId);
    };
  }, [deadlineAt]);

  return remainingSeconds;
}

export function OptionsClarificationCountdownSurface() {
  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);
  const questionSet = useResearchSessionStore((state) => state.stream.questionSet);
  const countdownDeadlineAt = useResearchSessionStore(
    (state) => state.ui.clarificationCountdownDeadlineAt,
  );
  const remainingSeconds = useCountdownSeconds(countdownDeadlineAt);

  if (
    snapshot === null ||
    snapshot.phase !== "clarifying" ||
    snapshot.clarification_mode !== "options" ||
    questionSet === null ||
    remainingSeconds === null
  ) {
    return null;
  }

  return (
    <div
      aria-label="选单澄清倒计时"
      aria-live="polite"
      className={`bg-surface-container-high px-4 py-3 text-[11px] font-ui font-medium uppercase tracking-[0.15em] ${
        remainingSeconds <= 10
          ? "text-[#FF6B6B] animate-pulse-fast"
          : "text-surface-tint"
      }`}
      role="status"
    >
      {remainingSeconds <= 10 ? "即将自动提交 — " : null}
      剩余 {remainingSeconds} 秒
    </div>
  );
}

export function ClarificationDetailPanel() {
  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);
  const clarificationText = useResearchSessionStore(
    (state) => state.stream.clarificationText,
  );
  const questionSet = useResearchSessionStore((state) => state.stream.questionSet);
  const optionAnswers = useResearchSessionStore((state) => state.ui.optionAnswers);
  const clarificationFieldError = useResearchSessionStore(
    (state) => state.ui.clarificationFieldError,
  );
  const pendingAction = useResearchSessionStore((state) => state.ui.pendingAction);
  const canSubmitClarification = useResearchSessionStore(selectCanSubmitClarification);
  const setOptionAnswer = useResearchSessionStore((state) => state.setOptionAnswer);
  const submitClarification = useClarificationSubmit();
  const isSubmitting = pendingAction === "submitting_clarification";

  if (snapshot === null || snapshot.phase !== "clarifying") {
    return null;
  }

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <h3
          className="text-lg font-semibold text-primary"
          data-research-anchor-target="clarification-title"
        >
          澄清详情
        </h3>
        <p className="text-sm leading-6 text-secondary">
          在开始之前，有一些问题需要你的反馈
        </p>
      </div>

      {questionSet !== null ? (
        (() => {
          const introText = extractClarificationIntro(clarificationText, questionSet);
          return introText.length > 0 ? (
            <div className="whitespace-pre-line bg-surface-container-low px-4 py-4 font-narrative text-sm leading-7 text-secondary">
              {introText}
            </div>
          ) : null;
        })()
      ) : (
        <div className="whitespace-pre-line bg-surface-container-low px-4 py-4 font-narrative text-sm leading-7 text-secondary">
          {clarificationText.length > 0
            ? clarificationText
            : "正在生成追问..."}
        </div>
      )}

      {snapshot.clarification_mode === "options" && questionSet !== null ? (
        <div className="space-y-4">
          {questionSet.questions.map((question) => (
            <fieldset
              className="space-y-3 bg-surface-container-low px-4 py-4"
              key={question.question_id}
            >
              <legend className="px-2 font-narrative text-sm font-semibold text-primary">
                {question.question}
              </legend>
              <div className="space-y-2">
                {question.options.map((option) => (
                  <label
                    className="flex cursor-pointer items-start gap-3 bg-surface-container-lowest px-4 py-3 transition hover:bg-surface-container-high"
                    key={option.option_id}
                  >
                    <input
                      checked={optionAnswers[question.question_id] === option.option_id}
                      className="mt-1 accent-surface-tint"
                      name={question.question_id}
                      onChange={() =>
                        setOptionAnswer({
                          questionId: question.question_id,
                          optionId: option.option_id,
                        })
                      }
                      type="radio"
                      value={option.option_id}
                    />
                    <span className="font-narrative text-sm text-primary">{option.label}</span>
                  </label>
                ))}
              </div>
            </fieldset>
          ))}

          {clarificationFieldError !== null ? (
            <p className="text-sm text-[#FF6B6B]" role="alert">
              {clarificationFieldError}
            </p>
          ) : null}

          <button
            className="bg-primary px-5 py-3 text-sm font-semibold text-on-primary transition hover:shadow-glow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-surface-tint disabled:cursor-not-allowed disabled:bg-tertiary disabled:text-surface"
            disabled={!canSubmitClarification || isSubmitting}
            onClick={() => {
              void submitClarification();
            }}
            type="button"
          >
            {isSubmitting ? "正在提交..." : "提交澄清"}
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function RequirementAnalysisPanel() {
  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);
  const analysisText = useResearchSessionStore((state) => state.stream.analysisText);
  const requirementDetail = useResearchSessionStore(
    (state) => state.remote.currentRevision?.requirement_detail ?? null,
  );

  if (snapshot === null || snapshot.phase === "clarifying") {
    return null;
  }

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <h3 className="text-lg font-semibold text-primary">需求分析交接</h3>
        <p className="text-sm leading-6 text-secondary">
          Stage 4 只展示轻量状态文案与 requirement_detail，不进入时间线透明度。
        </p>
      </div>

      {analysisText.length > 0 ? (
        <div className="bg-surface-container-high px-4 py-4 text-sm leading-7 text-surface-tint">
          正在分析需求：{analysisText}
        </div>
      ) : null}

      {requirementDetail !== null ? (
        <article className="bg-surface-container-low px-5 py-5">
          <p className="text-[11px] font-ui font-semibold uppercase tracking-[0.15em] text-tertiary">
            需求摘要已生成
          </p>
          <h3 className="mt-sp-2 text-xl font-narrative font-semibold text-primary">
            {requirementDetail.research_goal}
          </h3>
          <dl className="mt-4 space-y-sp-2 text-sm leading-6 text-secondary">
            <div>
              <dt className="font-ui font-medium text-tertiary">领域</dt>
              <dd className="font-narrative">{requirementDetail.domain}</dd>
            </div>
            <div>
              <dt className="font-ui font-medium text-tertiary">细化说明</dt>
              <dd className="font-narrative">{requirementDetail.requirement_details}</dd>
            </div>
            <div>
              <dt className="font-ui font-medium text-tertiary">输出格式</dt>
              <dd className="font-narrative">{requirementDetail.output_format}</dd>
            </div>
          </dl>
        </article>
      ) : null}
    </div>
  );
}
