"use client";

import {
  isValidationErrorItemArray,
  TaskApiClientError,
} from "@/lib/api/task-api-client";

import {
  useResearchRuntime,
  useResearchSessionStore,
} from "../providers/research-workspace-providers";
import { selectCanSubmitFeedback } from "../store/selectors";

function getFeedbackValidationMessage(error: TaskApiClientError) {
  const validationItems = error.detail.errors;

  if (!isValidationErrorItemArray(validationItems)) {
    return error.message;
  }

  const feedbackError = validationItems.find((item) => {
    return item.loc[0] === "body" && item.loc[1] === "feedback_text";
  });

  return feedbackError?.msg ?? error.message;
}

export function useFeedbackSubmit() {
  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);
  const taskId = useResearchSessionStore((state) => state.session.taskId);
  const taskToken = useResearchSessionStore((state) => state.session.taskToken);
  const feedbackDraft = useResearchSessionStore((state) => state.ui.feedbackDraft);
  const pendingAction = useResearchSessionStore((state) => state.ui.pendingAction);
  const canSubmitFeedback = useResearchSessionStore(selectCanSubmitFeedback);
  const setPendingAction = useResearchSessionStore((state) => state.setPendingAction);
  const setFeedbackDraft = useResearchSessionStore((state) => state.setFeedbackDraft);
  const setFeedbackFieldError = useResearchSessionStore(
    (state) => state.setFeedbackFieldError,
  );
  const setFeedbackSubmitError = useResearchSessionStore(
    (state) => state.setFeedbackSubmitError,
  );
  const startRevisionTransition = useResearchSessionStore(
    (state) => state.startRevisionTransition,
  );
  const { taskApiClient } = useResearchRuntime();

  return async function submitFeedback() {
    if (
      snapshot === null ||
      taskId === null ||
      taskToken === null ||
      !canSubmitFeedback ||
      pendingAction === "submitting_feedback"
    ) {
      return;
    }

    const trimmedDraft = feedbackDraft.trim();

    setFeedbackFieldError(null);
    setFeedbackSubmitError(null);

    if (trimmedDraft.length === 0) {
      setFeedbackFieldError("请输入反馈意见。");
      return;
    }

    setPendingAction("submitting_feedback");

    try {
      const result = await taskApiClient.submitFeedback({
        taskId,
        token: taskToken,
        request: {
          feedback_text: trimmedDraft,
        },
      });

      setFeedbackDraft("");
      startRevisionTransition({
        pendingRevisionId: result.revision_id,
        pendingRevisionNumber: result.revision_number,
      });
    } catch (error) {
      if (error instanceof TaskApiClientError) {
        if (error.code === "validation_error") {
          setFeedbackFieldError(getFeedbackValidationMessage(error));
        } else {
          setFeedbackSubmitError(error.message);
        }
      } else {
        setFeedbackSubmitError("提交反馈失败，请稍后重试。");
      }
    } finally {
      setPendingAction(null);
    }
  };
}
