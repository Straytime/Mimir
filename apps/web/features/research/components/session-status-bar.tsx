"use client";

import { useResearchSessionStore } from "../providers/research-workspace-providers";

const SSE_STATE_LABELS = {
  idle: "未连接",
  connecting: "连接中",
  open: "已连接",
  closed: "已关闭",
  failed: "连接失败",
} as const;

const PHASE_LABELS = {
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
} as const;

export function SessionStatusBar() {
  const sseState = useResearchSessionStore((state) => state.session.sseState);
  const lastServerActivityAt = useResearchSessionStore(
    (state) => state.session.lastServerActivityAt,
  );
  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);

  return (
    <section
      aria-label="会话状态"
      className="flex flex-wrap items-center gap-3 rounded-full border border-slate-200/80 bg-white/88 px-4 py-3 text-sm text-slate-700 shadow-sm backdrop-blur"
      role="region"
    >
      <span className="font-semibold text-slate-950">连接状态</span>
      <span className="rounded-full bg-slate-100 px-3 py-1 font-medium text-slate-900">
        {SSE_STATE_LABELS[sseState]}
      </span>
      <span className="text-slate-500">当前阶段</span>
      <span className="rounded-full bg-sky-50 px-3 py-1 font-medium text-sky-900">
        {snapshot ? PHASE_LABELS[snapshot.phase] : "未开始"}
      </span>
      <span className="text-slate-500">
        最近服务端活动：{lastServerActivityAt ?? "尚未收到"}
      </span>
    </section>
  );
}
