import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";

import { DeliveryActions } from "@/features/research/components/delivery-actions";
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

test("renders '开始新研究' button when phase is delivered", () => {
  const store = createDeliveryStore();

  renderWithStore(<DeliveryActions />, { store });

  expect(screen.getByRole("button", { name: "开始新研究" })).toBeInTheDocument();
});

test("calls reset when '开始新研究' button is clicked", async () => {
  const user = userEvent.setup();
  const store = createDeliveryStore();
  const resetSpy = vi.fn();

  store.setState((state) => ({
    ...state,
    reset: resetSpy,
  }));

  renderWithStore(<DeliveryActions />, { store });

  await user.click(screen.getByRole("button", { name: "开始新研究" }));

  expect(resetSpy).toHaveBeenCalledTimes(1);
});
