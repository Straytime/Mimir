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
  makeWriterToolCallCompletedEvent,
  makeWriterToolCallRequestedEvent,
} from "@/tests/fixtures/builders";

function reduceEvents(
  events: Parameters<typeof reduceTimelineStream>[1][],
) {
  return events.reduce(
    (stream, event) => reduceTimelineStream(stream, event),
    {
      timeline: createResearchSessionState().stream.timeline,
      outlineReady: createResearchSessionState().stream.outlineReady,
    },
  );
}

describe("reduceTimelineStream", () => {
  test("tracks analysis progress, requirement handoff, and outline drafting without leaking raw outline delta", () => {
    const result = reduceEvents([
      makeAnalysisDeltaEvent(),
      makeAnalysisCompletedEvent(),
      makeOutlineDeltaEvent({
        payload: {
          delta: '{ "outline": "raw debug delta" }',
        },
      }),
    ]);

    expect(result.timeline).toEqual([
      expect.objectContaining({
        id: "analysis:rev_stage0",
        kind: "system",
        label: "需求摘要已生成",
        status: "completed",
      }),
      expect.objectContaining({
        id: "outline:rev_stage0",
        kind: "system",
        label: "正在构思报告结构",
        status: "running",
      }),
    ]);
    expect(result.timeline[1]?.detail).toBeUndefined();
    expect(result.outlineReady).toBe(false);
  });

  test("maps planning, collection, summary, and merged-source events into user-readable timeline items", () => {
    const result = reduceEvents([
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
    ]);

    expect(result.timeline).toEqual([
      expect.objectContaining({
        id: "planning:rev_stage0",
        kind: "reasoning",
        label: "正在规划研究路径",
        detail: "当前还缺少代表性玩家与市场趋势信息。",
        status: "running",
      }),
      expect.objectContaining({
        id: "collect:call_ai_search",
        kind: "collect",
        label: "收集 2024-2026 年中国 AI 搜索产品的主要厂商与公开进展",
        collectTarget:
          "收集 2024-2026 年中国 AI 搜索产品的主要厂商与公开进展",
        subtaskId: "sub_ai_search",
        toolCallId: "call_ai_search",
        status: "completed",
      }),
      expect.objectContaining({
        id: "summary:call_ai_search:sub_ai_search",
        kind: "summary",
        label: "阶段结论已整理",
        collectTarget:
          "收集 2024-2026 年中国 AI 搜索产品的主要厂商与公开进展",
        status: "completed",
      }),
      expect.objectContaining({
        id: "sources-merged:23",
        kind: "system",
        label: "来源已去重并整理引用",
        status: "completed",
      }),
    ]);

    expect(result.timeline[1]?.detail).toContain("先做高时效搜索，再读取官方来源。");
    expect(result.timeline[1]?.detail).toContain("搜索： 中国 AI 搜索 产品 2025");
    expect(result.timeline[1]?.detail).toContain("搜索完成：10 条结果");
    expect(result.timeline[1]?.detail).toContain("读取资料：https://example.com/article");
    expect(result.timeline[1]?.detail).toContain("读取完成：某公司发布会回顾");
    expect(result.timeline[1]?.detail).toContain("搜集完成：4 条资料");
    expect(result.timeline[2]?.detail).toContain("官方披露更多集中在 2025 年后。");
    expect(result.timeline[3]?.detail).toContain("18 -> 11");
  });

  test("keeps interleaved sub-agent events attached to the correct collect target", () => {
    const result = reduceEvents([
      makePlannerToolCallRequestedEvent({
        payload: {
          tool_call_id: "call_ai_search",
          collect_target: "收集 AI 搜索厂商",
          additional_info: "优先官方资料。",
        },
      }),
      makePlannerToolCallRequestedEvent({
        seq: 16,
        payload: {
          tool_call_id: "call_revenue",
          collect_target: "收集商业化与收入线索",
          additional_info: "关注 2025 年财报。",
        },
      }),
      makeCollectorReasoningDeltaEvent({
        seq: 17,
        payload: {
          subtask_id: "sub_revenue",
          tool_call_id: "call_revenue",
          delta: "先查财报与业绩会。",
        },
      }),
      makeCollectorSearchStartedEvent({
        seq: 18,
        payload: {
          subtask_id: "sub_ai_search",
          tool_call_id: "call_ai_search",
          search_query: "AI 搜索 厂商 2025",
          search_recency_filter: "noLimit",
        },
      }),
      makeCollectorSearchStartedEvent({
        seq: 19,
        payload: {
          subtask_id: "sub_revenue",
          tool_call_id: "call_revenue",
          search_query: "AI 搜索 商业化 收入 2025",
          search_recency_filter: "noLimit",
        },
      }),
    ]);

    expect(result.timeline).toEqual([
      expect.objectContaining({
        id: "collect:call_ai_search",
        collectTarget: "收集 AI 搜索厂商",
      }),
      expect.objectContaining({
        id: "collect:call_revenue",
        collectTarget: "收集商业化与收入线索",
      }),
    ]);
    expect(result.timeline[0]?.detail).toContain("搜索： AI 搜索 厂商 2025");
    expect(result.timeline[0]?.detail).not.toContain("AI 搜索 商业化 收入 2025");
    expect(result.timeline[1]?.detail).toContain("先查财报与业绩会。");
    expect(result.timeline[1]?.detail).toContain("搜索： AI 搜索 商业化 收入 2025");
    expect(result.timeline[1]?.detail).not.toContain("AI 搜索 厂商 2025");
  });

  test("maps outline completion, writer progress, artifact generation, and report completion into readable timeline items", () => {
    const result = reduceEvents([
      makeOutlineDeltaEvent(),
      makeOutlineCompletedEvent(),
      makeWriterReasoningDeltaEvent(),
      makeWriterToolCallRequestedEvent(),
      makeWriterToolCallCompletedEvent(),
      makeArtifactReadyEvent(),
      makeReportCompletedEvent(),
    ]);

    expect(result.outlineReady).toBe(true);
    expect(result.timeline).toEqual([
      expect.objectContaining({
        id: "outline:rev_stage0",
        kind: "system",
        label: "章节概览已生成",
        status: "completed",
      }),
      expect.objectContaining({
        id: "writer:rev_stage0",
        kind: "reasoning",
        label: "正在撰写报告",
        detail: "先完成市场格局章节，再决定是否需要图表支撑。",
        status: "running",
      }),
      expect.objectContaining({
        id: "writer-tool:call_writer_figure",
        kind: "tool_call",
        label: "正在生成配图",
        toolCallId: "call_writer_figure",
        status: "completed",
      }),
      expect.objectContaining({
        id: "artifact:art_stage0_chart",
        kind: "system",
        label: "已生成配图",
        status: "completed",
      }),
      expect.objectContaining({
        id: "report:rev_stage0",
        kind: "system",
        label: "报告已完成",
        status: "completed",
      }),
    ]);
  });

  test("maps feedback-processing and new-round phase changes into explicit timeline items", () => {
    const result = reduceEvents([
      makePhaseChangedEvent({
        seq: 60,
        revision_id: "rev_stage1",
        phase: "processing_feedback",
        payload: {
          from_phase: "delivered",
          to_phase: "processing_feedback",
          status: "running",
        },
      }),
      makePhaseChangedEvent({
        seq: 61,
        revision_id: "rev_stage1",
        phase: "planning_collection",
        payload: {
          from_phase: "processing_feedback",
          to_phase: "planning_collection",
          status: "running",
        },
      }),
    ]);

    expect(result.timeline).toEqual([
      expect.objectContaining({
        id: "phase:60",
        kind: "phase",
        revisionId: "rev_stage1",
        label: "正在处理反馈",
        status: "running",
      }),
      expect.objectContaining({
        id: "phase:61",
        kind: "phase",
        revisionId: "rev_stage1",
        label: "新一轮研究已进入规划阶段",
        status: "running",
      }),
    ]);
  });
});
