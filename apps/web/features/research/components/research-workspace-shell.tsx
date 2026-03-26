"use client";

import {
  ClarificationActionPanel,
  ClarificationDetailPanel,
} from "./clarification-panels";
import { ArtifactGallery } from "./artifact-gallery";
import { DeliveryActions } from "./delivery-actions";
import { RequirementSummaryCard } from "./requirement-summary-card";
import { ReportCanvas } from "./report-canvas";
import { useClarificationCountdown } from "../hooks/use-clarification-countdown";
import { useHeartbeatLoop } from "../hooks/use-heartbeat-loop";
import { useTaskStream } from "../hooks/use-task-stream";
import { useResearchSessionStore } from "../providers/research-workspace-providers";
import { PulseIndicator } from "./pulse-indicator";
import { SessionStatusBar } from "./session-status-bar";
import { TerminalBanner } from "./terminal-banner";
import { TimelinePanel } from "./timeline-panel";

function getStageStatusCopy(phase: string) {
  switch (phase) {
    case "analyzing_requirement":
      return {
        eyebrow: "Requirement Analysis",
        title: "正在分析你的研究需求",
        description:
          "系统正在固化研究目标、范围与输出格式，完成后将进入规划与搜集。",
      };
    case "planning_collection":
      return {
        eyebrow: "Collection Planning",
        title: "正在规划研究路径",
        description: "规划器正在拆解搜集目标，规划后续子任务的执行路径。",
      };
    case "collecting":
      return {
        eyebrow: "Collection",
        title: "正在搜索与读取资料",
        description: "子任务正在按搜集目标搜索与读取资料，进展会同步到时间线。",
      };
    case "summarizing_collection":
      return {
        eyebrow: "Collection Summary",
        title: "正在整理阶段结论",
        description: "系统正在汇总每个搜集目标的阶段结论，为来源合并做准备。",
      };
    case "merging_sources":
      return {
        eyebrow: "Source Merge",
        title: "正在去重并整理引用",
        description: "系统正在合并重复来源，固定当前可用的引用集合。",
      };
    case "preparing_outline":
      return {
        eyebrow: "Outline Drafting",
        title: "正在构思报告结构",
        description: "系统正在基于搜集结果构思报告大纲与章节结构。",
      };
    case "writing_report":
      return {
        eyebrow: "Report Writing",
        title: "正在撰写报告与生成配图",
        description: "报告正文持续生成中，配图完成后会同步展示。",
      };
    case "processing_feedback":
      return {
        eyebrow: "Feedback Processing",
        title: "正在处理反馈",
        description: "系统正在根据你的反馈修订报告内容。",
      };
    case "delivered":
      return {
        eyebrow: "Delivery",
        title: "报告已完成并进入交付阶段",
        description: "报告已就绪，你可以下载或提交反馈。",
      };
    default:
      return {
        eyebrow: "Workspace",
        title: "工作台已接管当前任务",
        description: "当前任务仍在进行中，工作台会按阶段依次展示进展。",
      };
  }
}

export function ResearchWorkspaceShell() {
  useTaskStream();
  useHeartbeatLoop();
  useClarificationCountdown();

  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);
  const analysisText = useResearchSessionStore(
    (state) => state.stream.analysisText,
  );
  const timelineItems = useResearchSessionStore(
    (state) => state.stream.timeline,
  );
  const requirementDetail = useResearchSessionStore(
    (state) => state.remote.currentRevision?.requirement_detail ?? null,
  );

  if (snapshot === null) {
    return null;
  }

  const stageStatusCopy = getStageStatusCopy(snapshot.phase);
  const analysisPrefix =
    snapshot.phase === "processing_feedback"
      ? "正在处理反馈："
      : "正在分析需求：";

  return (
    <section className="space-y-6">
      <SessionStatusBar />
      <TerminalBanner />

      {snapshot.phase === "clarifying" ? (
        <>
          <ClarificationActionPanel compact={false} />
          <ClarificationDetailPanel compact={false} />
        </>
      ) : (
        <div className="space-y-5">
          <div className="bg-surface-container-high px-5 py-5">
            <h3 className="flex items-center gap-3 text-lg font-narrative font-semibold text-primary">
              {snapshot.phase !== "delivered" ? <PulseIndicator /> : null}
              {stageStatusCopy.title}
            </h3>
            <p className="mt-3 text-sm leading-7 text-secondary">
              {stageStatusCopy.description}
            </p>
            {analysisText.length > 0 ? (
              <p className="mt-4 whitespace-pre-line text-sm leading-7 text-surface-tint">
                {analysisPrefix}
                {analysisText}
              </p>
            ) : null}
          </div>

          <RequirementSummaryCard requirementDetail={requirementDetail} />
          <ReportCanvas />
          <ArtifactGallery />
          <DeliveryActions />
        </div>
      )}

      <TimelinePanel items={timelineItems} />
    </section>
  );
}
