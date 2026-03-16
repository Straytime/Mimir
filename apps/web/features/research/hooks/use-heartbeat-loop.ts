"use client";

import { useEffect } from "react";

import { TaskApiClientError } from "@/lib/api/task-api-client";
import { TERMINAL_TASK_STATUSES } from "@/lib/contracts";

import { useResearchRuntime, useResearchSessionStore } from "../providers/research-workspace-providers";

const HEARTBEAT_INTERVAL_MS = 20_000;
const HEARTBEAT_ELIGIBLE_STATUSES = new Set([
  "awaiting_feedback",
  "awaiting_user_input",
  "running",
]);
const TERMINAL_STATUS_SET = new Set<string>(TERMINAL_TASK_STATUSES);

export function useHeartbeatLoop() {
  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);
  const heartbeatUrl = useResearchSessionStore((state) => state.session.heartbeatUrl);
  const taskToken = useResearchSessionStore((state) => state.session.taskToken);
  const sseState = useResearchSessionStore((state) => state.session.sseState);
  const setTerminalState = useResearchSessionStore((state) => state.setTerminalState);
  const { taskApiClient } = useResearchRuntime();

  useEffect(() => {
    if (
      snapshot === null ||
      heartbeatUrl === null ||
      taskToken === null ||
      sseState !== "open" ||
      TERMINAL_STATUS_SET.has(snapshot.status) ||
      !HEARTBEAT_ELIGIBLE_STATUSES.has(snapshot.status)
    ) {
      return;
    }

    let stopped = false;

    const intervalId = setInterval(() => {
      void taskApiClient
        .sendHeartbeat({
          url: heartbeatUrl,
          token: taskToken,
          request: {
            client_time: new Date().toISOString(),
          },
        })
        .catch((error) => {
          if (
            stopped ||
            !(error instanceof TaskApiClientError) ||
            (error.status !== 404 && error.status !== 409)
          ) {
            return;
          }

          stopped = true;
          clearInterval(intervalId);
          setTerminalState({
            terminalReason: "terminated",
            timestamp: new Date().toISOString(),
            sseState: "failed",
          });
        });
    }, HEARTBEAT_INTERVAL_MS);

    return () => {
      stopped = true;
      clearInterval(intervalId);
    };
  }, [heartbeatUrl, setTerminalState, snapshot, sseState, taskApiClient, taskToken]);
}
