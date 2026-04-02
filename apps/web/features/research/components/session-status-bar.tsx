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
    case "clarifying":
      return {
        title: "等待你的澄清反馈",
        tag: "Stage 01 / Clarifying",
      };
    case "analyzing_requirement":
      return {
        title: "正在分析你的研究需求",
        tag: "Stage 02 / Analyzing",
      };
    case "planning_collection":
      return {
        title: "正在规划研究路径",
        tag: "Stage 03 / Planning",
      };
    case "collecting":
      return {
        title: "正在搜索与读取资料",
        tag: "Stage 04 / Collecting",
      };
    case "summarizing_collection":
      return {
        title: "正在整理阶段结论",
        tag: "Stage 05 / Summarizing",
      };
    case "merging_sources":
      return {
        title: "正在去重并整理引用",
        tag: "Stage 06 / Merging",
      };
    case "preparing_outline":
      return {
        title: "正在构思报告结构",
        tag: "Stage 07 / Outline",
      };
    case "writing_report":
      return {
        title: "正在生成研究内容",
        tag: "Stage 08 / Writing",
      };
    case "processing_feedback":
      return {
        title: "正在处理反馈",
        tag: "Stage 10 / Feedback",
      };
    case "delivered":
      return {
        title: "报告已完成并进入交付阶段",
        tag: "Stage 09 / Delivered",
      };
    default:
      return {
        title: "工作台已接管当前任务",
        tag: "Stage ?? / Active",
      };
  }
}

const TERMINAL_LABELS: Record<string, string> = {
  failed: "任务已失败",
  terminated: "任务已终止",
  expired: "任务已过期",
};

const TERMINAL_META_LABELS: Record<string, string> = {
  failed: "Terminal / Failed",
  terminated: "Terminal / Terminated",
  expired: "Terminal / Expired",
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
  const stageTag = terminalReason
    ? (TERMINAL_META_LABELS[terminalReason] ?? "Terminal / State")
    : stageCopy
      ? stageCopy.tag
      : "Stage 00 / Idle";

  const isTerminal = terminalReason !== null;
  const isDeliveredPhase = snapshot?.phase === "delivered" && !isTerminal;
  const showStageEllipsis =
    snapshot !== null && !isTerminal && snapshot.phase !== "delivered";
  const showTerminalLabel = isTerminal;
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
      <div className="grid gap-3 md:grid-cols-[minmax(0,1fr),auto] md:items-center">
        <div className="flex flex-wrap items-center gap-2 text-[11px] font-medium uppercase tracking-[0.15em]">
          <span className="flex items-center gap-2 bg-surface-container-low px-3 py-2 text-secondary">
            {sseState === "open" ? <PulseIndicator /> : null}
            {SSE_STATE_LABELS[sseState]}
          </span>
          <span
            aria-label={`${stageTag} ${stageTitle}`}
            className="inline-flex items-center gap-1.5 bg-surface-container-high px-3 py-2 text-surface-tint"
            data-research-stage-chip="true"
          >
            <span>{stageTag}</span>
            {showStageEllipsis ? (
              <span
                aria-hidden="true"
                className="research-stage-ellipsis inline-flex items-center"
                data-research-stage-ellipsis="true"
              >
                <span>.</span>
                <span>.</span>
                <span>.</span>
              </span>
            ) : null}
          </span>
          {showTerminalLabel ? (
            <span className="px-1 text-primary">{stageTitle}</span>
          ) : null}
          {taskId !== null ? (
            <p
              className="px-1 text-[10px] uppercase tracking-[0.18em] text-tertiary"
              data-research-task-meta="true"
            >
              taskId: {taskId}
            </p>
          ) : null}
        </div>

        <div className="flex items-center justify-start md:justify-end">
          <button
            className="bg-surface-container-lowest px-4 py-3 text-sm font-medium text-primary transition-colors hover:bg-surface-container-high focus-visible:outline focus-visible:outline-2 focus-visible:outline-surface-tint disabled:cursor-not-allowed disabled:text-tertiary"
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
      </div>
      <style>{`
        .research-stage-ellipsis span {
          animation: research-stage-ellipsis 1.2s infinite;
          opacity: 0.25;
        }

        .research-stage-ellipsis span:nth-child(2) {
          animation-delay: 0.2s;
        }

        .research-stage-ellipsis span:nth-child(3) {
          animation-delay: 0.4s;
        }

        @keyframes research-stage-ellipsis {
          0%,
          20% {
            opacity: 0.2;
          }

          50% {
            opacity: 1;
          }

          100% {
            opacity: 0.2;
          }
        }
      `}</style>
    </section>
  );
}
