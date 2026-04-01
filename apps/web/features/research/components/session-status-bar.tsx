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

function getStageStatusCopy(phase: string) {
  switch (phase) {
    case "analyzing_requirement":
      return { title: "正在分析你的研究需求" };
    case "planning_collection":
      return { title: "正在规划研究路径" };
    case "collecting":
      return { title: "正在搜索与读取资料" };
    case "summarizing_collection":
      return { title: "正在整理阶段结论" };
    case "merging_sources":
      return { title: "正在去重并整理引用" };
    case "preparing_outline":
      return { title: "正在构思报告结构" };
    case "writing_report":
      return { title: "正在生成研究内容" };
    case "processing_feedback":
      return { title: "正在处理反馈" };
    case "delivered":
      return { title: "报告已完成并进入交付阶段" };
    default:
      return { title: "工作台已接管当前任务" };
  }
}

const TERMINAL_LABELS: Record<string, string> = {
  failed: "任务已失败",
  terminated: "任务已终止",
  expired: "任务已过期",
};

export function SessionStatusBar() {
  const sseState = useResearchSessionStore((state) => state.session.sseState);
  const taskId = useResearchSessionStore((state) => state.session.taskId);
  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);
  const pendingAction = useResearchSessionStore(
    (state) => state.ui.pendingAction,
  );
  const terminalReason = useResearchSessionStore(
    (state) => state.ui.terminalReason,
  );
  const reset = useResearchSessionStore((state) => state.reset);
  const canDisconnectTask = useResearchSessionStore(selectCanDisconnectTask);
  const disconnectTask = useDisconnectGuard();

  const stageCopy = snapshot ? getStageStatusCopy(snapshot.phase) : null;

  const stageTitle = terminalReason
    ? (TERMINAL_LABELS[terminalReason] ?? terminalReason)
    : stageCopy
      ? stageCopy.title
      : "未开始";

  const isTerminal = terminalReason !== null;
  const isDeliveredPhase =
    snapshot?.phase === "delivered" && !isTerminal;
  const actionLabel = isDeliveredPhase
    ? "新研究"
    : pendingAction === "disconnecting"
      ? "正在终止..."
      : "终止任务";

  return (
    <section
      aria-label="会话状态"
      data-research-status-bar="true"
      className="bg-surface/70 px-4 py-3 font-ui text-sm backdrop-blur-[20px]"
      role="region"
    >
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <span className="flex items-center gap-2 font-medium text-secondary">
            {sseState === "open" ? <PulseIndicator /> : null}
            {SSE_STATE_LABELS[sseState]}
          </span>
          <span className="text-tertiary">·</span>
          <span className="font-medium text-primary">{stageTitle}</span>
        </div>

        <button
          className="bg-transparent px-4 py-1.5 text-sm font-medium text-primary shadow-ghost transition hover:shadow-glow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-surface-tint disabled:cursor-not-allowed disabled:text-tertiary disabled:shadow-none"
          disabled={isDeliveredPhase ? false : !canDisconnectTask}
          onClick={() => {
            if (isDeliveredPhase) {
              reset();
              return;
            }

            void disconnectTask();
          }}
          type="button"
        >
          {actionLabel}
        </button>
      </div>

      {taskId !== null ? (
        <div className="mt-1 text-xs text-secondary">
          <p className="truncate">taskId: {taskId}</p>
        </div>
      ) : null}
    </section>
  );
}
