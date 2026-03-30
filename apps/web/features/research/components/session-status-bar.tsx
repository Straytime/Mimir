"use client";

import { useResearchSessionStore } from "../providers/research-workspace-providers";
import { useDisconnectGuard } from "../hooks/use-disconnect-guard";
import { selectCanDisconnectTask, selectCollectProgress } from "../store/selectors";
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
      return { eyebrow: "Requirement Analysis", title: "正在分析你的研究需求", description: "系统正在固化研究目标、范围与输出格式，完成后将进入规划与搜集。" };
    case "planning_collection":
      return { eyebrow: "Collection Planning", title: "正在规划研究路径", description: "规划器正在拆解搜集目标，规划后续子任务的执行路径。" };
    case "collecting":
      return { eyebrow: "Collection", title: "正在搜索与读取资料", description: "子任务正在按搜集目标搜索与读取资料，进展会同步到时间线。" };
    case "summarizing_collection":
      return { eyebrow: "Collection Summary", title: "正在整理阶段结论", description: "系统正在汇总每个搜集目标的阶段结论，为来源合并做准备。" };
    case "merging_sources":
      return { eyebrow: "Source Merge", title: "正在去重并整理引用", description: "系统正在合并重复来源，固定当前可用的引用集合。" };
    case "preparing_outline":
      return { eyebrow: "Outline Drafting", title: "正在构思报告结构", description: "系统正在基于搜集结果构思报告大纲与章节结构。" };
    case "writing_report":
      return { eyebrow: "Report Writing", title: "正在撰写报告与生成配图", description: "报告正文持续生成中，配图完成后会同步展示。" };
    case "processing_feedback":
      return { eyebrow: "Feedback Processing", title: "正在处理反馈", description: "系统正在根据你的反馈修订报告内容。" };
    case "delivered":
      return { eyebrow: "Delivery", title: "报告已完成并进入交付阶段", description: "报告已就绪，你可以下载或提交反馈。" };
    default:
      return { eyebrow: "Workspace", title: "工作台已接管当前任务", description: "当前任务仍在进行中，工作台会按阶段依次展示进展。" };
  }
}

const TERMINAL_LABELS: Record<string, string> = {
  failed: "任务已失败",
  terminated: "任务已终止",
  expired: "任务已过期",
};

function fmt02(n: number): string {
  return String(n).padStart(2, "0");
}

export function SessionStatusBar() {
  const sseState = useResearchSessionStore((state) => state.session.sseState);
  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);
  const pendingAction = useResearchSessionStore(
    (state) => state.ui.pendingAction,
  );
  const terminalReason = useResearchSessionStore(
    (state) => state.ui.terminalReason,
  );
  const canDisconnectTask = useResearchSessionStore(selectCanDisconnectTask);
  const collectProgressTotal = useResearchSessionStore(
    (state) => selectCollectProgress(state)?.total ?? null,
  );
  const collectProgressFinished = useResearchSessionStore(
    (state) => selectCollectProgress(state)?.finished ?? null,
  );
  const analysisText = useResearchSessionStore(
    (state) => state.stream.analysisText,
  );
  const disconnectTask = useDisconnectGuard();

  const stageCopy = snapshot ? getStageStatusCopy(snapshot.phase) : null;

  const stageTitle = terminalReason
    ? (TERMINAL_LABELS[terminalReason] ?? terminalReason)
    : stageCopy
      ? stageCopy.title
      : "未开始";

  const isTerminal = terminalReason !== null;
  const hasDetailContent = snapshot !== null && !isTerminal && stageCopy !== null;

  const analysisPrefix =
    snapshot?.phase === "processing_feedback"
      ? "正在处理反馈："
      : "正在分析需求：";

  return (
    <section
      aria-label="会话状态"
      className="sticky top-0 z-50 bg-surface/70 px-4 py-3 font-ui text-sm backdrop-blur-[20px]"
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
          disabled={!canDisconnectTask}
          onClick={() => {
            void disconnectTask();
          }}
          type="button"
        >
          {pendingAction === "disconnecting" ? "正在终止..." : "终止任务"}
        </button>
      </div>

      {hasDetailContent ? (
        <div className="mt-1 text-xs text-secondary">
          <span>{stageCopy.description}</span>
          {collectProgressTotal !== null && collectProgressFinished !== null ? (
            <span>
              {" "}
              · 搜集进度: {fmt02(collectProgressFinished)}/
              {fmt02(collectProgressTotal)}
            </span>
          ) : null}
          {analysisText.length > 0 ? (
            <p className="mt-1 truncate">
              {analysisPrefix}
              {analysisText}
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
