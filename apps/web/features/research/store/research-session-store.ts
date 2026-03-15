import { createStore } from "zustand/vanilla";

import type {
  ClarificationMode,
  CreateTaskResponse,
  EventEnvelope,
  TaskDetailResponse,
} from "@/lib/contracts";

import { mergeTaskSnapshot } from "../mappers/task-snapshot-merger";
import { reduceResearchSessionEvent } from "../reducers/event-reducer";
import type {
  CreateTaskUiState,
  PendingAction,
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

function clearCreateTaskUiStateInState(
  state: ResearchSessionState,
): ResearchSessionState["ui"]["createTask"] {
  return {
    ...state.ui.createTask,
    initialQueryError: null,
    submitError: null,
    errorCode: null,
    nextAvailableAt: null,
    retryAfterLabel: null,
  };
}

function bootstrapCreateTaskIntoState(
  state: ResearchSessionState,
  response: CreateTaskResponse,
  requestId: string | null,
): ResearchSessionState {
  return {
    ...state,
    session: {
      ...state.session,
      taskId: response.task_id,
      taskToken: response.task_token,
      traceId: response.trace_id,
      requestId,
      eventsUrl: response.urls.events,
      heartbeatUrl: response.urls.heartbeat,
      disconnectUrl: response.urls.disconnect,
      connectDeadlineAt: response.connect_deadline_at,
      sseState: "connecting",
    },
    remote: {
      ...state.remote,
      snapshot: mergeTaskSnapshot({
        currentSnapshot: state.remote.snapshot,
        incomingSnapshot: response.snapshot,
        source: "bootstrap",
      }),
    },
    ui: {
      ...state.ui,
      createTask: clearCreateTaskUiStateInState(state),
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
    setInitialPromptDraft: (draft) => {
      set((state) => ({
        ...state,
        ui: {
          ...state.ui,
          initialPromptDraft: draft,
        },
      }));
    },
    setCreateTaskClarificationModeDraft: (mode: ClarificationMode) => {
      set((state) => ({
        ...state,
        ui: {
          ...state.ui,
          createTask: {
            ...state.ui.createTask,
            clarificationModeDraft: mode,
          },
        },
      }));
    },
    setCreateTaskUiState: (patch: Partial<CreateTaskUiState>) => {
      set((state) => ({
        ...state,
        ui: {
          ...state.ui,
          createTask: {
            ...state.ui.createTask,
            ...patch,
          },
        },
      }));
    },
    clearCreateTaskUiState: () => {
      set((state) => ({
        ...state,
        ui: {
          ...state.ui,
          createTask: clearCreateTaskUiStateInState(state),
        },
      }));
    },
    setPendingAction: (pendingAction: PendingAction) => {
      set((state) => ({
        ...state,
        ui: {
          ...state.ui,
          pendingAction,
        },
      }));
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
    bootstrapCreateTask: ({ response, requestId }) => {
      set((state) => bootstrapCreateTaskIntoState(state, response, requestId));
    },
    mergeTaskDetail: (detail: TaskDetailResponse) => {
      set((state) => mergeTaskDetailIntoState(state, detail));
    },
    applyEvent: (event: EventEnvelope) => {
      set((state) => reduceResearchSessionEvent(state, event));
    },
  }));
}
