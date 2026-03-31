import { screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { ResearchWorkspaceShell } from "@/features/research/components/research-workspace-shell";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makeCollectionCollectGroup,
  makeCollectionPlanRoundNode,
  makeCollectionTraceRoot,
  makeResearchSessionState,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";
import { renderWithStore } from "@/tests/fixtures/render";

test("shows the collection trace card once collection begins", () => {
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
        collectionTrace: makeCollectionTraceRoot({
          nodes: [
            makeCollectionPlanRoundNode({
              collectGroups: [
                makeCollectionCollectGroup({
                  id: "c1",
                  toolCallId: "call_1",
                  collectTarget: "搜集子任务 1",
                }),
                makeCollectionCollectGroup({
                  id: "c2",
                  toolCallId: "call_2",
                  collectTarget: "搜集子任务 2",
                }),
                makeCollectionCollectGroup({
                  id: "c3",
                  toolCallId: "call_3",
                  collectTarget: "搜集子任务 3",
                }),
              ],
            }),
          ],
        }),
      },
    }),
  );

  renderWithStore(<ResearchWorkspaceShell />, { store });

  expect(screen.getByRole("region", { name: "Collection Trace" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Plan Round 1" })).toBeInTheDocument();
  expect(screen.getAllByRole("heading", { name: "Collect" })).toHaveLength(3);
  expect(screen.queryByText(/搜集进度/)).not.toBeInTheDocument();
});

test("keeps the collection trace visible during later phases", () => {
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
        collectionTrace: makeCollectionTraceRoot({
          nodes: [
            makeCollectionPlanRoundNode({
              collectGroups: [
                makeCollectionCollectGroup({
                  id: "c1",
                  toolCallId: "call_1",
                }),
              ],
            }),
          ],
        }),
      },
    }),
  );

  renderWithStore(<ResearchWorkspaceShell />, { store });

  expect(screen.getByRole("region", { name: "Collection Trace" })).toBeInTheDocument();
});
