import { screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { SessionStatusBar } from "@/features/research/components/session-status-bar";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makeResearchSessionState,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";
import { renderWithStore } from "@/tests/fixtures/render";

test("displays phase label when terminalReason is null", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        sseState: "open",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "collecting",
          status: "running",
        }),
      },
      ui: {
        terminalReason: null,
      },
    }),
  );

  renderWithStore(<SessionStatusBar />, { store });

  expect(screen.getByText("正在搜索与读取资料")).toBeInTheDocument();
});

test('displays "任务已失败" when terminalReason is "failed"', () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        sseState: "closed",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "collecting",
          status: "failed",
          available_actions: [],
        }),
      },
      ui: {
        terminalReason: "failed",
      },
    }),
  );

  renderWithStore(<SessionStatusBar />, { store });

  expect(screen.getByText("任务已失败")).toBeInTheDocument();
  expect(screen.queryByText("正在搜索与读取资料")).not.toBeInTheDocument();
});

test('displays "任务已终止" when terminalReason is "terminated"', () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        sseState: "closed",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "writing_report",
          status: "terminated",
          available_actions: [],
        }),
      },
      ui: {
        terminalReason: "terminated",
      },
    }),
  );

  renderWithStore(<SessionStatusBar />, { store });

  expect(screen.getByText("任务已终止")).toBeInTheDocument();
  expect(screen.queryByText("正在撰写报告")).not.toBeInTheDocument();
});

test('displays "任务已过期" when terminalReason is "expired"', () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        sseState: "closed",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "delivered",
          status: "expired",
          available_actions: [],
        }),
      },
      ui: {
        terminalReason: "expired",
      },
    }),
  );

  renderWithStore(<SessionStatusBar />, { store });

  expect(screen.getByText("任务已过期")).toBeInTheDocument();
  expect(screen.queryByText("已进入交付阶段")).not.toBeInTheDocument();
});
