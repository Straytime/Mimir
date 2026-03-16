"use client";

import { useCallback, useRef } from "react";

import type { TaskDetailResult } from "@/lib/api/task-api-client";

import {
  useResearchRuntime,
  useResearchSessionStore,
} from "../providers/research-workspace-providers";

export function useDeliveryRefresh() {
  const taskId = useResearchSessionStore((state) => state.session.taskId);
  const taskToken = useResearchSessionStore((state) => state.session.taskToken);
  const mergeTaskDetail = useResearchSessionStore((state) => state.mergeTaskDetail);
  const setRefreshingDelivery = useResearchSessionStore(
    (state) => state.setRefreshingDelivery,
  );
  const { taskApiClient } = useResearchRuntime();

  const inFlightRefreshRef = useRef<Promise<TaskDetailResult | null> | null>(null);

  return useCallback(async () => {
    if (taskId === null || taskToken === null) {
      return null;
    }

    if (inFlightRefreshRef.current !== null) {
      return inFlightRefreshRef.current;
    }

    const refreshPromise = (async () => {
      setRefreshingDelivery(true);

      try {
        const detail = await taskApiClient.getTaskDetail({
          taskId,
          token: taskToken,
        });

        mergeTaskDetail(detail);
        return detail;
      } finally {
        setRefreshingDelivery(false);
      }
    })();

    inFlightRefreshRef.current = refreshPromise;

    try {
      return await refreshPromise;
    } finally {
      inFlightRefreshRef.current = null;
    }
  }, [mergeTaskDetail, setRefreshingDelivery, taskApiClient, taskId, taskToken]);
}
