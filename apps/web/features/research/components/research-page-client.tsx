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
      <div className="animate-fade-in-up space-y-1" data-testid="research-hero">
        <h1 className="text-[68px] font-ui font-semibold uppercase leading-[0.88] tracking-[-0.02em] text-white sm:text-[84px]">
          MIMIR
        </h1>
        <div
          className="flex w-full items-baseline justify-between gap-4"
          data-testid="research-hero-metadata-row"
        >
          <p
            className="flex max-w-[20rem] min-w-0 items-baseline gap-[0.14rem] text-[11px] font-ui font-medium tracking-[0.24em] text-secondary sm:max-w-none"
            data-testid="research-hero-slogan"
          >
            <span className="text-secondary opacity-70">Draw from depth</span>
            <span aria-hidden="true" className="text-primary opacity-45">
              _
            </span>
          </p>
          <a
            className="inline-flex shrink-0 justify-self-end items-baseline gap-1 whitespace-nowrap text-[10px] font-ui font-medium uppercase tracking-[0.18em] text-secondary opacity-55 transition-opacity hover:opacity-80 focus-visible:opacity-80"
            href="https://robiniflore.com"
            rel="noreferrer noopener"
            target="_blank"
          >
            <span aria-hidden="true" className="text-tertiary">
              &gt;
            </span>
            <span>robiniflore.com</span>
            <span aria-hidden="true" className="text-tertiary">
              ↗
            </span>
          </a>
        </div>
      </div>

      {isActiveWorkspace ? (
        <>
          <ResearchWorkspaceShell />
          <UnifiedInputBar />
        </>
      ) : (
        <section className="flex flex-1 flex-col justify-center">
          <div className="flex w-full flex-col gap-4">
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
