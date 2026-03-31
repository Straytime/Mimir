import { act, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { SessionStatusBar } from "@/features/research/components/session-status-bar";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makeCollectionCollectGroup,
  makeCollectionPlanRoundNode,
  makeCollectionTraceRoot,
  makePhaseChangedEvent,
  makeResearchSessionState,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";
import { renderWithStore } from "@/tests/fixtures/render";

test("shows SSE state, stage title, taskId, and disconnect button in the status bar", () => {
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
  expect(screen.getByText("taskId: tsk_stage0")).toBeInTheDocument();
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

test("shows taskId only in the lower row and omits description, collect progress, and analysisText", () => {
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
        analysisText: "用户希望研究量子计算的最新进展",
        collectionTrace: makeCollectionTraceRoot({
          nodes: [
            makeCollectionPlanRoundNode({
              collectGroups: [
                makeCollectionCollectGroup({
                  id: "collect_1",
                  toolCallId: "call_1",
                }),
                makeCollectionCollectGroup({
                  id: "collect_2",
                  toolCallId: "call_2",
                  collect: {
                    id: "collect_2_node",
                    kind: "collect",
                    label: "搜集子任务 2",
                    status: "running",
                    occurredAt: "2026-03-31T10:00:00+08:00",
                    entries: [],
                  },
                }),
              ],
            }),
          ],
        }),
      },
    }),
  );

  renderWithStore(<SessionStatusBar />, { store });

  expect(screen.getByText("正在规划研究路径")).toBeInTheDocument();
  expect(screen.getByText("taskId: tsk_stage0")).toBeInTheDocument();
  expect(
    screen.queryByText("规划器正在拆解搜集目标，规划后续子任务的执行路径。"),
  ).not.toBeInTheDocument();
  expect(screen.queryByText(/搜集进度:/)).not.toBeInTheDocument();
  expect(screen.queryByText(/正在分析需求：/)).not.toBeInTheDocument();
  expect(
    screen.queryByText(/用户希望研究量子计算的最新进展/),
  ).not.toBeInTheDocument();
});
