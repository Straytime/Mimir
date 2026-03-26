"use client";

import { useResearchSessionStore } from "../providers/research-workspace-providers";
import { useDisconnectGuard } from "../hooks/use-disconnect-guard";
import { selectCanDisconnectTask } from "../store/selectors";
import { PulseIndicator } from "./pulse-indicator";

const SSE_STATE_LABELS = {
  idle: "未连接",
  connecting: "连接中",
  open: "已连接",
  closed: "已关闭",
  failed: "连接失败",
} as const;

const PHASE_LABELS: Record<string, string> = {
  clarifying: "等待澄清",
  analyzing_requirement: "正在分析需求",
  planning_collection: "正在规划研究路径",
  collecting: "正在搜索与读取资料",
  summarizing_collection: "正在整理阶段结论",
  merging_sources: "正在整理来源",
  preparing_outline: "正在构思报告结构",
  writing_report: "正在撰写报告",
  delivered: "已进入交付阶段",
  processing_feedback: "正在处理反馈",
};

export function SessionStatusBar() {
  const sseState = useResearchSessionStore((state) => state.session.sseState);
  const taskId = useResearchSessionStore((state) => state.session.taskId);
  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);
  const pendingAction = useResearchSessionStore(
    (state) => state.ui.pendingAction,
  );
  const canDisconnectTask = useResearchSessionStore(selectCanDisconnectTask);
  const disconnectTask = useDisconnectGuard();

  const phaseLabel = snapshot
    ? (PHASE_LABELS[snapshot.phase] ?? snapshot.phase)
    : "未开始";

  return (
    <section
      aria-label="会话状态"
      className="sticky top-0 z-50 flex items-center justify-between gap-4 bg-surface/70 px-4 py-3 font-ui text-sm backdrop-blur-[20px]"
      role="region"
    >
      <div className="flex flex-wrap items-center gap-3">
        <span className="flex items-center gap-2 font-medium text-secondary">
          {sseState === "open" ? <PulseIndicator /> : null}
          {SSE_STATE_LABELS[sseState]}
        </span>
        <span className="text-tertiary">·</span>
        <span className="font-medium text-primary">{phaseLabel}</span>
        {taskId ? (
          <>
            <span className="text-tertiary">·</span>
            <span className="font-mono text-xs text-tertiary">{taskId}</span>
          </>
        ) : null}
      </div>

      <button
        className="border border-outline-variant px-4 py-1.5 text-sm font-medium text-primary transition hover:border-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-surface-tint disabled:cursor-not-allowed disabled:text-tertiary disabled:border-tertiary"
        disabled={!canDisconnectTask}
        onClick={() => {
          void disconnectTask();
        }}
        type="button"
      >
        {pendingAction === "disconnecting" ? "正在终止..." : "终止任务"}
      </button>
    </section>
  );
}
