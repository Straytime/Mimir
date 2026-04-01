import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { TimelinePanel } from "@/features/research/components/timeline-panel";
import {
  makeCollectionCollectCompletedEvent,
  makeCollectionCollectGroup,
  makeCollectionPlanRoundNode,
  makeCollectionReasoningBurst,
  makeCollectionSourcesMergedNode,
  makeCollectionSummaryNode,
  makeCollectionToolEvent,
  makeCollectionTraceRoot,
} from "@/tests/fixtures/builders";

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

test("renders hierarchical collection trace with plan rounds, collect groups, sibling summary, and sources merged", () => {
  render(
    <TimelinePanel
      trace={makeCollectionTraceRoot({
        nodes: [
          makeCollectionPlanRoundNode({
            id: "plan_round_1",
            roundIndex: 1,
            collectGroups: [
              makeCollectionCollectGroup({
                id: "collect_group_1",
                toolCallId: "call_1",
                collectTarget: "收集 AI 搜索厂商",
              }),
            ],
          }),
          makeCollectionPlanRoundNode({
            id: "plan_round_2",
            roundIndex: 2,
            collectGroups: [
              makeCollectionCollectGroup({
                id: "collect_group_2",
                toolCallId: "call_2",
                collectTarget: "收集商业化线索",
              }),
            ],
          }),
          makeCollectionSourcesMergedNode(),
        ],
      })}
    />,
  );

  const trace = screen.getByRole("region", { name: "Collection Trace" });
  expect(within(trace).getByRole("heading", { name: "Plan Round 1" })).toBeInTheDocument();
  expect(within(trace).getByRole("heading", { name: "Plan Round 2" })).toBeInTheDocument();
  expect(within(trace).getAllByRole("heading", { name: "Collect" })).toHaveLength(2);
  expect(within(trace).getAllByRole("heading", { name: "Summary" })).toHaveLength(2);
  expect(within(trace).getByRole("heading", { name: "Sources Merged" })).toBeInTheDocument();
  expect(within(trace).getByText("收集 AI 搜索厂商")).toBeInTheDocument();
  expect(within(trace).getByText("收集商业化线索")).toBeInTheDocument();
});

test("keeps collect entries in chronological order", () => {
  render(
    <TimelinePanel
      trace={makeCollectionTraceRoot({
        nodes: [
          makeCollectionPlanRoundNode({
            collectGroups: [
              makeCollectionCollectGroup({
                collectEntries: [
                  makeCollectionReasoningBurst({
                    id: "collect_reasoning_1",
                    detail: "先看官方站点。",
                  }),
                  makeCollectionToolEvent({
                    id: "search_started_1",
                    kind: "search_started",
                    label: "Search Started",
                    detail: "AI 搜索 厂商 2025",
                  }),
                  makeCollectionToolEvent({
                    id: "search_completed_1",
                    kind: "search_completed",
                    label: "Search Completed",
                    detail: "命中 5 条结果",
                  }),
                  makeCollectionToolEvent({
                    id: "fetch_started_1",
                    kind: "fetch_started",
                    label: "Fetch Started",
                    detail: "https://example.com/a",
                  }),
                  makeCollectionToolEvent({
                    id: "fetch_completed_1",
                    kind: "fetch_completed",
                    label: "Fetch Completed",
                    detail: "已读取官方新闻稿",
                  }),
                  makeCollectionCollectCompletedEvent({
                    id: "collect_completed_1",
                    detail: "已整理 3 条候选来源。",
                  }),
                ],
              }),
            ],
          }),
        ],
      })}
    />,
  );

  const collectSection = screen.getByRole("group", { name: "Collect 收集 AI 搜索厂商" });
  const eventText = within(collectSection)
    .getAllByTestId("collection-trace-entry-label")
    .map((entry) => entry.textContent);

  expect(eventText).toEqual([
    "Reasoning 1",
    "Search",
    "Fetch",
    "Collect Completed",
  ]);
});

test("keeps plan and collect status badges on a single stable row for long targets", () => {
  render(
    <TimelinePanel
      trace={makeCollectionTraceRoot({
        nodes: [
          makeCollectionPlanRoundNode({
            status: "running",
            collectGroups: [
              makeCollectionCollectGroup({
                collectTarget:
                  "收集关于全球企业级 AI 搜索产品定价模型、渠道策略、交付周期与安全合规定位的长目标描述",
                collectEntries: [
                  makeCollectionReasoningBurst({
                    id: "collect_reasoning_1",
                    detail: "先看官网与公开资料。",
                  }),
                ],
              }),
            ],
          }),
        ],
      })}
    />,
  );

  const planSection = screen.getByRole("heading", { name: "Plan Round 1" }).closest("section");
  const collectSection = screen
    .getByRole("group", {
      name:
        "Collect 收集关于全球企业级 AI 搜索产品定价模型、渠道策略、交付周期与安全合规定位的长目标描述",
    })
    .closest("section");

  expect(planSection).not.toBeNull();
  expect(collectSection).not.toBeNull();
  expect(planSection?.firstElementChild).toHaveClass("flex-nowrap");
  expect(collectSection?.firstElementChild).toHaveClass("flex-nowrap");

  const planHeader = planSection?.firstElementChild as HTMLElement;
  const collectHeader = collectSection?.firstElementChild as HTMLElement;
  const planBadge = within(planHeader).getByText(/已完成|进行中|已失败/);
  const collectBadge = within(collectHeader).getByText(
    /已完成|进行中|已失败/,
  );

  expect(planBadge).toHaveClass("shrink-0", "whitespace-nowrap");
  expect(collectBadge).toHaveClass("shrink-0", "whitespace-nowrap");
});

test("does not repeat completed badge on collect completed entry rows", () => {
  render(
    <TimelinePanel
      trace={makeCollectionTraceRoot({
        nodes: [
          makeCollectionPlanRoundNode({
            collectGroups: [
              makeCollectionCollectGroup({
                collectEntries: [
                  makeCollectionCollectCompletedEvent({
                    id: "collect_completed_1",
                    detail: "已整理 3 条候选来源。",
                    status: "completed",
                  }),
                ],
              }),
            ],
          }),
        ],
      })}
    />,
  );

  const collectSection = screen.getByRole("group", { name: "Collect 收集 AI 搜索厂商" });
  expect(within(collectSection).getByText("已完成")).toBeInTheDocument();

  const completedRow = within(collectSection)
    .getByText("Collect Completed")
    .closest("div");
  expect(completedRow).not.toBeNull();
  expect(within(completedRow as HTMLElement).queryByText("已完成")).not.toBeInTheDocument();
  expect(within(completedRow as HTMLElement).getByText("已整理 3 条候选来源。")).toBeInTheDocument();
});

test("renders a search started/completed pair as one merged row with query object and done status", () => {
  render(
    <TimelinePanel
      trace={makeCollectionTraceRoot({
        nodes: [
          makeCollectionPlanRoundNode({
            collectGroups: [
              makeCollectionCollectGroup({
                collectEntries: [
                  makeCollectionReasoningBurst({
                    id: "collect_reasoning_1",
                    detail: "先看官方站点。",
                  }),
                  makeCollectionToolEvent({
                    id: "search_started_1",
                    kind: "search_started",
                    label: "Search Started",
                    detail: "AI 搜索 厂商 2025",
                  }),
                  makeCollectionToolEvent({
                    id: "search_completed_1",
                    kind: "search_completed",
                    label: "Search Completed",
                    detail: "命中 5 条结果",
                  }),
                  makeCollectionToolEvent({
                    id: "fetch_started_1",
                    kind: "fetch_started",
                    label: "Fetch Started",
                    detail: "https://example.com/a",
                  }),
                  makeCollectionToolEvent({
                    id: "fetch_completed_1",
                    kind: "fetch_completed",
                    label: "Fetch Completed",
                    detail: "已读取官方新闻稿",
                  }),
                ],
              }),
            ],
          }),
        ],
      })}
    />,
  );

  const collectSection = screen.getByRole("group", { name: "Collect 收集 AI 搜索厂商" });
  const toolRows = within(collectSection).getAllByTestId("collection-trace-tool-row");

  expect(toolRows).toHaveLength(2);
  expect(within(toolRows[0]).getByText("Search")).toBeInTheDocument();
  expect(within(toolRows[0]).getByTestId("collection-trace-tool-row-object")).toHaveTextContent(
    "AI 搜索 厂商 2025",
  );
  expect(within(toolRows[0]).getByText("Done")).toBeInTheDocument();
});

test("renders a fetch started/completed pair as one merged row with url object and done status", () => {
  render(
    <TimelinePanel
      trace={makeCollectionTraceRoot({
        nodes: [
          makeCollectionPlanRoundNode({
            collectGroups: [
              makeCollectionCollectGroup({
                collectEntries: [
                  makeCollectionToolEvent({
                    id: "fetch_started_1",
                    kind: "fetch_started",
                    label: "Fetch Started",
                    detail: "https://example.com/research/company-profile",
                  }),
                  makeCollectionToolEvent({
                    id: "fetch_completed_1",
                    kind: "fetch_completed",
                    label: "Fetch Completed",
                    detail: "已读取官方新闻稿",
                  }),
                ],
              }),
            ],
          }),
        ],
      })}
    />,
  );

  const collectSection = screen.getByRole("group", { name: "Collect 收集 AI 搜索厂商" });
  const toolRows = within(collectSection).getAllByTestId("collection-trace-tool-row");

  expect(toolRows).toHaveLength(1);
  expect(within(toolRows[0]).getByText("Fetch")).toBeInTheDocument();
  expect(within(toolRows[0]).getByTestId("collection-trace-tool-row-object")).toHaveTextContent(
    "example.com/research/company-profile",
  );
  expect(within(toolRows[0]).getByText("Done")).toBeInTheDocument();
});

test("hides completed-only search counts and fetch titles in merged tool rows", () => {
  render(
    <TimelinePanel
      trace={makeCollectionTraceRoot({
        nodes: [
          makeCollectionPlanRoundNode({
            collectGroups: [
              makeCollectionCollectGroup({
                collectEntries: [
                  makeCollectionToolEvent({
                    id: "search_started_1",
                    kind: "search_started",
                    label: "Search Started",
                    detail: "AI 搜索 厂商 2025",
                  }),
                  makeCollectionToolEvent({
                    id: "search_completed_1",
                    kind: "search_completed",
                    label: "Search Completed",
                    detail: "命中 5 条结果",
                  }),
                  makeCollectionToolEvent({
                    id: "fetch_started_1",
                    kind: "fetch_started",
                    label: "Fetch Started",
                    detail: "https://example.com/a",
                  }),
                  makeCollectionToolEvent({
                    id: "fetch_completed_1",
                    kind: "fetch_completed",
                    label: "Fetch Completed",
                    detail: "已读取官方新闻稿",
                  }),
                ],
              }),
            ],
          }),
        ],
      })}
    />,
  );

  const collectSection = screen.getByRole("group", { name: "Collect 收集 AI 搜索厂商" });

  expect(within(collectSection).queryByText("命中 5 条结果")).not.toBeInTheDocument();
  expect(within(collectSection).queryByText("已读取官方新闻稿")).not.toBeInTheDocument();
});

test("keeps a started-only tool event as one row with started status", () => {
  render(
    <TimelinePanel
      trace={makeCollectionTraceRoot({
        nodes: [
          makeCollectionPlanRoundNode({
            collectGroups: [
              makeCollectionCollectGroup({
                collectEntries: [
                  makeCollectionToolEvent({
                    id: "search_started_1",
                    kind: "search_started",
                    label: "Search Started",
                    detail: "AI 搜索 厂商 2025",
                  }),
                ],
              }),
            ],
          }),
        ],
      })}
    />,
  );

  const collectSection = screen.getByRole("group", { name: "Collect 收集 AI 搜索厂商" });
  const toolRows = within(collectSection).getAllByTestId("collection-trace-tool-row");

  expect(toolRows).toHaveLength(1);
  expect(within(toolRows[0]).getByText("Search")).toBeInTheDocument();
  expect(within(toolRows[0]).getByTestId("collection-trace-tool-row-object")).toHaveTextContent(
    "AI 搜索 厂商 2025",
  );
  expect(within(toolRows[0]).getByText("Started")).toBeInTheDocument();
});

test("uses one unified tool row treatment for search and fetch rows", () => {
  render(
    <TimelinePanel
      trace={makeCollectionTraceRoot({
        nodes: [
          makeCollectionPlanRoundNode({
            collectGroups: [
              makeCollectionCollectGroup({
                collectEntries: [
                  makeCollectionToolEvent({
                    id: "search_started_1",
                    kind: "search_started",
                    label: "Search Started",
                    detail: "AI 搜索 厂商 2025",
                  }),
                  makeCollectionToolEvent({
                    id: "search_completed_1",
                    kind: "search_completed",
                    label: "Search Completed",
                    detail: "命中 5 条结果",
                  }),
                  makeCollectionToolEvent({
                    id: "fetch_started_1",
                    kind: "fetch_started",
                    label: "Fetch Started",
                    detail: "https://example.com/a",
                  }),
                  makeCollectionToolEvent({
                    id: "fetch_completed_1",
                    kind: "fetch_completed",
                    label: "Fetch Completed",
                    detail: "已读取官方新闻稿",
                  }),
                ],
              }),
            ],
          }),
        ],
      })}
    />,
  );

  const collectSection = screen.getByRole("group", { name: "Collect 收集 AI 搜索厂商" });
  const [searchRow, fetchRow] = within(collectSection).getAllByTestId("collection-trace-tool-row");

  expect(searchRow).toHaveClass("collection-trace-tool-row--merged");
  expect(fetchRow).toHaveClass("collection-trace-tool-row--merged");
});

test("formats long fetch urls into host and truncated path while keeping the full url accessible", () => {
  const longUrl =
    "https://news.example.com/research/2026/04/01/very-long-report/with/many/segments/and/a/query-string?source=collection-trace&campaign=density-check";

  render(
    <TimelinePanel
      trace={makeCollectionTraceRoot({
        nodes: [
          makeCollectionPlanRoundNode({
            collectGroups: [
              makeCollectionCollectGroup({
                collectEntries: [
                  makeCollectionToolEvent({
                    id: "fetch_started_long_url",
                    kind: "fetch_started",
                    label: "Fetch Started",
                    detail: longUrl,
                  }),
                ],
              }),
            ],
          }),
        ],
      })}
    />,
  );

  const detail = screen.getByTestId("collection-trace-tool-row-object");

  expect(detail).toHaveTextContent("news.example.com/");
  expect(detail).toHaveAttribute("title", longUrl);
  expect(detail.textContent).not.toEqual(longUrl);
});

test("shows one-line previews for reasoning and summary and expands independently", async () => {
  const user = userEvent.setup();

  render(
    <TimelinePanel
      trace={makeCollectionTraceRoot({
        nodes: [
          makeCollectionPlanRoundNode({
            reasoningBursts: [
              makeCollectionReasoningBurst({
                id: "plan_reasoning_1",
                detail: "第一行计划预览\n第二行计划正文",
              }),
            ],
            collectGroups: [
              makeCollectionCollectGroup({
                collectEntries: [
                  makeCollectionReasoningBurst({
                    id: "collect_reasoning_1",
                    detail: "第一行搜集预览\n第二行搜集正文",
                  }),
                ],
                summary: makeCollectionSummaryNode({
                  id: "summary_1",
                  detail: "第一行总结预览\n第二行总结正文",
                }),
              }),
            ],
          }),
        ],
      })}
    />,
  );

  expect(screen.getByText("第一行计划预览")).toBeInTheDocument();
  expect(screen.queryByText("第二行计划正文")).not.toBeInTheDocument();
  expect(screen.getByText("第一行搜集预览")).toBeInTheDocument();
  expect(screen.queryByText("第二行搜集正文")).not.toBeInTheDocument();
  expect(screen.getByText("第一行总结预览")).toBeInTheDocument();
  expect(screen.queryByText("第二行总结正文")).not.toBeInTheDocument();

  await user.click(
    screen.getByRole("button", {
      name: "展开 Plan Round 1 reasoning 1",
    }),
  );

  expect(
    screen.getByText((content) => content.includes("第二行计划正文")),
  ).toBeInTheDocument();
  expect(
    screen.queryByText((content) => content.includes("第二行搜集正文")),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByText((content) => content.includes("第二行总结正文")),
  ).not.toBeInTheDocument();

  await user.click(
    screen.getByRole("button", {
      name: "展开 Collect 收集 AI 搜索厂商 reasoning 1",
    }),
  );
  await user.click(
    screen.getByRole("button", {
      name: "展开 Summary 收集 AI 搜索厂商",
    }),
  );

  expect(
    screen.getByText((content) => content.includes("第二行搜集正文")),
  ).toBeInTheDocument();
  expect(
    screen.getByText((content) => content.includes("第二行总结正文")),
  ).toBeInTheDocument();
});

test("auto-scrolls to the latest collection trace item by default", () => {
  const { rerender } = render(
    <TimelinePanel
      trace={makeCollectionTraceRoot({
        nodes: [
          makeCollectionPlanRoundNode({
            id: "plan_round_1",
          }),
        ],
      })}
    />,
  );

  rerender(
    <TimelinePanel
      trace={makeCollectionTraceRoot({
        nodes: [
          makeCollectionPlanRoundNode({
            id: "plan_round_1",
          }),
          makeCollectionSourcesMergedNode({
            id: "sources_merged_1",
          }),
        ],
      })}
    />,
  );

  expect(scrollToSpy).toHaveBeenCalled();
  expect(scrollIntoViewSpy).not.toHaveBeenCalled();
});

test("shows collection-specific empty copy", () => {
  render(<TimelinePanel trace={{ nodes: [] }} />);

  expect(screen.getByText("资料搜集会在这里逐步展开。")).toBeInTheDocument();
  expect(screen.queryByText("研究进展将在这里实时显示。")).not.toBeInTheDocument();
});

test("renders up to three collect groups inside a single plan round", () => {
  render(
    <TimelinePanel
      trace={makeCollectionTraceRoot({
        nodes: [
          makeCollectionPlanRoundNode({
            id: "plan_round_multi_collect",
            roundIndex: 1,
            collectGroups: [
              makeCollectionCollectGroup({
                id: "collect_group_1",
                toolCallId: "call_vendors",
                collectTarget: "收集主要厂商与产品进展",
              }),
              makeCollectionCollectGroup({
                id: "collect_group_2",
                toolCallId: "call_revenue",
                collectTarget: "收集商业化与收入线索",
              }),
              makeCollectionCollectGroup({
                id: "collect_group_3",
                toolCallId: "call_policy",
                collectTarget: "收集监管与政策变化",
              }),
            ],
          }),
        ],
      })}
    />,
  );

  const trace = screen.getByRole("region", { name: "Collection Trace" });

  expect(within(trace).getByRole("heading", { name: "Plan Round 1" })).toBeInTheDocument();
  expect(within(trace).getAllByRole("heading", { name: "Collect" })).toHaveLength(3);
  expect(within(trace).getByText("收集主要厂商与产品进展")).toBeInTheDocument();
  expect(within(trace).getByText("收集商业化与收入线索")).toBeInTheDocument();
  expect(within(trace).getByText("收集监管与政策变化")).toBeInTheDocument();
});
