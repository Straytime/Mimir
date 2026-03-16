import type { ResearchRuntime } from "@/features/research/providers/research-workspace-providers";
import type { ResearchSessionStore } from "@/features/research/store/research-session-store.types";
import type { StoreApi } from "zustand";

declare global {
  interface Window {
    __MIMIR_TEST_RUNTIME__?: Partial<ResearchRuntime>;
    __MIMIR_TEST_STORE__?: StoreApi<ResearchSessionStore>;
  }
}

export {};
