"use client";

import { useRef } from "react";
import type { StoreApi } from "zustand";

import { ResearchWorkspaceProviders, type ResearchRuntime } from "../providers/research-workspace-providers";
import { useWorkspaceBodyMaxHeight } from "../hooks/use-workspace-body-max-height";
import type { ResearchSessionStore } from "../store/research-session-store.types";
import { useResearchSessionStore } from "../providers/research-workspace-providers";
import { ExamplePrompts } from "./example-prompts";
import { ResearchConfigPanel } from "./research-config-panel";
import { ResearchWorkspaceShell } from "./research-workspace-shell";
import { UnifiedInputBar } from "./unified-input-bar";

export type ResearchPageClientProps = {
  runtime?: Partial<ResearchRuntime>;
  store?: StoreApi<ResearchSessionStore>;
};

function ResearchPageContent() {
  const taskId = useResearchSessionStore((state) => state.session.taskId);
  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);
  const isActiveWorkspace = taskId !== null && snapshot !== null;
  const mainRef = useRef<HTMLElement | null>(null);

  useWorkspaceBodyMaxHeight(mainRef, isActiveWorkspace);

  return (
    <main
      className="mx-auto flex min-h-screen w-full max-w-[800px] flex-col gap-sp-10 bg-radial-glow px-sp-8 pb-32 py-16"
      ref={mainRef}
    >
      <div className="animate-fade-in-up space-y-3">
        <h1 className="max-w-[7ch] text-[72px] font-ui font-semibold leading-none tracking-[-0.08em] text-primary sm:text-[88px]">
          Mimir
        </h1>
        <p className="max-w-[20rem] pl-1 text-[12px] font-ui font-medium tracking-[0.28em] text-primary/88 sm:max-w-none">
          Draw from depth.
        </p>
      </div>

      {isActiveWorkspace ? (
        <ResearchWorkspaceShell />
      ) : (
        <section className="space-y-sp-10">
          <div className="animate-fade-in-up stagger-1">
            <ResearchConfigPanel />
          </div>
          <div className="animate-fade-in-up stagger-2">
            <ExamplePrompts />
          </div>
        </section>
      )}

      <UnifiedInputBar />
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
