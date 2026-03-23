"use client";

import { useEffect, useRef } from "react";

import { TERMINAL_TASK_STATUSES } from "@/lib/contracts";

import {
  useResearchRuntime,
  useResearchSessionStore,
  useResearchSessionStoreApi,
} from "../providers/research-workspace-providers";

const IN_PAGE_RECONNECT_BASE_DELAY_MS = 1_000;
const IN_PAGE_RECONNECT_MAX_DELAY_MS = 5_000;
const TERMINAL_STATUS_SET = new Set<string>(TERMINAL_TASK_STATUSES);

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
  const store = useResearchSessionStoreApi();
  const { taskEventSource } = useResearchRuntime();

  const streamTeardownRef = useRef<(() => void) | null>(null);
  const isMountedRef = useRef(true);
  const connectDeadlineTimerRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptRef = useRef(0);
  const initialConnectAttemptPendingRef = useRef(true);

  const clearReconnectTimer = () => {
    if (reconnectTimerRef.current !== null) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  };

  const clearConnectDeadlineTimer = () => {
    if (connectDeadlineTimerRef.current !== null) {
      clearTimeout(connectDeadlineTimerRef.current);
      connectDeadlineTimerRef.current = null;
    }
  };

  const canReconnectInPage = () => {
    const state = store.getState();
    const snapshotStatus = state.remote.snapshot?.status ?? null;

    return (
      isMountedRef.current &&
      state.session.taskId !== null &&
      state.session.taskToken !== null &&
      state.session.eventsUrl !== null &&
      state.ui.terminalReason === null &&
      state.ui.pendingAction !== "disconnecting" &&
      state.session.explicitAbortRequested === false &&
      (snapshotStatus === null || !TERMINAL_STATUS_SET.has(snapshotStatus))
    );
  };

  const scheduleReconnect = (nextSseState: "closed" | "failed") => {
    clearConnectDeadlineTimer();
    streamTeardownRef.current?.();
    setSessionContext({
      sseState: nextSseState,
    });

    if (!canReconnectInPage()) {
      return;
    }

    const reconnectDelayMs = Math.min(
      IN_PAGE_RECONNECT_BASE_DELAY_MS * 2 ** reconnectAttemptRef.current,
      IN_PAGE_RECONNECT_MAX_DELAY_MS,
    );
    reconnectAttemptRef.current += 1;
    clearReconnectTimer();
    reconnectTimerRef.current = setTimeout(() => {
      reconnectTimerRef.current = null;

      if (!canReconnectInPage()) {
        return;
      }

      setSessionContext({
        sseState: "connecting",
      });
    }, reconnectDelayMs);
  };

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

    let didOpen = false;

    const unsubscribe = taskEventSource.connect({
      url: eventsUrl,
      token: taskToken,
      onOpen: () => {
        if (!isMountedRef.current) {
          return;
        }

        didOpen = true;
        initialConnectAttemptPendingRef.current = false;
        clearConnectDeadlineTimer();
        clearReconnectTimer();
        reconnectAttemptRef.current = 0;
        setSessionContext({
          sseState: "open",
        });
      },
      onEvent: (event) => {
        if (!isMountedRef.current) {
          return;
        }

        applyEvent(event);
      },
      onError: () => {
        if (!isMountedRef.current) {
          return;
        }

        initialConnectAttemptPendingRef.current = false;
        scheduleReconnect("failed");
      },
      onClose: () => {
        if (!isMountedRef.current) {
          return;
        }

        initialConnectAttemptPendingRef.current = false;
        scheduleReconnect("closed");
      },
    });

    streamTeardownRef.current = () => {
      unsubscribe();
      streamTeardownRef.current = null;
    };

    if (connectDeadlineAt !== null && initialConnectAttemptPendingRef.current) {
      const connectTimeoutMs = Math.max(
        0,
        new Date(connectDeadlineAt).getTime() - Date.now(),
      );

      connectDeadlineTimerRef.current = setTimeout(() => {
        if (!isMountedRef.current || didOpen) {
          return;
        }

        initialConnectAttemptPendingRef.current = false;
        scheduleReconnect("failed");
      }, connectTimeoutMs);
    }
  }, [
    applyEvent,
    connectDeadlineAt,
    eventsUrl,
    setSessionContext,
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

    clearConnectDeadlineTimer();
    clearReconnectTimer();
    streamTeardownRef.current?.();
  }, [terminalReason]);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;

      clearConnectDeadlineTimer();
      clearReconnectTimer();
      streamTeardownRef.current?.();
    };
  }, []);
}
