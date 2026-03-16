"use client";

import type { StoreApi } from "zustand";

import { ResearchWorkspaceProviders, type ResearchRuntime } from "../providers/research-workspace-providers";
import type { ResearchSessionStore } from "../store/research-session-store.types";
import { useResearchSessionStore } from "../providers/research-workspace-providers";
import { ResearchConfigPanel } from "./research-config-panel";
import { ResearchInputPanel } from "./research-input-panel";
import { ResearchWorkspaceShell } from "./research-workspace-shell";

export type ResearchPageClientProps = {
  runtime?: Partial<ResearchRuntime>;
  store?: StoreApi<ResearchSessionStore>;
};

function ResearchPageContent() {
  const taskId = useResearchSessionStore((state) => state.session.taskId);
  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);
  const isActiveWorkspace = taskId !== null && snapshot !== null;

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 px-6 py-16">
      <div className="space-y-4">
        <p className="text-sm font-medium uppercase tracking-[0.24em] text-sky-700">
          Mimir
        </p>
        <h1 className="text-4xl font-semibold tracking-tight text-slate-950">
          AI 研究工作台
        </h1>
        <p className="max-w-2xl text-base leading-7 text-slate-700">
          当前阶段已接上需求分析、规划与资料搜集透明度时间线；仍保持 v1
          不恢复、不重连，也不提前进入 report / artifact / delivery。
        </p>
      </div>

      {isActiveWorkspace ? (
        <ResearchWorkspaceShell />
      ) : (
        <section className="grid gap-6 lg:grid-cols-[1.25fr_0.95fr]">
          <ResearchInputPanel />
          <div className="space-y-6">
            <ResearchConfigPanel />
            <article className="rounded-[2rem] border border-slate-200/70 bg-white/80 p-6 shadow-sm backdrop-blur">
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
                Idle
              </p>
              <h2 className="mt-4 text-xl font-semibold text-slate-950">
                从空态进入研究工作台
              </h2>
              <p className="mt-3 text-sm leading-7 text-slate-700">
                创建成功后，前端会立即把 `task_id`、`task_token`、`urls` 与初始
                snapshot 写入 store，并在工作台内接管后续 SSE、heartbeat、澄清提交、
                requirement summary 与 timeline transparency 展示。
              </p>
            </article>
          </div>
        </section>
      )}
    </main>
  );
}

export function ResearchPageClient({ runtime, store }: ResearchPageClientProps) {
  return (
    <ResearchWorkspaceProviders runtime={runtime} store={store}>
      <ResearchPageContent />
    </ResearchWorkspaceProviders>
  );
}
