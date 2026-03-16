"use client";

import { useEffect, useRef } from "react";

import { useResearchRuntime, useResearchSessionStore } from "../providers/research-workspace-providers";

function getTerminationTimestamp(connectDeadlineAt: string | null) {
  return connectDeadlineAt ?? new Date().toISOString();
}

export function useTaskStream() {
  const taskId = useResearchSessionStore((state) => state.session.taskId);
  const taskToken = useResearchSessionStore((state) => state.session.taskToken);
  const eventsUrl = useResearchSessionStore((state) => state.session.eventsUrl);
  const connectDeadlineAt = useResearchSessionStore(
    (state) => state.session.connectDeadlineAt,
  );
  const sseState = useResearchSessionStore((state) => state.session.sseState);
  const terminalReason = useResearchSessionStore((state) => state.ui.terminalReason);
  const applyEvent = useResearchSessionStore((state) => state.applyEvent);
  const setSessionContext = useResearchSessionStore((state) => state.setSessionContext);
  const setTerminalState = useResearchSessionStore((state) => state.setTerminalState);
  const { taskEventSource } = useResearchRuntime();

  const streamTeardownRef = useRef<(() => void) | null>(null);
  const connectDeadlineTimerRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );

  useEffect(() => {
    if (
      taskId === null ||
      taskToken === null ||
      eventsUrl === null ||
      terminalReason !== null ||
      sseState !== "connecting" ||
      streamTeardownRef.current !== null
    ) {
      return;
    }

    let disposed = false;
    let didOpen = false;

    const clearConnectDeadlineTimer = () => {
      if (connectDeadlineTimerRef.current !== null) {
        clearTimeout(connectDeadlineTimerRef.current);
        connectDeadlineTimerRef.current = null;
      }
    };

    const unsubscribe = taskEventSource.connect({
      url: eventsUrl,
      token: taskToken,
      onOpen: () => {
        if (disposed) {
          return;
        }

        didOpen = true;
        clearConnectDeadlineTimer();
        setSessionContext({
          sseState: "open",
        });
      },
      onEvent: (event) => {
        if (disposed) {
          return;
        }

        applyEvent(event);
      },
      onError: () => {
        if (disposed) {
          return;
        }

        clearConnectDeadlineTimer();
        setTerminalState({
          terminalReason: "terminated",
          timestamp: new Date().toISOString(),
          sseState: "failed",
        });
      },
      onClose: () => {
        if (disposed) {
          return;
        }

        clearConnectDeadlineTimer();
        setTerminalState({
          terminalReason: "terminated",
          timestamp: new Date().toISOString(),
          sseState: "closed",
        });
      },
    });

    streamTeardownRef.current = () => {
      unsubscribe();
      streamTeardownRef.current = null;
    };

    if (connectDeadlineAt !== null) {
      const connectTimeoutMs = Math.max(
        0,
        new Date(connectDeadlineAt).getTime() - Date.now(),
      );

      connectDeadlineTimerRef.current = setTimeout(() => {
        if (disposed || didOpen) {
          return;
        }

        streamTeardownRef.current?.();
        clearConnectDeadlineTimer();
        setTerminalState({
          terminalReason: "terminated",
          timestamp: getTerminationTimestamp(connectDeadlineAt),
          sseState: "failed",
        });
      }, connectTimeoutMs);
    }

    return () => {
      disposed = true;
    };
  }, [
    applyEvent,
    connectDeadlineAt,
    eventsUrl,
    setSessionContext,
    setTerminalState,
    sseState,
    taskEventSource,
    taskId,
    taskToken,
    terminalReason,
  ]);

  useEffect(() => {
    if (terminalReason === null) {
      return;
    }

    if (connectDeadlineTimerRef.current !== null) {
      clearTimeout(connectDeadlineTimerRef.current);
      connectDeadlineTimerRef.current = null;
    }

    streamTeardownRef.current?.();
  }, [terminalReason]);

  useEffect(() => {
    return () => {
      if (connectDeadlineTimerRef.current !== null) {
        clearTimeout(connectDeadlineTimerRef.current);
        connectDeadlineTimerRef.current = null;
      }

      streamTeardownRef.current?.();
    };
  }, []);
}
