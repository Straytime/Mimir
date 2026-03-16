import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test } from "vitest";

import { ResearchPageClient } from "@/features/research/components/research-page-client";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makeDeliverySummary,
  makeResearchSessionState,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";

test("renders the idle workspace shell before a task is created", () => {
  render(<ResearchPageClient />);

  expect(screen.getByRole("heading", { name: "AI 研究工作台" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "输入研究主题" })).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "从空态进入研究工作台" }),
  ).toBeInTheDocument();
});

test("only renders the feedback composer after task.awaiting_feedback", () => {
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

  expect(screen.getByRole("textbox", { name: "反馈意见" })).toHaveAttribute(
    "maxlength",
    "1000",
  );
  expect(screen.getByRole("button", { name: "提交反馈" })).toBeDisabled();
});

test("replaces the mobile report segment with clarification detail during clarifying phase", () => {
  const originalMatchMedia = window.matchMedia;

  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: (query: string) => ({
      matches: query === "(max-width: 767px)",
      media: query,
      onchange: null,
      addListener() {},
      removeListener() {},
      addEventListener() {},
      removeEventListener() {},
      dispatchEvent() {
        return false;
      },
    }),
  });

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
          phase: "clarifying",
          status: "awaiting_user_input",
          available_actions: ["submit_clarification"],
        }),
      },
    }),
  );

  try {
    render(<ResearchPageClient store={store} />);

    expect(screen.getByRole("button", { name: "操作" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "澄清详情" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "进度" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "报告" })).not.toBeInTheDocument();
  } finally {
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      writable: true,
      value: originalMatchMedia,
    });
  }
});

test("supports mobile 操作 / 报告 / 进度 switching with accessible pressed state", async () => {
  const user = userEvent.setup();
  const originalMatchMedia = window.matchMedia;

  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: (query: string) => ({
      matches: query === "(max-width: 767px)",
      media: query,
      onchange: null,
      addListener() {},
      removeListener() {},
      addEventListener() {},
      removeEventListener() {},
      dispatchEvent() {
        return false;
      },
    }),
  });

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
      stream: {
        reportMarkdown: "# 报告标题\n\n正文第一段。",
      },
    }),
  );

  try {
    render(<ResearchPageClient store={store} />);

    const controlButton = screen.getByRole("button", { name: "操作" });
    const reportButton = screen.getByRole("button", { name: "报告" });
    const progressButton = screen.getByRole("button", { name: "进度" });

    expect(controlButton).toHaveAttribute("aria-pressed", "true");
    expect(reportButton).toHaveAttribute("aria-pressed", "false");
    expect(progressButton).toHaveAttribute("aria-pressed", "false");

    await user.click(reportButton);

    expect(reportButton).toHaveAttribute("aria-pressed", "true");
    expect(controlButton).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("region", { name: "报告画布" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "反馈意见" })).toBeInTheDocument();

    await user.click(progressButton);

    expect(progressButton).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("region", { name: "时间线" })).toBeInTheDocument();
  } finally {
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      writable: true,
      value: originalMatchMedia,
    });
  }
});
