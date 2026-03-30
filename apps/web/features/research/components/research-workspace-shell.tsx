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

  if (snapshot === null) {
    return null;
  }

  return (
    <section className="space-y-sp-10 pb-32">
      <SessionStatusBar />
      <TerminalBanner />

      <div className="space-y-sp-10">
        <div className="animate-fade-in-up">
          <ClarificationDetailPanel />
        </div>
        <div className="animate-fade-in-up stagger-1">
          <RequirementSummaryCard requirementDetail={requirementDetail} />
        </div>
        <div className="animate-fade-in-up stagger-2">
          <TimelinePanel items={timelineItems} />
        </div>
        <div className="animate-fade-in-up stagger-3">
          <OutlineCard />
        </div>
        <div className="animate-fade-in-up stagger-4">
          <ReportCanvas />
        </div>
        <div className="animate-fade-in-up stagger-5">
          <ArtifactGallery />
        </div>
        <div className="animate-fade-in-up stagger-6">
          <DeliveryActions />
        </div>
      </div>
    </section>
  );
}
