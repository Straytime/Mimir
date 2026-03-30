import { act, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { SessionStatusBar } from "@/features/research/components/session-status-bar";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makePhaseChangedEvent,
  makeResearchSessionState,
  makeTaskSnapshot,
  makeTimelineItem,
} from "@/tests/fixtures/builders";
import { renderWithStore } from "@/tests/fixtures/render";

test("shows SSE state, stage title, and disconnect button in the status bar", () => {
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
  // clarifying falls through to default title in getStageStatusCopy
  expect(screen.getByText("工作台已接管当前任务")).toBeInTheDocument();
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

  expect(screen.getByText("正在分析你的研究需求")).toBeInTheDocument();
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

test("shows description in sub-row for active phase", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        sseState: "open",
        taskId: "tsk_stage0",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "planning_collection",
          status: "running",
        }),
      },
    }),
  );

  renderWithStore(<SessionStatusBar />, { store });

  expect(
    screen.getByText("规划器正在拆解搜集目标，规划后续子任务的执行路径。"),
  ).toBeInTheDocument();
});

test("shows collect progress during collecting phase", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        sseState: "open",
        taskId: "tsk_stage0",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "collecting",
          status: "running",
        }),
      },
      stream: {
        timeline: [
          makeTimelineItem({ id: "t1", kind: "collect", status: "completed" }),
          makeTimelineItem({ id: "t2", kind: "collect", status: "completed" }),
          makeTimelineItem({ id: "t3", kind: "collect", status: "completed" }),
          makeTimelineItem({ id: "t4", kind: "collect", status: "running" }),
          makeTimelineItem({ id: "t5", kind: "collect", status: "running" }),
        ],
      },
    }),
  );

  renderWithStore(<SessionStatusBar />, { store });

  expect(screen.getByText(/03\/05/)).toBeInTheDocument();
});

test("does not show collect progress during non-collecting phase", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        sseState: "open",
        taskId: "tsk_stage0",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "planning_collection",
          status: "running",
        }),
      },
      stream: {
        timeline: [
          makeTimelineItem({ id: "t1", kind: "collect", status: "completed" }),
        ],
      },
    }),
  );

  renderWithStore(<SessionStatusBar />, { store });

  expect(screen.queryByText(/\/01/)).not.toBeInTheDocument();
});

test("shows analysisText when non-empty", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        sseState: "open",
        taskId: "tsk_stage0",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "analyzing_requirement",
          status: "running",
        }),
      },
      stream: {
        analysisText: "用户希望研究量子计算的最新进展",
      },
    }),
  );

  renderWithStore(<SessionStatusBar />, { store });

  expect(screen.getByText(/正在分析需求：/)).toBeInTheDocument();
  expect(
    screen.getByText(/用户希望研究量子计算的最新进展/),
  ).toBeInTheDocument();
});

test("shows feedback prefix for analysisText during processing_feedback phase", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        sseState: "open",
        taskId: "tsk_stage0",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "processing_feedback",
          status: "running",
        }),
      },
      stream: {
        analysisText: "用户要求补充更多细节",
      },
    }),
  );

  renderWithStore(<SessionStatusBar />, { store });

  expect(screen.getByText(/正在处理反馈：/)).toBeInTheDocument();
  expect(screen.getByText(/用户要求补充更多细节/)).toBeInTheDocument();
});
