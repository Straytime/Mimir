import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { ResearchPageClient } from "@/features/research/components/research-page-client";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makeArtifactSummary,
  makeDeliverySummary,
  makeResearchSessionState,
  makeResearchOutline,
  makeRevisionSummary,
  makeTimelineItem,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";

test("renders the idle workspace shell before a task is created", () => {
  render(<ResearchPageClient />);

  expect(screen.getByRole("heading", { name: "AI 研究工作台" })).toBeInTheDocument();
  expect(screen.getByPlaceholderText("输入你的研究主题...")).toBeInTheDocument();
});

test("renders the clarification copy and keeps unstarted cards hidden", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        sseState: "open",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "clarifying",
          status: "running",
        }),
      },
      stream: {
        clarificationText: "为了更好地理解需求，请先确认几个问题。",
      },
    }),
  );

  render(<ResearchPageClient store={store} />);

  expect(
    screen.getByText("在开始之前，有一些问题需要你的反馈"),
  ).toBeInTheDocument();
  expect(screen.getByText("澄清详情")).toBeInTheDocument();
  expect(screen.queryByText("Requirement Summary")).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "时间线" })).not.toBeInTheDocument();
  expect(screen.queryByLabelText("报告大纲")).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "报告画布" })).not.toBeInTheDocument();
  expect(screen.queryByLabelText("图库")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("交付操作")).not.toBeInTheDocument();
});

test("renders stage-gated workspace cards once their content is ready", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        sseState: "open",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "writing_report",
          status: "running",
        }),
        currentRevision: makeRevisionSummary({
          requirement_detail: {
            research_goal: "分析中国 AI 搜索产品竞争格局",
            domain: "互联网 / AI 产品",
            requirement_details: "聚焦中国市场，偏商业分析，覆盖近两年变化。",
            output_format: "business_report",
            freshness_requirement: "high",
            language: "zh-CN",
          },
        }),
      },
      stream: {
        timeline: [
          makeTimelineItem({
            id: "t1",
            kind: "system",
            label: "正在规划研究路径",
            status: "completed",
          }),
        ],
        outline: makeResearchOutline(),
        outlineReady: true,
        reportMarkdown: "# 标题\n\n正文。",
        artifacts: [
          makeArtifactSummary({
            url: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAE/wJ/lL0uWQAAAABJRU5ErkJggg==",
          }),
        ],
      },
    }),
  );

  render(<ResearchPageClient store={store} />);

  expect(screen.getByText("需求摘要已生成")).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "时间线" })).toBeInTheDocument();
  expect(screen.getByLabelText("报告大纲")).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "报告画布" })).toBeInTheDocument();
  expect(screen.getByLabelText("图库")).toBeInTheDocument();
  expect(screen.queryByLabelText("交付操作")).not.toBeInTheDocument();
});

test("does not render the feedback composer even during task.awaiting_feedback", () => {
  const runningStore = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        eventsUrl: "/api/v1/tasks/tsk_stage0/events",
        heartbeatUrl: "/api/v1/tasks/tsk_stage0/heartbeat",
        disconnectUrl: "/api/v1/tasks/tsk_stage0/disconnect",
        sseState: "idle",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "delivered",
          status: "running",
          available_actions: [],
        }),
        delivery: makeDeliverySummary({
          artifact_count: 0,
          artifacts: [],
        }),
      },
    }),
  );

  const awaitingFeedbackStore = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        eventsUrl: "/api/v1/tasks/tsk_stage0/events",
        heartbeatUrl: "/api/v1/tasks/tsk_stage0/heartbeat",
        disconnectUrl: "/api/v1/tasks/tsk_stage0/disconnect",
        sseState: "idle",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "delivered",
          status: "awaiting_feedback",
          available_actions: [
            "submit_feedback",
            "download_markdown",
            "download_pdf",
          ],
        }),
        delivery: makeDeliverySummary({
          artifact_count: 0,
          artifacts: [],
        }),
      },
    }),
  );

  const { unmount } = render(<ResearchPageClient store={runningStore} />);

  expect(
    screen.queryByRole("textbox", { name: "反馈意见" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "提交反馈" }),
  ).not.toBeInTheDocument();

  unmount();
  render(<ResearchPageClient store={awaitingFeedbackStore} />);

  expect(
    screen.queryByRole("textbox", { name: "反馈意见" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "提交反馈" }),
  ).not.toBeInTheDocument();
});

test("does not render revision transition overlay when revision state exists", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        eventsUrl: "/api/v1/tasks/tsk_stage0/events",
        heartbeatUrl: "/api/v1/tasks/tsk_stage0/heartbeat",
        disconnectUrl: "/api/v1/tasks/tsk_stage0/disconnect",
        sseState: "idle",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "delivered",
          status: "awaiting_feedback",
          available_actions: [
            "submit_feedback",
            "download_markdown",
            "download_pdf",
          ],
        }),
        delivery: makeDeliverySummary({
          artifact_count: 0,
          artifacts: [],
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

  render(<ResearchPageClient store={store} />);

  expect(
    screen.queryByText("正在处理反馈并准备新一轮研究..."),
  ).not.toBeInTheDocument();
  expect(screen.queryByText(/等待第 2 轮/)).not.toBeInTheDocument();
});
