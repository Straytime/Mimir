import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { TimelinePanel } from "@/features/research/components/timeline-panel";
import { makeTimelineItem } from "@/tests/fixtures/builders";

let scrollIntoViewSpy: ReturnType<typeof vi.fn>;
let scrollToSpy: ReturnType<typeof vi.fn>;
let originalScrollIntoView: typeof Element.prototype.scrollIntoView;
let originalScrollTo: typeof Element.prototype.scrollTo;

beforeEach(() => {
  scrollIntoViewSpy = vi.fn();
  scrollToSpy = vi.fn();
  originalScrollIntoView = Element.prototype.scrollIntoView;
  originalScrollTo = Element.prototype.scrollTo;
  Object.defineProperty(Element.prototype, "scrollIntoView", {
    configurable: true,
    writable: true,
    value: scrollIntoViewSpy,
  });
  Object.defineProperty(Element.prototype, "scrollTo", {
    configurable: true,
    writable: true,
    value: scrollToSpy,
  });
});

afterEach(() => {
  Object.defineProperty(Element.prototype, "scrollIntoView", {
    configurable: true,
    writable: true,
    value: originalScrollIntoView,
  });
  Object.defineProperty(Element.prototype, "scrollTo", {
    configurable: true,
    writable: true,
    value: originalScrollTo,
  });
});

test("renders collection trace items with collect_target labels", () => {
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
  expect(
    screen.getByRole("region", { name: "Collection Trace" }),
  ).toHaveStyle({ maxHeight: "var(--research-card-max-h)" });

  const body = screen.getByRole("region", { name: "Collection Trace" }).querySelector(
    "[aria-live='polite']",
  );

  expect(body).toHaveClass("flex-1", "min-h-0", "overflow-y-auto");
});

test("auto-scrolls to the latest collection trace item by default", () => {
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

  expect(scrollToSpy).toHaveBeenCalled();
  expect(scrollIntoViewSpy).not.toHaveBeenCalled();
});

test("shows collection-specific empty copy", () => {
  render(<TimelinePanel items={[]} />);

  expect(screen.getByText("资料搜集会在这里逐步展开。")).toBeInTheDocument();
  expect(screen.queryByText("研究进展将在这里实时显示。")).not.toBeInTheDocument();
});
