"use client";

import { useEffect, useRef } from "react";

import { useResearchSessionStore } from "../providers/research-workspace-providers";

const AUTO_SCROLL_RESUME_THRESHOLD_PX = 80;

export function useReportAutoScroll(args: {
  contentKey: string;
  phase: string;
}) {
  const { contentKey, phase } = args;
  const autoScrollEnabled = useResearchSessionStore(
    (state) => state.ui.reportAutoScrollEnabled,
  );
  const setReportAutoScrollEnabled = useResearchSessionStore(
    (state) => state.setReportAutoScrollEnabled,
  );

  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const deliveredInitialPositionedRef = useRef(false);
  const isStreamingPhase = phase === "writing_report";
  const isDeliveredPhase = phase === "delivered";

  useEffect(() => {
    const container = scrollContainerRef.current;

    if (!isDeliveredPhase) {
      deliveredInitialPositionedRef.current = false;
      return;
    }

    if (container === null || deliveredInitialPositionedRef.current) {
      return;
    }

    container.scrollTo({
      top: 0,
      behavior: "auto",
    });
    deliveredInitialPositionedRef.current = true;
  }, [contentKey, isDeliveredPhase]);

  useEffect(() => {
    const container = scrollContainerRef.current;

    if (!isStreamingPhase || !autoScrollEnabled || container === null) {
      return;
    }

    container.scrollTo({
      top: container.scrollHeight,
      behavior: "smooth",
    });
  }, [autoScrollEnabled, contentKey, isStreamingPhase]);

  function handleScroll() {
    const container = scrollContainerRef.current;

    if (!isStreamingPhase || container === null) {
      return;
    }

    const distanceFromBottom =
      container.scrollHeight - container.clientHeight - container.scrollTop;
    const nextAutoScrollEnabled =
      distanceFromBottom <= AUTO_SCROLL_RESUME_THRESHOLD_PX;

    if (nextAutoScrollEnabled !== autoScrollEnabled) {
      setReportAutoScrollEnabled(nextAutoScrollEnabled);
    }
  }

  function scrollToBottom() {
    const container = scrollContainerRef.current;

    setReportAutoScrollEnabled(true);
    container?.scrollTo({
      top: container.scrollHeight,
      behavior: "smooth",
    });
  }

  return {
    autoScrollEnabled,
    handleScroll,
    scrollContainerRef,
    scrollToBottom,
    showScrollToBottom: isStreamingPhase && !autoScrollEnabled,
  };
}
