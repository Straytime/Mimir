import type {
  TaskEventSource,
  TaskEventSourceConnectArgs,
} from "@/lib/sse/task-event-source";

type TimedStep = {
  delayMs?: number;
};

export type ScriptedTaskEventSourceStep<TEvent = unknown> =
  | ({ type: "open" } & TimedStep)
  | ({ type: "event"; event: TEvent } & TimedStep)
  | ({ type: "error"; error?: unknown } & TimedStep)
  | ({ type: "close" } & TimedStep)
  | ({ type: "hang" } & TimedStep);

export class ScriptedTaskEventSource<TEvent = unknown>
  implements TaskEventSource<TEvent>
{
  constructor(private readonly steps: ScriptedTaskEventSourceStep<TEvent>[]) {}

  connect(args: TaskEventSourceConnectArgs<TEvent>) {
    let disposed = false;
    const timers = new Set<ReturnType<typeof setTimeout>>();

    const clearTimers = () => {
      for (const timer of timers) {
        clearTimeout(timer);
      }
      timers.clear();
    };

    const scheduleStep = (index: number) => {
      if (disposed || index >= this.steps.length) {
        return;
      }

      const step = this.steps[index];
      const timer = setTimeout(() => {
        timers.delete(timer);

        if (disposed) {
          return;
        }

        switch (step.type) {
          case "open":
            args.onOpen();
            scheduleStep(index + 1);
            break;
          case "event":
            args.onEvent(step.event);
            scheduleStep(index + 1);
            break;
          case "error":
            args.onError(step.error ?? new Error("Scripted task event source error."));
            scheduleStep(index + 1);
            break;
          case "close":
            args.onClose();
            break;
          case "hang":
            break;
        }
      }, step.delayMs ?? 0);

      timers.add(timer);
    };

    scheduleStep(0);

    return () => {
      disposed = true;
      clearTimers();
    };
  }
}
