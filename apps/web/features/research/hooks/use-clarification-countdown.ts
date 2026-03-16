"use client";

import { useEffect, useEffectEvent } from "react";

import { useResearchSessionStore } from "../providers/research-workspace-providers";
import { selectCanSubmitClarification } from "../store/selectors";
import { useClarificationSubmit } from "./use-clarification-submit";

export function useClarificationCountdown() {
  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);
  const deadlineAt = useResearchSessionStore(
    (state) => state.ui.clarificationCountdownDeadlineAt,
  );
  const questionSet = useResearchSessionStore((state) => state.stream.questionSet);
  const pendingAction = useResearchSessionStore((state) => state.ui.pendingAction);
  const canSubmitClarification = useResearchSessionStore(
    selectCanSubmitClarification,
  );
  const submitClarification = useClarificationSubmit();
  const handleTimeout = useEffectEvent(() => {
    void submitClarification({
      submittedByTimeout: true,
    });
  });

  useEffect(() => {
    if (
      snapshot === null ||
      snapshot.phase !== "clarifying" ||
      snapshot.clarification_mode !== "options" ||
      deadlineAt === null ||
      questionSet === null ||
      !canSubmitClarification ||
      pendingAction === "submitting_clarification"
    ) {
      return;
    }

    const timeoutMs = new Date(deadlineAt).getTime() - Date.now();

    if (timeoutMs <= 0) {
      handleTimeout();
      return;
    }

    const timer = setTimeout(() => {
      handleTimeout();
    }, timeoutMs);

    return () => {
      clearTimeout(timer);
    };
  }, [
    canSubmitClarification,
    deadlineAt,
    pendingAction,
    questionSet,
    snapshot,
    handleTimeout,
  ]);
}
