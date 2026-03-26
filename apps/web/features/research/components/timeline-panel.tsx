"use client";

import { useEffect, useRef } from "react";

import type { TimelineItem } from "../store/research-session-store.types";
import { PulseIndicator } from "./pulse-indicator";

type TimelinePanelProps = {
  items: TimelineItem[];
};

function getStatusLabel(status: TimelineItem["status"]) {
  if (status === "completed") {
    return "已完成";
  }

  if (status === "failed") {
    return "已失败";
  }

  return "进行中";
}

function getStatusClassName(status: TimelineItem["status"]) {
  if (status === "completed") {
    return "bg-surface-container-high text-surface-tint";
  }

  if (status === "failed") {
    return "bg-surface-container-high text-[#FF6B6B]";
  }

  return "bg-surface-container-high text-surface-tint";
}

export function TimelinePanel({ items }: TimelinePanelProps) {
  const bottomAnchorRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (typeof bottomAnchorRef.current?.scrollIntoView !== "function") {
      return;
    }

    bottomAnchorRef.current.scrollIntoView({
      block: "end",
      behavior: "smooth",
    });
  }, [items]);

  return (
    <section
      aria-label="时间线"
      className="bg-surface-container-low p-6"
      role="region"
    >
      <p className="text-[11px] font-ui font-semibold uppercase tracking-[0.15em] text-tertiary">
        Live Timeline
      </p>

      <div
        aria-live="polite"
        className="mt-4 max-h-[34rem] overflow-y-auto pr-1"
      >
        {items.length === 0 ? (
          <div className="bg-surface-container-lowest px-5 py-5 text-sm leading-7 text-tertiary">
            等待研究透明度事件进入时间线。
          </div>
        ) : (
          <ol className="space-y-sp-6">
            {items.map((item) => (
              <li key={item.id}>
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <p className="text-sm font-ui font-semibold text-primary">
                      {item.label}
                    </p>
                    {item.collectTarget && item.kind !== "collect" ? (
                      <p className="text-[11px] font-ui uppercase tracking-[0.15em] text-tertiary">
                        Collect Target
                      </p>
                    ) : null}
                    {item.collectTarget && item.kind !== "collect" ? (
                      <p className="text-sm leading-6 text-secondary">
                        {item.collectTarget}
                      </p>
                    ) : null}
                  </div>
                  <span
                    className={`flex items-center gap-2 px-3 py-1 text-[11px] font-ui font-medium uppercase tracking-[0.15em] ${getStatusClassName(item.status)}`}
                  >
                    {item.status === "running" ? <PulseIndicator /> : null}
                    {getStatusLabel(item.status)}
                  </span>
                </div>

                {item.detail ? (
                  <p className="mt-3 whitespace-pre-line text-sm font-ui leading-6 text-secondary">
                    {item.detail}
                  </p>
                ) : null}
              </li>
            ))}
          </ol>
        )}

        <div ref={bottomAnchorRef} />
      </div>
    </section>
  );
}
