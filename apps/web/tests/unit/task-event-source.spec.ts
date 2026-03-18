import { afterEach, describe, expect, test, vi } from "vitest";

import { createFetchTaskEventSource } from "@/lib/sse/task-event-source";

function createSseStream(chunks: string[]) {
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(new TextEncoder().encode(chunk));
      }
      controller.close();
    },
  });
}

describe("createFetchTaskEventSource", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("sends Authorization header, opens the stream, parses events, and closes", async () => {
    const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      expect(String(input)).toBe("https://api.example.com/api/v1/tasks/tsk_1/events");
      expect(init?.headers).toMatchObject({
        Accept: "text/event-stream",
        Authorization: "Bearer secret-task-token",
      });

      return new Response(
        createSseStream([
          'id: 1\nevent: task.created\ndata: {"seq":1,"event":"task.created"}\n\n',
          'id: 2\nevent: heartbeat\ndata: {"seq":2,"event":"heartbeat"}\n\n',
        ]),
        {
          status: 200,
          headers: {
            "Content-Type": "text/event-stream",
          },
        },
      );
    });

    const onOpen = vi.fn();
    const onEvent = vi.fn();
    const onClose = vi.fn();
    const onError = vi.fn();

    createFetchTaskEventSource({ fetchImpl }).connect({
      url: "https://api.example.com/api/v1/tasks/tsk_1/events",
      token: "secret-task-token",
      onOpen,
      onEvent,
      onClose,
      onError,
    });

    await vi.waitFor(() => {
      expect(onOpen).toHaveBeenCalledTimes(1);
      expect(onEvent).toHaveBeenCalledTimes(2);
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    expect(onEvent).toHaveBeenNthCalledWith(1, {
      seq: 1,
      event: "task.created",
    });
    expect(onEvent).toHaveBeenNthCalledWith(2, {
      seq: 2,
      event: "heartbeat",
    });
    expect(onError).not.toHaveBeenCalled();
  });

  test("reports stream errors for non-ok responses", async () => {
    const fetchImpl = vi.fn(async () => new Response("unauthorized", { status: 401 }));
    const onError = vi.fn();

    createFetchTaskEventSource({ fetchImpl }).connect({
      url: "https://api.example.com/api/v1/tasks/tsk_1/events",
      token: "secret-task-token",
      onOpen: vi.fn(),
      onEvent: vi.fn(),
      onClose: vi.fn(),
      onError,
    });

    await vi.waitFor(() => {
      expect(onError).toHaveBeenCalledTimes(1);
    });
  });

  test("aborting the stream suppresses close and error callbacks", async () => {
    const controls: { releaseChunk?: () => void } = {};
    const fetchImpl = vi.fn(async () => {
      const stream = new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(
            new TextEncoder().encode(
              'id: 1\nevent: task.created\ndata: {"seq":1,"event":"task.created"}\n\n',
            ),
          );
          controls.releaseChunk = () => controller.close();
        },
      });

      return new Response(stream, {
        status: 200,
        headers: {
          "Content-Type": "text/event-stream",
        },
      });
    });

    const onOpen = vi.fn();
    const onEvent = vi.fn();
    const onClose = vi.fn();
    const onError = vi.fn();

    const unsubscribe = createFetchTaskEventSource({ fetchImpl }).connect({
      url: "https://api.example.com/api/v1/tasks/tsk_1/events",
      token: "secret-task-token",
      onOpen,
      onEvent,
      onClose,
      onError,
    });

    await vi.waitFor(() => {
      expect(onOpen).toHaveBeenCalledTimes(1);
      expect(onEvent).toHaveBeenCalledTimes(1);
    });

    unsubscribe();
    if (typeof controls.releaseChunk === "function") {
      controls.releaseChunk();
    }

    await Promise.resolve();
    await Promise.resolve();

    expect(onClose).not.toHaveBeenCalled();
    expect(onError).not.toHaveBeenCalled();
  });
});
