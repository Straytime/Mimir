import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";

import { ResearchInputPanel } from "@/features/research/components/research-input-panel";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makeCreateTaskResponse,
  makeResearchSessionState,
} from "@/tests/fixtures/builders";
import { renderWithStore } from "@/tests/fixtures/render";

test("ResearchInputPanel enforces the 500-character limit and submits on Enter", async () => {
  const user = userEvent.setup();
  const createTask = vi.fn().mockResolvedValue({
    response: makeCreateTaskResponse(),
    requestId: "req_stage2",
    traceId: "trc_stage2",
  });

  renderWithStore(<ResearchInputPanel />, {
    runtime: {
      taskApiClient: {
        createTask,
        getTaskDetail: vi.fn(),
        submitClarification: vi.fn(),
        submitFeedback: vi.fn(),
        sendHeartbeat: vi.fn(),
        disconnectTask: vi.fn(),
      },
    },
  });

  const textarea = screen.getByLabelText("研究主题");
  await user.type(textarea, "x".repeat(550));

  expect(textarea).toHaveValue("x".repeat(500));

  await user.keyboard("{Enter}");

  await waitFor(() => {
    expect(createTask).toHaveBeenCalledTimes(1);
  });
});

test("shows specialized copy when createTaskUi.errorCode is 'resource_busy'", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      ui: {
        createTask: {
          clarificationModeDraft: "natural",
          initialQueryError: null,
          errorCode: "resource_busy",
          submitError: "当前系统正处理另一项研究，请稍后重试。",
          nextAvailableAt: null,
          retryAfterLabel: null,
        },
      },
    }),
  );

  renderWithStore(<ResearchInputPanel />, { store });

  expect(
    screen.getByText("当前已有一个研究任务正在进行中。请等待其完成或终止后再创建新任务。"),
  ).toBeInTheDocument();
});

test("shows original submitError for non-resource_busy error codes", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      ui: {
        createTask: {
          clarificationModeDraft: "natural",
          initialQueryError: null,
          errorCode: "unknown",
          submitError: "创建任务失败，请稍后重试。",
          nextAvailableAt: null,
          retryAfterLabel: null,
        },
      },
    }),
  );

  renderWithStore(<ResearchInputPanel />, { store });

  expect(screen.getByText("创建任务失败，请稍后重试。")).toBeInTheDocument();
});
