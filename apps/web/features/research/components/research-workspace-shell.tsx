"use client";

import { useResearchSessionStore } from "../providers/research-workspace-providers";

export function ResearchWorkspaceShell() {
  const session = useResearchSessionStore((state) => state.session);
  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);

  if (snapshot === null) {
    return null;
  }

  return (
    <section className="grid gap-6 xl:grid-cols-[1.1fr_2fr_1.1fr]">
      <article className="rounded-[2rem] border border-slate-200/70 bg-white/82 p-6 shadow-sm backdrop-blur">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
          Control Rail
        </p>
        <h2 className="mt-4 text-2xl font-semibold text-slate-950">
          活跃工作台
        </h2>
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
          Report Canvas
        </p>
        <h2 className="mt-4 text-2xl font-semibold text-slate-950">
          工作台已切换到活跃态
        </h2>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-700">
          `POST /tasks` 已成功，前端已经把 `task_id`、`task_token`、`urls` 与初始
          snapshot 写入 store，并触发了 SSE 建连动作。报告流、时间线和终态生命周期
          留到 Stage 3 之后继续实现。
        </p>
      </article>

      <article className="rounded-[2rem] border border-slate-200/70 bg-white/82 p-6 shadow-sm backdrop-blur">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
          Live Timeline
        </p>
        <div className="mt-4 rounded-3xl border border-dashed border-slate-300 bg-slate-50/80 p-5 text-sm leading-7 text-slate-600">
          Stage 2 只保留工作台骨架。真正的 SSE 生命周期消费、heartbeat、disconnect
          与终态处理会在下一阶段接入。
        </div>
      </article>
    </section>
  );
}
