import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { TimelinePanel } from "@/features/research/components/timeline-panel";
import { makeTimelineItem } from "@/tests/fixtures/builders";

let scrollIntoViewSpy: ReturnType<typeof vi.fn>;
let originalScrollIntoView: typeof Element.prototype.scrollIntoView;

beforeEach(() => {
  scrollIntoViewSpy = vi.fn();
  originalScrollIntoView = Element.prototype.scrollIntoView;
  Object.defineProperty(Element.prototype, "scrollIntoView", {
    configurable: true,
    writable: true,
    value: scrollIntoViewSpy,
  });
});

afterEach(() => {
  Object.defineProperty(Element.prototype, "scrollIntoView", {
    configurable: true,
    writable: true,
    value: originalScrollIntoView,
  });
});

test("renders collect_target on timeline items", () => {
  render(
    <TimelinePanel
      items={[
        makeTimelineItem({
          id: "collect:call_ai_search",
          kind: "collect",
          label: "收集 2024-2026 年中国 AI 搜索产品的主要厂商与公开进展",
          collectTarget:
            "收集 2024-2026 年中国 AI 搜索产品的主要厂商与公开进展",
          detail: "搜索： 中国 AI 搜索 产品 2025",
          status: "running",
        }),
      ]}
    />,
  );

  expect(
    screen.getByText("收集 2024-2026 年中国 AI 搜索产品的主要厂商与公开进展"),
  ).toBeInTheDocument();
  expect(screen.getByText("搜索： 中国 AI 搜索 产品 2025")).toBeInTheDocument();
});

test("auto-scrolls to the latest timeline item by default", () => {
  const { rerender } = render(
    <TimelinePanel
      items={[
        makeTimelineItem({
          id: "analysis:rev_stage0",
          label: "正在分析你的研究需求",
        }),
      ]}
    />,
  );

  rerender(
    <TimelinePanel
      items={[
        makeTimelineItem({
          id: "analysis:rev_stage0",
          label: "正在分析你的研究需求",
        }),
        makeTimelineItem({
          id: "summary:call_ai_search:sub_ai_search",
          kind: "summary",
          label: "阶段结论已整理",
          status: "completed",
        }),
      ]}
    />,
  );

  expect(scrollIntoViewSpy).toHaveBeenCalled();
});
