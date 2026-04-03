"use client";

import { type FocusEvent, useState } from "react";

import { useResearchSessionStore } from "../providers/research-workspace-providers";

const NATURAL_HINT =
  "通过自然对话，开放式地向我反馈需求细节，适合复杂、需要详细说明的研究任务";
const OPTIONS_HINT =
  "通过自动生成的选单直接向我提供预设建议，适合快速启动";

export function ResearchConfigPanel() {
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
    activeHint === "natural" ? "问答" : activeHint === "options" ? "选项" : null;

  return (
    <fieldset
      className="space-y-3 bg-surface-container-lowest px-3 py-3"
      disabled={isDisabled}
      onBlurCapture={handleBlur}
    >
      <p className="px-1 text-[11px] font-ui font-medium tracking-[0.12em] text-tertiary">
        你喜欢什么样的需求沟通方式？
      </p>

      <div className="grid gap-2 sm:grid-cols-2">
        <label
          className={`flex cursor-pointer items-center justify-between bg-surface-container-low px-3 py-3 transition ${
            clarificationModeDraft === "natural"
              ? "text-primary outline outline-1 outline-primary/30"
              : "text-secondary hover:bg-surface-container"
          }`}
          onMouseEnter={() => setActiveHint("natural")}
          onMouseLeave={() => setActiveHint(null)}
        >
          <span className="text-sm font-semibold">问答</span>
          <input
            aria-label="问答"
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
            className="font-ui text-[11px] uppercase tracking-[0.18em] text-tertiary"
          >
            qa
          </span>
        </label>

        <label
          className={`flex cursor-pointer items-center justify-between bg-surface-container-low px-3 py-3 transition ${
            clarificationModeDraft === "options"
              ? "text-primary outline outline-1 outline-primary/30"
              : "text-secondary hover:bg-surface-container"
          }`}
          onMouseEnter={() => setActiveHint("options")}
          onMouseLeave={() => setActiveHint(null)}
        >
          <span className="text-sm font-semibold">选项</span>
          <input
            aria-label="选项"
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
            className="font-ui text-[11px] uppercase tracking-[0.18em] text-tertiary"
          >
            opt
          </span>
        </label>
      </div>

      {hintCopy !== null && hintLabel !== null ? (
        <div className="bg-surface-container-low px-3 py-2 text-xs leading-6 text-secondary">
          <p className="mb-1 font-ui text-[11px] font-semibold uppercase tracking-[0.15em] text-primary">
            {hintLabel}
          </p>
          <p>{hintCopy}</p>
        </div>
      ) : null}
    </fieldset>
  );
}
