import { screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { ClarificationDetailPanel } from "@/features/research/components/clarification-panels";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makeResearchSessionState,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";
import { renderWithStore } from "@/tests/fixtures/render";

test("natural mode — text container has whitespace-pre-line to preserve newlines", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_1",
        taskToken: "secret_1",
        sseState: "open",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "clarifying",
          status: "running",
          clarification_mode: "natural",
        }),
      },
      stream: {
        clarificationText: "第一段\n\n第二段",
      },
    }),
  );

  renderWithStore(<ClarificationDetailPanel />, { store });

  const container = screen.getByText("第一段", { exact: false });
  expect(container.className).toContain("whitespace-pre-line");
});

test("options mode — shows only intro text when questionSet arrives, not full raw text", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_2",
        taskToken: "secret_2",
        sseState: "open",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "clarifying",
          status: "running",
          clarification_mode: "options",
        }),
      },
      stream: {
        clarificationText: [
          "为了更好地理解需求，请回答以下问题：",
          "",
          "1. 你希望侧重哪个领域？",
          "   A. 技术",
          "   B. 商业",
        ].join("\n"),
        questionSet: {
          questions: [
            {
              question_id: "q_0",
              question: "你希望侧重哪个领域？",
              options: [
                { option_id: "o_1", label: "技术" },
                { option_id: "o_2", label: "商业" },
              ],
            },
          ],
        },
      },
    }),
  );

  renderWithStore(<ClarificationDetailPanel />, { store });

  // Intro text should be visible
  expect(screen.getByText("为了更好地理解需求，请回答以下问题：")).toBeInTheDocument();
  // The question should only appear in the fieldset legend, not in the raw text block
  const legends = screen.getAllByText("你希望侧重哪个领域？");
  expect(legends).toHaveLength(1); // only in legend, not duplicated in text block
});

test("options mode — when intro is empty, text block is not rendered", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_3",
        taskToken: "secret_3",
        sseState: "open",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "clarifying",
          status: "running",
          clarification_mode: "options",
        }),
      },
      stream: {
        clarificationText: [
          "你希望侧重哪个领域？",
          "   A. 技术",
          "   B. 商业",
        ].join("\n"),
        questionSet: {
          questions: [
            {
              question_id: "q_0",
              question: "你希望侧重哪个领域？",
              options: [
                { option_id: "o_1", label: "技术" },
                { option_id: "o_2", label: "商业" },
              ],
            },
          ],
        },
      },
    }),
  );

  renderWithStore(<ClarificationDetailPanel />, { store });

  // The "正在生成追问..." placeholder should not be present
  expect(screen.queryByText("正在生成追问...")).not.toBeInTheDocument();
  // The question text should only appear once (in the legend)
  const legends = screen.getAllByText("你希望侧重哪个领域？");
  expect(legends).toHaveLength(1);
});
