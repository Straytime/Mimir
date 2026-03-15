import { expect, test } from "vitest";

import type { EventEnvelope } from "@/lib/contracts";
import {
  makeClarificationDeltaEvent,
  makeHeartbeatEvent,
  makePhaseChangedEvent,
  makeTaskCreatedEvent,
  makeTaskExpiredEvent,
  makeTaskFailedEvent,
  makeTaskTerminatedEvent,
} from "@/tests/fixtures/builders";

test("EventEnvelope fixtures stay aligned with the Stage 1 event union", () => {
  const fixtures: EventEnvelope[] = [
    makeTaskCreatedEvent(),
    makePhaseChangedEvent(),
    makeHeartbeatEvent(),
    makeTaskFailedEvent(),
    makeTaskTerminatedEvent(),
    makeTaskExpiredEvent(),
    makeClarificationDeltaEvent(),
  ];

  expect(fixtures.map((fixture) => fixture.event)).toEqual([
    "task.created",
    "phase.changed",
    "heartbeat",
    "task.failed",
    "task.terminated",
    "task.expired",
    "clarification.delta",
  ]);

  expect(fixtures[0]?.payload).toHaveProperty("snapshot");
  expect(fixtures[1]?.payload).toMatchObject({
    from_phase: "clarifying",
    to_phase: "analyzing_requirement",
    status: "running",
  });
  expect(fixtures[2]?.payload).toMatchObject({
    server_time: "2026-03-13T14:35:30+08:00",
  });
});
