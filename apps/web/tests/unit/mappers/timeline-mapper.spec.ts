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
  test("keeps up to three planner tool calls in the same plan round and backfills each collect group by tool_call_id", () => {
    const result = reduceEvents([
      makePhaseChangedEvent({
        seq: 10,
        revision_id: "rev_stage0",
        phase: "planning_collection",
        payload: {
          from_phase: "analyzing_requirement",
          to_phase: "planning_collection",
          status: "running",
        },
      }),
      makePlannerReasoningDeltaEvent({
        seq: 11,
        timestamp: "2026-03-13T14:31:00+08:00",
        payload: {
          delta: "这一轮先并行补齐厂商、商业化和监管三个方向。",
        },
      }),
      makePlannerToolCallRequestedEvent({
        seq: 12,
        timestamp: "2026-03-13T14:31:05+08:00",
        payload: {
          tool_call_id: "call_vendors",
          collect_target: "收集主要厂商与产品进展",
          additional_info: "关注 2024-2026 时间窗。",
        },
      }),
      makePlannerToolCallRequestedEvent({
        seq: 13,
        timestamp: "2026-03-13T14:31:06+08:00",
        payload: {
          tool_call_id: "call_revenue",
          collect_target: "收集商业化与收入线索",
          additional_info: "优先看财报和业绩会。",
        },
      }),
      makePlannerToolCallRequestedEvent({
        seq: 14,
        timestamp: "2026-03-13T14:31:07+08:00",
        payload: {
          tool_call_id: "call_policy",
          collect_target: "收集监管与政策变化",
          additional_info: "关注主管部门与公开政策文件。",
        },
      }),
      makeCollectorReasoningDeltaEvent({
        seq: 15,
        timestamp: "2026-03-13T14:31:10+08:00",
        payload: {
          tool_call_id: "call_vendors",
          subtask_id: "sub_vendors",
          delta: "先搜索代表性厂商与产品发布时间线。",
        },
      }),
      makeCollectorSearchStartedEvent({
        seq: 16,
        timestamp: "2026-03-13T14:31:12+08:00",
        payload: {
          tool_call_id: "call_vendors",
          subtask_id: "sub_vendors",
          search_query: "中国 AI 搜索 厂商 2025",
          search_recency_filter: "30d",
        },
      }),
      makeCollectorSearchCompletedEvent({
        seq: 17,
        timestamp: "2026-03-13T14:31:13+08:00",
        payload: {
          tool_call_id: "call_vendors",
          subtask_id: "sub_vendors",
          search_query: "中国 AI 搜索 厂商 2025",
          result_count: 8,
          titles: ["厂商观察", "产品时间线"],
        },
      }),
      makeCollectorCompletedEvent({
        seq: 18,
        timestamp: "2026-03-13T14:31:18+08:00",
        payload: {
          tool_call_id: "call_vendors",
          subtask_id: "sub_vendors",
          status: "completed",
          item_count: 3,
          search_queries: ["中国 AI 搜索 厂商 2025"],
        },
      }),
      makeSummaryCompletedEvent({
        seq: 19,
        timestamp: "2026-03-13T14:31:20+08:00",
        payload: {
          tool_call_id: "call_vendors",
          subtask_id: "sub_vendors",
          collect_target: "收集主要厂商与产品进展",
          status: "completed",
          message: "厂商方向已识别出主要玩家与发布时间线。",
          key_findings_markdown: null,
          search_queries: ["中国 AI 搜索 厂商 2025"],
        },
      }),
      makeCollectorReasoningDeltaEvent({
        seq: 20,
        timestamp: "2026-03-13T14:31:22+08:00",
        payload: {
          tool_call_id: "call_revenue",
          subtask_id: "sub_revenue",
          delta: "补齐财报与业绩会里的收入披露。",
        },
      }),
      makeCollectorFetchStartedEvent({
        seq: 21,
        timestamp: "2026-03-13T14:31:24+08:00",
        payload: {
          tool_call_id: "call_revenue",
          subtask_id: "sub_revenue",
          url: "https://example.com/revenue",
        },
      }),
      makeCollectorFetchCompletedEvent({
        seq: 22,
        timestamp: "2026-03-13T14:31:26+08:00",
        payload: {
          tool_call_id: "call_revenue",
          subtask_id: "sub_revenue",
          url: "https://example.com/revenue",
          success: true,
          title: "收入披露摘录",
        },
      }),
      makeCollectorCompletedEvent({
        seq: 23,
        timestamp: "2026-03-13T14:31:28+08:00",
        payload: {
          tool_call_id: "call_revenue",
          subtask_id: "sub_revenue",
          status: "completed",
          item_count: 2,
          search_queries: ["AI 搜索 财报 收入"],
        },
      }),
      makeSummaryCompletedEvent({
        seq: 24,
        timestamp: "2026-03-13T14:31:30+08:00",
        payload: {
          tool_call_id: "call_revenue",
          subtask_id: "sub_revenue",
          collect_target: "收集商业化与收入线索",
          status: "completed",
          message: "商业化方向已补齐财报与业绩会摘要。",
          key_findings_markdown: null,
          search_queries: ["AI 搜索 财报 收入"],
        },
      }),
      makeCollectorReasoningDeltaEvent({
        seq: 25,
        timestamp: "2026-03-13T14:31:32+08:00",
        payload: {
          tool_call_id: "call_policy",
          subtask_id: "sub_policy",
          delta: "最后补齐监管与政策口径。",
        },
      }),
      makeCollectorSearchStartedEvent({
        seq: 26,
        timestamp: "2026-03-13T14:31:34+08:00",
        payload: {
          tool_call_id: "call_policy",
          subtask_id: "sub_policy",
          search_query: "中国 AI 搜索 监管 政策 2025",
          search_recency_filter: "365d",
        },
      }),
      makeCollectorSearchCompletedEvent({
        seq: 27,
        timestamp: "2026-03-13T14:31:35+08:00",
        payload: {
          tool_call_id: "call_policy",
          subtask_id: "sub_policy",
          search_query: "中国 AI 搜索 监管 政策 2025",
          result_count: 5,
          titles: ["政策口径", "监管信号"],
        },
      }),
      makeCollectorCompletedEvent({
        seq: 28,
        timestamp: "2026-03-13T14:31:38+08:00",
        payload: {
          tool_call_id: "call_policy",
          subtask_id: "sub_policy",
          status: "completed",
          item_count: 2,
          search_queries: ["中国 AI 搜索 监管 政策 2025"],
        },
      }),
      makeSummaryCompletedEvent({
        seq: 29,
        timestamp: "2026-03-13T14:31:40+08:00",
        payload: {
          tool_call_id: "call_policy",
          subtask_id: "sub_policy",
          collect_target: "收集监管与政策变化",
          status: "completed",
          message: "监管方向已补齐主管部门与政策文件。",
          key_findings_markdown: null,
          search_queries: ["中国 AI 搜索 监管 政策 2025"],
        },
      }),
    ]);

    expect(result.collectionTrace.nodes).toHaveLength(1);

    const planRound = result.collectionTrace.nodes[0];

    if (planRound?.kind !== "plan_round") {
      throw new Error("expected a single plan round");
    }

    expect(planRound.collectGroups).toHaveLength(3);
    expect(planRound.collectGroups.map((group) => group.toolCallId)).toEqual([
      "call_vendors",
      "call_revenue",
      "call_policy",
    ]);

    expect(planRound.collectGroups[0]).toEqual(
      expect.objectContaining({
        toolCallId: "call_vendors",
        subtaskId: "sub_vendors",
        collectTarget: "收集主要厂商与产品进展",
      }),
    );
    expect(planRound.collectGroups[0]?.collect.entries).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          kind: "search_started",
          detail: "中国 AI 搜索 厂商 2025",
        }),
        expect.objectContaining({
          kind: "search_completed",
          detail: "8 条结果",
        }),
      ]),
    );
    expect(planRound.collectGroups[0]?.summary?.detail).toContain(
      "厂商方向已识别出主要玩家与发布时间线。",
    );

    expect(planRound.collectGroups[1]).toEqual(
      expect.objectContaining({
        toolCallId: "call_revenue",
        subtaskId: "sub_revenue",
        collectTarget: "收集商业化与收入线索",
      }),
    );
    expect(planRound.collectGroups[1]?.collect.entries).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          kind: "fetch_started",
          detail: "https://example.com/revenue",
        }),
        expect.objectContaining({
          kind: "fetch_completed",
          detail: "收入披露摘录",
        }),
      ]),
    );
    expect(planRound.collectGroups[1]?.summary?.detail).toContain(
      "商业化方向已补齐财报与业绩会摘要。",
    );

    expect(planRound.collectGroups[2]).toEqual(
      expect.objectContaining({
        toolCallId: "call_policy",
        subtaskId: "sub_policy",
        collectTarget: "收集监管与政策变化",
      }),
    );
    expect(planRound.collectGroups[2]?.collect.entries).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          kind: "search_started",
          detail: "中国 AI 搜索 监管 政策 2025",
        }),
        expect.objectContaining({
          kind: "search_completed",
          detail: "5 条结果",
        }),
      ]),
    );
    expect(planRound.collectGroups[2]?.summary?.detail).toContain(
      "监管方向已补齐主管部门与政策文件。",
    );
  });

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
