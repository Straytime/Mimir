import { expect, test } from "vitest";

import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makePhaseChangedEvent,
  makeResearchSessionState,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";

test("switches into the pending revision without inserting a revision divider", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      remote: {
        snapshot: makeTaskSnapshot({
          active_revision_id: "rev_stage0",
          active_revision_number: 1,
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

  store.getState().applyEvent(
    makePhaseChangedEvent({
      seq: 61,
      revision_id: "rev_stage1",
      phase: "planning_collection",
      timestamp: "2026-03-31T17:36:00+08:00",
      payload: {
        from_phase: "delivered",
        to_phase: "planning_collection",
        status: "running",
      },
    }),
  );

  const nextState = store.getState();

  expect(nextState.ui.revisionTransition.status).toBe("idle");
  expect(nextState.remote.snapshot).toMatchObject({
    active_revision_id: "rev_stage1",
    active_revision_number: 2,
    phase: "planning_collection",
    status: "running",
  });
  expect(nextState.stream.collectionTrace.nodes).toEqual([]);
  expect("timeline" in (nextState.stream as Record<string, unknown>)).toBe(false);
});
