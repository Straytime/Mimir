import { createStore } from "zustand/vanilla";

import type {
  ClarificationMode,
  CreateTaskResponse,
  EventEnvelope,
  TaskSnapshot,
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

const TERMINAL_STATUS_SET = new Set<string>(["terminated", "failed", "expired"]);

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

function clearClarificationUiStateInState(
): Pick<
  ResearchSessionState["ui"],
  | "clarificationFieldError"
  | "clarificationSubmitError"
  | "clarificationCountdownDeadlineAt"
  | "clarificationCountdownDurationSeconds"
> {
  return {
    clarificationFieldError: null,
    clarificationSubmitError: null,
    clarificationCountdownDeadlineAt: null,
    clarificationCountdownDurationSeconds: null,
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

function mergeRemoteSnapshotIntoState(
  state: ResearchSessionState,
  snapshot: TaskSnapshot,
): ResearchSessionState {
  return {
    ...state,
    remote: {
      ...state.remote,
      snapshot: mergeTaskSnapshot({
        currentSnapshot: state.remote.snapshot,
        incomingSnapshot: snapshot,
        source: "authoritative",
      }),
    },
  };
}

function setTerminalStateInState(
  state: ResearchSessionState,
  args: {
    terminalReason: Exclude<ResearchSessionState["ui"]["terminalReason"], null>;
    timestamp: string;
    expiresAt?: string | null;
    sseState?: ResearchSessionState["session"]["sseState"];
  },
): ResearchSessionState {
  const currentTerminalReason = state.ui.terminalReason;
  const snapshot = state.remote.snapshot;

  if (currentTerminalReason !== null) {
    return {
      ...state,
      session: {
        ...state.session,
        sseState: args.sseState ?? state.session.sseState,
      },
    };
  }

  if (snapshot === null) {
    return {
      ...state,
      session: {
        ...state.session,
        sseState: args.sseState ?? state.session.sseState,
      },
      ui: {
        ...state.ui,
        terminalReason: args.terminalReason,
      },
    };
  }

  const nextStatus =
    args.terminalReason === "failed"
      ? "failed"
      : args.terminalReason === "expired"
        ? "expired"
        : "terminated";

  return {
    ...state,
    session: {
      ...state.session,
      sseState: args.sseState ?? state.session.sseState,
    },
    remote: {
      ...state.remote,
      snapshot: TERMINAL_STATUS_SET.has(snapshot.status)
        ? snapshot
        : {
            ...snapshot,
            status: nextStatus,
            updated_at: args.timestamp,
            expires_at:
              args.terminalReason === "expired"
                ? args.expiresAt ?? args.timestamp
                : snapshot.expires_at,
            available_actions: [],
          },
    },
    ui: {
      ...state.ui,
      terminalReason: args.terminalReason,
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
    setClarificationDraft: (draft) => {
      set((state) => ({
        ...state,
        ui: {
          ...state.ui,
          clarificationDraft: draft,
          clarificationFieldError: null,
          clarificationSubmitError: null,
        },
      }));
    },
    setClarificationFieldError: (message) => {
      set((state) => ({
        ...state,
        ui: {
          ...state.ui,
          clarificationFieldError: message,
        },
      }));
    },
    setClarificationSubmitError: (message) => {
      set((state) => ({
        ...state,
        ui: {
          ...state.ui,
          clarificationSubmitError: message,
        },
      }));
    },
    clearClarificationUiState: () => {
      set((state) => ({
        ...state,
        ui: {
          ...state.ui,
          ...clearClarificationUiStateInState(),
        },
      }));
    },
    setOptionAnswer: ({ questionId, optionId }) => {
      set((state) => ({
        ...state,
        ui: {
          ...state.ui,
          optionAnswers: {
            ...state.ui.optionAnswers,
            [questionId]: optionId,
          },
          clarificationCountdownDeadlineAt:
            state.ui.clarificationCountdownDurationSeconds === null
              ? state.ui.clarificationCountdownDeadlineAt
              : new Date(
                  Date.now() +
                    state.ui.clarificationCountdownDurationSeconds * 1000,
                ).toISOString(),
          clarificationFieldError: null,
          clarificationSubmitError: null,
        },
      }));
    },
    setClarificationCountdown: ({ durationSeconds, startedAt }) => {
      set((state) => ({
        ...state,
        ui: {
          ...state.ui,
          clarificationCountdownDeadlineAt: new Date(
            (startedAt === null || startedAt === undefined
              ? Date.now()
              : new Date(startedAt).getTime()) +
              durationSeconds * 1000,
          ).toISOString(),
          clarificationCountdownDurationSeconds: durationSeconds,
        },
      }));
    },
    clearClarificationCountdown: () => {
      set((state) => ({
        ...state,
        ui: {
          ...state.ui,
          clarificationCountdownDeadlineAt: null,
          clarificationCountdownDurationSeconds: null,
        },
      }));
    },
    mergeRemoteSnapshot: (snapshot: TaskSnapshot) => {
      set((state) => mergeRemoteSnapshotIntoState(state, snapshot));
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
    setReportAutoScrollEnabled: (enabled) => {
      set((state) => ({
        ...state,
        ui: {
          ...state.ui,
          reportAutoScrollEnabled: enabled,
        },
      }));
    },
    setRefreshingDelivery: (refreshingDelivery) => {
      set((state) => ({
        ...state,
        deliveryUi: {
          ...state.deliveryUi,
          refreshingDelivery,
        },
      }));
    },
    setDownloadState: ({ format, state: nextState }) => {
      set((currentState) => ({
        ...currentState,
        deliveryUi: {
          ...currentState.deliveryUi,
          markdownDownloadState:
            format === "markdown"
              ? nextState
              : currentState.deliveryUi.markdownDownloadState,
          pdfDownloadState:
            format === "pdf"
              ? nextState
              : currentState.deliveryUi.pdfDownloadState,
        },
      }));
    },
    setTerminalState: (args) => {
      set((state) => setTerminalStateInState(state, args));
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
