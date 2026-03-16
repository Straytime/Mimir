"use client";

import { useDisconnectGuard } from "../hooks/use-disconnect-guard";
import { useHeartbeatLoop } from "../hooks/use-heartbeat-loop";
import { useTaskStream } from "../hooks/use-task-stream";
import { useResearchSessionStore } from "../providers/research-workspace-providers";
import { selectCanDisconnectTask } from "../store/selectors";
import { SessionStatusBar } from "./session-status-bar";
import { TerminalBanner } from "./terminal-banner";

export function ResearchWorkspaceShell() {
  useTaskStream();
  useHeartbeatLoop();

  const session = useResearchSessionStore((state) => state.session);
  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);
  const pendingAction = useResearchSessionStore((state) => state.ui.pendingAction);
  const canDisconnectTask = useResearchSessionStore(selectCanDisconnectTask);
  const disconnectTask = useDisconnectGuard();

  if (snapshot === null) {
    return null;
  }

  return (
    <section className="space-y-6">
      <SessionStatusBar />
      <TerminalBanner />

      <div className="grid gap-6 xl:grid-cols-[1.1fr_2fr_1.1fr]">
        <article className="rounded-[2rem] border border-slate-200/70 bg-white/82 p-6 shadow-sm backdrop-blur">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
            Control Rail
          </p>
          <div className="mt-4 flex items-start justify-between gap-4">
            <h2 className="text-2xl font-semibold text-slate-950">活跃工作台</h2>
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
              <dt className="text-slate-500">SSE</dt>
              <dd className="font-medium text-slate-950">{session.sseState}</dd>
            </div>
          </dl>
        </article>

        <article className="rounded-[2rem] border border-slate-200/70 bg-white/82 p-6 shadow-sm backdrop-blur">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
            Lifecycle Canvas
          </p>
          <h2 className="mt-4 text-2xl font-semibold text-slate-950">
            Stage 3 生命周期已接入
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-700">
            当前工作台会消费 `task.created`、维护 connect deadline、在允许状态下发送
            heartbeat，并处理 `beforeunload`、`pagehide`、手动 disconnect 与终态 UI。
          </p>
        </article>

        <article className="rounded-[2rem] border border-slate-200/70 bg-white/82 p-6 shadow-sm backdrop-blur">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
            Constraints
          </p>
          <div className="mt-4 rounded-3xl border border-dashed border-slate-300 bg-slate-50/80 p-5 text-sm leading-7 text-slate-600">
            v1 不支持断线恢复、自动重连或刷新恢复旧任务。进入终态后，旧操作会立即禁用。
          </div>
        </article>
      </div>
    </section>
  );
}
