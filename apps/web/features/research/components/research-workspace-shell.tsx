"use client";

import { useMemo, useRef } from "react";

import {
  ClarificationDetailPanel,
  OptionsClarificationCountdownSurface,
} from "./clarification-panels";
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

function hasClarificationContent(args: {
  clarificationText: string;
  questionCount: number;
}) {
  return args.clarificationText.trim().length > 0 || args.questionCount > 0;
}

function hasOutlineContent(args: {
  outlineReady: boolean;
  sectionCount: number;
}) {
  return args.outlineReady && args.sectionCount > 0;
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
  const delivery = useResearchSessionStore((state) => state.remote.delivery);
  const clarificationRef = useRef<HTMLDivElement | null>(null);
  const requirementSummaryRef = useRef<HTMLDivElement | null>(null);
  const collectionTraceRef = useRef<HTMLDivElement | null>(null);
  const outlineRef = useRef<HTMLDivElement | null>(null);
  const reportRef = useRef<HTMLDivElement | null>(null);
  const deliveryRef = useRef<HTMLDivElement | null>(null);
  if (snapshot === null) {
    return null;
  }

  const clarificationQuestionCount = questionSet?.questions.length ?? 0;
  const outlineSectionCount = outline?.sections.length ?? 0;
  const shouldShowClarification =
    snapshot.phase === "clarifying" &&
    hasClarificationContent({
      clarificationText,
      questionCount: clarificationQuestionCount,
    });
  const shouldShowRequirementSummary =
    isPhaseAtOrAfter(snapshot.phase, "analyzing_requirement") &&
    requirementDetail !== null;
  const shouldShowCollectionTrace =
    isPhaseAtOrAfter(snapshot.phase, "planning_collection") &&
    collectionTrace.nodes.length > 0;
  const shouldShowOutline =
    isPhaseAtOrAfter(snapshot.phase, "preparing_outline") &&
    hasOutlineContent({
      outlineReady,
      sectionCount: outlineSectionCount,
    });
  const shouldShowReport =
    isPhaseAtOrAfter(snapshot.phase, "writing_report") &&
    reportMarkdown.trim().length > 0;
  const shouldShowDelivery =
    snapshot.phase === "delivered" && delivery !== null;
  const activeCardAnchor = useMemo<WorkspaceCardAnchor | null>(() => {
    if (shouldShowClarification) {
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
    shouldShowClarification,
    shouldShowOutline,
    shouldShowReport,
    shouldShowRequirementSummary,
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
  const cardAnchorTargets = useMemo(
    () => ({
      clarification: {
        selector: "[data-research-anchor-target='clarification-title']",
      },
      requirementSummary: {
        selector: "[data-research-anchor-target='requirement-summary-content']",
      },
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
          shouldShowClarification ? "card-visible" : "card-hidden",
          clarificationText.trim().length > 0 ? "text-ready" : "text-pending",
          clarificationQuestionCount,
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
    clarificationQuestionCount,
    clarificationText,
    collectionTrace.nodes.length,
    outline,
    outlineReady,
    reportMarkdown,
    requirementDetail,
    shouldShowClarification,
    shouldShowDelivery,
    snapshot.phase,
  ]);

  useWorkspaceCardAnchor(
    activeCardAnchor,
    cardAnchorRefs,
    anchorSignal,
    cardAnchorTargets,
  );

  return (
    <section className="space-y-sp-10 pb-32">
      <div
        className="sticky top-0 z-50"
        data-research-top-stack="true"
      >
        <SessionStatusBar />
        <OptionsClarificationCountdownSurface />
        <div className="pt-3">
          <TerminalBanner />
        </div>
      </div>

      <div className="space-y-sp-10">
        {shouldShowClarification ? (
          <div
            className="animate-fade-in-up"
            data-research-card-anchor="clarification"
            ref={clarificationRef}
          >
            <ClarificationDetailPanel />
          </div>
        ) : null}
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
