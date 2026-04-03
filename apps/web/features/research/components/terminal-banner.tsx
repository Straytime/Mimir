"use client";

import type { TerminationReason } from "@/lib/contracts";

import { useResearchSessionStore } from "../providers/research-workspace-providers";
import type { TerminalReason } from "../store/research-session-store.types";

const TERMINAL_CONTENT = {
  failed: {
    title: "任务已失败，旧任务操作已禁用。",
    detail: "上游执行已停止。v1 不支持从当前页面恢复旧任务，请重新创建。",
    tone: "bg-surface-container-high text-[#FF6B6B]",
  },
  terminated: {
    title: "任务已终止",
    detail: "当前任务已停止，旧任务操作不可恢复，请重新创建研究。",
    tone: "bg-surface-container-high text-[#FFB86C]",
  },
  expired: {
    title: "任务已过期，旧任务操作已禁用。",
    detail: "过期任务不会恢复旧会话。请重新创建新的研究任务。",
    tone: "bg-surface-container-high text-tertiary",
  },
} as const;

const TERMINATED_DETAIL_BY_REASON: Record<TerminationReason, string> = {
  sendbeacon_received:
    "系统已收到页面关闭信号，当前任务已停止。旧任务操作不可恢复，请重新创建研究。",
  client_disconnected:
    "当前页面已主动断开连接，任务已停止。旧任务操作不可恢复，请重新创建研究。",
  heartbeat_timeout:
    "任务因长时间未收到心跳而停止。旧任务操作不可恢复，请重新创建研究。",
  risk_control_limit:
    "研究内容触发了平台内容安全策略，当前任务已停止。请调整研究主题后重新创建研究。",
  sse_connect_timeout:
    "任务因长时间未建立事件连接而停止。旧任务操作不可恢复，请重新创建研究。",
  server_shutdown:
    "服务端连接已中断，当前任务被终止。旧任务操作不可恢复，请重新创建研究。",
} as const;

function resolveTerminalContent(
  terminalReason: Exclude<TerminalReason, null>,
  terminationDetail: TerminationReason | null,
) {
  if (terminalReason !== "terminated") {
    return TERMINAL_CONTENT[terminalReason];
  }

  return {
    ...TERMINAL_CONTENT.terminated,
    detail:
      terminationDetail === null
        ? TERMINAL_CONTENT.terminated.detail
        : TERMINATED_DETAIL_BY_REASON[terminationDetail],
  };
}

export function TerminalBanner() {
  const terminalReason = useResearchSessionStore((state) => state.ui.terminalReason);
  const terminationDetail = useResearchSessionStore((state) => state.ui.terminationDetail);
  const reset = useResearchSessionStore((state) => state.reset);

  if (terminalReason === null) {
    return null;
  }

  const content = resolveTerminalContent(terminalReason, terminationDetail);

  return (
    <section className={`px-5 py-4 text-sm ${content.tone}`}>
      <h2 className="text-base font-semibold">{content.title}</h2>
      <p className="mt-2 leading-6">{content.detail}</p>
      <button
        className="mt-4 bg-primary px-5 py-3 text-sm font-semibold text-on-primary transition hover:shadow-glow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
        onClick={reset}
        type="button"
      >
        开始新研究
      </button>
    </section>
  );
}
