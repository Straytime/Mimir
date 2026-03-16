"use client";

import { useEffect, useRef } from "react";

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
  const submitClarificationRef = useRef(submitClarification);

  useEffect(() => {
    submitClarificationRef.current = submitClarification;
  }, [submitClarification]);

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
      void submitClarificationRef.current({
        submittedByTimeout: true,
      });
      return;
    }

    const timer = setTimeout(() => {
      void submitClarificationRef.current({
        submittedByTimeout: true,
      });
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
  ]);
}
