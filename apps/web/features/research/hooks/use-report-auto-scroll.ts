"use client";

import { useEffect, useRef } from "react";

import { useResearchSessionStore } from "../providers/research-workspace-providers";

const AUTO_SCROLL_RESUME_THRESHOLD_PX = 80;

export function useReportAutoScroll(contentKey: string) {
  const autoScrollEnabled = useResearchSessionStore(
    (state) => state.ui.reportAutoScrollEnabled,
  );
  const setReportAutoScrollEnabled = useResearchSessionStore(
    (state) => state.setReportAutoScrollEnabled,
  );

  const scrollContainerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = scrollContainerRef.current;

    if (!autoScrollEnabled || container === null) {
      return;
    }

    container.scrollTo({
      top: container.scrollHeight,
      behavior: "smooth",
    });
  }, [autoScrollEnabled, contentKey]);

  function handleScroll() {
    const container = scrollContainerRef.current;

    if (container === null) {
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
  };
}
