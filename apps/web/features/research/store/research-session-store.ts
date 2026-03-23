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
  TimelineItem,
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

function clearFeedbackUiStateInState(): Pick<
  ResearchSessionState["ui"],
  "feedbackFieldError" | "feedbackSubmitError"
> {
  return {
    feedbackFieldError: null,
    feedbackSubmitError: null,
  };
}

function createRevisionDividerTimelineItem(
  args: {
    revisionId: string;
    revisionNumber: number;
    occurredAt: string;
  },
): TimelineItem {
  return {
    id: `revision-divider:${args.revisionId}`,
    revisionId: args.revisionId,
    kind: "phase",
    label: `第 ${args.revisionNumber} 轮研究开始`,
    status: "completed",
    occurredAt: args.occurredAt,
  };
}

function startRevisionTransitionInState(
  state: ResearchSessionState,
  args: {
    pendingRevisionId: string;
    pendingRevisionNumber: number;
  },
): ResearchSessionState {
  return {
    ...state,
    ui: {
      ...state.ui,
      ...clearFeedbackUiStateInState(),
      revisionTransition: {
        status: "waiting_next_revision",
        pendingRevisionId: args.pendingRevisionId,
        pendingRevisionNumber: args.pendingRevisionNumber,
      },
    },
  };
}

function enterRevisionSwitchingInState(
  state: ResearchSessionState,
  event: EventEnvelope,
): ResearchSessionState {
  const pendingRevisionId =
    state.ui.revisionTransition.pendingRevisionId ?? event.revision_id ?? "rev_unknown";
  const pendingRevisionNumber =
    state.ui.revisionTransition.pendingRevisionNumber ??
    state.remote.snapshot?.active_revision_number ??
    1;
  const nextSnapshot =
    state.remote.snapshot === null
      ? null
      : {
          ...state.remote.snapshot,
          active_revision_id: pendingRevisionId,
          active_revision_number: pendingRevisionNumber,
          phase: event.phase,
          status:
            state.remote.snapshot.status === "awaiting_feedback"
              ? "running"
              : state.remote.snapshot.status,
          updated_at: event.timestamp,
          available_actions: [],
        };
  const hasDivider = state.stream.timeline.some((item) => {
    return item.id === `revision-divider:${pendingRevisionId}`;
  });

  return {
    ...state,
    remote: {
      ...state.remote,
      snapshot: nextSnapshot,
      currentRevision: {
        revision_id: pendingRevisionId,
        revision_number: pendingRevisionNumber,
        revision_status: "in_progress",
        started_at: event.timestamp,
        finished_at: null,
        requirement_detail: null,
      },
      delivery: null,
    },
    stream: {
      ...state.stream,
      analysisText: "",
      clarificationText: "",
      questionSet: null,
      reportMarkdown: "",
      outline: null,
      outlineReady: false,
      timeline: hasDivider
        ? state.stream.timeline
        : [
            ...state.stream.timeline,
            createRevisionDividerTimelineItem({
              revisionId: pendingRevisionId,
              revisionNumber: pendingRevisionNumber,
              occurredAt: event.timestamp,
            }),
          ],
      artifacts: [],
    },
    ui: {
      ...state.ui,
      clarificationDraft: "",
      optionAnswers: {},
      clarificationCountdownDeadlineAt: null,
      clarificationCountdownDurationSeconds: null,
      clarificationFieldError: null,
      clarificationSubmitError: null,
      ...clearFeedbackUiStateInState(),
      revisionTransition: {
        status: "switching",
        pendingRevisionId,
        pendingRevisionNumber,
      },
      reportAutoScrollEnabled: true,
    },
    deliveryUi: {
      ...state.deliveryUi,
      refreshingDelivery: false,
      markdownDownloadState: "idle",
      pdfDownloadState: "idle",
    },
  };
}

function finishRevisionTransitionInState(
  state: ResearchSessionState,
): ResearchSessionState {
  return {
    ...state,
    ui: {
      ...state.ui,
      revisionTransition: {
        status: "idle",
        pendingRevisionId: null,
        pendingRevisionNumber: null,
      },
    },
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
      explicitAbortRequested: false,
      lastServerActivityAt: null,
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
        pendingAction: null,
        revisionTransition: {
          status: "idle",
          pendingRevisionId: null,
          pendingRevisionNumber: null,
        },
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
      pendingAction: null,
      revisionTransition: {
        status: "idle",
        pendingRevisionId: null,
        pendingRevisionNumber: null,
      },
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
    setFeedbackDraft: (draft) => {
      set((state) => ({
        ...state,
        ui: {
          ...state.ui,
          feedbackDraft: draft,
          ...clearFeedbackUiStateInState(),
        },
      }));
    },
    setFeedbackFieldError: (message) => {
      set((state) => ({
        ...state,
        ui: {
          ...state.ui,
          feedbackFieldError: message,
        },
      }));
    },
    setFeedbackSubmitError: (message) => {
      set((state) => ({
        ...state,
        ui: {
          ...state.ui,
          feedbackSubmitError: message,
        },
      }));
    },
    clearFeedbackUiState: () => {
      set((state) => ({
        ...state,
        ui: {
          ...state.ui,
          ...clearFeedbackUiStateInState(),
        },
      }));
    },
    startRevisionTransition: ({ pendingRevisionId, pendingRevisionNumber }) => {
      set((state) =>
        startRevisionTransitionInState(state, {
          pendingRevisionId,
          pendingRevisionNumber,
        }),
      );
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
      set((state) => {
        if (
          state.stream.lastEventSeq !== null &&
          event.seq <= state.stream.lastEventSeq
        ) {
          return state;
        }

        let nextState: ResearchSessionState = state;

        if (
          nextState.ui.revisionTransition.status === "waiting_next_revision" &&
          nextState.ui.revisionTransition.pendingRevisionId !== null &&
          event.revision_id === nextState.ui.revisionTransition.pendingRevisionId
        ) {
          nextState = enterRevisionSwitchingInState(nextState, event);
        }

        nextState = reduceResearchSessionEvent(nextState, event);

        if (
          nextState.ui.revisionTransition.status === "switching" &&
          nextState.ui.revisionTransition.pendingRevisionId !== null &&
          event.event === "phase.changed" &&
          event.revision_id === nextState.ui.revisionTransition.pendingRevisionId &&
          event.payload.to_phase === "planning_collection"
        ) {
          nextState = finishRevisionTransitionInState(nextState);
        }

        return {
          ...state,
          ...nextState,
        };
      });
    },
  }));
}
