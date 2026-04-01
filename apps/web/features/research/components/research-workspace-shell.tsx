"use client";

import { useMemo, useRef } from "react";

import { ClarificationDetailPanel } from "./clarification-panels";
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
  const collectionTrace = useResearchSessionStore(
    (state) => state.stream.collectionTrace,
  );
  const requirementDetail = useResearchSessionStore(
    (state) => state.remote.currentRevision?.requirement_detail ?? null,
  );
  const clarificationText = useResearchSessionStore(
    (state) => state.stream.clarificationText,
  );
  const questionSet = useResearchSessionStore((state) => state.stream.questionSet);
  const outline = useResearchSessionStore((state) => state.stream.outline);
  const outlineReady = useResearchSessionStore(
    (state) => state.stream.outlineReady,
  );
  const reportMarkdown = useResearchSessionStore(
    (state) => state.stream.reportMarkdown,
  );
  const clarificationRef = useRef<HTMLDivElement | null>(null);
  const requirementSummaryRef = useRef<HTMLDivElement | null>(null);
  const collectionTraceRef = useRef<HTMLDivElement | null>(null);
  const outlineRef = useRef<HTMLDivElement | null>(null);
  const reportRef = useRef<HTMLDivElement | null>(null);
  const deliveryRef = useRef<HTMLDivElement | null>(null);
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
  const shouldShowDelivery = snapshot.phase === "delivered";
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

  const anchorSignal = useMemo(() => {
    if (activeCardAnchor === null) {
      return null;
    }

    switch (activeCardAnchor) {
      case "clarification":
        return [
          snapshot.phase,
          clarificationText.trim().length > 0 ? "text-ready" : "text-pending",
          questionSet?.questions.length ?? 0,
        ].join(":");
      case "requirementSummary":
        return [
          snapshot.phase,
          requirementDetail === null ? "pending" : "ready",
        ].join(":");
      case "collectionTrace":
        return [
          snapshot.phase,
          collectionTrace.nodes.length > 0 ? "trace-ready" : "trace-pending",
        ].join(":");
      case "outline":
        return [
          snapshot.phase,
          outlineReady ? "outline-ready" : "outline-pending",
          outline?.sections.length ?? 0,
        ].join(":");
      case "report":
        return [
          snapshot.phase,
          reportMarkdown.trim().length > 0 ? "report-ready" : "report-pending",
          shouldShowDelivery ? "delivery-visible" : "delivery-hidden",
        ].join(":");
    }
  }, [
    activeCardAnchor,
    clarificationText,
    collectionTrace.nodes.length,
    outline,
    outlineReady,
    questionSet,
    reportMarkdown,
    requirementDetail,
    shouldShowDelivery,
    snapshot.phase,
  ]);

  useWorkspaceCardAnchor(activeCardAnchor, cardAnchorRefs, anchorSignal);

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
            <TimelinePanel trace={collectionTrace} />
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
        {shouldShowDelivery ? (
          <div
            className="animate-fade-in-up stagger-5"
            data-research-card-anchor="delivery"
            ref={deliveryRef}
          >
            <DeliveryActions />
          </div>
        ) : null}
      </div>
    </section>
  );
}
