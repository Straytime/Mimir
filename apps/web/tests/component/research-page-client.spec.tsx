import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { ResearchPageClient } from "@/features/research/components/research-page-client";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import { makeResearchSessionState, makeTaskSnapshot } from "@/tests/fixtures/builders";

test("renders the idle workspace shell before a task is created", () => {
  render(<ResearchPageClient />);

  expect(screen.getByRole("heading", { name: "AI 研究工作台" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "输入研究主题" })).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "从空态进入研究工作台" }),
  ).toBeInTheDocument();
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
