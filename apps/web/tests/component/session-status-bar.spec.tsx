import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";

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

test("shows SSE state, stage chip, weak taskId, and disconnect button in the status bar", () => {
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
  expect(screen.getByText("Stage 01 / Clarifying")).toBeInTheDocument();
  expect(screen.getByText("tsk_stage0")).toBeInTheDocument();
  expect(screen.queryByText(/taskId:/)).not.toBeInTheDocument();
  expect(
    document.querySelector('[data-research-stage-ellipsis="true"]'),
  ).not.toBeNull();
  expect(
    screen.queryByText("等待你的澄清反馈"),
  ).not.toBeInTheDocument();
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

  expect(screen.getByText("Stage 02 / Analyzing")).toBeInTheDocument();
  expect(
    screen.queryByText("正在分析你的研究需求"),
  ).not.toBeInTheDocument();
});

test("renders in-progress stage chip with looping ellipsis and keeps taskId visually weak", () => {
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
    }),
  );

  renderWithStore(<SessionStatusBar />, { store });

  const stageChipText = screen.getByText("Stage 04 / Collecting");
  const stageChip = stageChipText.closest('[data-research-stage-chip="true"]');
  const taskIdMeta = screen.getByText("tsk_stage0");

  expect(stageChip).toHaveAttribute("data-research-stage-chip", "true");
  expect(stageChip).toHaveClass("text-surface-tint");
  expect(
    document.querySelector('[data-research-stage-ellipsis="true"]'),
  ).not.toBeNull();
  expect(
    screen.queryByText("正在搜索与读取资料"),
  ).not.toBeInTheDocument();
  expect(taskIdMeta).toHaveAttribute("data-research-task-meta", "true");
  expect(taskIdMeta).toHaveClass("text-[10px]", "text-tertiary/80");
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

test("uses the writing stage chip and keeps the large Chinese title hidden during writing_report", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        sseState: "open",
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        disconnectUrl: "/api/v1/tasks/tsk_stage0/disconnect",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "writing_report",
          status: "running",
        }),
      },
    }),
  );

  renderWithStore(<SessionStatusBar />, { store });

  expect(screen.getByText("Stage 08 / Writing")).toBeInTheDocument();
  expect(
    document.querySelector('[data-research-stage-ellipsis="true"]'),
  ).not.toBeNull();
  expect(screen.queryByText("正在生成研究内容")).not.toBeInTheDocument();
  expect(
    screen.queryByText("正在撰写报告与生成配图"),
  ).not.toBeInTheDocument();
});

test("keeps disconnect behavior unchanged before delivery", async () => {
  const user = userEvent.setup();
  const disconnectTask = vi.fn().mockResolvedValue({
    accepted: true,
    requestId: "req_disconnect",
    traceId: "trc_disconnect",
  });
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        sseState: "open",
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        disconnectUrl: "/api/v1/tasks/tsk_stage0/disconnect",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "collecting",
          status: "running",
        }),
      },
    }),
  );

  renderWithStore(<SessionStatusBar />, {
    runtime: {
      taskApiClient: {
        createTask: vi.fn(),
        getTaskDetail: vi.fn(),
        submitClarification: vi.fn(),
        submitFeedback: vi.fn(),
        sendHeartbeat: vi.fn(),
        disconnectTask,
      },
    },
    store,
  });

  await user.click(screen.getByRole("button", { name: "终止任务" }));

  expect(disconnectTask).toHaveBeenCalledWith({
    url: "/api/v1/tasks/tsk_stage0/disconnect",
    token: "secret_stage0",
    reason: "client_manual_abort",
  });
});

test("switches the delivered action button to '新研究' and resets without disconnecting", async () => {
  const user = userEvent.setup();
  const disconnectTask = vi.fn();
  const resetSpy = vi.fn();
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        sseState: "open",
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        disconnectUrl: "/api/v1/tasks/tsk_stage0/disconnect",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "delivered",
          status: "awaiting_feedback",
          available_actions: ["download_markdown", "download_pdf"],
        }),
      },
    }),
  );

  store.setState((state) => ({
    ...state,
    reset: resetSpy,
  }));

  renderWithStore(<SessionStatusBar />, {
    runtime: {
      taskApiClient: {
        createTask: vi.fn(),
        getTaskDetail: vi.fn(),
        submitClarification: vi.fn(),
        submitFeedback: vi.fn(),
        sendHeartbeat: vi.fn(),
        disconnectTask,
      },
    },
    store,
  });

  expect(screen.getByText("Stage 09 / Delivered")).toBeInTheDocument();
  expect(
    document.querySelector('[data-research-stage-ellipsis="true"]'),
  ).toBeNull();
  expect(
    screen.queryByText("报告已完成并进入交付阶段"),
  ).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "新研究" })).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "终止任务" }),
  ).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "新研究" }));

  expect(resetSpy).toHaveBeenCalledTimes(1);
  expect(disconnectTask).not.toHaveBeenCalled();
});

test("keeps taskId present in the thin header and omits description, collect progress, and analysisText", () => {
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

  expect(screen.getByText("Stage 03 / Planning")).toBeInTheDocument();
  expect(screen.getByText("tsk_stage0")).toBeInTheDocument();
  expect(screen.queryByText(/taskId:/)).not.toBeInTheDocument();
  expect(
    screen.queryByText("正在规划研究路径"),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByText("规划器正在拆解搜集目标，规划后续子任务的执行路径。"),
  ).not.toBeInTheDocument();
  expect(screen.queryByText(/搜集进度:/)).not.toBeInTheDocument();
  expect(screen.queryByText(/正在分析需求：/)).not.toBeInTheDocument();
  expect(
    screen.queryByText(/用户希望研究量子计算的最新进展/),
  ).not.toBeInTheDocument();
});

test("does not render the looping ellipsis for delivered or terminal states", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        sseState: "closed",
        taskId: "tsk_stage0",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "delivered",
          status: "expired",
        }),
      },
      ui: {
        terminalReason: "expired",
      },
    }),
  );

  renderWithStore(<SessionStatusBar />, { store });

  expect(screen.getByText("Terminal / Expired")).toBeInTheDocument();
  expect(
    document.querySelector('[data-research-stage-ellipsis="true"]'),
  ).toBeNull();
});
