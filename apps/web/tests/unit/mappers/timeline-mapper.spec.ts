import { describe, expect, test } from "vitest";

import { reduceTimelineStream } from "@/features/research/mappers/timeline-mapper";
import { createResearchSessionState } from "@/features/research/store/research-session-store.types";
import {
  makeAnalysisCompletedEvent,
  makeAnalysisDeltaEvent,
  makeArtifactReadyEvent,
  makeCollectorCompletedEvent,
  makeCollectorFetchCompletedEvent,
  makeCollectorFetchStartedEvent,
  makeCollectorReasoningDeltaEvent,
  makeCollectorSearchCompletedEvent,
  makeCollectorSearchStartedEvent,
  makeOutlineCompletedEvent,
  makeOutlineDeltaEvent,
  makePlannerReasoningDeltaEvent,
  makePlannerToolCallRequestedEvent,
  makePhaseChangedEvent,
  makeReportCompletedEvent,
  makeSourcesMergedEvent,
  makeSummaryCompletedEvent,
  makeWriterReasoningDeltaEvent,
} from "@/tests/fixtures/builders";

function reduceEvents(
  events: Parameters<typeof reduceTimelineStream>[1][],
) {
  const baseStream = createResearchSessionState().stream;

  return events.reduce(
    (stream, event) => reduceTimelineStream(stream, event),
    {
      collectionTrace: baseStream.collectionTrace,
      outlineReady: baseStream.outlineReady,
    },
  );
}

describe("reduceTimelineStream", () => {
  test("creates independent top-level plan rounds for separate planner loops", () => {
    const result = reduceEvents([
      makePhaseChangedEvent({
        seq: 29,
        revision_id: "rev_stage0",
        phase: "planning_collection",
        payload: {
          from_phase: "analyzing_requirement",
          to_phase: "planning_collection",
          status: "running",
        },
      }),
      makePlannerReasoningDeltaEvent(),
      makePlannerToolCallRequestedEvent(),
      makePlannerReasoningDeltaEvent({
        seq: 30,
        timestamp: "2026-03-13T14:33:00+08:00",
        payload: {
          delta: "还缺少商业化与收入线索。",
        },
      }),
      makePlannerToolCallRequestedEvent({
        seq: 31,
        timestamp: "2026-03-13T14:33:05+08:00",
        payload: {
          tool_call_id: "call_revenue",
          collect_target: "收集商业化与收入线索",
          additional_info: "关注财报与业绩会。",
        },
      }),
    ]);

    expect(result.collectionTrace.nodes).toHaveLength(2);
    expect(result.collectionTrace.nodes).toEqual([
      expect.objectContaining({
        kind: "plan_round",
        roundIndex: 1,
        revisionId: "rev_stage0",
      }),
      expect.objectContaining({
        kind: "plan_round",
        roundIndex: 2,
        revisionId: "rev_stage0",
      }),
    ]);

    const firstPlanRound = result.collectionTrace.nodes[0];
    const secondPlanRound = result.collectionTrace.nodes[1];

    if (firstPlanRound?.kind !== "plan_round" || secondPlanRound?.kind !== "plan_round") {
      throw new Error("expected plan rounds");
    }

    expect(firstPlanRound.reasoningBursts).toEqual([
      expect.objectContaining({
        kind: "reasoning_burst",
        detail: "当前还缺少代表性玩家与市场趋势信息。",
      }),
    ]);
    expect(firstPlanRound.collectGroups).toEqual([
      expect.objectContaining({
        toolCallId: "call_ai_search",
        collectTarget:
          "收集 2024-2026 年中国 AI 搜索产品的主要厂商与公开进展",
      }),
    ]);

    expect(secondPlanRound.reasoningBursts).toEqual([
      expect.objectContaining({
        kind: "reasoning_burst",
        detail: "还缺少商业化与收入线索。",
      }),
    ]);
    expect(secondPlanRound.collectGroups).toEqual([
      expect.objectContaining({
        toolCallId: "call_revenue",
        collectTarget: "收集商业化与收入线索",
      }),
    ]);
  });

  test("keeps collect reasoning bursts and four tool event types in time order within one collect group", () => {
    const result = reduceEvents([
      makePlannerReasoningDeltaEvent(),
      makePlannerToolCallRequestedEvent(),
      makeCollectorReasoningDeltaEvent(),
      makeCollectorSearchStartedEvent(),
      makeCollectorSearchCompletedEvent(),
      makeCollectorReasoningDeltaEvent({
        seq: 19,
        timestamp: "2026-03-13T14:32:18+08:00",
        payload: {
          subtask_id: "sub_ai_search",
          tool_call_id: "call_ai_search",
          delta: "再读取官方来源与发布会回顾。",
        },
      }),
      makeCollectorFetchStartedEvent(),
      makeCollectorFetchCompletedEvent(),
      makeCollectorCompletedEvent(),
    ]);

    const firstPlanRound = result.collectionTrace.nodes[0];

    if (firstPlanRound?.kind !== "plan_round") {
      throw new Error("expected a plan round");
    }

    const collectGroup = firstPlanRound.collectGroups[0];

    expect(collectGroup).toEqual(
      expect.objectContaining({
        toolCallId: "call_ai_search",
        collectTarget:
          "收集 2024-2026 年中国 AI 搜索产品的主要厂商与公开进展",
      }),
    );

    expect(collectGroup?.collect.entries.map((entry) => entry.kind)).toEqual([
      "reasoning_burst",
      "search_started",
      "search_completed",
      "reasoning_burst",
      "fetch_started",
      "fetch_completed",
      "collect_completed",
    ]);
    expect(collectGroup?.collect.entries[0]).toEqual(
      expect.objectContaining({
        kind: "reasoning_burst",
        detail: "先做高时效搜索，再读取官方来源。",
      }),
    );
    expect(collectGroup?.collect.entries[1]).toEqual(
      expect.objectContaining({
        kind: "search_started",
        detail: "中国 AI 搜索 产品 2025",
      }),
    );
    expect(collectGroup?.collect.entries[2]).toEqual(
      expect.objectContaining({
        kind: "search_completed",
        detail: "10 条结果",
      }),
    );
    expect(collectGroup?.collect.entries[3]).toEqual(
      expect.objectContaining({
        kind: "reasoning_burst",
        detail: "再读取官方来源与发布会回顾。",
      }),
    );
    expect(collectGroup?.collect.entries[4]).toEqual(
      expect.objectContaining({
        kind: "fetch_started",
        detail: "https://example.com/article",
      }),
    );
    expect(collectGroup?.collect.entries[5]).toEqual(
      expect.objectContaining({
        kind: "fetch_completed",
        detail: "某公司发布会回顾",
      }),
    );
    expect(collectGroup?.collect.entries[6]).toEqual(
      expect.objectContaining({
        kind: "collect_completed",
        detail: "搜集完成：4 条资料",
        status: "completed",
      }),
    );
  });

  test("stores summary as a sibling of collect within the same collect group", () => {
    const result = reduceEvents([
      makePlannerReasoningDeltaEvent(),
      makePlannerToolCallRequestedEvent(),
      makeCollectorReasoningDeltaEvent(),
      makeCollectorCompletedEvent(),
      makeSummaryCompletedEvent(),
    ]);

    const firstPlanRound = result.collectionTrace.nodes[0];

    if (firstPlanRound?.kind !== "plan_round") {
      throw new Error("expected a plan round");
    }

    const collectGroup = firstPlanRound.collectGroups[0];

    expect(collectGroup?.summary).toEqual(
      expect.objectContaining({
        kind: "summary",
        status: "completed",
      }),
    );
    expect(collectGroup?.summary?.detail).toContain("官方披露更多集中在 2025 年后。");
    expect(collectGroup?.collect.entries.map((entry) => entry.kind)).not.toContain("summary");
  });

  test("appends sources merged as a top-level terminal node", () => {
    const result = reduceEvents([
      makePlannerReasoningDeltaEvent(),
      makePlannerToolCallRequestedEvent(),
      makeSourcesMergedEvent(),
    ]);

    expect(result.collectionTrace.nodes).toHaveLength(2);
    expect(result.collectionTrace.nodes[1]).toEqual(
      expect.objectContaining({
        kind: "sources_merged",
        status: "completed",
        sourceCountBeforeMerge: 18,
        sourceCountAfterMerge: 11,
        referenceCount: 11,
      }),
    );
  });

  test("keeps collection trace filtered to collection events only", () => {
    const result = reduceEvents([
      makeAnalysisDeltaEvent(),
      makeAnalysisCompletedEvent(),
      makeOutlineDeltaEvent({
        payload: {
          delta: '{ "outline": "raw debug delta" }',
        },
      }),
      makeWriterReasoningDeltaEvent(),
      makeArtifactReadyEvent(),
      makeReportCompletedEvent(),
      makeOutlineCompletedEvent(),
    ]);

    expect(result.collectionTrace.nodes).toEqual([]);
    expect(result.outlineReady).toBe(true);
  });

  test("does not retain a legacy timeline projection for collection events", () => {
    const result = reduceEvents([
      makePlannerReasoningDeltaEvent(),
      makePlannerToolCallRequestedEvent(),
      makeCollectorCompletedEvent(),
    ]);

    expect(result.collectionTrace.nodes).toHaveLength(1);
    expect("timeline" in (result as Record<string, unknown>)).toBe(false);
  });
});
