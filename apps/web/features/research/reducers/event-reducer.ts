import type {
  EventEnvelope,
  RevisionSummary,
  TaskExpiredEventEnvelope,
  TaskFailedEventEnvelope,
  TaskTerminatedEventEnvelope,
  TaskSnapshot,
} from "@/lib/contracts";

import { mergeTaskSnapshot } from "../mappers/task-snapshot-merger";
import { reduceTimelineStream } from "../mappers/timeline-mapper";
import type {
  ResearchSessionState,
  TerminalReason,
} from "../store/research-session-store.types";

type TerminalEventEnvelope =
  | TaskExpiredEventEnvelope
  | TaskFailedEventEnvelope
  | TaskTerminatedEventEnvelope;

function withLastEventSeq(
  state: ResearchSessionState,
  lastEventSeq: number,
): ResearchSessionState {
  return {
    ...state,
    stream: {
      ...state.stream,
      lastEventSeq,
    },
  };
}

function updateSnapshotForTerminalEvent(
  snapshot: TaskSnapshot | null,
  event: TerminalEventEnvelope,
): TaskSnapshot | null {
  if (snapshot === null) {
    return null;
  }

  return {
    ...snapshot,
    status:
      event.event === "task.failed"
        ? "failed"
        : event.event === "task.terminated"
          ? "terminated"
          : "expired",
    updated_at: event.timestamp,
    expires_at:
      event.event === "task.expired"
        ? event.payload.expired_at
        : snapshot.expires_at,
    available_actions: [],
  };
}

function applyTerminalEvent(
  state: ResearchSessionState,
  event: TerminalEventEnvelope,
  terminalReason: TerminalReason,
): ResearchSessionState {
  return {
    ...withLastEventSeq(state, event.seq),
    remote: {
      ...state.remote,
      snapshot: updateSnapshotForTerminalEvent(state.remote.snapshot, event),
    },
    ui: {
      ...state.ui,
      terminalReason,
      pendingAction: null,
      revisionTransition: {
        status: "idle",
        pendingRevisionId: null,
        pendingRevisionNumber: null,
      },
    },
  };
}

function updateClarificationSnapshot(
  snapshot: TaskSnapshot | null,
  args: {
    status: "awaiting_user_input";
    availableActions: TaskSnapshot["available_actions"];
    clarificationMode: TaskSnapshot["clarification_mode"];
    timestamp: string;
  },
): TaskSnapshot | null {
  if (snapshot === null) {
    return null;
  }

  return {
    ...snapshot,
    status: args.status,
    available_actions: args.availableActions,
    clarification_mode: args.clarificationMode,
    updated_at: args.timestamp,
  };
}

function ensureCurrentRevision(
  state: ResearchSessionState,
  event: Extract<EventEnvelope, { event: "analysis.completed" }>,
): RevisionSummary {
  if (state.remote.currentRevision !== null) {
    return state.remote.currentRevision;
  }

  return {
    revision_id:
      event.revision_id ??
      state.remote.snapshot?.active_revision_id ??
      "rev_unknown",
    revision_number: state.remote.snapshot?.active_revision_number ?? 1,
    revision_status: "in_progress",
    started_at: event.timestamp,
    finished_at: null,
    requirement_detail: null,
  };
}

function reduceStreamTimeline(
  state: ResearchSessionState,
  event: EventEnvelope,
) {
  return reduceTimelineStream(
    {
      timeline: state.stream.timeline,
      outlineReady: state.stream.outlineReady,
    },
    event,
  );
}

export function reduceResearchSessionEvent(
  state: ResearchSessionState,
  event: EventEnvelope,
): ResearchSessionState {
  const stateWithLastEventSeq = withLastEventSeq(state, event.seq);

  switch (event.event) {
    case "task.created":
      return {
        ...stateWithLastEventSeq,
        remote: {
          ...state.remote,
          snapshot: mergeTaskSnapshot({
            currentSnapshot: state.remote.snapshot,
            incomingSnapshot: event.payload.snapshot,
            source: "authoritative",
          }),
        },
        ui: {
          ...state.ui,
          terminalReason: null,
        },
      };
    case "phase.changed":
      if (state.remote.snapshot === null) {
        return state;
      }

      {
        const nextTimelineStream = reduceStreamTimeline(
          stateWithLastEventSeq,
          event,
        );

        return {
          ...stateWithLastEventSeq,
          remote: {
            ...state.remote,
            snapshot: {
              ...state.remote.snapshot,
              phase: event.payload.to_phase,
              status: event.payload.status,
              active_revision_id:
                event.revision_id ?? state.remote.snapshot.active_revision_id,
              active_revision_number:
                event.revision_id === state.remote.snapshot.active_revision_id
                  ? state.remote.snapshot.active_revision_number
                  : state.remote.snapshot.active_revision_number,
              updated_at: event.timestamp,
            },
          },
          stream: {
            ...stateWithLastEventSeq.stream,
            ...nextTimelineStream,
          },
        };
      }
    case "heartbeat":
      return {
        ...stateWithLastEventSeq,
        session: {
          ...state.session,
          lastHeartbeatAt: event.payload.server_time,
        },
      };
    case "clarification.delta":
      return {
        ...stateWithLastEventSeq,
        stream: {
          ...stateWithLastEventSeq.stream,
          clarificationText: `${state.stream.clarificationText}${event.payload.delta}`,
        },
      };
    case "clarification.natural.ready":
      return {
        ...stateWithLastEventSeq,
        remote: {
          ...state.remote,
          snapshot: updateClarificationSnapshot(state.remote.snapshot, {
            status: event.payload.status,
            availableActions: event.payload.available_actions,
            clarificationMode: "natural",
            timestamp: event.timestamp,
          }),
        },
        stream: {
          ...stateWithLastEventSeq.stream,
          questionSet: null,
        },
        ui: {
          ...state.ui,
          optionAnswers: {},
          clarificationCountdownDeadlineAt: null,
          clarificationCountdownDurationSeconds: null,
          clarificationFieldError: null,
          clarificationSubmitError: null,
        },
      };
    case "clarification.options.ready":
      return {
        ...stateWithLastEventSeq,
        remote: {
          ...state.remote,
          snapshot: updateClarificationSnapshot(state.remote.snapshot, {
            status: event.payload.status,
            availableActions: event.payload.available_actions,
            clarificationMode: "options",
            timestamp: event.timestamp,
          }),
        },
        stream: {
          ...stateWithLastEventSeq.stream,
          questionSet: event.payload.question_set,
        },
        ui: {
          ...state.ui,
          optionAnswers: Object.fromEntries(
            event.payload.question_set.questions.map((question) => [
              question.question_id,
              "o_auto",
            ]),
          ),
          clarificationCountdownDeadlineAt: null,
          clarificationCountdownDurationSeconds: null,
          clarificationFieldError: null,
          clarificationSubmitError: null,
        },
      };
    case "clarification.countdown.started":
      return {
        ...stateWithLastEventSeq,
        ui: {
          ...state.ui,
          clarificationCountdownDeadlineAt: new Date(
            new Date(event.payload.started_at).getTime() +
              event.payload.duration_seconds * 1000,
          ).toISOString(),
          clarificationCountdownDurationSeconds: event.payload.duration_seconds,
        },
      };
    case "clarification.fallback_to_natural":
      return {
        ...stateWithLastEventSeq,
        remote: {
          ...state.remote,
          snapshot:
            state.remote.snapshot === null
              ? null
              : {
                  ...state.remote.snapshot,
                  clarification_mode: "natural",
                  updated_at: event.timestamp,
                },
        },
        stream: {
          ...stateWithLastEventSeq.stream,
          questionSet: null,
        },
        ui: {
          ...state.ui,
          optionAnswers: {},
          clarificationCountdownDeadlineAt: null,
          clarificationCountdownDurationSeconds: null,
          clarificationFieldError: null,
          clarificationSubmitError: null,
        },
      };
    case "analysis.delta":
      {
        const nextTimelineStream = reduceStreamTimeline(
          stateWithLastEventSeq,
          event,
        );

        return {
          ...stateWithLastEventSeq,
          stream: {
            ...stateWithLastEventSeq.stream,
            ...nextTimelineStream,
            analysisText: `${state.stream.analysisText}${event.payload.delta}`,
          },
        };
      }
    case "analysis.completed":
      {
        const nextTimelineStream = reduceStreamTimeline(
          stateWithLastEventSeq,
          event,
        );

        return {
          ...stateWithLastEventSeq,
          remote: {
            ...state.remote,
            currentRevision: {
              ...ensureCurrentRevision(state, event),
              requirement_detail: event.payload.requirement_detail,
            },
          },
          stream: {
            ...stateWithLastEventSeq.stream,
            ...nextTimelineStream,
            analysisText: "",
          },
        };
      }
    case "outline.delta":
    case "outline.completed":
    case "writer.reasoning.delta":
    case "writer.tool_call.requested":
    case "writer.tool_call.completed":
      if (event.event === "outline.completed") {
        return {
          ...stateWithLastEventSeq,
          stream: {
            ...stateWithLastEventSeq.stream,
            ...reduceStreamTimeline(stateWithLastEventSeq, event),
            outline: event.payload.outline,
          },
        };
      }

      return {
        ...stateWithLastEventSeq,
        stream: {
          ...stateWithLastEventSeq.stream,
          ...reduceStreamTimeline(stateWithLastEventSeq, event),
        },
      };
    case "writer.delta":
      return {
        ...stateWithLastEventSeq,
        stream: {
          ...stateWithLastEventSeq.stream,
          reportMarkdown: `${state.stream.reportMarkdown}${event.payload.delta}`,
        },
      };
    case "artifact.ready":
      return {
        ...stateWithLastEventSeq,
        stream: {
          ...stateWithLastEventSeq.stream,
          ...reduceStreamTimeline(stateWithLastEventSeq, event),
          artifacts: state.stream.artifacts.some(
            (artifact) =>
              artifact.artifact_id === event.payload.artifact.artifact_id,
          )
            ? state.stream.artifacts.map((artifact) =>
                artifact.artifact_id === event.payload.artifact.artifact_id
                  ? event.payload.artifact
                  : artifact,
              )
            : [...state.stream.artifacts, event.payload.artifact],
        },
      };
    case "report.completed":
      return {
        ...stateWithLastEventSeq,
        remote: {
          ...state.remote,
          delivery: event.payload.delivery,
        },
        stream: {
          ...stateWithLastEventSeq.stream,
          ...reduceStreamTimeline(stateWithLastEventSeq, event),
        },
      };
    case "task.awaiting_feedback":
      return {
        ...stateWithLastEventSeq,
        remote: {
          ...state.remote,
          snapshot:
            state.remote.snapshot === null
              ? null
              : {
                  ...state.remote.snapshot,
                  status: "awaiting_feedback",
                  phase: "delivered",
                  expires_at: event.payload.expires_at,
                  available_actions: event.payload.available_actions,
                  updated_at: event.timestamp,
                },
        },
      };
    case "planner.reasoning.delta":
    case "planner.tool_call.requested":
    case "collector.reasoning.delta":
    case "collector.search.started":
    case "collector.search.completed":
    case "collector.fetch.started":
    case "collector.fetch.completed":
    case "collector.completed":
    case "summary.completed":
    case "sources.merged":
      return {
        ...stateWithLastEventSeq,
        stream: {
          ...stateWithLastEventSeq.stream,
          ...reduceStreamTimeline(stateWithLastEventSeq, event),
        },
      };
    case "task.failed":
      return applyTerminalEvent(state, event, "failed");
    case "task.terminated":
      return applyTerminalEvent(state, event, "terminated");
    case "task.expired":
      return applyTerminalEvent(state, event, "expired");
    default:
      return state;
  }
}
