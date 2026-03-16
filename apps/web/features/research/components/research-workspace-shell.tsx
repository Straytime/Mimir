"use client";

import { useEffect, useState } from "react";

import { ClarificationActionPanel, ClarificationDetailPanel, RequirementAnalysisPanel } from "./clarification-panels";
import { useClarificationCountdown } from "../hooks/use-clarification-countdown";
import { useDisconnectGuard } from "../hooks/use-disconnect-guard";
import { useHeartbeatLoop } from "../hooks/use-heartbeat-loop";
import { useTaskStream } from "../hooks/use-task-stream";
import { useResearchSessionStore } from "../providers/research-workspace-providers";
import { selectCanDisconnectTask } from "../store/selectors";
import { SessionStatusBar } from "./session-status-bar";
import { TerminalBanner } from "./terminal-banner";

type MobileSegment = "control" | "detail" | "progress";

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

  const detailSegmentLabel =
    snapshot.phase === "clarifying" ? "澄清详情" : "报告";

  const controlRail = (
    <article className="rounded-[2rem] border border-slate-200/70 bg-white/82 p-6 shadow-sm backdrop-blur">
      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
        Control Rail
      </p>
      <div className="mt-4 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-slate-950">活跃工作台</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            {snapshot.phase === "clarifying"
              ? "当前处于澄清阶段，提交成功后将立即切到需求分析。"
              : "澄清已提交，当前工作台只展示最小需求分析交接结果。"}
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
    </article>
  );

  const detailPanel = (
    <article className="rounded-[2rem] border border-slate-200/70 bg-white/82 p-6 shadow-sm backdrop-blur">
      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
        {snapshot.phase === "clarifying" ? "Clarification Detail" : "Analysis Handoff"}
      </p>
      <div className="mt-4">
        {snapshot.phase === "clarifying" ? (
          <ClarificationDetailPanel compact={isMobileLayout} />
        ) : (
          <RequirementAnalysisPanel />
        )}
      </div>
    </article>
  );

  const progressPanel = (
    <article className="rounded-[2rem] border border-slate-200/70 bg-white/82 p-6 shadow-sm backdrop-blur">
      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
        Progress
      </p>
      <div className="mt-4 space-y-4 text-sm leading-7 text-slate-700">
        <div className="rounded-3xl border border-dashed border-slate-300 bg-slate-50/80 p-5">
          当前允许动作：{availableActions.length > 0 ? availableActions.join(", ") : "无"}
        </div>
        <div className="rounded-3xl border border-slate-200 bg-white/90 p-5">
          <p className="font-semibold text-slate-950">v1 约束</p>
          <p className="mt-2 text-slate-600">
            不支持断线恢复、自动重连或跨刷新保留 task_token。本阶段只处理澄清与需求分析交接。
          </p>
        </div>
      </div>
    </article>
  );

  return (
    <section className="space-y-6">
      <SessionStatusBar />
      <TerminalBanner />

      {isMobileLayout ? (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-2">
            <button
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
