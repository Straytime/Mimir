import type { EventEnvelope } from "@/lib/contracts";

import type { ResearchSessionState } from "../store/research-session-store.types";
import { reduceCollectionTrace } from "./collection-trace-builder";

export type TimelineStreamState = Pick<
  ResearchSessionState["stream"],
  "collectionTrace" | "outlineReady"
>;

const COLLECTION_TRACE_EVENTS = new Set<EventEnvelope["event"]>([
  "phase.changed",
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
]);

export function reduceTimelineStream(
  stream: TimelineStreamState,
  event: EventEnvelope,
): TimelineStreamState {
  const nextCollectionTrace =
    COLLECTION_TRACE_EVENTS.has(event.event) &&
    (event.event !== "phase.changed" ||
      event.payload.to_phase === "planning_collection")
      ? reduceCollectionTrace(stream.collectionTrace, event)
      : stream.collectionTrace;

  switch (event.event) {
    case "outline.delta":
      return {
        ...stream,
        collectionTrace: nextCollectionTrace,
        outlineReady: false,
      };
    case "outline.completed":
      return {
        ...stream,
        collectionTrace: nextCollectionTrace,
        outlineReady: true,
      };
    default:
      return {
        ...stream,
        collectionTrace: nextCollectionTrace,
      };
  }
}
