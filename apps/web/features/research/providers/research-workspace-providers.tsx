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
  taskEventSource: createNoopTaskEventSource<EventEnvelope>(),
};

const ResearchSessionStoreContext =
  createContext<StoreApi<ResearchSessionStore> | null>(null);
const ResearchRuntimeContext = createContext<ResearchRuntime>(defaultRuntime);

export function ResearchWorkspaceProviders({
  children,
  runtime,
  store,
}: ResearchWorkspaceProvidersProps) {
  const storeRef = useRef(store ?? createResearchSessionStore());

  return (
    <ResearchRuntimeContext.Provider
      value={{
        taskApiClient: runtime?.taskApiClient ?? defaultRuntime.taskApiClient,
        taskEventSource:
          runtime?.taskEventSource ?? defaultRuntime.taskEventSource,
      }}
    >
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
