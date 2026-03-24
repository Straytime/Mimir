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

test("shows recent server activity instead of recent heartbeat and updates on any new event", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        sseState: "open",
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

  expect(screen.getByText(/最近服务端活动：尚未收到/)).toBeInTheDocument();
  expect(screen.queryByText(/最近心跳/)).not.toBeInTheDocument();

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

  expect(screen.getByText(/2026-03-23T10:05:00\+08:00/)).toBeInTheDocument();
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
