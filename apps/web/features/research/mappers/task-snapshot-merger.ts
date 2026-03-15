import { TERMINAL_TASK_STATUSES } from "@/lib/contracts";
import type { TaskSnapshot } from "@/lib/contracts";

export type TaskSnapshotMergeSource = "bootstrap" | "authoritative" | "detail";

type MergeTaskSnapshotArgs = {
  currentSnapshot: TaskSnapshot | null;
  incomingSnapshot: TaskSnapshot;
  source: TaskSnapshotMergeSource;
};

const TERMINAL_STATUS_SET = new Set<string>(TERMINAL_TASK_STATUSES);

function isTerminalSnapshot(snapshot: TaskSnapshot | null): boolean {
  return snapshot !== null && TERMINAL_STATUS_SET.has(snapshot.status);
}

export function mergeTaskSnapshot({
  currentSnapshot,
  incomingSnapshot,
  source,
}: MergeTaskSnapshotArgs): TaskSnapshot {
  if (currentSnapshot === null) {
    return incomingSnapshot;
  }

  if (isTerminalSnapshot(currentSnapshot)) {
    return currentSnapshot;
  }

  if (source === "bootstrap") {
    return currentSnapshot;
  }

  if (source === "authoritative") {
    return incomingSnapshot;
  }

  if (incomingSnapshot.updated_at > currentSnapshot.updated_at) {
    return incomingSnapshot;
  }

  return currentSnapshot;
}
