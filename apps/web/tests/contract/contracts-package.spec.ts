import { expect, test } from "vitest";

test("workspace contracts package is importable from apps/web", async () => {
  const contractsModule = await import("@mimir/contracts");

  expect(contractsModule).toBeDefined();
  expect(Object.keys(contractsModule)).toEqual(
    expect.arrayContaining([
      "AVAILABLE_ACTIONS",
      "CLARIFICATION_MODES",
      "TASK_PHASES",
      "TASK_STATUSES",
      "TERMINAL_TASK_STATUSES",
    ]),
  );
});
