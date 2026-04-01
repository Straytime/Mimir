import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";

import { DeliveryActions } from "@/features/research/components/delivery-actions";
import { SessionStatusBar } from "@/features/research/components/session-status-bar";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makeDeliverySummary,
  makeResearchSessionState,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";
import { renderWithStore } from "@/tests/fixtures/render";

function createDeliveryStore() {
  return createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_new",
        taskToken: "secret_new",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "delivered",
          status: "awaiting_feedback",
          available_actions: ["download_markdown", "download_pdf", "submit_feedback"],
        }),
        delivery: makeDeliverySummary(),
      },
    }),
  );
}

test("does not render '开始新研究' inside DeliveryActions after delivery", () => {
  const store = createDeliveryStore();

  renderWithStore(<DeliveryActions />, { store });

  expect(
    screen.queryByRole("button", { name: "开始新研究" }),
  ).not.toBeInTheDocument();
});

test("moves the new research action to SessionStatusBar and uses reset there", async () => {
  const user = userEvent.setup();
  const store = createDeliveryStore();
  const resetSpy = vi.fn();
  const disconnectTask = vi.fn();

  store.setState((state) => ({
    ...state,
    reset: resetSpy,
  }));

  renderWithStore(
    <>
      <SessionStatusBar />
      <DeliveryActions />
    </>,
    {
      runtime: {
        taskApiClient: {
          createTask: vi.fn(),
          getTaskDetail: vi.fn(),
          submitClarification: vi.fn(),
          submitFeedback: vi.fn(),
          sendHeartbeat: vi.fn(),
          disconnectTask,
        },
      },
      store,
    },
  );

  expect(
    screen.queryByRole("button", { name: "开始新研究" }),
  ).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "新研究" }));

  expect(resetSpy).toHaveBeenCalledTimes(1);
  expect(disconnectTask).not.toHaveBeenCalled();
});
