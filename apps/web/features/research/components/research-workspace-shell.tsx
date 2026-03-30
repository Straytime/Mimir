"use client";

import { ClarificationDetailPanel } from "./clarification-panels";
import { ArtifactGallery } from "./artifact-gallery";
import { DeliveryActions } from "./delivery-actions";
import { OutlineCard } from "./outline-card";
import { RequirementSummaryCard } from "./requirement-summary-card";
import { ReportCanvas } from "./report-canvas";
import { useClarificationCountdown } from "../hooks/use-clarification-countdown";
import { useHeartbeatLoop } from "../hooks/use-heartbeat-loop";
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
  if (snapshot === null) {
    return null;
  }

  const shouldShowRequirementSummary = isPhaseAtOrAfter(
    snapshot.phase,
    "analyzing_requirement",
  );
  const shouldShowCollectionTrace =
    isPhaseAtOrAfter(snapshot.phase, "planning_collection") &&
    !isPhaseAtOrAfter(snapshot.phase, "preparing_outline");
  const shouldShowOutline =
    isPhaseAtOrAfter(snapshot.phase, "preparing_outline") &&
    outlineReady &&
    outline !== null;
  const shouldShowReport = isPhaseAtOrAfter(snapshot.phase, "writing_report");
  const shouldShowArtifactGallery = isPhaseAtOrAfter(
    snapshot.phase,
    "writing_report",
  );

  return (
    <section className="space-y-sp-10 pb-32">
      <SessionStatusBar />
      <TerminalBanner />

      <div className="space-y-sp-10">
        <div className="animate-fade-in-up">
          <ClarificationDetailPanel />
        </div>
        {shouldShowRequirementSummary ? (
          <div className="animate-fade-in-up stagger-1">
            <RequirementSummaryCard requirementDetail={requirementDetail} />
          </div>
        ) : null}
        {shouldShowCollectionTrace ? (
          <div className="animate-fade-in-up stagger-2">
            <TimelinePanel items={timelineItems} />
          </div>
        ) : null}
        {shouldShowOutline ? (
          <div className="animate-fade-in-up stagger-3">
            <OutlineCard />
          </div>
        ) : null}
        {shouldShowReport ? (
          <div className="animate-fade-in-up stagger-4">
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
