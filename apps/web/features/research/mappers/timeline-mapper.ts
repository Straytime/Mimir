import type { CollectSummaryStatus, EventEnvelope } from "@/lib/contracts";

import type {
  ResearchSessionState,
  TimelineItem,
} from "../store/research-session-store.types";

export type TimelineStreamState = Pick<
  ResearchSessionState["stream"],
  "timeline" | "outlineReady"
>;

function appendDetail(
  currentDetail: string | undefined,
  nextLine: string | null | undefined,
) {
  const normalizedNextLine = nextLine?.trim();

  if (!normalizedNextLine) {
    return currentDetail;
  }

  return currentDetail
    ? `${currentDetail}\n${normalizedNextLine}`
    : normalizedNextLine;
}

function upsertTimelineItem(
  timeline: TimelineItem[],
  id: string,
  createItem: () => TimelineItem,
  updateItem: (item: TimelineItem) => TimelineItem,
): TimelineItem[] {
  const existingIndex = timeline.findIndex((item) => item.id === id);

  if (existingIndex === -1) {
    return [...timeline, createItem()];
  }

  return timeline.map((item, index) =>
    index === existingIndex ? updateItem(item) : item,
  );
}

function findCollectItemIndex(
  timeline: TimelineItem[],
  args: {
    toolCallId?: string | null;
    subtaskId?: string | null;
  },
) {
  if (args.toolCallId) {
    const toolCallMatchIndex = timeline.findIndex(
      (item) => item.toolCallId === args.toolCallId,
    );

    if (toolCallMatchIndex !== -1) {
      return toolCallMatchIndex;
    }
  }

  if (args.subtaskId) {
    return timeline.findIndex((item) => item.subtaskId === args.subtaskId);
  }

  return -1;
}

function getCollectTarget(
  timeline: TimelineItem[],
  args: {
    toolCallId?: string | null;
    subtaskId?: string | null;
    collectTarget?: string | null;
  },
) {
  if (args.collectTarget) {
    return args.collectTarget;
  }

  const collectItemIndex = findCollectItemIndex(timeline, args);

  if (collectItemIndex === -1) {
    return undefined;
  }

  return timeline[collectItemIndex]?.collectTarget;
}

function mapCollectStatus(status: CollectSummaryStatus): TimelineItem["status"] {
  return status === "risk_blocked" ? "failed" : "completed";
}

function upsertCollectTimelineItem(
  timeline: TimelineItem[],
  args: {
    revisionId: string | null;
    occurredAt: string;
    toolCallId: string;
    subtaskId?: string | null;
    collectTarget?: string | null;
    detailLine?: string | null;
    status?: TimelineItem["status"];
  },
): TimelineItem[] {
  const collectItemIndex = findCollectItemIndex(timeline, {
    toolCallId: args.toolCallId,
    subtaskId: args.subtaskId,
  });

  if (collectItemIndex === -1) {
    const nextItem: TimelineItem = {
      id: `collect:${args.toolCallId}`,
      revisionId: args.revisionId,
      kind: "collect",
      label: args.collectTarget ?? "正在搜索与读取资料",
      detail: appendDetail(undefined, args.detailLine),
      status: args.status ?? "running",
      occurredAt: args.occurredAt,
      subtaskId: args.subtaskId ?? undefined,
      toolCallId: args.toolCallId,
      collectTarget: args.collectTarget ?? undefined,
    };

    return [
      ...timeline,
      nextItem,
    ];
  }

  return timeline.map((item, index) => {
    if (index !== collectItemIndex) {
      return item;
    }

    return {
      ...item,
      revisionId: args.revisionId ?? item.revisionId,
      label: args.collectTarget ?? item.collectTarget ?? item.label,
      detail: appendDetail(item.detail, args.detailLine),
      status: args.status ?? item.status,
      occurredAt: args.occurredAt,
      subtaskId: args.subtaskId ?? item.subtaskId,
      toolCallId: args.toolCallId,
      collectTarget: args.collectTarget ?? item.collectTarget,
    };
  });
}

function buildSummaryDetail(
  event: Extract<EventEnvelope, { event: "summary.completed" }>,
) {
  if (event.payload.message) {
    return event.payload.message;
  }

  return event.payload.key_findings_markdown ?? undefined;
}

export function reduceTimelineStream(
  stream: TimelineStreamState,
  event: EventEnvelope,
): TimelineStreamState {
  switch (event.event) {
    case "analysis.delta":
      return {
        ...stream,
        timeline: upsertTimelineItem(
          stream.timeline,
          `analysis:${event.revision_id ?? "unknown"}`,
          () => ({
            id: `analysis:${event.revision_id ?? "unknown"}`,
            revisionId: event.revision_id,
            kind: "system",
            label: "正在分析你的研究需求",
            status: "running",
            occurredAt: event.timestamp,
          }),
          (item) => ({
            ...item,
            label: "正在分析你的研究需求",
            status: "running",
            occurredAt: event.timestamp,
          }),
        ),
      };
    case "analysis.completed":
      return {
        ...stream,
        timeline: upsertTimelineItem(
          stream.timeline,
          `analysis:${event.revision_id ?? "unknown"}`,
          () => ({
            id: `analysis:${event.revision_id ?? "unknown"}`,
            revisionId: event.revision_id,
            kind: "system",
            label: "需求摘要已生成",
            status: "completed",
            occurredAt: event.timestamp,
          }),
          (item) => ({
            ...item,
            label: "需求摘要已生成",
            status: "completed",
            occurredAt: event.timestamp,
          }),
        ),
      };
    case "planner.reasoning.delta":
      return {
        ...stream,
        timeline: upsertTimelineItem(
          stream.timeline,
          `planning:${event.revision_id ?? "unknown"}`,
          () => ({
            id: `planning:${event.revision_id ?? "unknown"}`,
            revisionId: event.revision_id,
            kind: "reasoning",
            label: "正在规划研究路径",
            detail: event.payload.delta,
            status: "running",
            occurredAt: event.timestamp,
          }),
          (item) => ({
            ...item,
            label: "正在规划研究路径",
            detail: appendDetail(item.detail, event.payload.delta),
            status: "running",
            occurredAt: event.timestamp,
          }),
        ),
      };
    case "planner.tool_call.requested":
      return {
        ...stream,
        timeline: upsertCollectTimelineItem(stream.timeline, {
          revisionId: event.revision_id,
          occurredAt: event.timestamp,
          toolCallId: event.payload.tool_call_id,
          collectTarget: event.payload.collect_target,
          detailLine: event.payload.additional_info,
        }),
      };
    case "collector.reasoning.delta":
      return {
        ...stream,
        timeline: upsertCollectTimelineItem(stream.timeline, {
          revisionId: event.revision_id,
          occurredAt: event.timestamp,
          toolCallId: event.payload.tool_call_id,
          subtaskId: event.payload.subtask_id,
          detailLine: event.payload.delta,
        }),
      };
    case "collector.search.started":
      return {
        ...stream,
        timeline: upsertCollectTimelineItem(stream.timeline, {
          revisionId: event.revision_id,
          occurredAt: event.timestamp,
          toolCallId: event.payload.tool_call_id,
          subtaskId: event.payload.subtask_id,
          detailLine: `搜索： ${event.payload.search_query}`,
        }),
      };
    case "collector.search.completed":
      return {
        ...stream,
        timeline: upsertCollectTimelineItem(stream.timeline, {
          revisionId: event.revision_id,
          occurredAt: event.timestamp,
          toolCallId: event.payload.tool_call_id,
          subtaskId: event.payload.subtask_id,
          detailLine: `搜索完成：${event.payload.result_count} 条结果`,
        }),
      };
    case "collector.fetch.started":
      return {
        ...stream,
        timeline: upsertCollectTimelineItem(stream.timeline, {
          revisionId: event.revision_id,
          occurredAt: event.timestamp,
          toolCallId: event.payload.tool_call_id,
          subtaskId: event.payload.subtask_id,
          detailLine: `读取资料：${event.payload.url}`,
        }),
      };
    case "collector.fetch.completed":
      return {
        ...stream,
        timeline: upsertCollectTimelineItem(stream.timeline, {
          revisionId: event.revision_id,
          occurredAt: event.timestamp,
          toolCallId: event.payload.tool_call_id,
          subtaskId: event.payload.subtask_id,
          detailLine: event.payload.success
            ? `读取完成：${event.payload.title ?? event.payload.url}`
            : `读取失败：${event.payload.url}`,
        }),
      };
    case "collector.completed":
      return {
        ...stream,
        timeline: upsertCollectTimelineItem(stream.timeline, {
          revisionId: event.revision_id,
          occurredAt: event.timestamp,
          toolCallId: event.payload.tool_call_id,
          subtaskId: event.payload.subtask_id,
          detailLine:
            event.payload.status === "risk_blocked"
              ? "搜集受阻"
              : `搜集完成：${event.payload.item_count} 条资料`,
          status: mapCollectStatus(event.payload.status),
        }),
      };
    case "summary.completed":
      {
        const timelineItem: TimelineItem = {
          id: `summary:${event.payload.tool_call_id}:${event.payload.subtask_id}`,
          revisionId: event.revision_id,
          kind: "summary",
          label: "阶段结论已整理",
          detail: buildSummaryDetail(event),
          status: mapCollectStatus(event.payload.status),
          occurredAt: event.timestamp,
          subtaskId: event.payload.subtask_id,
          toolCallId: event.payload.tool_call_id,
          collectTarget: getCollectTarget(stream.timeline, {
            toolCallId: event.payload.tool_call_id,
            subtaskId: event.payload.subtask_id,
            collectTarget: event.payload.collect_target,
          }),
        };

        return {
          ...stream,
          timeline: [...stream.timeline, timelineItem],
        };
      }
    case "sources.merged":
      {
        const timelineItem: TimelineItem = {
          id: `sources-merged:${event.seq}`,
          revisionId: event.revision_id,
          kind: "system",
          label: "来源已去重并整理引用",
          detail: `来源去重：${event.payload.source_count_before_merge} -> ${event.payload.source_count_after_merge}，引用 ${event.payload.reference_count} 条`,
          status: "completed",
          occurredAt: event.timestamp,
        };

        return {
          ...stream,
          timeline: [...stream.timeline, timelineItem],
        };
      }
    case "outline.delta":
      return {
        ...stream,
        outlineReady: false,
        timeline: upsertTimelineItem(
          stream.timeline,
          `outline:${event.revision_id ?? "unknown"}`,
          () => ({
            id: `outline:${event.revision_id ?? "unknown"}`,
            revisionId: event.revision_id,
            kind: "system",
            label: "正在构思报告结构",
            status: "running",
            occurredAt: event.timestamp,
          }),
          (item) => ({
            ...item,
            label: "正在构思报告结构",
            status: "running",
            occurredAt: event.timestamp,
          }),
        ),
      };
    case "outline.completed":
      return {
        ...stream,
        outlineReady: true,
        timeline: upsertTimelineItem(
          stream.timeline,
          `outline:${event.revision_id ?? "unknown"}`,
          () => ({
            id: `outline:${event.revision_id ?? "unknown"}`,
            revisionId: event.revision_id,
            kind: "system",
            label: "章节概览已生成",
            status: "completed",
            occurredAt: event.timestamp,
          }),
          (item) => ({
            ...item,
            label: "章节概览已生成",
            status: "completed",
            occurredAt: event.timestamp,
          }),
        ),
      };
    case "writer.reasoning.delta":
      return {
        ...stream,
        timeline: upsertTimelineItem(
          stream.timeline,
          `writer:${event.revision_id ?? "unknown"}`,
          () => ({
            id: `writer:${event.revision_id ?? "unknown"}`,
            revisionId: event.revision_id,
            kind: "reasoning",
            label: "正在撰写报告",
            detail: event.payload.delta,
            status: "running",
            occurredAt: event.timestamp,
          }),
          (item) => ({
            ...item,
            label: "正在撰写报告",
            detail: appendDetail(item.detail, event.payload.delta),
            status: "running",
            occurredAt: event.timestamp,
          }),
        ),
      };
    case "writer.tool_call.requested":
      return {
        ...stream,
        timeline: upsertTimelineItem(
          stream.timeline,
          `writer-tool:${event.payload.tool_call_id}`,
          () => ({
            id: `writer-tool:${event.payload.tool_call_id}`,
            revisionId: event.revision_id,
            kind: "tool_call",
            label: "正在生成配图",
            detail: event.payload.tool_name,
            status: "running",
            occurredAt: event.timestamp,
            toolCallId: event.payload.tool_call_id,
          }),
          (item) => ({
            ...item,
            label: "正在生成配图",
            detail: event.payload.tool_name,
            status: "running",
            occurredAt: event.timestamp,
            toolCallId: event.payload.tool_call_id,
          }),
        ),
      };
    case "writer.tool_call.completed":
      return {
        ...stream,
        timeline: upsertTimelineItem(
          stream.timeline,
          `writer-tool:${event.payload.tool_call_id}`,
          () => ({
            id: `writer-tool:${event.payload.tool_call_id}`,
            revisionId: event.revision_id,
            kind: "tool_call",
            label: "正在生成配图",
            detail: event.payload.tool_name,
            status: event.payload.success ? "completed" : "failed",
            occurredAt: event.timestamp,
            toolCallId: event.payload.tool_call_id,
          }),
          (item) => ({
            ...item,
            label: "正在生成配图",
            detail: event.payload.tool_name,
            status: event.payload.success ? "completed" : "failed",
            occurredAt: event.timestamp,
            toolCallId: event.payload.tool_call_id,
          }),
        ),
      };
    case "artifact.ready":
      {
        const timelineItem: TimelineItem = {
          id: `artifact:${event.payload.artifact.artifact_id}`,
          revisionId: event.revision_id,
          kind: "system",
          label: "已生成配图",
          detail: event.payload.artifact.filename,
          status: "completed",
          occurredAt: event.timestamp,
        };

        return {
          ...stream,
          timeline: [...stream.timeline, timelineItem],
        };
      }
    case "report.completed":
      return {
        ...stream,
        timeline: upsertTimelineItem(
          stream.timeline,
          `report:${event.payload.delivery.revision_id}`,
          () => ({
            id: `report:${event.payload.delivery.revision_id}`,
            revisionId: event.payload.delivery.revision_id,
            kind: "system",
            label: "报告已完成",
            detail: `${event.payload.delivery.word_count} 字，${event.payload.delivery.artifact_count} 张配图`,
            status: "completed",
            occurredAt: event.timestamp,
          }),
          (item) => ({
            ...item,
            label: "报告已完成",
            detail: `${event.payload.delivery.word_count} 字，${event.payload.delivery.artifact_count} 张配图`,
            status: "completed",
            occurredAt: event.timestamp,
          }),
        ),
      };
    default:
      return stream;
  }
}
