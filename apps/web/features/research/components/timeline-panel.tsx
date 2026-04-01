"use client";

import type { ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

import type {
  CollectionCollectEntry,
  CollectionCollectGroup,
  CollectionCollectCompletedEvent,
  CollectionPlanRoundNode,
  CollectionReasoningBurst,
  CollectionSummaryNode,
  CollectionToolEvent,
  CollectionTraceRoot,
} from "../store/research-session-store.types";
import { RESEARCH_CARD_MAX_HEIGHT_STYLE_VALUE } from "../utils/layout-vars";
import { PulseIndicator } from "./pulse-indicator";

type TimelinePanelProps = {
  trace: CollectionTraceRoot;
};

function getStatusLabel(status: "running" | "completed" | "failed") {
  if (status === "completed") {
    return "已完成";
  }

  if (status === "failed") {
    return "已失败";
  }

  return "进行中";
}

function getStatusClassName(status: "running" | "completed" | "failed") {
  if (status === "completed") {
    return "bg-surface-container-high text-surface-tint";
  }

  if (status === "failed") {
    return "bg-surface-container-high text-[#FF6B6B]";
  }

  return "bg-surface-container-high text-surface-tint";
}

function getPreviewLine(detail: string | undefined) {
  if (!detail) {
    return "";
  }

  const normalized = detail
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => line.length > 0);

  return normalized ?? detail.trim();
}

function hasExpandableContent(detail: string | undefined) {
  if (!detail) {
    return false;
  }

  const preview = getPreviewLine(detail);

  return preview.length > 0 && preview !== detail.trim();
}

type ToolRowKind = "search" | "fetch";
type ToolRowStatus = "started" | "done";

type MergedToolRowEntry = {
  id: string;
  kind: "tool_row";
  occurredAt: string;
  tool: ToolRowKind;
  detail?: string;
  status: ToolRowStatus;
};

type RenderableCollectEntry =
  | CollectionReasoningBurst
  | CollectionCollectCompletedEvent
  | MergedToolRowEntry;

function getToolRowLabel(tool: ToolRowKind) {
  return tool === "search" ? "Search" : "Fetch";
}

function getToolRowStatusLabel(status: ToolRowStatus) {
  return status === "done" ? "Done" : "Started";
}

function getToolKindFromEventKind(kind: CollectionToolEvent["kind"]): ToolRowKind {
  return kind.startsWith("search") ? "search" : "fetch";
}

function isMatchingToolCompletion(
  startedEvent: CollectionToolEvent,
  nextEntry: CollectionCollectEntry | undefined,
) {
  if (nextEntry === undefined) {
    return false;
  }

  return (
    (startedEvent.kind === "search_started" && nextEntry.kind === "search_completed") ||
    (startedEvent.kind === "fetch_started" && nextEntry.kind === "fetch_completed")
  );
}

function mergeCollectEntries(entries: CollectionCollectEntry[]): RenderableCollectEntry[] {
  const mergedEntries: RenderableCollectEntry[] = [];

  for (let entryIndex = 0; entryIndex < entries.length; entryIndex += 1) {
    const entry = entries[entryIndex];

    if (entry.kind === "reasoning_burst" || entry.kind === "collect_completed") {
      mergedEntries.push(entry);
      continue;
    }

    if (entry.kind === "search_started" || entry.kind === "fetch_started") {
      const nextEntry = entries[entryIndex + 1];
      const hasMatchingCompletion = isMatchingToolCompletion(entry, nextEntry);

      mergedEntries.push({
        id: hasMatchingCompletion ? `${entry.id}:${nextEntry.id}` : entry.id,
        kind: "tool_row",
        occurredAt: entry.occurredAt,
        tool: getToolKindFromEventKind(entry.kind),
        detail: entry.detail ?? (hasMatchingCompletion ? nextEntry.detail : undefined),
        status: hasMatchingCompletion ? "done" : "started",
      });

      if (hasMatchingCompletion) {
        entryIndex += 1;
      }

      continue;
    }

    mergedEntries.push({
      id: entry.id,
      kind: "tool_row",
      occurredAt: entry.occurredAt,
      tool: getToolKindFromEventKind(entry.kind),
      detail: entry.detail,
      status: "done",
    });
  }

  return mergedEntries;
}

function formatToolRowDetail(tool: ToolRowKind, detail: string | undefined) {
  if (!detail) {
    return null;
  }

  if (tool !== "fetch") {
    return {
      text: detail,
      title: detail,
    };
  }

  try {
    const url = new URL(detail);
    const normalizedPath = `${url.pathname}${url.search}${url.hash}` || "/";
    const maxPathLength = 44;
    const truncatedPath =
      normalizedPath.length > maxPathLength
        ? `${normalizedPath.slice(0, maxPathLength - 1)}…`
        : normalizedPath;

    return {
      text: `${url.host}${truncatedPath}`,
      title: detail,
    };
  } catch {
    const fallbackLength = 64;
    return {
      text:
        detail.length > fallbackLength
          ? `${detail.slice(0, fallbackLength - 1)}…`
          : detail,
      title: detail,
    };
  }
}

type StatusBadgeProps = {
  status: "running" | "completed" | "failed";
};

function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-2 whitespace-nowrap px-3 py-1 text-[11px] font-ui font-medium uppercase tracking-[0.15em] ${getStatusClassName(status)}`}
    >
      {status === "running" ? <PulseIndicator /> : null}
      {getStatusLabel(status)}
    </span>
  );
}

type ExpandableTextProps = {
  blockId: string;
  label: string;
  detail?: string;
  expandedBlocks: Record<string, boolean>;
  onToggle: (blockId: string) => void;
  className?: string;
};

function ExpandableText({
  blockId,
  label,
  detail,
  expandedBlocks,
  onToggle,
  className = "text-sm font-ui leading-6 text-secondary",
}: ExpandableTextProps) {
  if (!detail) {
    return null;
  }

  const isExpanded = expandedBlocks[blockId] ?? false;
  const expandable = hasExpandableContent(detail);
  const visibleText = isExpanded ? detail : getPreviewLine(detail);

  return (
    <div className="space-y-2">
      <p className={`${className} ${isExpanded ? "whitespace-pre-line" : ""}`}>
        {visibleText}
      </p>
      {expandable ? (
        <button
          aria-label={`${isExpanded ? "收起" : "展开"} ${label}`}
          className="text-xs font-ui font-semibold uppercase tracking-[0.15em] text-surface-tint"
          onClick={() => onToggle(blockId)}
          type="button"
        >
          {isExpanded ? "收起" : "展开"}
        </button>
      ) : null}
    </div>
  );
}

type EntryRowProps = {
  label: string;
  toneClassName: string;
  children?: ReactNode;
};

function EntryRow({ label, toneClassName, children }: EntryRowProps) {
  return (
    <div className={`rounded-2xl border border-surface-container-high px-4 py-4 ${toneClassName}`}>
      <p
        className="text-[11px] font-ui font-semibold uppercase tracking-[0.15em] text-tertiary"
        data-testid="collection-trace-entry-label"
      >
        {label}
      </p>
      {children ? <div className="mt-2">{children}</div> : null}
    </div>
  );
}

function ToolRow({ entry }: { entry: MergedToolRowEntry }) {
  const detail = formatToolRowDetail(entry.tool, entry.detail);

  return (
    <div
      className="collection-trace-tool-row collection-trace-tool-row--merged grid min-w-0 grid-cols-[auto,minmax(0,1fr),auto] items-center gap-3 bg-surface-container-low px-3 py-2"
      data-testid="collection-trace-tool-row"
    >
      <p
        className="text-[11px] font-ui font-semibold uppercase tracking-[0.15em] text-tertiary"
        data-testid="collection-trace-entry-label"
      >
        {getToolRowLabel(entry.tool)}
      </p>
      <p
        className="min-w-0 truncate text-sm font-ui leading-5 text-secondary"
        data-testid="collection-trace-tool-row-object"
        title={detail?.title}
      >
        {detail?.text ?? ""}
      </p>
      <span className="text-[11px] font-ui font-medium uppercase tracking-[0.15em] text-tertiary">
        {getToolRowStatusLabel(entry.status)}
      </span>
    </div>
  );
}

function renderCollectEntry(args: {
  entry: RenderableCollectEntry;
  reasoningIndex: number;
  collectTargetLabel: string;
  expandedBlocks: Record<string, boolean>;
  onToggle: (blockId: string) => void;
}) {
  const { entry, reasoningIndex, collectTargetLabel, expandedBlocks, onToggle } = args;

  if (entry.kind === "reasoning_burst") {
    return (
      <EntryRow
        key={entry.id}
        label={`Reasoning ${reasoningIndex}`}
        toneClassName="bg-surface-container-low"
      >
        <div data-testid="collection-trace-reasoning-row">
          <ExpandableText
            blockId={entry.id}
            detail={entry.detail}
            expandedBlocks={expandedBlocks}
            label={`Collect ${collectTargetLabel} reasoning ${reasoningIndex}`}
            onToggle={onToggle}
          />
        </div>
      </EntryRow>
    );
  }

  if (entry.kind === "collect_completed") {
    return (
      <div
        key={entry.id}
        className="space-y-2 rounded-2xl border border-surface-container-high bg-surface-container px-4 py-4"
      >
        <p
          className="text-[11px] font-ui font-semibold uppercase tracking-[0.15em] text-tertiary"
          data-testid="collection-trace-entry-label"
        >
          Collect Completed
        </p>
        <p className="text-sm font-ui leading-6 text-secondary">{entry.detail}</p>
      </div>
    );
  }

  return <ToolRow entry={entry} key={entry.id} />;
}

function CollectGroupCard(args: {
  group: CollectionCollectGroup;
  expandedBlocks: Record<string, boolean>;
  onToggle: (blockId: string) => void;
}) {
  const { group, expandedBlocks, onToggle } = args;
  const collectTargetLabel = group.collectTarget ?? group.collect.label;
  const mergedEntries = useMemo(
    () => mergeCollectEntries(group.collect.entries),
    [group.collect.entries],
  );
  let reasoningIndex = 0;

  return (
    <div className="space-y-4 border-l border-surface-container-high pl-4">
      <section
        aria-label={`Collect ${collectTargetLabel}`}
        className="rounded-3xl border border-surface-container-high bg-surface-container px-5 py-5"
        role="group"
      >
        <div className="flex flex-nowrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1 space-y-1">
            <h3 className="text-sm font-ui font-semibold uppercase tracking-[0.15em] text-primary">
              Collect
            </h3>
            <p className="min-w-0 text-sm font-ui font-semibold leading-6 text-primary">
              {collectTargetLabel}
            </p>
          </div>
          <StatusBadge status={group.collect.status} />
        </div>
        <div className="mt-4 space-y-2">
          {mergedEntries.map((entry) => {
            if (entry.kind === "reasoning_burst") {
              reasoningIndex += 1;
            }

            return renderCollectEntry({
              entry,
              reasoningIndex,
              collectTargetLabel,
              expandedBlocks,
              onToggle,
            });
          })}
        </div>
      </section>

      {group.summary ? (
        <SummaryCard
          collectTargetLabel={collectTargetLabel}
          expandedBlocks={expandedBlocks}
          onToggle={onToggle}
          summary={group.summary}
        />
      ) : null}
    </div>
  );
}

function SummaryCard(args: {
  summary: CollectionSummaryNode;
  collectTargetLabel: string;
  expandedBlocks: Record<string, boolean>;
  onToggle: (blockId: string) => void;
}) {
  const { summary, collectTargetLabel, expandedBlocks, onToggle } = args;

  return (
    <section className="rounded-3xl border border-surface-container-high bg-surface-container-low px-5 py-5">
      <div className="flex flex-nowrap items-start justify-between gap-4">
        <h3 className="text-sm font-ui font-semibold uppercase tracking-[0.15em] text-primary">
          Summary
        </h3>
        <StatusBadge status={summary.status} />
      </div>
      <div className="mt-3">
        <ExpandableText
          blockId={summary.id}
          detail={summary.detail}
          expandedBlocks={expandedBlocks}
          label={`Summary ${collectTargetLabel}`}
          onToggle={onToggle}
        />
      </div>
    </section>
  );
}

function PlanRoundCard(args: {
  node: CollectionPlanRoundNode;
  expandedBlocks: Record<string, boolean>;
  onToggle: (blockId: string) => void;
}) {
  const { node, expandedBlocks, onToggle } = args;

  return (
    <section className="rounded-3xl border border-surface-container-high bg-surface-container px-5 py-5">
      <div className="flex flex-nowrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1 space-y-1">
          <h2 className="text-base font-ui font-semibold text-primary">
            {`Plan Round ${node.roundIndex}`}
          </h2>
          <p className="text-[11px] font-ui uppercase tracking-[0.15em] text-tertiary">
            Planner Loop
          </p>
        </div>
        <StatusBadge status={node.status} />
      </div>

      {node.reasoningBursts.length > 0 ? (
        <div className="mt-4 space-y-3">
          {node.reasoningBursts.map((burst, index) => (
            <EntryRow
              key={burst.id}
              label={`Reasoning ${index + 1}`}
              toneClassName="bg-surface-container-low"
            >
              <ExpandableText
                blockId={burst.id}
                detail={burst.detail}
                expandedBlocks={expandedBlocks}
                label={`Plan Round ${node.roundIndex} reasoning ${index + 1}`}
                onToggle={onToggle}
              />
            </EntryRow>
          ))}
        </div>
      ) : null}

      {node.collectGroups.length > 0 ? (
        <div className="mt-5 space-y-4">
          {node.collectGroups.map((group) => (
            <CollectGroupCard
              expandedBlocks={expandedBlocks}
              group={group}
              key={group.id}
              onToggle={onToggle}
            />
          ))}
        </div>
      ) : null}
    </section>
  );
}

export function TimelinePanel({ trace }: TimelinePanelProps) {
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const [expandedBlocks, setExpandedBlocks] = useState<Record<string, boolean>>(
    {},
  );
  const nodes = trace.nodes;

  useEffect(() => {
    const container = scrollContainerRef.current;

    if (container === null || typeof container.scrollTo !== "function") {
      return;
    }

    container.scrollTo({
      top: container.scrollHeight,
      behavior: "smooth",
    });
  }, [trace]);

  const renderedNodes = useMemo(
    () =>
      nodes.map((node) => {
        if (node.kind === "sources_merged") {
          return (
            <section
              className="rounded-3xl border border-surface-container-high bg-surface-container-low px-5 py-5"
              key={node.id}
            >
              <div className="flex flex-nowrap items-start justify-between gap-4">
                <div className="min-w-0 flex-1 space-y-1">
                  <h2 className="text-base font-ui font-semibold text-primary">
                    Sources Merged
                  </h2>
                  <p className="text-[11px] font-ui uppercase tracking-[0.15em] text-tertiary">
                    Collection Finalization
                  </p>
                </div>
                <StatusBadge status={node.status} />
              </div>
              <p className="mt-3 text-sm font-ui leading-6 text-secondary">
                {node.detail}
              </p>
              <dl className="mt-4 grid grid-cols-1 gap-3 text-sm text-secondary sm:grid-cols-3">
                <div className="rounded-2xl bg-surface-container px-4 py-3">
                  <dt className="text-[11px] font-ui uppercase tracking-[0.15em] text-tertiary">
                    Before Merge
                  </dt>
                  <dd className="mt-1 font-ui font-semibold text-primary">
                    {node.sourceCountBeforeMerge}
                  </dd>
                </div>
                <div className="rounded-2xl bg-surface-container px-4 py-3">
                  <dt className="text-[11px] font-ui uppercase tracking-[0.15em] text-tertiary">
                    After Merge
                  </dt>
                  <dd className="mt-1 font-ui font-semibold text-primary">
                    {node.sourceCountAfterMerge}
                  </dd>
                </div>
                <div className="rounded-2xl bg-surface-container px-4 py-3">
                  <dt className="text-[11px] font-ui uppercase tracking-[0.15em] text-tertiary">
                    References
                  </dt>
                  <dd className="mt-1 font-ui font-semibold text-primary">
                    {node.referenceCount}
                  </dd>
                </div>
              </dl>
            </section>
          );
        }

        return (
          <PlanRoundCard
            expandedBlocks={expandedBlocks}
            key={node.id}
            node={node}
            onToggle={(blockId) => {
              setExpandedBlocks((current) => ({
                ...current,
                [blockId]: !current[blockId],
              }));
            }}
          />
        );
      }),
    [expandedBlocks, nodes],
  );

  return (
    <section
      aria-label="Collection Trace"
      className="flex flex-col overflow-hidden bg-surface-container-low p-6"
      role="region"
      style={{
        height: RESEARCH_CARD_MAX_HEIGHT_STYLE_VALUE,
        maxHeight: RESEARCH_CARD_MAX_HEIGHT_STYLE_VALUE,
      }}
    >
      <p className="text-[11px] font-ui font-semibold uppercase tracking-[0.15em] text-tertiary">
        Collection Trace
      </p>

      <div
        aria-live="polite"
        className="mt-4 min-h-0 flex-1 overflow-y-auto pr-1"
        ref={scrollContainerRef}
      >
        {nodes.length === 0 ? (
          <div className="bg-surface-container-lowest px-5 py-5 text-sm leading-7 text-tertiary">
            资料搜集会在这里逐步展开。
          </div>
        ) : (
          <div className="space-y-sp-6">{renderedNodes}</div>
        )}
      </div>
    </section>
  );
}
