import { TERMINAL_TASK_STATUSES } from "@/lib/contracts";
import type { AvailableAction } from "@/lib/contracts";

import type { ResearchSessionState } from "./research-session-store.types";

const TERMINAL_STATUS_SET = new Set<string>(TERMINAL_TASK_STATUSES);

export function selectSnapshot(state: ResearchSessionState) {
  return state.remote.snapshot;
}

export function selectAvailableActions(state: ResearchSessionState) {
  return state.remote.snapshot?.available_actions ?? [];
}

export function selectIsAwaitingClarification(state: ResearchSessionState) {
  return state.remote.snapshot?.status === "awaiting_user_input";
}

export function selectIsResearchRunning(state: ResearchSessionState) {
  return state.remote.snapshot?.status === "running";
}

export function selectIsAwaitingFeedback(state: ResearchSessionState) {
  return (
    state.remote.snapshot?.status === "awaiting_feedback" &&
    state.remote.snapshot.phase === "delivered"
  );
}

function isTerminalState(state: ResearchSessionState) {
  const snapshot = state.remote.snapshot;

  return snapshot !== null && TERMINAL_STATUS_SET.has(snapshot.status);
}

export function selectIsTerminalState(state: ResearchSessionState) {
  return isTerminalState(state);
}

function hasAvailableAction(
  state: ResearchSessionState,
  action: AvailableAction,
) {
  if (isTerminalState(state)) {
    return false;
  }

  return selectAvailableActions(state).includes(action);
}

export function selectCanSubmitClarification(state: ResearchSessionState) {
  return hasAvailableAction(state, "submit_clarification");
}

export function selectCanSubmitFeedback(state: ResearchSessionState) {
  return hasAvailableAction(state, "submit_feedback");
}

export function selectCanDownloadMarkdown(state: ResearchSessionState) {
  return hasAvailableAction(state, "download_markdown");
}

export function selectCanDownloadPdf(state: ResearchSessionState) {
  return hasAvailableAction(state, "download_pdf");
}

export function selectCanDisconnectTask(state: ResearchSessionState) {
  return (
    state.remote.snapshot !== null &&
    !isTerminalState(state) &&
    state.ui.pendingAction !== "disconnecting"
  );
}
