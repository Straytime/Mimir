import { expect, test } from "vitest";

import type { TaskSnapshot } from "@/lib/contracts";
import { makeTaskSnapshot } from "@/tests/fixtures/builders";

test("TaskSnapshot fixture stays compatible with the shared contract type", () => {
  const fixture: TaskSnapshot = makeTaskSnapshot();

  expect(fixture).toMatchObject({
    task_id: "tsk_stage0",
    status: "running",
    phase: "clarifying",
    active_revision_id: "rev_stage0",
    active_revision_number: 1,
    clarification_mode: "natural",
    expires_at: null,
    available_actions: [],
  });
});
