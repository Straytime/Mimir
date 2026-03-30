import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import { UnifiedInputBar } from "@/features/research/components/unified-input-bar";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makeResearchSessionState,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";
import { renderWithStore } from "@/tests/fixtures/render";

const mockCreateTask = vi.fn();
const mockSubmitClarification = vi.fn();

vi.mock("@/features/research/hooks/use-create-task", () => ({
  useCreateTask: () => mockCreateTask,
}));

vi.mock("@/features/research/hooks/use-clarification-submit", () => ({
  useClarificationSubmit: () => mockSubmitClarification,
}));

beforeEach(() => {
  mockCreateTask.mockClear();
  mockSubmitClarification.mockClear();
});

test("shows correct placeholder when no task exists (snapshot=null)", () => {
  const store = createResearchSessionStore();

  renderWithStore(<UnifiedInputBar />, { store });

  const textarea = screen.getByRole("textbox");
  expect(textarea).toBeEnabled();
  expect(textarea).toHaveAttribute("placeholder", "输入你的研究主题...");
});

test("shows correct placeholder in natural clarification mode", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "clarifying",
          status: "awaiting_user_input",
          clarification_mode: "natural",
          available_actions: ["submit_clarification"],
        }),
      },
    }),
  );

  renderWithStore(<UnifiedInputBar />, { store });

  const textarea = screen.getByRole("textbox");
  expect(textarea).toBeEnabled();
  expect(textarea).toHaveAttribute("placeholder", "输入澄清补充说明...");
});

test("disables textarea in options clarification mode", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "clarifying",
          status: "awaiting_user_input",
          clarification_mode: "options",
          available_actions: ["submit_clarification"],
        }),
      },
    }),
  );

  renderWithStore(<UnifiedInputBar />, { store });

  const textarea = screen.getByRole("textbox");
  expect(textarea).toBeDisabled();
  expect(textarea).toHaveAttribute(
    "placeholder",
    "选单澄清模式下请在上方选择选项",
  );
});

test("disables textarea when research is in progress (collecting phase)", () => {
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
        }),
      },
    }),
  );

  renderWithStore(<UnifiedInputBar />, { store });

  const textarea = screen.getByRole("textbox");
  expect(textarea).toBeDisabled();
  expect(textarea).toHaveAttribute("placeholder", "研究进行中...");
});

test("enables textarea when phase is delivered", () => {
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
          available_actions: ["submit_feedback", "download_markdown", "download_pdf"],
        }),
      },
    }),
  );

  renderWithStore(<UnifiedInputBar />, { store });

  const textarea = screen.getByRole("textbox");
  expect(textarea).toBeEnabled();
  expect(textarea.getAttribute("placeholder")).toContain("新的研究主题");
});

test("enables textarea when terminal reason is failed", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "writing_report",
          status: "failed",
        }),
      },
      ui: {
        terminalReason: "failed",
      },
    }),
  );

  renderWithStore(<UnifiedInputBar />, { store });

  const textarea = screen.getByRole("textbox");
  expect(textarea).toBeEnabled();
  expect(textarea.getAttribute("placeholder")).toContain("新的研究主题");
});

test("delivered submit triggers window.confirm and calls reset on confirm", async () => {
  const user = userEvent.setup();
  const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

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
          available_actions: ["submit_feedback"],
        }),
      },
    }),
  );

  renderWithStore(<UnifiedInputBar />, { store });

  const textarea = screen.getByRole("textbox");
  await user.type(textarea, "新主题内容");
  await user.keyboard("{Enter}");

  expect(confirmSpy).toHaveBeenCalledTimes(1);
  // After confirm, reset should have been called (store snapshot becomes null)
  // and createTask should be called
  expect(mockCreateTask).toHaveBeenCalledTimes(1);

  confirmSpy.mockRestore();
});

test("delivered submit does not call reset when confirm is cancelled", async () => {
  const user = userEvent.setup();
  const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);

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
          available_actions: ["submit_feedback"],
        }),
      },
    }),
  );

  renderWithStore(<UnifiedInputBar />, { store });

  const textarea = screen.getByRole("textbox");
  await user.type(textarea, "新主题内容");
  await user.keyboard("{Enter}");

  expect(confirmSpy).toHaveBeenCalledTimes(1);
  expect(mockCreateTask).not.toHaveBeenCalled();

  confirmSpy.mockRestore();
});

test("Enter key triggers submit, Shift+Enter does not", async () => {
  const user = userEvent.setup();

  const store = createResearchSessionStore();
  // snapshot is null by default, so initial mode

  renderWithStore(<UnifiedInputBar />, { store });

  const textarea = screen.getByRole("textbox");
  await user.type(textarea, "研究主题");

  // Shift+Enter should not submit
  await user.keyboard("{Shift>}{Enter}{/Shift}");
  expect(mockCreateTask).not.toHaveBeenCalled();

  // Enter should submit
  await user.keyboard("{Enter}");
  expect(mockCreateTask).toHaveBeenCalledTimes(1);
});
