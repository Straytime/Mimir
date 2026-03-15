import { createStore } from "zustand/vanilla";

import type { EventEnvelope, TaskDetailResponse } from "@/lib/contracts";

import { mergeTaskSnapshot } from "../mappers/task-snapshot-merger";
import { reduceResearchSessionEvent } from "../reducers/event-reducer";
import type {
  ResearchSessionState,
  ResearchSessionStore,
} from "./research-session-store.types";
import { createResearchSessionState } from "./research-session-store.types";

function mergeTaskDetailIntoState(
  state: ResearchSessionState,
  detail: TaskDetailResponse,
): ResearchSessionState {
  return {
    ...state,
    remote: {
      snapshot: mergeTaskSnapshot({
        currentSnapshot: state.remote.snapshot,
        incomingSnapshot: detail.snapshot,
        source: "detail",
      }),
      currentRevision: detail.current_revision,
      delivery: detail.delivery,
    },
  };
}

export function createResearchSessionStore(
  initialState: ResearchSessionState = createResearchSessionState(),
) {
  return createStore<ResearchSessionStore>()((set) => ({
    ...initialState,
    reset: () => {
      set(createResearchSessionState());
    },
    setSessionContext: (sessionPatch) => {
      set((state) => ({
        ...state,
        session: {
          ...state.session,
          ...sessionPatch,
        },
      }));
    },
    mergeTaskDetail: (detail: TaskDetailResponse) => {
      set((state) => mergeTaskDetailIntoState(state, detail));
    },
    applyEvent: (event: EventEnvelope) => {
      set((state) => reduceResearchSessionEvent(state, event));
    },
  }));
}
