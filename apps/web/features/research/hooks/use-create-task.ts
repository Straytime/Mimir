"use client";

import { isValidationErrorItemArray, TaskApiClientError } from "@/lib/api/task-api-client";

import { useResearchRuntime, useResearchSessionStore } from "../providers/research-workspace-providers";

function getClientTimezone() {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
}

function getClientLocale() {
  return navigator.language || "zh-CN";
}

function formatRetryAfterLabel(retryAfterSeconds: number | null) {
  if (retryAfterSeconds === null || retryAfterSeconds <= 0) {
    return null;
  }

  const hours = Math.floor(retryAfterSeconds / 3600);
  const minutes = Math.floor((retryAfterSeconds % 3600) / 60);
  const seconds = retryAfterSeconds % 60;
  const parts: string[] = [];

  if (hours > 0) {
    parts.push(`${hours}小时`);
  }
  if (minutes > 0) {
    parts.push(`${minutes}分钟`);
  }
  if (parts.length === 0 && seconds > 0) {
    parts.push(`${seconds}秒`);
  }

  return parts.length > 0 ? `约 ${parts.join("")} 后可再次创建。` : null;
}

function getInitialQueryValidationMessage(error: TaskApiClientError) {
  const validationItems = error.detail.errors;

  if (!isValidationErrorItemArray(validationItems)) {
    return error.message;
  }

  const initialQueryError = validationItems.find((item) => {
    return item.loc[0] === "body" && item.loc[1] === "initial_query";
  });

  return initialQueryError?.msg ?? error.message;
}

export function useCreateTask() {
  const initialPromptDraft = useResearchSessionStore(
    (state) => state.ui.initialPromptDraft,
  );
  const clarificationModeDraft = useResearchSessionStore(
    (state) => state.ui.createTask.clarificationModeDraft,
  );
  const setPendingAction = useResearchSessionStore(
    (state) => state.setPendingAction,
  );
  const setCreateTaskUiState = useResearchSessionStore(
    (state) => state.setCreateTaskUiState,
  );
  const bootstrapCreateTask = useResearchSessionStore(
    (state) => state.bootstrapCreateTask,
  );
  const { taskApiClient } = useResearchRuntime();

  return async function createTask() {
    const trimmedPrompt = initialPromptDraft.trim();

    if (trimmedPrompt.length === 0) {
      setCreateTaskUiState({
        errorCode: "validation_error",
        initialQueryError: "请输入研究主题。",
        submitError: null,
        nextAvailableAt: null,
        retryAfterLabel: null,
      });
      return;
    }

    setCreateTaskUiState({
      errorCode: null,
      initialQueryError: null,
      submitError: null,
      nextAvailableAt: null,
      retryAfterLabel: null,
    });
    setPendingAction("creating_task");

    try {
      const result = await taskApiClient.createTask({
        initial_query: trimmedPrompt,
        config: {
          clarification_mode: clarificationModeDraft,
        },
        client: {
          timezone: getClientTimezone(),
          locale: getClientLocale(),
        },
      });

      bootstrapCreateTask({
        response: result.response,
        requestId: result.requestId,
      });
    } catch (error) {
      if (error instanceof TaskApiClientError) {
        if (error.code === "validation_error") {
          setCreateTaskUiState({
            errorCode: "validation_error",
            initialQueryError: getInitialQueryValidationMessage(error),
            submitError: null,
            nextAvailableAt: null,
            retryAfterLabel: null,
          });
        } else if (error.code === "resource_busy") {
          setCreateTaskUiState({
            errorCode: "resource_busy",
            initialQueryError: null,
            submitError: error.message,
            nextAvailableAt: null,
            retryAfterLabel: null,
          });
        } else if (error.code === "ip_quota_exceeded") {
          setCreateTaskUiState({
            errorCode: "ip_quota_exceeded",
            initialQueryError: null,
            submitError: error.message,
            nextAvailableAt:
              typeof error.detail.next_available_at === "string"
                ? error.detail.next_available_at
                : null,
            retryAfterLabel: formatRetryAfterLabel(error.retryAfterSeconds),
          });
        } else {
          setCreateTaskUiState({
            errorCode: "unknown",
            initialQueryError: null,
            submitError: error.message,
            nextAvailableAt: null,
            retryAfterLabel: null,
          });
        }
      } else {
        setCreateTaskUiState({
          errorCode: "unknown",
          initialQueryError: null,
          submitError: "创建任务失败，请稍后重试。",
          nextAvailableAt: null,
          retryAfterLabel: null,
        });
      }
    } finally {
      setPendingAction(null);
    }
  };
}
