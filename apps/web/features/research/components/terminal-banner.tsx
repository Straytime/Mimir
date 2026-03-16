"use client";

import { useResearchSessionStore } from "../providers/research-workspace-providers";

const TERMINAL_CONTENT = {
  failed: {
    title: "任务已失败，旧任务操作已禁用。",
    detail: "上游执行已停止。v1 不支持从当前页面恢复旧任务，请重新创建。",
    tone: "border-rose-200 bg-rose-50 text-rose-900",
  },
  terminated: {
    title: "任务已终止，旧任务操作已禁用。",
    detail: "连接中断、手动终止或 connect deadline 超时后，v1 不会自动重连。",
    tone: "border-amber-200 bg-amber-50 text-amber-900",
  },
  expired: {
    title: "任务已过期，旧任务操作已禁用。",
    detail: "过期任务不会恢复旧会话。请重新创建新的研究任务。",
    tone: "border-slate-200 bg-slate-100 text-slate-900",
  },
} as const;

export function TerminalBanner() {
  const terminalReason = useResearchSessionStore((state) => state.ui.terminalReason);

  if (terminalReason === null) {
    return null;
  }

  const content = TERMINAL_CONTENT[terminalReason];

  return (
    <section className={`rounded-[1.75rem] border px-5 py-4 text-sm shadow-sm ${content.tone}`}>
      <h2 className="text-base font-semibold">{content.title}</h2>
      <p className="mt-2 leading-6">{content.detail}</p>
    </section>
  );
}
