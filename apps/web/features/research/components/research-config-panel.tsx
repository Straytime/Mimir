"use client";

import { type FocusEvent, useId, useState } from "react";

import { useResearchSessionStore } from "../providers/research-workspace-providers";

const NATURAL_HINT =
  "通过自然对话，开放式地向我反馈需求细节，适合复杂、需要详细说明的研究任务";
const OPTIONS_HINT =
  "通过自动生成的选单直接向我提供预设建议，适合快速启动";

export function ResearchConfigPanel() {
  const headingId = useId();
  const clarificationModeDraft = useResearchSessionStore(
    (state) => state.ui.createTask.clarificationModeDraft,
  );
  const pendingAction = useResearchSessionStore((state) => state.ui.pendingAction);
  const setClarificationModeDraft = useResearchSessionStore(
    (state) => state.setCreateTaskClarificationModeDraft,
  );
  const [activeHint, setActiveHint] = useState<"natural" | "options" | null>(null);

  const isDisabled = pendingAction === "creating_task";

  function handleBlur(event: FocusEvent<HTMLFieldSetElement>) {
    if (event.currentTarget.contains(event.relatedTarget)) {
      return;
    }

    setActiveHint(null);
  }

  const hintCopy =
    activeHint === "natural"
      ? NATURAL_HINT
      : activeHint === "options"
        ? OPTIONS_HINT
        : null;

  const hintLabel =
    activeHint === "natural" ? "问答式" : activeHint === "options" ? "选项式" : null;

  return (
    <fieldset
      aria-labelledby={headingId}
      className="space-y-2 bg-surface-container-lowest px-2 py-2"
      disabled={isDisabled}
      onBlurCapture={handleBlur}
    >
      <p
        className="px-1 text-[11px] font-ui font-medium tracking-[0.12em] text-tertiary"
        id={headingId}
      >
        你喜欢什么样的需求沟通方式？
      </p>

      <div
        className="space-y-1"
        data-testid="research-config-selector-region"
        onMouseLeave={(event) => {
          if (
            event.relatedTarget instanceof Node &&
            event.currentTarget.contains(event.relatedTarget)
          ) {
            return;
          }

          setActiveHint(null);
        }}
      >
        <div className="grid gap-1.5 sm:grid-cols-2">
          <label
            className={`flex h-10 cursor-pointer items-center justify-between bg-surface-container-lowest px-2.5 transition-colors outline outline-1 ${
              clarificationModeDraft === "natural"
                ? "bg-surface-container-low text-primary outline-primary/25"
                : "text-secondary outline-outline-variant/15 hover:bg-surface-container-low hover:text-primary"
            }`}
            onMouseEnter={() => setActiveHint("natural")}
          >
            <span className="text-[13px] font-semibold tracking-[0.01em]">问答式</span>
            <input
              aria-label="问答式"
              checked={clarificationModeDraft === "natural"}
              className="sr-only"
              name="clarification_mode"
              onFocus={() => setActiveHint("natural")}
              onChange={() => setClarificationModeDraft("natural")}
              type="radio"
              value="natural"
            />
            <span
              aria-hidden="true"
              className="font-ui text-[10px] uppercase tracking-[0.18em] text-tertiary"
            >
              qa
            </span>
          </label>

          <label
            className={`flex h-10 cursor-pointer items-center justify-between bg-surface-container-lowest px-2.5 transition-colors outline outline-1 ${
              clarificationModeDraft === "options"
                ? "bg-surface-container-low text-primary outline-primary/25"
                : "text-secondary outline-outline-variant/15 hover:bg-surface-container-low hover:text-primary"
            }`}
            onMouseEnter={() => setActiveHint("options")}
          >
            <span className="text-[13px] font-semibold tracking-[0.01em]">选项式</span>
            <input
              aria-label="选项式"
              checked={clarificationModeDraft === "options"}
              className="sr-only"
              name="clarification_mode"
              onFocus={() => setActiveHint("options")}
              onChange={() => setClarificationModeDraft("options")}
              type="radio"
              value="options"
            />
            <span
              aria-hidden="true"
              className="font-ui text-[10px] uppercase tracking-[0.18em] text-tertiary"
            >
              opt
            </span>
          </label>
        </div>

        {hintCopy !== null && hintLabel !== null ? (
          <div
            aria-label={`${hintLabel}提示`}
            className="bg-surface-container-low px-2.5 py-2 text-[11px] leading-5 text-secondary outline outline-1 outline-outline-variant/15"
            role="note"
          >
            <p className="mb-1 font-ui text-[10px] font-semibold uppercase tracking-[0.16em] text-primary">
              {hintLabel}
            </p>
            <p>{hintCopy}</p>
          </div>
        ) : null}
      </div>
    </fieldset>
  );
}
