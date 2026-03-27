import { screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { ClarificationDetailPanel } from "@/features/research/components/clarification-panels";
import { TimelinePanel } from "@/features/research/components/timeline-panel";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makeResearchSessionState,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";
import { renderWithStore } from "@/tests/fixtures/render";

test("ClarificationDetailPanel empty state shows user-facing copy", () => {
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
          clarification_mode: "natural",
        }),
      },
      stream: {
        clarificationText: "",
      },
    }),
  );

  renderWithStore(<ClarificationDetailPanel />, { store });

  expect(screen.getByText("正在生成追问...")).toBeInTheDocument();
  expect(screen.queryByText(/流式输出/)).not.toBeInTheDocument();
});

test("TimelinePanel empty state shows user-facing copy", () => {
  renderWithStore(<TimelinePanel items={[]} />);

  expect(screen.getByText("研究进展将在这里实时显示。")).toBeInTheDocument();
  expect(screen.queryByText(/透明度事件/)).not.toBeInTheDocument();
});
