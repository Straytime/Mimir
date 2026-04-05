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
      className={`mx-auto flex min-h-screen w-full max-w-[800px] flex-col bg-radial-glow px-sp-8 pt-16 ${
        isActiveWorkspace ? "gap-sp-10 pb-32" : "gap-sp-8 pb-16"
      }`}
      ref={mainRef}
    >
      <div className="animate-fade-in-up space-y-1">
        <h1 className="text-[68px] font-ui font-semibold uppercase leading-[0.88] tracking-[-0.02em] text-white sm:text-[84px]">
          MIMIR
        </h1>
        <p
          className="flex max-w-[20rem] items-baseline gap-[0.14rem] pl-[0.18rem] text-[11px] font-ui font-medium tracking-[0.24em] text-secondary sm:max-w-none"
          data-testid="research-hero-slogan"
        >
          <span className="text-secondary opacity-70">Draw from depth</span>
          <span aria-hidden="true" className="text-primary opacity-45">
            _
          </span>
        </p>
      </div>

      {isActiveWorkspace ? (
        <>
          <ResearchWorkspaceShell />
          <UnifiedInputBar />
        </>
      ) : (
        <section className="flex flex-1 flex-col justify-center">
          <div className="mx-auto flex w-full max-w-[680px] flex-col gap-4">
            <div className="animate-fade-in-up stagger-1">
              <ExamplePrompts />
            </div>
            <div className="animate-fade-in-up stagger-2">
              <UnifiedInputBar />
            </div>
            <div className="animate-fade-in-up stagger-3">
              <ResearchConfigPanel />
            </div>
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
