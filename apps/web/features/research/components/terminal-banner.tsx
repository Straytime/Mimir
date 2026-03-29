"use client";

import { useResearchSessionStore } from "../providers/research-workspace-providers";

const TERMINAL_CONTENT = {
  failed: {
    title: "任务已失败，旧任务操作已禁用。",
    detail: "上游执行已停止。v1 不支持从当前页面恢复旧任务，请重新创建。",
    tone: "bg-surface-container-high text-[#FF6B6B]",
  },
  terminated: {
    title: "任务已终止，旧任务操作已禁用。",
    detail: "只有手动终止或确认离开页面后，任务才会结束。v1 不支持恢复旧任务。",
    tone: "bg-surface-container-high text-[#FFB86C]",
  },
  expired: {
    title: "任务已过期，旧任务操作已禁用。",
    detail: "过期任务不会恢复旧会话。请重新创建新的研究任务。",
    tone: "bg-surface-container-high text-tertiary",
  },
} as const;

export function TerminalBanner() {
  const terminalReason = useResearchSessionStore((state) => state.ui.terminalReason);
  const reset = useResearchSessionStore((state) => state.reset);

  if (terminalReason === null) {
    return null;
  }

  const content = TERMINAL_CONTENT[terminalReason];

  return (
    <section className={`px-5 py-4 text-sm ${content.tone}`}>
      <h2 className="text-base font-semibold">{content.title}</h2>
      <p className="mt-2 leading-6">{content.detail}</p>
      <button
        className="mt-4 bg-primary px-5 py-3 text-sm font-semibold text-on-primary transition hover:shadow-glow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-surface-tint"
        onClick={reset}
        type="button"
      >
        开始新研究
      </button>
    </section>
  );
}
