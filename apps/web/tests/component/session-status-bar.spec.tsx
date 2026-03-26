import { act, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { SessionStatusBar } from "@/features/research/components/session-status-bar";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makePhaseChangedEvent,
  makeResearchSessionState,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";
import { renderWithStore } from "@/tests/fixtures/render";

test("shows SSE state, phase label, and disconnect button in the status bar", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        sseState: "open",
        taskId: "tsk_stage0",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "clarifying",
          status: "running",
        }),
      },
    }),
  );

  renderWithStore(<SessionStatusBar />, { store });

  expect(screen.getByText("已连接")).toBeInTheDocument();
  expect(screen.getByText("等待澄清")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "终止任务" })).toBeInTheDocument();

  act(() => {
    store.getState().applyEvent(
      makePhaseChangedEvent({
        seq: 5,
        timestamp: "2026-03-23T10:05:00+08:00",
        payload: {
          from_phase: "clarifying",
          to_phase: "analyzing_requirement",
          status: "running",
        },
      }),
    );
  });

  expect(screen.getByText("正在分析需求")).toBeInTheDocument();
});

test("does not expose revision transition badges in the status bar", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        sseState: "open",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "delivered",
          status: "awaiting_feedback",
        }),
      },
      ui: {
        revisionTransition: {
          status: "waiting_next_revision",
          pendingRevisionId: "rev_stage1",
          pendingRevisionNumber: 2,
        },
      },
    }),
  );

  renderWithStore(<SessionStatusBar />, { store });

  expect(screen.queryByText("Revision")).not.toBeInTheDocument();
  expect(screen.queryByText(/等待第 2 轮/)).not.toBeInTheDocument();
});
