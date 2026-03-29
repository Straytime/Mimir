import { screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { DeliveryActions } from "@/features/research/components/delivery-actions";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makeDeliverySummary,
  makeResearchSessionState,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";
import { renderWithStore } from "@/tests/fixtures/render";

test("does not render when phase is collecting", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "collecting",
          status: "running",
          available_actions: [],
        }),
        delivery: makeDeliverySummary(),
      },
    }),
  );

  renderWithStore(<DeliveryActions />, { store });

  expect(screen.queryByLabelText("交付操作")).not.toBeInTheDocument();
});

test("renders when phase is delivered", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
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

  renderWithStore(<DeliveryActions />, { store });

  expect(screen.getByLabelText("交付操作")).toBeInTheDocument();
});
