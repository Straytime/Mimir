import { describe, expect, test } from "vitest";

import { reduceResearchSessionEvent } from "@/features/research/reducers/event-reducer";
import { makeResearchSessionState } from "@/tests/fixtures/builders";
import {
  makeClarificationDeltaEvent,
  makeHeartbeatEvent,
  makePhaseChangedEvent,
  makeTaskCreatedEvent,
  makeTaskExpiredEvent,
  makeTaskFailedEvent,
  makeTaskTerminatedEvent,
} from "@/tests/fixtures/builders";

describe("reduceResearchSessionEvent", () => {
  test("handles task.created by replacing the snapshot from the authoritative event", () => {
    const state = makeResearchSessionState({
      remote: {
        snapshot: null,
      },
    });
    const event = makeTaskCreatedEvent();

    const result = reduceResearchSessionEvent(state, event);

    expect(result.remote.snapshot).toEqual(event.payload.snapshot);
    expect(result.stream.lastEventSeq).toBe(event.seq);
  });

  test("handles phase.changed by updating phase and status", () => {
    const state = makeResearchSessionState();
    const event = makePhaseChangedEvent({
      revision_id: "rev_stage1",
      payload: {
        from_phase: "clarifying",
        to_phase: "analyzing_requirement",
        status: "running",
      },
      timestamp: "2026-03-13T14:31:11+08:00",
    });

    const result = reduceResearchSessionEvent(state, event);

    expect(result.remote.snapshot).toMatchObject({
      phase: "analyzing_requirement",
      status: "running",
      active_revision_id: "rev_stage1",
      updated_at: "2026-03-13T14:31:11+08:00",
    });
    expect(result.stream.lastEventSeq).toBe(event.seq);
  });

  test("handles heartbeat by recording the last heartbeat time", () => {
    const state = makeResearchSessionState();
    const event = makeHeartbeatEvent({
      payload: {
        server_time: "2026-03-13T14:35:30+08:00",
      },
    });

    const result = reduceResearchSessionEvent(state, event);

    expect(result.session.lastHeartbeatAt).toBe("2026-03-13T14:35:30+08:00");
    expect(result.stream.lastEventSeq).toBe(event.seq);
  });

  test.each([
    {
      name: "task.failed",
      event: makeTaskFailedEvent(),
      terminalReason: "failed",
      status: "failed",
      expiresAt: null,
    },
    {
      name: "task.terminated",
      event: makeTaskTerminatedEvent(),
      terminalReason: "terminated",
      status: "terminated",
      expiresAt: null,
    },
    {
      name: "task.expired",
      event: makeTaskExpiredEvent(),
      terminalReason: "expired",
      status: "expired",
      expiresAt: "2026-03-13T15:25:00+08:00",
    },
  ])(
    "handles $name by switching the store into a terminal state",
    ({ event, terminalReason, status, expiresAt }) => {
      const state = makeResearchSessionState({
        remote: {
          snapshot: {
            ...makeResearchSessionState().remote.snapshot!,
            available_actions: ["submit_feedback", "download_markdown", "download_pdf"],
          },
        },
      });

      const result = reduceResearchSessionEvent(state, event);

      expect(result.ui.terminalReason).toBe(terminalReason);
      expect(result.remote.snapshot).toMatchObject({
        status,
        available_actions: [],
      });
      expect(result.remote.snapshot?.expires_at ?? null).toBe(expiresAt);
      expect(result.stream.lastEventSeq).toBe(event.seq);
    },
  );

  test("keeps unsupported events as a no-op for the current stage", () => {
    const state = makeResearchSessionState();
    const event = makeClarificationDeltaEvent();

    const result = reduceResearchSessionEvent(state, event);

    expect(result).toBe(state);
  });
});
