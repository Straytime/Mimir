import { expect, test } from "vitest";

import type { EventEnvelope } from "@/lib/contracts";
import {
  makeAnalysisCompletedEvent,
  makeAnalysisDeltaEvent,
  makeClarificationDeltaEvent,
  makeClarificationFallbackToNaturalEvent,
  makeClarificationNaturalReadyEvent,
  makeClarificationOptionsReadyEvent,
  makeClarificationCountdownStartedEvent,
  makeHeartbeatEvent,
  makePhaseChangedEvent,
  makeTaskCreatedEvent,
  makeTaskExpiredEvent,
  makeTaskFailedEvent,
  makeTaskTerminatedEvent,
} from "@/tests/fixtures/builders";

test("EventEnvelope fixtures stay aligned with the current event union", () => {
  const fixtures: EventEnvelope[] = [
    makeTaskCreatedEvent(),
    makePhaseChangedEvent(),
    makeHeartbeatEvent(),
    makeTaskFailedEvent(),
    makeTaskTerminatedEvent(),
    makeTaskExpiredEvent(),
    makeClarificationDeltaEvent(),
    makeClarificationNaturalReadyEvent(),
    makeClarificationOptionsReadyEvent(),
    makeClarificationCountdownStartedEvent(),
    makeClarificationFallbackToNaturalEvent(),
    makeAnalysisDeltaEvent(),
    makeAnalysisCompletedEvent(),
  ];

  expect(fixtures.map((fixture) => fixture.event)).toEqual([
    "task.created",
    "phase.changed",
    "heartbeat",
    "task.failed",
    "task.terminated",
    "task.expired",
    "clarification.delta",
    "clarification.natural.ready",
    "clarification.options.ready",
    "clarification.countdown.started",
    "clarification.fallback_to_natural",
    "analysis.delta",
    "analysis.completed",
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
  expect(fixtures[7]?.payload).toMatchObject({
    status: "awaiting_user_input",
    available_actions: ["submit_clarification"],
  });
  expect(fixtures[8]?.payload).toHaveProperty("question_set.questions");
  expect(fixtures[11]?.payload).toHaveProperty("delta");
  expect(fixtures[12]?.payload).toHaveProperty("requirement_detail");
});
