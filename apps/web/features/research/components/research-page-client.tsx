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
    <main className="mx-auto flex min-h-screen w-full max-w-[800px] flex-col gap-6 px-6 py-16">
      <div className="space-y-4">
        <p className="text-[11px] font-ui font-medium uppercase tracking-[0.15em] text-surface-tint">
          Mimir
        </p>
        <h1 className="text-[56px] font-ui font-semibold leading-tight tracking-tight text-primary">
          AI 研究工作台
        </h1>
      </div>

      {isActiveWorkspace ? (
        <ResearchWorkspaceShell />
      ) : (
        <section className="space-y-6">
          <ResearchInputPanel />
          <ResearchConfigPanel />
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
