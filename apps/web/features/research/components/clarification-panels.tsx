"use client";

import { useEffect, useState } from "react";

import { useClarificationSubmit } from "../hooks/use-clarification-submit";
import { useResearchSessionStore } from "../providers/research-workspace-providers";
import { selectCanSubmitClarification } from "../store/selectors";
import { extractClarificationIntro } from "../utils/clarification-text";

const MAX_CLARIFICATION_LENGTH = 500;

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

export function ClarificationActionPanel() {
  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);
  const clarificationDraft = useResearchSessionStore(
    (state) => state.ui.clarificationDraft,
  );
  const clarificationFieldError = useResearchSessionStore(
    (state) => state.ui.clarificationFieldError,
  );
  const clarificationSubmitError = useResearchSessionStore(
    (state) => state.ui.clarificationSubmitError,
  );
  const pendingAction = useResearchSessionStore((state) => state.ui.pendingAction);
  const setClarificationDraft = useResearchSessionStore(
    (state) => state.setClarificationDraft,
  );
  const canSubmitClarification = useResearchSessionStore(
    selectCanSubmitClarification,
  );
  const submitClarification = useClarificationSubmit();

  if (snapshot === null) {
    return null;
  }

  const isClarifying = snapshot.phase === "clarifying";
  const isNaturalMode = snapshot.clarification_mode === "natural";
  const isSubmitting = pendingAction === "submitting_clarification";
  const isTextareaDisabled =
    !isClarifying || !isNaturalMode || !canSubmitClarification || isSubmitting;

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <h3 className="text-lg font-semibold text-primary">澄清提交</h3>
        <p className="text-sm leading-6 text-secondary">
          {isClarifying
            ? isNaturalMode
              ? "系统正在生成追问，就绪后可在下方输入补充说明。"
              : "下方问题已自动选择默认选项，你可以修改后提交或直接提交。"
            : "澄清已完成，系统正在进入下一阶段。"}
        </p>
      </div>

      {isClarifying && isNaturalMode ? (
        <div className="space-y-2">
          <label
            className="text-sm font-medium text-primary"
            htmlFor="clarification-draft"
          >
            澄清补充说明
          </label>
          <textarea
            aria-describedby="clarification-counter"
            aria-invalid={clarificationFieldError !== null}
            className="min-h-32 w-full border-0 bg-surface-container-lowest px-4 py-4 text-base leading-7 text-primary placeholder:text-tertiary outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-surface-tint transition focus:bg-surface-container-high focus:shadow-inset-caret disabled:cursor-not-allowed disabled:opacity-70"
            disabled={isTextareaDisabled}
            id="clarification-draft"
            maxLength={MAX_CLARIFICATION_LENGTH}
            onChange={(event) => setClarificationDraft(event.target.value)}
            placeholder="例如：重点看中国市场，偏商业分析，覆盖近两年变化。"
            value={clarificationDraft}
          />
          <div className="flex items-center justify-between text-xs text-tertiary">
            <span>提交后将进入需求分析阶段。</span>
            <span id="clarification-counter">
              {clarificationDraft.length}/{MAX_CLARIFICATION_LENGTH}
            </span>
          </div>
          {clarificationFieldError !== null ? (
            <p className="text-sm text-[#FF6B6B]" role="alert">
              {clarificationFieldError}
            </p>
          ) : null}
        </div>
      ) : null}

      {isClarifying && !isNaturalMode ? (
        <div className="bg-surface-container-low px-4 py-4 text-sm leading-7 text-secondary">
          请在下方的问题列表中选择选项，倒计时结束后将自动提交。
        </div>
      ) : null}

      {clarificationSubmitError !== null ? (
        <div
          className="bg-surface-container-high px-4 py-3 text-sm text-[#FFB86C]"
          role="alert"
        >
          {clarificationSubmitError}
        </div>
      ) : null}

      <button
        className="bg-primary px-5 py-3 text-sm font-semibold text-on-primary transition hover:shadow-glow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-surface-tint disabled:cursor-not-allowed disabled:bg-tertiary disabled:text-surface"
        disabled={!isClarifying || !canSubmitClarification || isSubmitting}
        onClick={() => {
          void submitClarification();
        }}
        type="button"
      >
        {isSubmitting ? "正在提交..." : "提交澄清"}
      </button>
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
  const countdownDeadlineAt = useResearchSessionStore(
    (state) => state.ui.clarificationCountdownDeadlineAt,
  );
  const clarificationFieldError = useResearchSessionStore(
    (state) => state.ui.clarificationFieldError,
  );
  const setOptionAnswer = useResearchSessionStore((state) => state.setOptionAnswer);
  const remainingSeconds = useCountdownSeconds(countdownDeadlineAt);

  if (snapshot === null || snapshot.phase !== "clarifying") {
    return null;
  }

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <h3 className="text-lg font-semibold text-primary">澄清详情</h3>
        <p className="text-sm leading-6 text-secondary">
          系统根据你的研究主题生成了以下追问，帮助进一步明确需求。
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
          {remainingSeconds !== null ? (
            <div
              className={`bg-surface-container-high px-4 py-3 text-[11px] font-ui font-medium uppercase tracking-[0.15em] ${
                remainingSeconds <= 10
                  ? "text-[#FF6B6B] animate-pulse-fast"
                  : "text-surface-tint"
              }`}
            >
              {remainingSeconds <= 10 ? "即将自动提交 — " : null}
              剩余 {remainingSeconds} 秒
            </div>
          ) : null}

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
