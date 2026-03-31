"use client";

import { useMemo, useRef } from "react";

import { ClarificationDetailPanel } from "./clarification-panels";
import { ArtifactGallery } from "./artifact-gallery";
import { DeliveryActions } from "./delivery-actions";
import { OutlineCard } from "./outline-card";
import { RequirementSummaryCard } from "./requirement-summary-card";
import { ReportCanvas } from "./report-canvas";
import { useClarificationCountdown } from "../hooks/use-clarification-countdown";
import { useHeartbeatLoop } from "../hooks/use-heartbeat-loop";
import { useWorkspaceCardAnchor } from "../hooks/use-workspace-card-anchor";
import { useTaskStream } from "../hooks/use-task-stream";
import { useResearchSessionStore } from "../providers/research-workspace-providers";
import { SessionStatusBar } from "./session-status-bar";
import { TerminalBanner } from "./terminal-banner";
import { TimelinePanel } from "./timeline-panel";

const PHASE_ORDER = [
  "clarifying",
  "analyzing_requirement",
  "planning_collection",
  "collecting",
  "summarizing_collection",
  "merging_sources",
  "preparing_outline",
  "writing_report",
  "delivered",
  "processing_feedback",
] as const;

const CARD_ANCHORS = [
  "clarification",
  "requirementSummary",
  "collectionTrace",
  "outline",
  "report",
] as const;

type WorkspaceCardAnchor = (typeof CARD_ANCHORS)[number];

function isPhaseAtOrAfter(
  phase: (typeof PHASE_ORDER)[number],
  targetPhase: (typeof PHASE_ORDER)[number],
) {
  return PHASE_ORDER.indexOf(phase) >= PHASE_ORDER.indexOf(targetPhase);
}

export function ResearchWorkspaceShell() {
  useTaskStream();
  useHeartbeatLoop();
  useClarificationCountdown();

  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);
  const timelineItems = useResearchSessionStore(
    (state) => state.stream.timeline,
  );
  const requirementDetail = useResearchSessionStore(
    (state) => state.remote.currentRevision?.requirement_detail ?? null,
  );
  const outline = useResearchSessionStore((state) => state.stream.outline);
  const outlineReady = useResearchSessionStore(
    (state) => state.stream.outlineReady,
  );
  const clarificationRef = useRef<HTMLDivElement | null>(null);
  const requirementSummaryRef = useRef<HTMLDivElement | null>(null);
  const collectionTraceRef = useRef<HTMLDivElement | null>(null);
  const outlineRef = useRef<HTMLDivElement | null>(null);
  const reportRef = useRef<HTMLDivElement | null>(null);
  if (snapshot === null) {
    return null;
  }

  const shouldShowRequirementSummary = isPhaseAtOrAfter(
    snapshot.phase,
    "analyzing_requirement",
  );
  const shouldShowCollectionTrace = isPhaseAtOrAfter(
    snapshot.phase,
    "planning_collection",
  );
  const shouldShowOutline =
    isPhaseAtOrAfter(snapshot.phase, "preparing_outline") &&
    outlineReady &&
    outline !== null;
  const shouldShowReport = isPhaseAtOrAfter(snapshot.phase, "writing_report");
  const shouldShowArtifactGallery = isPhaseAtOrAfter(
    snapshot.phase,
    "writing_report",
  );
  const activeCardAnchor = useMemo<WorkspaceCardAnchor | null>(() => {
    if (snapshot.phase === "clarifying") {
      return "clarification";
    }

    if (shouldShowReport) {
      return "report";
    }

    if (shouldShowOutline) {
      return "outline";
    }

    if (shouldShowCollectionTrace) {
      return "collectionTrace";
    }

    if (shouldShowRequirementSummary) {
      return "requirementSummary";
    }

    return null;
  }, [
    shouldShowCollectionTrace,
    shouldShowOutline,
    shouldShowReport,
    shouldShowRequirementSummary,
    snapshot.phase,
  ]);
  const cardAnchorRefs = useMemo(
    () => ({
      clarification: clarificationRef,
      requirementSummary: requirementSummaryRef,
      collectionTrace: collectionTraceRef,
      outline: outlineRef,
      report: reportRef,
    }),
    [],
  );

  useWorkspaceCardAnchor(activeCardAnchor, cardAnchorRefs);

  return (
    <section className="space-y-sp-10 pb-32">
      <SessionStatusBar />
      <TerminalBanner />

      <div className="space-y-sp-10">
        <div
          className="animate-fade-in-up"
          data-research-card-anchor="clarification"
          ref={clarificationRef}
        >
          <ClarificationDetailPanel />
        </div>
        {shouldShowRequirementSummary ? (
          <div
            className="animate-fade-in-up stagger-1"
            data-research-card-anchor="requirementSummary"
            ref={requirementSummaryRef}
          >
            <RequirementSummaryCard requirementDetail={requirementDetail} />
          </div>
        ) : null}
        {shouldShowCollectionTrace ? (
          <div
            className="animate-fade-in-up stagger-2"
            data-research-card-anchor="collectionTrace"
            ref={collectionTraceRef}
          >
            <TimelinePanel items={timelineItems} />
          </div>
        ) : null}
        {shouldShowOutline ? (
          <div
            className="animate-fade-in-up stagger-3"
            data-research-card-anchor="outline"
            ref={outlineRef}
          >
            <OutlineCard />
          </div>
        ) : null}
        {shouldShowReport ? (
          <div
            className="animate-fade-in-up stagger-4"
            data-research-card-anchor="report"
            ref={reportRef}
          >
            <ReportCanvas />
          </div>
        ) : null}
        {shouldShowArtifactGallery ? (
          <div className="animate-fade-in-up stagger-5">
            <ArtifactGallery />
          </div>
        ) : null}
        <div className="animate-fade-in-up stagger-6">
          <DeliveryActions />
        </div>
      </div>
    </section>
  );
}
