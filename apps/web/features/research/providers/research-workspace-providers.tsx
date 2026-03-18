"use client";

import {
  createContext,
  useContext,
  useRef,
  type PropsWithChildren,
} from "react";
import { useStore, type StoreApi } from "zustand";

import { createFetchTaskApiClient, type TaskApiClient } from "@/lib/api/task-api-client";
import {
  createFetchTaskEventSource,
  createNoopTaskEventSource,
  type TaskEventSource,
} from "@/lib/sse/task-event-source";
import type { EventEnvelope } from "@/lib/contracts";

import {
  createResearchSessionStore,
} from "../store/research-session-store";
import type { ResearchSessionStore } from "../store/research-session-store.types";

export type ResearchRuntime = {
  taskApiClient: TaskApiClient;
  taskEventSource: TaskEventSource<EventEnvelope>;
};

export type ResearchWorkspaceProvidersProps = PropsWithChildren<{
  runtime?: Partial<ResearchRuntime>;
  store?: StoreApi<ResearchSessionStore>;
}>;

const defaultRuntime: ResearchRuntime = {
  taskApiClient: createFetchTaskApiClient(),
  taskEventSource:
    typeof window === "undefined"
      ? createNoopTaskEventSource<EventEnvelope>()
      : createFetchTaskEventSource<EventEnvelope>(),
};

const ResearchSessionStoreContext =
  createContext<StoreApi<ResearchSessionStore> | null>(null);
const ResearchRuntimeContext = createContext<ResearchRuntime>(defaultRuntime);

export function ResearchWorkspaceProviders({
  children,
  runtime,
  store,
}: ResearchWorkspaceProvidersProps) {
  const windowRuntimeOverride =
    typeof window === "undefined" ? null : window.__MIMIR_TEST_RUNTIME__;
  const storeRef = useRef(store ?? createResearchSessionStore());
  const runtimeRef = useRef<ResearchRuntime | null>(null);

  if (runtimeRef.current === null) {
    runtimeRef.current = {
      taskApiClient:
        runtime?.taskApiClient ??
        windowRuntimeOverride?.taskApiClient ??
        defaultRuntime.taskApiClient,
      taskEventSource:
        runtime?.taskEventSource ??
        windowRuntimeOverride?.taskEventSource ??
        defaultRuntime.taskEventSource,
    };
  }

  if (windowRuntimeOverride !== null && typeof window !== "undefined") {
    Reflect.set(window, "__MIMIR_TEST_STORE__", storeRef.current);
  }

  return (
    <ResearchRuntimeContext.Provider value={runtimeRef.current}>
      <ResearchSessionStoreContext.Provider value={storeRef.current}>
        {children}
      </ResearchSessionStoreContext.Provider>
    </ResearchRuntimeContext.Provider>
  );
}

export function useResearchRuntime() {
  return useContext(ResearchRuntimeContext);
}

export function useResearchSessionStore<T>(
  selector: (state: ResearchSessionStore) => T,
) {
  const store = useContext(ResearchSessionStoreContext);

  if (store === null) {
    throw new Error("useResearchSessionStore must be used within providers.");
  }

  return useStore(store, selector);
}
