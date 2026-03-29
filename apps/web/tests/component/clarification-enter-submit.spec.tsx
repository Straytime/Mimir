import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import { ClarificationActionPanel } from "@/features/research/components/clarification-panels";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makeResearchSessionState,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";
import { renderWithStore } from "@/tests/fixtures/render";

const mockSubmitClarification = vi.fn();

vi.mock("@/features/research/hooks/use-clarification-submit", () => ({
  useClarificationSubmit: () => mockSubmitClarification,
}));

beforeEach(() => {
  mockSubmitClarification.mockClear();
});

function createNaturalModeStore(overrides?: {
  canSubmit?: boolean;
  isSubmitting?: boolean;
  draft?: string;
}) {
  const canSubmit = overrides?.canSubmit ?? true;
  const isSubmitting = overrides?.isSubmitting ?? false;
  const draft = overrides?.draft ?? "补充说明内容";

  return createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        sseState: "open",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "clarifying",
          status: "awaiting_user_input",
          clarification_mode: "natural",
          available_actions: canSubmit ? ["submit_clarification"] : [],
        }),
      },
      ui: {
        clarificationDraft: draft,
        pendingAction: isSubmitting ? "submitting_clarification" : null,
      },
    }),
  );
}

test("natural mode: Enter key triggers submit", async () => {
  const store = createNaturalModeStore();
  renderWithStore(<ClarificationActionPanel />, { store });

  const textarea = screen.getByRole("textbox");
  textarea.focus();
  await userEvent.keyboard("{Enter}");

  expect(mockSubmitClarification).toHaveBeenCalledTimes(1);
});

test("natural mode: Shift+Enter does not trigger submit", async () => {
  const store = createNaturalModeStore();
  renderWithStore(<ClarificationActionPanel />, { store });

  const textarea = screen.getByRole("textbox");
  textarea.focus();
  await userEvent.keyboard("{Shift>}{Enter}{/Shift}");

  expect(mockSubmitClarification).not.toHaveBeenCalled();
});

test("natural mode: Enter does not trigger submit when textarea is disabled", async () => {
  const store = createNaturalModeStore({ canSubmit: false });
  renderWithStore(<ClarificationActionPanel />, { store });

  const textarea = screen.getByRole("textbox");
  // textarea is disabled, so we simulate keydown directly
  const event = new KeyboardEvent("keydown", {
    key: "Enter",
    bubbles: true,
  });
  textarea.dispatchEvent(event);

  expect(mockSubmitClarification).not.toHaveBeenCalled();
});
