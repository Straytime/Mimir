"use client";

import { isValidationErrorItemArray, TaskApiClientError } from "@/lib/api/task-api-client";
import type { ClarificationQuestion } from "@/lib/contracts";

import { useResearchRuntime, useResearchSessionStore } from "../providers/research-workspace-providers";
import { selectCanSubmitClarification } from "../store/selectors";

function resolveSelectedOption(
  question: ClarificationQuestion,
  selectedOptionId: string | null,
) {
  const preferredOptionId = selectedOptionId ?? "o_auto";

  return (
    question.options.find((option) => option.option_id === preferredOptionId) ??
    question.options.find((option) => option.option_id === "o_auto") ??
    question.options[0]
  );
}

function getClarificationValidationMessage(error: TaskApiClientError) {
  const validationItems = error.detail.errors;

  if (!isValidationErrorItemArray(validationItems)) {
    return error.message;
  }

  const clarificationError = validationItems.find((item) => {
    return (
      item.loc[0] === "body" &&
      (item.loc[1] === "answer_text" || item.loc[1] === "answers")
    );
  });

  return clarificationError?.msg ?? error.message;
}

export function useClarificationSubmit() {
  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);
  const taskId = useResearchSessionStore((state) => state.session.taskId);
  const taskToken = useResearchSessionStore((state) => state.session.taskToken);
  const clarificationDraft = useResearchSessionStore(
    (state) => state.ui.clarificationDraft,
  );
  const optionAnswers = useResearchSessionStore((state) => state.ui.optionAnswers);
  const questionSet = useResearchSessionStore((state) => state.stream.questionSet);
  const pendingAction = useResearchSessionStore((state) => state.ui.pendingAction);
  const canSubmitClarification = useResearchSessionStore(
    selectCanSubmitClarification,
  );
  const setPendingAction = useResearchSessionStore((state) => state.setPendingAction);
  const setClarificationDraft = useResearchSessionStore(
    (state) => state.setClarificationDraft,
  );
  const setClarificationFieldError = useResearchSessionStore(
    (state) => state.setClarificationFieldError,
  );
  const setClarificationSubmitError = useResearchSessionStore(
    (state) => state.setClarificationSubmitError,
  );
  const clearClarificationCountdown = useResearchSessionStore(
    (state) => state.clearClarificationCountdown,
  );
  const mergeRemoteSnapshot = useResearchSessionStore(
    (state) => state.mergeRemoteSnapshot,
  );
  const { taskApiClient } = useResearchRuntime();

  return async function submitClarification(options?: {
    submittedByTimeout?: boolean;
  }) {
    if (
      snapshot === null ||
      taskId === null ||
      taskToken === null ||
      !canSubmitClarification ||
      pendingAction === "submitting_clarification"
    ) {
      return;
    }

    setClarificationFieldError(null);
    setClarificationSubmitError(null);

    if (snapshot.clarification_mode === "natural") {
      const trimmedDraft = clarificationDraft.trim();

      if (trimmedDraft.length === 0) {
        setClarificationFieldError("请输入澄清补充说明。");
        return;
      }

      setPendingAction("submitting_clarification");
      clearClarificationCountdown();

      try {
        const result = await taskApiClient.submitClarification({
          taskId,
          token: taskToken,
          request: {
            mode: "natural",
            answer_text: trimmedDraft,
          },
        });

        mergeRemoteSnapshot(result.snapshot);
        setClarificationDraft("");
      } catch (error) {
        if (error instanceof TaskApiClientError) {
          if (error.code === "validation_error") {
            setClarificationFieldError(getClarificationValidationMessage(error));
          } else {
            setClarificationSubmitError(error.message);
          }
        } else {
          setClarificationSubmitError("提交澄清失败，请稍后重试。");
        }
      } finally {
        setPendingAction(null);
      }

      return;
    }

    if (questionSet === null) {
      return;
    }

    const answers = questionSet.questions
      .map((question) => {
        const option = resolveSelectedOption(
          question,
          optionAnswers[question.question_id] ?? null,
        );

        if (option === undefined) {
          return null;
        }

        return {
          question_id: question.question_id,
          selected_option_id: option.option_id,
          selected_label: option.label,
        };
      })
      .filter((answer) => answer !== null);

    setPendingAction("submitting_clarification");
    clearClarificationCountdown();

    try {
      const result = await taskApiClient.submitClarification({
        taskId,
        token: taskToken,
        request: {
          mode: "options",
          submitted_by_timeout: options?.submittedByTimeout ?? false,
          answers,
        },
      });

      mergeRemoteSnapshot(result.snapshot);
    } catch (error) {
      if (error instanceof TaskApiClientError) {
        if (error.code === "validation_error") {
          setClarificationFieldError(getClarificationValidationMessage(error));
        } else {
          setClarificationSubmitError(error.message);
        }
      } else {
        setClarificationSubmitError("提交澄清失败，请稍后重试。");
      }
    } finally {
      setPendingAction(null);
    }
  };
}
