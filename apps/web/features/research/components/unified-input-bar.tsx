"use client";

import { type KeyboardEvent, useCallback, useRef } from "react";

import type { TaskSnapshot } from "@/lib/contracts";

import { useCreateTask } from "../hooks/use-create-task";
import { useClarificationSubmit } from "../hooks/use-clarification-submit";
import { useResearchSessionStore } from "../providers/research-workspace-providers";
import type { TerminalReason } from "../store/research-session-store.types";

type InputError = {
  fieldError: string | null;
  submitError: string | null;
  ariaInvalid: boolean;
  submitErrorDetail: {
    errorCode: string | null;
    nextAvailableAt: string | null;
    retryAfterLabel: string | null;
  } | null;
};

type InputMode = {
  enabled: boolean;
  placeholder: string;
  draftKey: "initial" | "clarification";
};

export function resolveInputMode(args: {
  snapshot: TaskSnapshot | null;
  terminalReason: TerminalReason;
}): InputMode {
  const { snapshot, terminalReason } = args;

  if (snapshot === null) {
    return {
      enabled: true,
      placeholder: "输入你的研究主题...",
      draftKey: "initial",
    };
  }

  if (terminalReason !== null) {
    return {
      enabled: true,
      placeholder: "输入新的研究主题开始新研究...",
      draftKey: "initial",
    };
  }

  if (snapshot.phase === "clarifying" && snapshot.clarification_mode === "natural") {
    const canSubmit = snapshot.available_actions.includes("submit_clarification");
    return {
      enabled: canSubmit,
      placeholder: "输入澄清补充说明...",
      draftKey: "clarification",
    };
  }

  if (snapshot.phase === "clarifying" && snapshot.clarification_mode === "options") {
    return {
      enabled: false,
      placeholder: "选单澄清模式下请在上方选择选项",
      draftKey: "clarification",
    };
  }

  if (snapshot.phase === "delivered") {
    return {
      enabled: true,
      placeholder: "输入新的研究主题开始新研究...",
      draftKey: "initial",
    };
  }

  return {
    enabled: false,
    placeholder: "研究进行中...",
    draftKey: "initial",
  };
}

function useInputError(draftKey: "initial" | "clarification"): InputError {
  const createTaskUi = useResearchSessionStore((state) => state.ui.createTask);
  const clarificationFieldError = useResearchSessionStore(
    (state) => state.ui.clarificationFieldError,
  );
  const clarificationSubmitError = useResearchSessionStore(
    (state) => state.ui.clarificationSubmitError,
  );

  if (draftKey === "initial") {
    return {
      fieldError: createTaskUi.initialQueryError,
      submitError:
        createTaskUi.errorCode === "resource_busy"
          ? "当前已有一个研究任务正在进行中。请等待其完成或终止后再创建新任务。"
          : createTaskUi.submitError,
      ariaInvalid: createTaskUi.initialQueryError !== null,
      submitErrorDetail:
        createTaskUi.submitError !== null
          ? {
              errorCode: createTaskUi.errorCode,
              nextAvailableAt: createTaskUi.nextAvailableAt,
              retryAfterLabel: createTaskUi.retryAfterLabel,
            }
          : null,
    };
  }

  return {
    fieldError: clarificationFieldError,
    submitError: clarificationSubmitError,
    ariaInvalid: clarificationFieldError !== null,
    submitErrorDetail: null,
  };
}

export function UnifiedInputBar() {
  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);
  const terminalReason = useResearchSessionStore(
    (state) => state.ui.terminalReason,
  );
  const initialPromptDraft = useResearchSessionStore(
    (state) => state.ui.initialPromptDraft,
  );
  const clarificationDraft = useResearchSessionStore(
    (state) => state.ui.clarificationDraft,
  );
  const pendingAction = useResearchSessionStore(
    (state) => state.ui.pendingAction,
  );
  const setInitialPromptDraft = useResearchSessionStore(
    (state) => state.setInitialPromptDraft,
  );
  const setClarificationDraft = useResearchSessionStore(
    (state) => state.setClarificationDraft,
  );
  const reset = useResearchSessionStore((state) => state.reset);

  const createTask = useCreateTask();
  const submitClarification = useClarificationSubmit();

  const isSubmittingRef = useRef(false);

  const mode = resolveInputMode({ snapshot, terminalReason });
  const inputError = useInputError(mode.draftKey);
  const draftValue =
    mode.draftKey === "initial" ? initialPromptDraft : clarificationDraft;
  const setDraftValue =
    mode.draftKey === "initial" ? setInitialPromptDraft : setClarificationDraft;

  const isSubmitting =
    pendingAction === "creating_task" ||
    pendingAction === "submitting_clarification";

  const handleSubmit = useCallback(async () => {
    if (!mode.enabled || isSubmittingRef.current || isSubmitting) {
      return;
    }

    const trimmed = draftValue.trim();
    if (trimmed.length === 0) {
      return;
    }

    isSubmittingRef.current = true;

    try {
      if (mode.draftKey === "clarification") {
        await submitClarification();
        return;
      }

      // draftKey === "initial"
      if (snapshot === null) {
        await createTask();
        return;
      }

      if (snapshot.phase === "delivered") {
        const confirmed = window.confirm(
          "当前研究将被清除，确认开始新研究？",
        );
        if (!confirmed) {
          return;
        }

        const savedDraft = draftValue;
        reset();
        setInitialPromptDraft(savedDraft);
        await createTask();
        return;
      }

      if (terminalReason !== null) {
        const savedDraft = draftValue;
        reset();
        setInitialPromptDraft(savedDraft);
        await createTask();
        return;
      }
    } finally {
      isSubmittingRef.current = false;
    }
  }, [
    mode.enabled,
    mode.draftKey,
    isSubmitting,
    draftValue,
    snapshot,
    terminalReason,
    createTask,
    submitClarification,
    reset,
    setInitialPromptDraft,
  ]);

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSubmit();
    }
  }

  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-40 bg-[linear-gradient(180deg,rgba(19,19,19,0)_0%,rgba(19,19,19,0.76)_20%,rgba(19,19,19,0.94)_100%)] backdrop-blur-[20px]"
      data-research-input-bar="true"
      data-research-input-surface="docked"
    >
      <div className="mx-auto max-w-[800px] px-sp-8 pb-4 pt-5">
        {inputError.fieldError !== null ? (
          <p className="mb-2 text-sm text-[#FF6B6B]" role="alert">
            {inputError.fieldError}
          </p>
        ) : null}
        {inputError.submitError !== null ? (
          <div
            className="mb-2 bg-surface-container-high px-4 py-3 text-sm text-[#FFB86C]"
            role="alert"
          >
            <p>{inputError.submitError}</p>
            {inputError.submitErrorDetail?.nextAvailableAt !== null &&
            inputError.submitErrorDetail?.nextAvailableAt !== undefined ? (
              <p className="mt-1">
                下次可创建时间：{inputError.submitErrorDetail.nextAvailableAt}
              </p>
            ) : null}
            {inputError.submitErrorDetail?.retryAfterLabel !== null &&
            inputError.submitErrorDetail?.retryAfterLabel !== undefined ? (
              <p className="mt-1">{inputError.submitErrorDetail.retryAfterLabel}</p>
            ) : null}
          </div>
        ) : null}
        <div className="bg-surface-container-low/95 px-4 py-4 shadow-[0_-20px_48px_rgba(0,0,0,0.34),inset_0_1px_0_rgba(71,71,71,0.12)]">
          <div className="flex items-stretch gap-3">
            <textarea
              aria-invalid={inputError.ariaInvalid}
              className="min-h-[48px] flex-1 resize-none bg-surface-container-lowest px-4 py-3 text-base leading-7 text-primary placeholder:text-tertiary outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-surface-tint disabled:cursor-not-allowed disabled:opacity-70"
              disabled={!mode.enabled || isSubmitting}
              onChange={(event) => setDraftValue(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={mode.placeholder}
              rows={1}
              value={draftValue}
            />
            <button
              className="flex h-12 w-[120px] shrink-0 items-center justify-center self-stretch bg-primary px-4 py-3 text-sm font-medium text-on-primary transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-70"
              disabled={!mode.enabled || isSubmitting || draftValue.trim().length === 0}
              onClick={() => void handleSubmit()}
              type="button"
            >
              {isSubmitting ? "提交中..." : "提交"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
