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
