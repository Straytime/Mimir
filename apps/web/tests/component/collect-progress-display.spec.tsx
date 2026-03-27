import { screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { ResearchWorkspaceShell } from "@/features/research/components/research-workspace-shell";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import type { TimelineItem } from "@/features/research/store/research-session-store.types";
import {
  makeResearchSessionState,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";
import { renderWithStore } from "@/tests/fixtures/render";

function makeCollectItem(
  overrides: Partial<TimelineItem> & { id: string },
): TimelineItem {
  return {
    revisionId: "rev_0",
    kind: "collect",
    label: "搜集子任务",
    status: "running",
    occurredAt: "2026-03-27T00:00:00Z",
    ...overrides,
  };
}

test("shows collect progress during collecting phase", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        sseState: "open",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "collecting",
          status: "running",
        }),
      },
      stream: {
        timeline: [
          makeCollectItem({ id: "c1", status: "completed" }),
          makeCollectItem({ id: "c2", status: "running" }),
          makeCollectItem({ id: "c3", status: "running" }),
        ],
      },
    }),
  );

  renderWithStore(<ResearchWorkspaceShell />, { store });

  expect(screen.getByText(/搜集进度/)).toBeInTheDocument();
  expect(screen.getByText(/01\/03 子任务完成/)).toBeInTheDocument();
});

test("does not show collect progress during non-collecting phase", () => {
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
      },
      stream: {
        timeline: [
          makeCollectItem({ id: "c1", status: "completed" }),
        ],
      },
    }),
  );

  renderWithStore(<ResearchWorkspaceShell />, { store });

  expect(screen.queryByText(/搜集进度/)).not.toBeInTheDocument();
});
