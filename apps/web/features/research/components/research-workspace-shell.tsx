"use client";

import { useEffect, useState } from "react";

import {
  ClarificationActionPanel,
  ClarificationDetailPanel,
} from "./clarification-panels";
import { ArtifactGallery } from "./artifact-gallery";
import { DeliveryActions } from "./delivery-actions";
import { RequirementSummaryCard } from "./requirement-summary-card";
import { ReportCanvas } from "./report-canvas";
import { useClarificationCountdown } from "../hooks/use-clarification-countdown";
import { useDisconnectGuard } from "../hooks/use-disconnect-guard";
import { useHeartbeatLoop } from "../hooks/use-heartbeat-loop";
import { useTaskStream } from "../hooks/use-task-stream";
import { useResearchSessionStore } from "../providers/research-workspace-providers";
import { selectCanDisconnectTask } from "../store/selectors";
import { SessionStatusBar } from "./session-status-bar";
import { TerminalBanner } from "./terminal-banner";
import { TimelinePanel } from "./timeline-panel";

type MobileSegment = "control" | "detail" | "progress";

function getStageStatusCopy(phase: string) {
  switch (phase) {
    case "analyzing_requirement":
      return {
        eyebrow: "Requirement Analysis",
        title: "正在分析你的研究需求",
        description:
          "系统会先固化研究目标、范围、输出格式与语言要求，再进入后续规划与搜集。",
      };
    case "planning_collection":
      return {
        eyebrow: "Collection Planning",
        title: "正在规划研究路径",
        description:
          "规划器正在拆解搜集目标，并把 collect_target 写入时间线供后续子任务接力。",
      };
    case "collecting":
      return {
        eyebrow: "Collection",
        title: "正在搜索与读取资料",
        description:
          "子任务会按 collect_target 搜索、读取资料，并把关键动作串到线性时间线里。",
      };
    case "summarizing_collection":
      return {
        eyebrow: "Collection Summary",
        title: "正在整理阶段结论",
        description:
          "每个搜集目标的阶段结论会依次落入时间线，为后续来源合并做准备。",
      };
    case "merging_sources":
      return {
        eyebrow: "Source Merge",
        title: "正在去重并整理引用",
        description:
          "系统正在合并重复来源，并固定当前 revision 可用的引用集合。",
      };
    case "preparing_outline":
      return {
        eyebrow: "Outline Drafting",
        title: "正在构思报告结构",
        description:
          "本阶段只显示通用状态文案，不渲染 raw outline delta。",
      };
    case "writing_report":
      return {
        eyebrow: "Report Writing",
        title: "正在撰写报告与生成配图",
        description:
          "正文会由 writer.delta 持续追加，writer.reasoning 只进入时间线，配图生成状态也会同步展示。",
      };
    case "processing_feedback":
      return {
        eyebrow: "Feedback Processing",
        title: "正在处理反馈",
        description:
          "该阶段代表后端正在处理反馈相关状态；v1 前端不开放反馈交互，仅按只读工作台展示当前任务进展。",
      };
    case "delivered":
      return {
        eyebrow: "Delivery",
        title: "报告已完成并进入交付阶段",
        description:
          "下载区会先被 report.completed 更新；是否开放下载仍以后端 available_actions 为准。",
      };
    default:
      return {
        eyebrow: "Workspace",
        title: "工作台已接管当前任务",
        description:
          "当前任务仍在进行中；工作台会继续按阶段切换澄清、透明度、报告与交付视图。",
      };
  }
}

function useIsMobileLayout() {
  const [isMobileLayout, setIsMobileLayout] = useState(() => {
    if (typeof window === "undefined") {
      return false;
    }

    return window.matchMedia("(max-width: 767px)").matches;
  });

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const mediaQueryList = window.matchMedia("(max-width: 767px)");
    const handleChange = () => {
      setIsMobileLayout(mediaQueryList.matches);
    };

    handleChange();
    mediaQueryList.addEventListener("change", handleChange);

    return () => {
      mediaQueryList.removeEventListener("change", handleChange);
    };
  }, []);

  return isMobileLayout;
}

export function ResearchWorkspaceShell() {
  useTaskStream();
  useHeartbeatLoop();
  useClarificationCountdown();

  const session = useResearchSessionStore((state) => state.session);
  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);
  const pendingAction = useResearchSessionStore((state) => state.ui.pendingAction);
  const analysisText = useResearchSessionStore((state) => state.stream.analysisText);
  const timelineItems = useResearchSessionStore((state) => state.stream.timeline);
  const requirementDetail = useResearchSessionStore(
    (state) => state.remote.currentRevision?.requirement_detail ?? null,
  );
  const clarificationMode = useResearchSessionStore(
    (state) => state.remote.snapshot?.clarification_mode ?? "natural",
  );
  const availableActions = useResearchSessionStore(
    (state) => state.remote.snapshot?.available_actions ?? [],
  );
  const canDisconnectTask = useResearchSessionStore(selectCanDisconnectTask);
  const disconnectTask = useDisconnectGuard();
  const isMobileLayout = useIsMobileLayout();
  const [mobileSegment, setMobileSegment] = useState<MobileSegment>("control");

  if (snapshot === null) {
    return null;
  }

  const stageStatusCopy = getStageStatusCopy(snapshot.phase);
  const detailSegmentLabel =
    snapshot.phase === "clarifying" ? "澄清详情" : "报告";
  const analysisPrefix =
    snapshot.phase === "processing_feedback" ? "正在处理反馈：" : "正在分析需求：";

  const controlRail = (
    <article
      className="rounded-[2rem] border border-slate-200/70 bg-white/82 p-6 shadow-sm backdrop-blur"
      id="workspace-control-panel"
    >
      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
        Control Rail
      </p>
      <div className="mt-4 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-slate-950">活跃工作台</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            {snapshot.phase === "clarifying"
              ? "当前处于澄清阶段，提交成功后将立即切到需求分析。"
              : "当前工作台已接入透明度时间线、报告正文、图片制品与交付下载。"}
          </p>
        </div>
        <button
          className="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-800 transition hover:border-slate-950 hover:text-slate-950 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
          disabled={!canDisconnectTask}
          onClick={() => {
            void disconnectTask();
          }}
          type="button"
        >
          {pendingAction === "disconnecting" ? "正在终止..." : "终止任务"}
        </button>
      </div>
      <dl className="mt-6 space-y-3 text-sm text-slate-700">
        <div className="flex items-start justify-between gap-4">
          <dt className="text-slate-500">Task</dt>
          <dd className="font-medium text-slate-950">{session.taskId}</dd>
        </div>
        <div className="flex items-start justify-between gap-4">
          <dt className="text-slate-500">Phase</dt>
          <dd className="font-medium text-slate-950">{snapshot.phase}</dd>
        </div>
        <div className="flex items-start justify-between gap-4">
          <dt className="text-slate-500">Status</dt>
          <dd className="font-medium text-slate-950">{snapshot.status}</dd>
        </div>
        <div className="flex items-start justify-between gap-4">
          <dt className="text-slate-500">Mode</dt>
          <dd className="font-medium text-slate-950">{clarificationMode}</dd>
        </div>
        <div className="flex items-start justify-between gap-4">
          <dt className="text-slate-500">SSE</dt>
          <dd className="font-medium text-slate-950">{session.sseState}</dd>
        </div>
      </dl>

      <div className="mt-6">
        <ClarificationActionPanel compact={isMobileLayout} />
      </div>

      <div className="mt-6 rounded-3xl border border-slate-200 bg-white/90 p-5">
        <p className="text-sm font-semibold text-slate-950">当前允许动作</p>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          {availableActions.length > 0 ? availableActions.join(", ") : "无"}
        </p>
      </div>

      <div className="mt-4 rounded-3xl border border-slate-200 bg-slate-50/85 p-5">
        <p className="text-sm font-semibold text-slate-950">v1 约束</p>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          不支持跨刷新恢复或持久化 task_token；同页面内的观察流若短暂断开会自动重连，但离开页面后不会恢复旧任务。
        </p>
      </div>
    </article>
  );

  const detailPanel = (
    <article
      className="rounded-[2rem] border border-slate-200/70 bg-white/82 p-6 shadow-sm backdrop-blur"
      id="workspace-detail-panel"
    >
      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
        {snapshot.phase === "clarifying"
          ? "Clarification Detail"
          : stageStatusCopy.eyebrow}
      </p>
      <div className="mt-4">
        {snapshot.phase === "clarifying" ? (
          <ClarificationDetailPanel compact={isMobileLayout} />
        ) : (
          <div className="relative space-y-5">
            <div className="rounded-3xl border border-sky-200 bg-sky-50 px-5 py-5">
              <h3 className="text-xl font-semibold text-slate-950">
                {stageStatusCopy.title}
              </h3>
              <p className="mt-3 text-sm leading-7 text-slate-700">
                {stageStatusCopy.description}
              </p>
              {analysisText.length > 0 ? (
                <p className="mt-4 whitespace-pre-line text-sm leading-7 text-sky-900">
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
      </div>
    </article>
  );

  const progressPanel = (
    <div id="workspace-progress-panel">
      <TimelinePanel items={timelineItems} />
    </div>
  );

  return (
    <section className="space-y-6">
      <SessionStatusBar />
      <TerminalBanner />

      {isMobileLayout ? (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-2">
            <button
              aria-controls="workspace-control-panel"
              aria-pressed={mobileSegment === "control"}
              className={`rounded-full px-4 py-3 text-sm font-semibold ${
                mobileSegment === "control"
                  ? "bg-slate-950 text-white"
                  : "bg-white text-slate-700"
              }`}
              onClick={() => setMobileSegment("control")}
              type="button"
            >
              操作
            </button>
            <button
              aria-controls="workspace-detail-panel"
              aria-pressed={mobileSegment === "detail"}
              className={`rounded-full px-4 py-3 text-sm font-semibold ${
                mobileSegment === "detail"
                  ? "bg-slate-950 text-white"
                  : "bg-white text-slate-700"
              }`}
              onClick={() => setMobileSegment("detail")}
              type="button"
            >
              {detailSegmentLabel}
            </button>
            <button
              aria-controls="workspace-progress-panel"
              aria-pressed={mobileSegment === "progress"}
              className={`rounded-full px-4 py-3 text-sm font-semibold ${
                mobileSegment === "progress"
                  ? "bg-slate-950 text-white"
                  : "bg-white text-slate-700"
              }`}
              onClick={() => setMobileSegment("progress")}
              type="button"
            >
              进度
            </button>
          </div>

          {mobileSegment === "control" ? controlRail : null}
          {mobileSegment === "detail" ? detailPanel : null}
          {mobileSegment === "progress" ? progressPanel : null}
        </div>
      ) : (
        <div className="grid gap-6 xl:grid-cols-[1.1fr_2fr_1.1fr]">
          {controlRail}
          {detailPanel}
          {progressPanel}
        </div>
      )}
    </section>
  );
}
