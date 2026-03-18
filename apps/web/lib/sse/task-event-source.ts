export type TaskEventSourceConnectArgs<TEvent = unknown> = {
  url: string;
  token: string;
  onOpen: () => void;
  onEvent: (event: TEvent) => void;
  onError: (error: unknown) => void;
  onClose: () => void;
};

export type TaskEventSource<TEvent = unknown> = {
  connect: (args: TaskEventSourceConnectArgs<TEvent>) => () => void;
};

type FetchTaskEventSourceOptions = {
  fetchImpl?: typeof fetch;
};

export function createNoopTaskEventSource<TEvent = unknown>(): TaskEventSource<TEvent> {
  return {
    connect: () => () => {},
  };
}

type ParsedSseMessage = {
  data: string | null;
};

function parseSseMessage(block: string): ParsedSseMessage | null {
  const lines = block.split(/\r?\n/);
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.length === 0 || line.startsWith(":")) {
      continue;
    }

    const separatorIndex = line.indexOf(":");
    const field = separatorIndex === -1 ? line : line.slice(0, separatorIndex);
    const rawValue =
      separatorIndex === -1 ? "" : line.slice(separatorIndex + 1).replace(/^ /, "");

    if (field === "data") {
      dataLines.push(rawValue);
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  return {
    data: dataLines.join("\n"),
  };
}

export function createFetchTaskEventSource<TEvent = unknown>(
  options: FetchTaskEventSourceOptions = {},
): TaskEventSource<TEvent> {
  const fetchImpl = options.fetchImpl ?? fetch;

  return {
    connect(args) {
      const controller = new AbortController();
      let closed = false;

      const run = async () => {
        try {
          const response = await fetchImpl(args.url, {
            method: "GET",
            headers: {
              Accept: "text/event-stream",
              Authorization: `Bearer ${args.token}`,
            },
            cache: "no-store",
            signal: controller.signal,
          });

          if (!response.ok || response.body === null) {
            if (!closed) {
              args.onError(
                new Error(`task_event_stream_failed:${response.status}`),
              );
            }
            return;
          }

          args.onOpen();

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";

          while (!closed) {
            const { done, value } = await reader.read();

            if (done) {
              break;
            }

            buffer += decoder.decode(value, { stream: true });

            while (true) {
              const boundaryIndex = buffer.search(/\r?\n\r?\n/);

              if (boundaryIndex === -1) {
                break;
              }

              const rawMessage = buffer.slice(0, boundaryIndex);
              const separator = buffer[boundaryIndex] === "\r" ? "\r\n\r\n" : "\n\n";
              buffer = buffer.slice(boundaryIndex + separator.length);

              const parsed = parseSseMessage(rawMessage);

              if (parsed?.data === null || parsed?.data === undefined) {
                continue;
              }

              args.onEvent(JSON.parse(parsed.data) as TEvent);
            }
          }

          if (!closed) {
            args.onClose();
          }
        } catch (error) {
          if (
            closed ||
            (error instanceof DOMException && error.name === "AbortError")
          ) {
            return;
          }

          args.onError(error);
        }
      };

      void run();

      return () => {
        closed = true;
        controller.abort();
      };
    },
  };
}
