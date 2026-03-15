import { describe, expect, test } from "vitest";

import { mergeTaskSnapshot } from "@/features/research/mappers/task-snapshot-merger";
import { makeTaskSnapshot } from "@/tests/fixtures/builders";

describe("mergeTaskSnapshot", () => {
  test("uses the bootstrap snapshot when no local snapshot exists", () => {
    const bootstrapSnapshot = makeTaskSnapshot({
      available_actions: ["submit_clarification"],
      status: "awaiting_user_input",
      updated_at: "2026-03-13T14:30:02+08:00",
    });

    const result = mergeTaskSnapshot({
      currentSnapshot: null,
      incomingSnapshot: bootstrapSnapshot,
      source: "bootstrap",
    });

    expect(result).toEqual(bootstrapSnapshot);
  });

  test("lets task.created replace the bootstrap snapshot as the first authoritative snapshot", () => {
    const bootstrapSnapshot = makeTaskSnapshot({
      available_actions: ["submit_clarification"],
      status: "awaiting_user_input",
      updated_at: "2026-03-13T14:30:02+08:00",
    });
    const authoritativeSnapshot = makeTaskSnapshot({
      available_actions: [],
      status: "running",
      updated_at: "2026-03-13T14:30:00+08:00",
    });

    const result = mergeTaskSnapshot({
      currentSnapshot: bootstrapSnapshot,
      incomingSnapshot: authoritativeSnapshot,
      source: "authoritative",
    });

    expect(result).toEqual(authoritativeSnapshot);
  });

  test("keeps the newer local snapshot when a task detail payload is older", () => {
    const currentSnapshot = makeTaskSnapshot({
      phase: "writing_report",
      updated_at: "2026-03-13T14:40:00+08:00",
    });
    const staleDetailSnapshot = makeTaskSnapshot({
      phase: "analyzing_requirement",
      updated_at: "2026-03-13T14:35:00+08:00",
    });

    const result = mergeTaskSnapshot({
      currentSnapshot,
      incomingSnapshot: staleDetailSnapshot,
      source: "detail",
    });

    expect(result).toBe(currentSnapshot);
  });

  test("does not let later snapshots override a terminal snapshot", () => {
    const terminalSnapshot = makeTaskSnapshot({
      status: "terminated",
      phase: "writing_report",
      updated_at: "2026-03-13T14:45:00+08:00",
    });
    const laterDetailSnapshot = makeTaskSnapshot({
      status: "running",
      phase: "delivered",
      updated_at: "2026-03-13T14:50:00+08:00",
    });

    const result = mergeTaskSnapshot({
      currentSnapshot: terminalSnapshot,
      incomingSnapshot: laterDetailSnapshot,
      source: "detail",
    });

    expect(result).toBe(terminalSnapshot);
  });
});
