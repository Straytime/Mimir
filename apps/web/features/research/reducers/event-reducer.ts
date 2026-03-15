import type {
  EventEnvelope,
  TaskExpiredEventEnvelope,
  TaskFailedEventEnvelope,
  TaskTerminatedEventEnvelope,
  TaskSnapshot,
} from "@/lib/contracts";

import { mergeTaskSnapshot } from "../mappers/task-snapshot-merger";
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
    },
  };
}

export function reduceResearchSessionEvent(
  state: ResearchSessionState,
  event: EventEnvelope,
): ResearchSessionState {
  switch (event.event) {
    case "task.created":
      return {
        ...withLastEventSeq(state, event.seq),
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

      return {
        ...withLastEventSeq(state, event.seq),
        remote: {
          ...state.remote,
          snapshot: {
            ...state.remote.snapshot,
            phase: event.payload.to_phase,
            status: event.payload.status,
            active_revision_id:
              event.revision_id ?? state.remote.snapshot.active_revision_id,
            updated_at: event.timestamp,
          },
        },
      };
    case "heartbeat":
      return {
        ...withLastEventSeq(state, event.seq),
        session: {
          ...state.session,
          lastHeartbeatAt: event.payload.server_time,
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
