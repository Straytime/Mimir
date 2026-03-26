import { screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { ClarificationDetailPanel } from "@/features/research/components/clarification-panels";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makeResearchSessionState,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";
import { renderWithStore } from "@/tests/fixtures/render";

const QUESTION_SET = {
  questions: [
    {
      question_id: "q1",
      question: "研究范围？",
      options: [
        { option_id: "o_auto", label: "自动决定" },
        { option_id: "o1", label: "国内市场" },
      ],
    },
  ],
};

function createCountdownStore(secondsFromNow: number) {
  const deadlineAt = new Date(Date.now() + secondsFromNow * 1000).toISOString();

  return createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        sseState: "open",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "clarifying",
          status: "awaiting_user_input",
          clarification_mode: "options",
          available_actions: ["submit_clarification"],
        }),
      },
      stream: {
        questionSet: QUESTION_SET,
        clarificationText: "请回答以下问题。",
      },
      ui: {
        clarificationCountdownDeadlineAt: deadlineAt,
        clarificationCountdownDurationSeconds: secondsFromNow,
      },
    }),
  );
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

test("countdown > 10s uses default tint color and no pulse-fast animation", () => {
  vi.setSystemTime(new Date("2026-03-26T12:00:00Z"));
  const store = createCountdownStore(30);

  renderWithStore(<ClarificationDetailPanel />, { store });

  const countdownEl = screen.getByText(/剩余 \d+ 秒/);
  expect(countdownEl).toHaveClass("text-surface-tint");
  expect(countdownEl).not.toHaveClass("animate-pulse-fast");
  expect(countdownEl).not.toHaveClass("text-[#FF6B6B]");
});

test("countdown <= 10s uses red color and pulse-fast animation", () => {
  vi.setSystemTime(new Date("2026-03-26T12:00:00Z"));
  const store = createCountdownStore(8);

  renderWithStore(<ClarificationDetailPanel />, { store });

  const countdownEl = screen.getByText(/剩余 \d+ 秒/);
  expect(countdownEl).toHaveClass("text-[#FF6B6B]");
  expect(countdownEl).toHaveClass("animate-pulse-fast");
  expect(countdownEl).not.toHaveClass("text-surface-tint");
});

test("countdown > 10s shows '剩余 XX 秒' without urgency prefix", () => {
  vi.setSystemTime(new Date("2026-03-26T12:00:00Z"));
  const store = createCountdownStore(25);

  renderWithStore(<ClarificationDetailPanel />, { store });

  expect(screen.getByText(/剩余 \d+ 秒/)).toBeInTheDocument();
  expect(screen.queryByText(/即将自动提交/)).not.toBeInTheDocument();
});

test("countdown <= 10s shows '即将自动提交' prefix", () => {
  vi.setSystemTime(new Date("2026-03-26T12:00:00Z"));
  const store = createCountdownStore(5);

  renderWithStore(<ClarificationDetailPanel />, { store });

  expect(screen.getByText(/即将自动提交/)).toBeInTheDocument();
  expect(screen.getByText(/剩余 \d+ 秒/)).toBeInTheDocument();
});
