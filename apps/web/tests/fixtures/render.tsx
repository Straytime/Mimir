import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import type { StoreApi } from "zustand";

import { ResearchWorkspaceProviders, type ResearchRuntime } from "@/features/research/providers/research-workspace-providers";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import type { ResearchSessionStore } from "@/features/research/store/research-session-store.types";

type TestProvidersProps = {
  children: ReactNode;
  runtime?: Partial<ResearchRuntime>;
  store?: StoreApi<ResearchSessionStore>;
};

function TestProviders({ children, runtime, store }: TestProvidersProps) {
  return (
    <ResearchWorkspaceProviders runtime={runtime} store={store}>
      {children}
    </ResearchWorkspaceProviders>
  );
}

type RenderWithStoreOptions = Omit<RenderOptions, "wrapper"> & {
  runtime?: Partial<ResearchRuntime>;
  store?: StoreApi<ResearchSessionStore>;
};

export function renderWithStore(
  ui: ReactElement,
  options?: RenderWithStoreOptions,
) {
  const store = options?.store ?? createResearchSessionStore();
  const runtime = options?.runtime;
  const renderOptions = {
    ...options,
  };

  delete renderOptions.runtime;
  delete renderOptions.store;

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <TestProviders runtime={runtime} store={store}>
        {children}
      </TestProviders>
    );
  }

  const result = render(ui, {
    wrapper: Wrapper,
    ...renderOptions,
  });

  return {
    ...result,
    store,
  };
}
