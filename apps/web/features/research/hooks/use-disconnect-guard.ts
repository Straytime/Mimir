"use client";

import { useEffect } from "react";

import { TERMINAL_TASK_STATUSES } from "@/lib/contracts";

import { useResearchRuntime, useResearchSessionStore } from "../providers/research-workspace-providers";

const TERMINAL_STATUS_SET = new Set<string>(TERMINAL_TASK_STATUSES);

function createDisconnectBeaconPayload(taskToken: string) {
  return JSON.stringify({
    reason: "pagehide",
    task_token: taskToken,
  });
}

export function useDisconnectGuard() {
  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);
  const taskToken = useResearchSessionStore((state) => state.session.taskToken);
  const disconnectUrl = useResearchSessionStore((state) => state.session.disconnectUrl);
  const pendingAction = useResearchSessionStore((state) => state.ui.pendingAction);
  const setPendingAction = useResearchSessionStore((state) => state.setPendingAction);
  const { taskApiClient } = useResearchRuntime();

  const shouldGuardSession =
    snapshot !== null &&
    taskToken !== null &&
    disconnectUrl !== null &&
    !TERMINAL_STATUS_SET.has(snapshot.status);

  useEffect(() => {
    if (!shouldGuardSession || taskToken === null || disconnectUrl === null) {
      return;
    }

    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    const handlePageHide = () => {
      navigator.sendBeacon(
        disconnectUrl,
        createDisconnectBeaconPayload(taskToken),
      );
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    window.addEventListener("pagehide", handlePageHide);

    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
      window.removeEventListener("pagehide", handlePageHide);
    };
  }, [disconnectUrl, shouldGuardSession, taskToken]);

  return async function disconnectTask() {
    if (
      !shouldGuardSession ||
      disconnectUrl === null ||
      taskToken === null ||
      pendingAction === "disconnecting"
    ) {
      return;
    }

    setPendingAction("disconnecting");

    try {
      await taskApiClient.disconnectTask({
        url: disconnectUrl,
        token: taskToken,
        reason: "client_manual_abort",
      });
    } finally {
      setPendingAction(null);
    }
  };
}
