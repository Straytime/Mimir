import { expect, test } from "vitest";

import type { EventEnvelope } from "@/lib/contracts";
import {
  makeAnalysisCompletedEvent,
  makeAnalysisDeltaEvent,
  makeArtifactReadyEvent,
  makeClarificationDeltaEvent,
  makeClarificationFallbackToNaturalEvent,
  makeClarificationNaturalReadyEvent,
  makeClarificationOptionsReadyEvent,
  makeClarificationCountdownStartedEvent,
  makeCollectorCompletedEvent,
  makeCollectorFetchCompletedEvent,
  makeCollectorFetchStartedEvent,
  makeCollectorReasoningDeltaEvent,
  makeCollectorSearchCompletedEvent,
  makeCollectorSearchStartedEvent,
  makeHeartbeatEvent,
  makeOutlineCompletedEvent,
  makeOutlineDeltaEvent,
  makePlannerReasoningDeltaEvent,
  makePlannerToolCallRequestedEvent,
  makePhaseChangedEvent,
  makeReportCompletedEvent,
  makeSourcesMergedEvent,
  makeSummaryCompletedEvent,
  makeTaskAwaitingFeedbackEvent,
  makeTaskCreatedEvent,
  makeTaskExpiredEvent,
  makeTaskFailedEvent,
  makeTaskTerminatedEvent,
  makeWriterDeltaEvent,
  makeWriterReasoningDeltaEvent,
  makeWriterToolCallCompletedEvent,
  makeWriterToolCallRequestedEvent,
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
    makePlannerReasoningDeltaEvent(),
    makePlannerToolCallRequestedEvent(),
    makeCollectorReasoningDeltaEvent(),
    makeCollectorSearchStartedEvent(),
    makeCollectorSearchCompletedEvent(),
    makeCollectorFetchStartedEvent(),
    makeCollectorFetchCompletedEvent(),
    makeCollectorCompletedEvent(),
    makeSummaryCompletedEvent(),
    makeSourcesMergedEvent(),
    makeOutlineDeltaEvent(),
    makeOutlineCompletedEvent(),
    makeWriterReasoningDeltaEvent(),
    makeWriterToolCallRequestedEvent(),
    makeWriterToolCallCompletedEvent(),
    makeWriterDeltaEvent(),
    makeArtifactReadyEvent(),
    makeReportCompletedEvent(),
    makeTaskAwaitingFeedbackEvent(),
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
    "planner.reasoning.delta",
    "planner.tool_call.requested",
    "collector.reasoning.delta",
    "collector.search.started",
    "collector.search.completed",
    "collector.fetch.started",
    "collector.fetch.completed",
    "collector.completed",
    "summary.completed",
    "sources.merged",
    "outline.delta",
    "outline.completed",
    "writer.reasoning.delta",
    "writer.tool_call.requested",
    "writer.tool_call.completed",
    "writer.delta",
    "artifact.ready",
    "report.completed",
    "task.awaiting_feedback",
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
  expect(fixtures[14]?.payload).toHaveProperty("collect_target");
  expect(fixtures[18]?.payload).toHaveProperty("url");
  expect(fixtures[20]?.payload).toHaveProperty("status");
  expect(fixtures[21]?.payload).toHaveProperty("key_findings_markdown");
  expect(fixtures[22]?.payload).toHaveProperty("reference_count");
  expect(fixtures[24]?.payload).toHaveProperty("outline.sections");
  expect(fixtures[25]?.payload).toHaveProperty("delta");
  expect(fixtures[26]?.payload).toHaveProperty("tool_name");
  expect(fixtures[27]?.payload).toHaveProperty("success");
  expect(fixtures[28]?.payload).toHaveProperty("delta");
  expect(fixtures[29]?.payload).toHaveProperty("artifact.url");
  expect(fixtures[30]?.payload).toHaveProperty("delivery.pdf_url");
  expect(fixtures[31]?.payload).toHaveProperty("expires_at");
});
