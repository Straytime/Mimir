import type { CollectSummaryStatus, EventEnvelope } from "@/lib/contracts";

import type {
  CollectionCollectCompletedEvent,
  CollectionCollectEntry,
  CollectionCollectGroup,
  CollectionPlanRoundNode,
  CollectionReasoningBurst,
  CollectionSummaryNode,
  CollectionToolEvent,
  CollectionTraceRoot,
  CollectionTraceStatus,
} from "../store/research-session-store.types";

function appendLine(current: string | undefined, next: string | null | undefined) {
  const normalizedNext = next?.trim();

  if (!normalizedNext) {
    return current ?? "";
  }

  return current ? `${current}\n${normalizedNext}` : normalizedNext;
}

function cloneCollectEntry(entry: CollectionCollectEntry): CollectionCollectEntry {
  return { ...entry };
}

function cloneCollectionTraceRoot(
  root: CollectionTraceRoot,
): CollectionTraceRoot {
  return {
    nodes: root.nodes.map((node) => {
      if (node.kind === "sources_merged") {
        return { ...node };
      }

      return {
        ...node,
        reasoningBursts: node.reasoningBursts.map((burst) => ({ ...burst })),
        collectGroups: node.collectGroups.map((group) => ({
          ...group,
          collect: {
            ...group.collect,
            entries: group.collect.entries.map(cloneCollectEntry),
          },
          summary: group.summary ? { ...group.summary } : null,
        })),
      };
    }),
  };
}

function countPlanRounds(root: CollectionTraceRoot) {
  return root.nodes.filter((node) => node.kind === "plan_round").length;
}

function getLastPlanRoundIndex(root: CollectionTraceRoot) {
  for (let index = root.nodes.length - 1; index >= 0; index -= 1) {
    if (root.nodes[index]?.kind === "plan_round") {
      return index;
    }
  }

  return -1;
}

function mapCollectStatus(
  status: CollectSummaryStatus,
): Exclude<CollectionTraceStatus, "running"> {
  return status === "risk_blocked" ? "failed" : "completed";
}

function createReasoningBurst(args: {
  id: string;
  occurredAt: string;
  detail: string;
}): CollectionReasoningBurst {
  return {
    id: args.id,
    kind: "reasoning_burst",
    occurredAt: args.occurredAt,
    detail: args.detail.trim(),
  };
}

function createPlanRoundNode(args: {
  revisionId: string | null;
  roundIndex: number;
  occurredAt: string;
}): CollectionPlanRoundNode {
  return {
    id: `plan-round:${args.revisionId ?? "unknown"}:${args.roundIndex}`,
    kind: "plan_round",
    revisionId: args.revisionId,
    roundIndex: args.roundIndex,
    label: `规划轮次 ${args.roundIndex}`,
    status: "running",
    occurredAt: args.occurredAt,
    reasoningBursts: [],
    collectGroups: [],
  };
}

function createCollectGroup(args: {
  revisionId: string | null;
  toolCallId: string;
  subtaskId?: string | null;
  collectTarget?: string | null;
  occurredAt: string;
}): CollectionCollectGroup {
  const collectLabel = args.collectTarget ?? "正在搜索与读取资料";

  return {
    id: `collect-group:${args.toolCallId}`,
    revisionId: args.revisionId,
    toolCallId: args.toolCallId,
    subtaskId: args.subtaskId ?? undefined,
    collectTarget: args.collectTarget ?? undefined,
    occurredAt: args.occurredAt,
    collect: {
      id: `collect:${args.toolCallId}`,
      kind: "collect",
      label: collectLabel,
      status: "running",
      occurredAt: args.occurredAt,
      entries: [],
    },
    summary: null,
  };
}

function completeLastPlanRound(root: CollectionTraceRoot) {
  const lastPlanRoundIndex = getLastPlanRoundIndex(root);

  if (lastPlanRoundIndex === -1) {
    return;
  }

  const lastPlanRound = root.nodes[lastPlanRoundIndex];

  if (lastPlanRound?.kind !== "plan_round") {
    return;
  }

  lastPlanRound.status = "completed";
}

function ensurePlanRoundForPlannerReasoning(
  root: CollectionTraceRoot,
  args: {
    revisionId: string | null;
    occurredAt: string;
  },
): CollectionPlanRoundNode {
  const lastPlanRoundIndex = getLastPlanRoundIndex(root);
  const lastPlanRound =
    lastPlanRoundIndex === -1 ? null : root.nodes[lastPlanRoundIndex];

  if (lastPlanRound?.kind === "plan_round" && lastPlanRound.collectGroups.length === 0) {
    return lastPlanRound;
  }

  if (lastPlanRound?.kind === "plan_round") {
    lastPlanRound.status = "completed";
  }

  const nextPlanRound = createPlanRoundNode({
    revisionId: args.revisionId,
    roundIndex: countPlanRounds(root) + 1,
    occurredAt: args.occurredAt,
  });

  root.nodes.push(nextPlanRound);

  return nextPlanRound;
}

function ensurePlanRoundForCollectGroup(
  root: CollectionTraceRoot,
  args: {
    revisionId: string | null;
    occurredAt: string;
  },
): CollectionPlanRoundNode {
  const lastPlanRoundIndex = getLastPlanRoundIndex(root);

  if (lastPlanRoundIndex !== -1) {
    const lastPlanRound = root.nodes[lastPlanRoundIndex];

    if (lastPlanRound?.kind === "plan_round") {
      return lastPlanRound;
    }
  }

  const nextPlanRound = createPlanRoundNode({
    revisionId: args.revisionId,
    roundIndex: countPlanRounds(root) + 1,
    occurredAt: args.occurredAt,
  });

  root.nodes.push(nextPlanRound);

  return nextPlanRound;
}

function appendPlanReasoningBurst(
  planRound: CollectionPlanRoundNode,
  args: {
    revisionId: string | null;
    seq: number;
    occurredAt: string;
    detail: string;
  },
) {
  const lastBurst = planRound.reasoningBursts.at(-1);

  if (lastBurst) {
    lastBurst.detail = appendLine(lastBurst.detail, args.detail);
    lastBurst.occurredAt = args.occurredAt;
    return;
  }

  planRound.reasoningBursts.push(
    createReasoningBurst({
      id: `plan-reasoning:${args.revisionId ?? "unknown"}:${planRound.roundIndex}:${args.seq}`,
      occurredAt: args.occurredAt,
      detail: args.detail,
    }),
  );
}

function findCollectGroupLocation(
  root: CollectionTraceRoot,
  args: {
    toolCallId?: string | null;
    subtaskId?: string | null;
  },
) {
  for (let nodeIndex = root.nodes.length - 1; nodeIndex >= 0; nodeIndex -= 1) {
    const node = root.nodes[nodeIndex];

    if (node?.kind !== "plan_round") {
      continue;
    }

    for (
      let groupIndex = node.collectGroups.length - 1;
      groupIndex >= 0;
      groupIndex -= 1
    ) {
      const group = node.collectGroups[groupIndex];

      if (args.toolCallId && group?.toolCallId === args.toolCallId) {
        return { nodeIndex, groupIndex };
      }

      if (args.subtaskId && group?.subtaskId === args.subtaskId) {
        return { nodeIndex, groupIndex };
      }
    }
  }

  return null;
}

function ensureCollectGroup(
  root: CollectionTraceRoot,
  args: {
    revisionId: string | null;
    toolCallId: string;
    subtaskId?: string | null;
    collectTarget?: string | null;
    occurredAt: string;
  },
): CollectionCollectGroup {
  const location = findCollectGroupLocation(root, {
    toolCallId: args.toolCallId,
    subtaskId: args.subtaskId,
  });

  if (location !== null) {
    const planRound = root.nodes[location.nodeIndex];

    if (planRound?.kind !== "plan_round") {
      throw new Error("expected plan round for collect group");
    }

    const group = planRound.collectGroups[location.groupIndex];

    if (!group) {
      throw new Error("expected collect group");
    }

    group.revisionId = args.revisionId ?? group.revisionId;
    group.subtaskId = args.subtaskId ?? group.subtaskId;
    group.collectTarget = args.collectTarget ?? group.collectTarget;
    group.occurredAt = args.occurredAt;
    group.collect.label = args.collectTarget ?? group.collectTarget ?? group.collect.label;
    group.collect.occurredAt = args.occurredAt;

    return group;
  }

  const planRound = ensurePlanRoundForCollectGroup(root, {
    revisionId: args.revisionId,
    occurredAt: args.occurredAt,
  });
  const nextGroup = createCollectGroup(args);

  planRound.collectGroups.push(nextGroup);

  return nextGroup;
}

function appendCollectReasoningBurst(
  group: CollectionCollectGroup,
  args: {
    seq: number;
    occurredAt: string;
    detail: string;
  },
) {
  const lastEntry = group.collect.entries.at(-1);

  if (lastEntry?.kind === "reasoning_burst") {
    lastEntry.detail = appendLine(lastEntry.detail, args.detail);
    lastEntry.occurredAt = args.occurredAt;
  } else {
    group.collect.entries.push(
      createReasoningBurst({
        id: `collect-reasoning:${group.toolCallId}:${args.seq}`,
        occurredAt: args.occurredAt,
        detail: args.detail,
      }),
    );
  }

  group.collect.occurredAt = args.occurredAt;
}

function appendToolEvent(group: CollectionCollectGroup, event: CollectionToolEvent) {
  group.collect.entries.push(event);
  group.collect.occurredAt = event.occurredAt;
}

function appendCollectCompletedEvent(
  group: CollectionCollectGroup,
  event: CollectionCollectCompletedEvent,
) {
  group.collect.entries.push(event);
  group.collect.occurredAt = event.occurredAt;
  group.collect.status = event.status;
}

function buildSummaryDetail(
  event: Extract<EventEnvelope, { event: "summary.completed" }>,
) {
  if (event.payload.message) {
    return event.payload.message;
  }

  return event.payload.key_findings_markdown ?? undefined;
}

function toSearchStartedEvent(
  event: Extract<EventEnvelope, { event: "collector.search.started" }>,
): CollectionToolEvent {
  return {
    id: `search-started:${event.payload.tool_call_id}:${event.seq}`,
    kind: "search_started",
    occurredAt: event.timestamp,
    label: "开始搜索",
    detail: event.payload.search_query,
  };
}

function toSearchCompletedEvent(
  event: Extract<EventEnvelope, { event: "collector.search.completed" }>,
): CollectionToolEvent {
  return {
    id: `search-completed:${event.payload.tool_call_id}:${event.seq}`,
    kind: "search_completed",
    occurredAt: event.timestamp,
    label: "搜索完成",
    detail: `${event.payload.result_count} 条结果`,
  };
}

function toFetchStartedEvent(
  event: Extract<EventEnvelope, { event: "collector.fetch.started" }>,
): CollectionToolEvent {
  return {
    id: `fetch-started:${event.payload.tool_call_id}:${event.seq}`,
    kind: "fetch_started",
    occurredAt: event.timestamp,
    label: "开始读取资料",
    detail: event.payload.url,
  };
}

function toFetchCompletedEvent(
  event: Extract<EventEnvelope, { event: "collector.fetch.completed" }>,
): CollectionToolEvent {
  return {
    id: `fetch-completed:${event.payload.tool_call_id}:${event.seq}`,
    kind: "fetch_completed",
    occurredAt: event.timestamp,
    label: event.payload.success ? "读取完成" : "读取失败",
    detail: event.payload.success
      ? event.payload.title ?? event.payload.url
      : event.payload.url,
  };
}

export function reduceCollectionTrace(
  root: CollectionTraceRoot,
  event: EventEnvelope,
): CollectionTraceRoot {
  switch (event.event) {
    case "planner.reasoning.delta": {
      const nextRoot = cloneCollectionTraceRoot(root);
      const planRound = ensurePlanRoundForPlannerReasoning(nextRoot, {
        revisionId: event.revision_id,
        occurredAt: event.timestamp,
      });

      appendPlanReasoningBurst(planRound, {
        revisionId: event.revision_id,
        seq: event.seq,
        occurredAt: event.timestamp,
        detail: event.payload.delta,
      });

      return nextRoot;
    }
    case "planner.tool_call.requested": {
      const nextRoot = cloneCollectionTraceRoot(root);

      ensureCollectGroup(nextRoot, {
        revisionId: event.revision_id,
        toolCallId: event.payload.tool_call_id,
        collectTarget: event.payload.collect_target,
        occurredAt: event.timestamp,
      });

      return nextRoot;
    }
    case "collector.reasoning.delta": {
      const nextRoot = cloneCollectionTraceRoot(root);
      const group = ensureCollectGroup(nextRoot, {
        revisionId: event.revision_id,
        toolCallId: event.payload.tool_call_id,
        subtaskId: event.payload.subtask_id,
        occurredAt: event.timestamp,
      });

      appendCollectReasoningBurst(group, {
        seq: event.seq,
        occurredAt: event.timestamp,
        detail: event.payload.delta,
      });

      return nextRoot;
    }
    case "collector.search.started": {
      const nextRoot = cloneCollectionTraceRoot(root);
      const group = ensureCollectGroup(nextRoot, {
        revisionId: event.revision_id,
        toolCallId: event.payload.tool_call_id,
        subtaskId: event.payload.subtask_id,
        occurredAt: event.timestamp,
      });

      appendToolEvent(group, toSearchStartedEvent(event));

      return nextRoot;
    }
    case "collector.search.completed": {
      const nextRoot = cloneCollectionTraceRoot(root);
      const group = ensureCollectGroup(nextRoot, {
        revisionId: event.revision_id,
        toolCallId: event.payload.tool_call_id,
        subtaskId: event.payload.subtask_id,
        occurredAt: event.timestamp,
      });

      appendToolEvent(group, toSearchCompletedEvent(event));

      return nextRoot;
    }
    case "collector.fetch.started": {
      const nextRoot = cloneCollectionTraceRoot(root);
      const group = ensureCollectGroup(nextRoot, {
        revisionId: event.revision_id,
        toolCallId: event.payload.tool_call_id,
        subtaskId: event.payload.subtask_id,
        occurredAt: event.timestamp,
      });

      appendToolEvent(group, toFetchStartedEvent(event));

      return nextRoot;
    }
    case "collector.fetch.completed": {
      const nextRoot = cloneCollectionTraceRoot(root);
      const group = ensureCollectGroup(nextRoot, {
        revisionId: event.revision_id,
        toolCallId: event.payload.tool_call_id,
        subtaskId: event.payload.subtask_id,
        occurredAt: event.timestamp,
      });

      appendToolEvent(group, toFetchCompletedEvent(event));

      return nextRoot;
    }
    case "collector.completed": {
      const nextRoot = cloneCollectionTraceRoot(root);
      const group = ensureCollectGroup(nextRoot, {
        revisionId: event.revision_id,
        toolCallId: event.payload.tool_call_id,
        subtaskId: event.payload.subtask_id,
        occurredAt: event.timestamp,
      });

      appendCollectCompletedEvent(group, {
        id: `collect-completed:${event.payload.tool_call_id}:${event.seq}`,
        kind: "collect_completed",
        occurredAt: event.timestamp,
        status: mapCollectStatus(event.payload.status),
        detail:
          event.payload.status === "risk_blocked"
            ? "搜集受阻"
            : `搜集完成：${event.payload.item_count} 条资料`,
      });

      return nextRoot;
    }
    case "summary.completed": {
      const nextRoot = cloneCollectionTraceRoot(root);
      const group = ensureCollectGroup(nextRoot, {
        revisionId: event.revision_id,
        toolCallId: event.payload.tool_call_id,
        subtaskId: event.payload.subtask_id,
        collectTarget: event.payload.collect_target,
        occurredAt: event.timestamp,
      });
      const summary: CollectionSummaryNode = {
        id: `summary:${event.payload.tool_call_id}:${event.payload.subtask_id}`,
        kind: "summary",
        occurredAt: event.timestamp,
        status: mapCollectStatus(event.payload.status),
        detail: buildSummaryDetail(event),
      };

      group.summary = summary;

      return nextRoot;
    }
    case "sources.merged": {
      const nextRoot = cloneCollectionTraceRoot(root);

      completeLastPlanRound(nextRoot);
      nextRoot.nodes.push({
        id: `sources-merged:${event.seq}`,
        kind: "sources_merged",
        occurredAt: event.timestamp,
        status: "completed",
        sourceCountBeforeMerge: event.payload.source_count_before_merge,
        sourceCountAfterMerge: event.payload.source_count_after_merge,
        referenceCount: event.payload.reference_count,
        detail: `来源去重：${event.payload.source_count_before_merge} -> ${event.payload.source_count_after_merge}，引用 ${event.payload.reference_count} 条`,
      });

      return nextRoot;
    }
    default:
      return root;
  }
}
