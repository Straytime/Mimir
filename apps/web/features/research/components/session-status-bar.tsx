"use client";

import { useResearchSessionStore } from "../providers/research-workspace-providers";

const SSE_STATE_LABELS = {
  idle: "未连接",
  connecting: "连接中",
  open: "已连接",
  closed: "已关闭",
  failed: "连接失败",
} as const;

export function SessionStatusBar() {
  const sseState = useResearchSessionStore((state) => state.session.sseState);
  const lastHeartbeatAt = useResearchSessionStore(
    (state) => state.session.lastHeartbeatAt,
  );

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-full border border-slate-200/80 bg-white/88 px-4 py-3 text-sm text-slate-700 shadow-sm backdrop-blur">
      <span className="font-semibold text-slate-950">连接状态</span>
      <span className="rounded-full bg-slate-100 px-3 py-1 font-medium text-slate-900">
        {SSE_STATE_LABELS[sseState]}
      </span>
      <span className="text-slate-500">
        最近心跳：{lastHeartbeatAt ?? "尚未收到"}
      </span>
    </div>
  );
}
