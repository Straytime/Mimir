"use client";

import { useEffect, useState } from "react";

import { useClarificationSubmit } from "../hooks/use-clarification-submit";
import { useResearchSessionStore } from "../providers/research-workspace-providers";
import { selectCanSubmitClarification } from "../store/selectors";

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

type ClarificationActionPanelProps = {
  compact?: boolean;
};

export function ClarificationActionPanel({
  compact = false,
}: ClarificationActionPanelProps) {
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
    <div className={compact ? "space-y-4" : "space-y-5"}>
      <div className="space-y-2">
        <h3 className="text-lg font-semibold text-slate-950">澄清提交</h3>
        <p className="text-sm leading-6 text-slate-600">
          {isClarifying
            ? isNaturalMode
              ? "自然语言澄清在 ready 事件到达后开放输入。"
              : "选单澄清默认将每题初始化为 o_auto，可直接提交或先修改选项。"
            : "澄清已交接给需求分析阶段，旧操作不会继续保留。"}
        </p>
      </div>

      {isClarifying && isNaturalMode ? (
        <div className="space-y-2">
          <label
            className="text-sm font-medium text-slate-800"
            htmlFor="clarification-draft"
          >
            澄清补充说明
          </label>
          <textarea
            aria-describedby="clarification-counter"
            aria-invalid={clarificationFieldError !== null}
            className="min-h-32 w-full rounded-3xl border border-slate-300 bg-slate-50/80 px-4 py-4 text-base leading-7 text-slate-950 outline-none transition focus:border-sky-500 focus:bg-white disabled:cursor-not-allowed disabled:opacity-70"
            disabled={isTextareaDisabled}
            id="clarification-draft"
            maxLength={MAX_CLARIFICATION_LENGTH}
            onChange={(event) => setClarificationDraft(event.target.value)}
            placeholder="例如：重点看中国市场，偏商业分析，覆盖近两年变化。"
            value={clarificationDraft}
          />
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>提交后将进入需求分析阶段。</span>
            <span id="clarification-counter">
              {clarificationDraft.length}/{MAX_CLARIFICATION_LENGTH}
            </span>
          </div>
          {clarificationFieldError !== null ? (
            <p className="text-sm text-rose-600" role="alert">
              {clarificationFieldError}
            </p>
          ) : null}
        </div>
      ) : null}

      {isClarifying && !isNaturalMode ? (
        <div className="rounded-3xl border border-slate-200 bg-slate-50/80 px-4 py-4 text-sm leading-7 text-slate-700">
          当前处于选单澄清。问题与倒计时显示在“澄清详情”区域，操作区只保留提交入口。
        </div>
      ) : null}

      {clarificationSubmitError !== null ? (
        <div
          className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
          role="alert"
        >
          {clarificationSubmitError}
        </div>
      ) : null}

      <button
        className="rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
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

type ClarificationDetailPanelProps = {
  compact?: boolean;
};

export function ClarificationDetailPanel({
  compact = false,
}: ClarificationDetailPanelProps) {
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
    <div className={compact ? "space-y-4" : "space-y-5"}>
      <div className="space-y-2">
        <h3 className="text-lg font-semibold text-slate-950">澄清详情</h3>
        <p className="text-sm leading-6 text-slate-600">
          只消费后端返回的结构化 question_set，不解析原始 markdown。
        </p>
      </div>

      <div className="rounded-3xl border border-slate-200 bg-slate-50/80 px-4 py-4 text-sm leading-7 text-slate-700">
        {clarificationText.length > 0
          ? clarificationText
          : "等待澄清追问流式输出。"}
      </div>

      {snapshot.clarification_mode === "options" && questionSet !== null ? (
        <div className="space-y-4">
          {remainingSeconds !== null ? (
            <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm font-medium text-sky-900">
              剩余 {remainingSeconds} 秒
            </div>
          ) : null}

          {questionSet.questions.map((question) => (
            <fieldset
              className="space-y-3 rounded-3xl border border-slate-200 bg-white/90 px-4 py-4"
              key={question.question_id}
            >
              <legend className="px-2 text-sm font-semibold text-slate-900">
                {question.question}
              </legend>
              <div className="space-y-2">
                {question.options.map((option) => (
                  <label
                    className="flex cursor-pointer items-start gap-3 rounded-2xl border border-slate-200 px-4 py-3"
                    key={option.option_id}
                  >
                    <input
                      checked={optionAnswers[question.question_id] === option.option_id}
                      className="mt-1"
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
                    <span className="text-sm text-slate-800">{option.label}</span>
                  </label>
                ))}
              </div>
            </fieldset>
          ))}

          {clarificationFieldError !== null ? (
            <p className="text-sm text-rose-600" role="alert">
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
        <h3 className="text-lg font-semibold text-slate-950">需求分析交接</h3>
        <p className="text-sm leading-6 text-slate-600">
          Stage 4 只展示轻量状态文案与 requirement_detail，不进入时间线透明度。
        </p>
      </div>

      {analysisText.length > 0 ? (
        <div className="rounded-3xl border border-sky-200 bg-sky-50 px-4 py-4 text-sm leading-7 text-sky-900">
          正在分析需求：{analysisText}
        </div>
      ) : null}

      {requirementDetail !== null ? (
        <article className="rounded-3xl border border-slate-200 bg-white/90 px-5 py-5">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
            需求摘要已生成
          </p>
          <h3 className="mt-3 text-xl font-semibold text-slate-950">
            {requirementDetail.research_goal}
          </h3>
          <dl className="mt-4 space-y-3 text-sm leading-6 text-slate-700">
            <div>
              <dt className="font-medium text-slate-500">领域</dt>
              <dd>{requirementDetail.domain}</dd>
            </div>
            <div>
              <dt className="font-medium text-slate-500">细化说明</dt>
              <dd>{requirementDetail.requirement_details}</dd>
            </div>
            <div>
              <dt className="font-medium text-slate-500">输出格式</dt>
              <dd>{requirementDetail.output_format}</dd>
            </div>
          </dl>
        </article>
      ) : null}
    </div>
  );
}
