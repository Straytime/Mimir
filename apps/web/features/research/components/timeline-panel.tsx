"use client";

import { useEffect, useRef } from "react";

import type { TimelineItem } from "../store/research-session-store.types";

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
    return "bg-emerald-100 text-emerald-900";
  }

  if (status === "failed") {
    return "bg-rose-100 text-rose-900";
  }

  return "bg-sky-100 text-sky-900";
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
    <article className="rounded-[2rem] border border-slate-200/70 bg-white/82 p-6 shadow-sm backdrop-blur">
      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
        Live Timeline
      </p>

      <div
        aria-live="polite"
        className="mt-4 max-h-[34rem] overflow-y-auto pr-1"
      >
        {items.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-slate-300 bg-slate-50/80 px-5 py-5 text-sm leading-7 text-slate-600">
            等待研究透明度事件进入时间线。
          </div>
        ) : (
          <ol className="space-y-4">
            {items.map((item) => (
              <li
                className="rounded-3xl border border-slate-200 bg-white/90 px-4 py-4"
                key={item.id}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-slate-950">
                      {item.label}
                    </p>
                    {item.collectTarget && item.kind !== "collect" ? (
                      <p className="text-xs uppercase tracking-[0.12em] text-slate-500">
                        Collect Target
                      </p>
                    ) : null}
                    {item.collectTarget && item.kind !== "collect" ? (
                      <p className="text-sm leading-6 text-slate-700">
                        {item.collectTarget}
                      </p>
                    ) : null}
                  </div>
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-semibold ${getStatusClassName(item.status)}`}
                  >
                    {getStatusLabel(item.status)}
                  </span>
                </div>

                {item.detail ? (
                  <p className="mt-3 whitespace-pre-line text-sm leading-6 text-slate-700">
                    {item.detail}
                  </p>
                ) : null}
              </li>
            ))}
          </ol>
        )}

        <div ref={bottomAnchorRef} />
      </div>
    </article>
  );
}
