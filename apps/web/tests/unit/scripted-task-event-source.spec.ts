import { vi, describe, expect, test } from "vitest";

import { ScriptedTaskEventSource } from "@/tests/fixtures/scripted-task-event-source";

describe("ScriptedTaskEventSource", () => {
  test("replays open, event, and close steps in order", async () => {
    vi.useFakeTimers();

    const onOpen = vi.fn();
    const onEvent = vi.fn();
    const onError = vi.fn();
    const onClose = vi.fn();

    const eventSource = new ScriptedTaskEventSource([
      { type: "open" },
      {
        type: "event",
        event: {
          event: "task.created",
          data: { task_id: "tsk_stage0" },
        },
      },
      { type: "close" },
    ]);

    const disconnect = eventSource.connect({
      url: "/api/v1/events",
      token: "task_token",
      onOpen,
      onEvent,
      onError,
      onClose,
    });

    await vi.runAllTimersAsync();

    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(onEvent).toHaveBeenCalledWith({
      event: "task.created",
      data: { task_id: "tsk_stage0" },
    });
    expect(onError).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalledTimes(1);

    disconnect();
    vi.useRealTimers();
  });
});
