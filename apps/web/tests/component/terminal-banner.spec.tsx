import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test } from "vitest";

import { TerminalBanner } from "@/features/research/components/terminal-banner";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makeResearchSessionState,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";
import { renderWithStore } from "@/tests/fixtures/render";

function createTerminalStore(terminalReason: "failed" | "terminated" | "expired") {
  return createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        sseState: "closed",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "delivered",
          status: terminalReason,
        }),
      },
      ui: {
        terminalReason,
      },
    }),
  );
}

test("renders banner with '开始新研究' button when terminalReason is 'failed'", () => {
  const store = createTerminalStore("failed");
  renderWithStore(<TerminalBanner />, { store });

  expect(screen.getByText("任务已失败，旧任务操作已禁用。")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "开始新研究" })).toBeInTheDocument();
});

test("renders banner with '开始新研究' button when terminalReason is 'terminated'", () => {
  const store = createTerminalStore("terminated");
  renderWithStore(<TerminalBanner />, { store });

  expect(screen.getByText("任务已终止，旧任务操作已禁用。")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "开始新研究" })).toBeInTheDocument();
});

test("renders banner with '开始新研究' button when terminalReason is 'expired'", () => {
  const store = createTerminalStore("expired");
  renderWithStore(<TerminalBanner />, { store });

  expect(screen.getByText("任务已过期，旧任务操作已禁用。")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "开始新研究" })).toBeInTheDocument();
});

test("clicking '开始新研究' resets store to idle state", async () => {
  const user = userEvent.setup();
  const store = createTerminalStore("failed");

  renderWithStore(<TerminalBanner />, { store });

  expect(store.getState().session.taskId).toBe("tsk_stage0");

  await user.click(screen.getByRole("button", { name: "开始新研究" }));

  expect(store.getState().session.taskId).toBeNull();
  expect(store.getState().remote.snapshot).toBeNull();
  expect(store.getState().ui.terminalReason).toBeNull();
});

test("does not render banner when terminalReason is null", () => {
  const store = createResearchSessionStore();
  renderWithStore(<TerminalBanner />, { store });

  expect(screen.queryByText("任务已失败")).not.toBeInTheDocument();
  expect(screen.queryByText("任务已终止")).not.toBeInTheDocument();
  expect(screen.queryByText("任务已过期")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "开始新研究" })).not.toBeInTheDocument();
});
