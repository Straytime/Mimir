import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";

import { ResearchInputPanel } from "@/features/research/components/research-input-panel";
import { makeCreateTaskResponse } from "@/tests/fixtures/builders";
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
