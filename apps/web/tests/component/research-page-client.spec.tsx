import { act, render, screen, within } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { ResearchPageClient } from "@/features/research/components/research-page-client";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import { RESEARCH_CARD_ANCHOR_GAP_PX } from "@/features/research/utils/layout-vars";
import {
  makeArtifactSummary,
  makeCollectionPlanRoundNode,
  makeCollectionTraceRoot,
  makeDeliverySummary,
  makeResearchSessionState,
  makeResearchOutline,
  makeRevisionSummary,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";

test("renders the idle workspace shell before a task is created", () => {
  render(<ResearchPageClient />);

  expect(screen.getByRole("heading", { name: "Mimir" })).toBeInTheDocument();
  expect(screen.getByText("Draw from depth.")).toBeInTheDocument();
  expect(screen.getByPlaceholderText("输入你的研究主题...")).toBeInTheDocument();
  expect(
    screen.getByText("系统生成结构化问题并预选默认答案，30 秒倒计时后自动提交。"),
  ).toBeInTheDocument();
});

test("renders the clarification copy and keeps the collection trace hidden before collection starts", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        sseState: "open",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "clarifying",
          status: "running",
        }),
      },
      stream: {
        clarificationText: "为了更好地理解需求，请先确认几个问题。",
      },
    }),
  );

  render(<ResearchPageClient store={store} />);

  expect(
    screen.getByText("在开始之前，有一些问题需要你的反馈"),
  ).toBeInTheDocument();
  expect(screen.getByText("澄清详情")).toBeInTheDocument();
  expect(screen.queryByText("Requirement Summary")).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Collection Trace" })).not.toBeInTheDocument();
  expect(screen.queryByLabelText("报告大纲")).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "报告画布" })).not.toBeInTheDocument();
  expect(screen.queryByLabelText("图库")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("交付操作")).not.toBeInTheDocument();
});

test("renders stage-gated workspace cards once their content is ready", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        sseState: "open",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "writing_report",
          status: "running",
        }),
        currentRevision: makeRevisionSummary({
          requirement_detail: {
            research_goal: "分析中国 AI 搜索产品竞争格局",
            domain: "互联网 / AI 产品",
            requirement_details: "聚焦中国市场，偏商业分析，覆盖近两年变化。",
            output_format: "business_report",
            freshness_requirement: "high",
            language: "zh-CN",
          },
        }),
      },
      stream: {
        collectionTrace: makeCollectionTraceRoot({
          nodes: [makeCollectionPlanRoundNode()],
        }),
        outline: makeResearchOutline(),
        outlineReady: true,
        reportMarkdown: "# 标题\n\n正文。",
        artifacts: [
          makeArtifactSummary({
            url: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAE/wJ/lL0uWQAAAABJRU5ErkJggg==",
          }),
        ],
      },
    }),
  );

  render(<ResearchPageClient store={store} />);

  expect(screen.getByText("需求摘要已生成")).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "Collection Trace" })).toBeInTheDocument();
  expect(screen.getByLabelText("报告大纲")).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "报告画布" })).toBeInTheDocument();
  expect(screen.queryByText("配图制品")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("交付操作")).not.toBeInTheDocument();
});

test("computes the shared long-card max height from the viewport content band", () => {
  const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;
  const originalInnerHeight = window.innerHeight;
  const topStackRect = {
    x: 0,
    y: 220,
    top: 220,
    left: 0,
    right: 800,
    bottom: 396,
    width: 800,
    height: 176,
    toJSON() {
      return this;
    },
  } as DOMRect;

  Object.defineProperty(window, "innerHeight", {
    configurable: true,
    writable: true,
    value: 960,
  });
  Object.defineProperty(Element.prototype, "getBoundingClientRect", {
    configurable: true,
    writable: true,
    value(this: Element) {
      if (this.getAttribute("data-research-top-stack") === "true") {
        return topStackRect;
      }

      if (this.getAttribute("data-research-status-bar") === "true") {
        return {
          x: 0,
          y: 220,
          top: 220,
          left: 0,
          right: 800,
          bottom: 324,
          width: 800,
          height: 104,
          toJSON() {
            return this;
          },
        } as DOMRect;
      }

      if (this.getAttribute("data-research-input-bar") === "true") {
        return {
          x: 0,
          y: 832,
          top: 832,
          left: 0,
          right: 800,
          bottom: 960,
          width: 800,
          height: 128,
          toJSON() {
            return this;
          },
        } as DOMRect;
      }

      return originalGetBoundingClientRect.call(this);
    },
  });

  try {
    const store = createResearchSessionStore(
      makeResearchSessionState({
        session: {
          taskId: "tsk_stage0",
          taskToken: "secret_stage0",
          sseState: "open",
        },
        remote: {
          snapshot: makeTaskSnapshot({
            phase: "writing_report",
            status: "running",
          }),
        },
        stream: {
          collectionTrace: makeCollectionTraceRoot({
            nodes: [makeCollectionPlanRoundNode()],
          }),
          outline: makeResearchOutline(),
          outlineReady: true,
          reportMarkdown: "# 标题\n\n正文。",
        },
      }),
    );

    render(<ResearchPageClient store={store} />);

    const expectedMaxHeight =
      window.innerHeight - 176 - 128 - RESEARCH_CARD_ANCHOR_GAP_PX * 2;
    const main = screen.getByRole("main");

    expect(main.style.getPropertyValue("--research-card-max-h")).toBe(
      `${expectedMaxHeight}px`,
    );
    expect(screen.getByRole("region", { name: "Collection Trace" })).toHaveStyle({
      maxHeight: "var(--research-card-max-h)",
    });
    expect(screen.getByRole("region", { name: "报告画布" })).toHaveStyle({
      maxHeight: "var(--research-card-max-h)",
    });
  } finally {
    Object.defineProperty(window, "innerHeight", {
      configurable: true,
      writable: true,
      value: originalInnerHeight,
    });
    Object.defineProperty(Element.prototype, "getBoundingClientRect", {
      configurable: true,
      writable: true,
      value: originalGetBoundingClientRect,
    });
  }
});

test("renders the embedded gallery inside DeliveryActions and not as a standalone card after delivery", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        sseState: "open",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "delivered",
          status: "awaiting_feedback",
          available_actions: ["download_markdown", "download_pdf"],
        }),
        delivery: makeDeliverySummary({
          artifact_count: 1,
          artifacts: [
            makeArtifactSummary({
              filename: "chart_market_share.png",
              url: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAE/wJ/lL0uWQAAAABJRU5ErkJggg==",
            }),
          ],
        }),
      },
      stream: {
        outline: makeResearchOutline(),
        outlineReady: true,
        reportMarkdown: "# 标题\n\n正文。",
        artifacts: [
          makeArtifactSummary({
            filename: "chart_market_share.png",
            url: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAE/wJ/lL0uWQAAAABJRU5ErkJggg==",
          }),
        ],
      },
    }),
  );

  render(<ResearchPageClient store={store} />);

  const deliveryPanel = screen.getByRole("region", { name: "交付操作" });

  expect(screen.queryByRole("region", { name: "图库" })).not.toBeInTheDocument();
  expect(within(deliveryPanel).getByText("配图制品")).toBeInTheDocument();
  expect(within(deliveryPanel).getByText("chart_market_share.png")).toBeInTheDocument();
});

test("scrolls the current focus card to the shared workspace anchor offset", () => {
  const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;
  const originalScrollTo = window.scrollTo;
  const scrollToSpy = vi.fn();
  const statusBarRect = {
    x: 0,
    y: 0,
    top: 0,
    left: 0,
    right: 800,
    bottom: 104,
    width: 800,
    height: 104,
    toJSON() {
      return this;
    },
  } as DOMRect;
  const reportCardRect = {
    x: 0,
    y: 420,
    top: 420,
    left: 0,
    right: 800,
    bottom: 820,
    width: 800,
    height: 400,
    toJSON() {
      return this;
    },
  } as DOMRect;

  Object.defineProperty(window, "scrollTo", {
    configurable: true,
    writable: true,
    value: scrollToSpy,
  });
  Object.defineProperty(Element.prototype, "getBoundingClientRect", {
    configurable: true,
    writable: true,
    value(this: Element) {
      if (this.getAttribute("data-research-status-bar") === "true") {
        return statusBarRect;
      }

      if (this.getAttribute("data-research-card-anchor") === "report") {
        return reportCardRect;
      }

      return originalGetBoundingClientRect.call(this);
    },
  });

  try {
    const store = createResearchSessionStore(
      makeResearchSessionState({
        session: {
          taskId: "tsk_stage0",
          taskToken: "secret_stage0",
          sseState: "open",
        },
        remote: {
          snapshot: makeTaskSnapshot({
            phase: "writing_report",
            status: "running",
          }),
          currentRevision: makeRevisionSummary({
            requirement_detail: {
              research_goal: "分析中国 AI 搜索产品竞争格局",
              domain: "互联网 / AI 产品",
              requirement_details: "聚焦中国市场，偏商业分析，覆盖近两年变化。",
              output_format: "business_report",
              freshness_requirement: "high",
              language: "zh-CN",
            },
          }),
        },
        stream: {
          outline: makeResearchOutline(),
          outlineReady: true,
          reportMarkdown: "# 标题\n\n正文。",
        },
      }),
    );

    render(<ResearchPageClient store={store} />);

    expect(scrollToSpy).toHaveBeenCalledWith({
      behavior: "smooth",
      top: 292,
    });
  } finally {
    Object.defineProperty(window, "scrollTo", {
      configurable: true,
      writable: true,
      value: originalScrollTo,
    });
    Object.defineProperty(Element.prototype, "getBoundingClientRect", {
      configurable: true,
      writable: true,
      value: originalGetBoundingClientRect,
    });
  }
});

test("reanchors the clarification title when natural clarification content becomes ready", () => {
  const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;
  const originalScrollTo = window.scrollTo;
  const scrollToSpy = vi.fn();
  const topStackRect = {
    x: 0,
    y: 0,
    top: 0,
    left: 0,
    right: 800,
    bottom: 176,
    width: 800,
    height: 176,
    toJSON() {
      return this;
    },
  } as DOMRect;
  const statusBarRect = {
    x: 0,
    y: 0,
    top: 0,
    left: 0,
    right: 800,
    bottom: 104,
    width: 800,
    height: 104,
    toJSON() {
      return this;
    },
  } as DOMRect;
  const clarificationCardRect = {
    x: 0,
    y: 360,
    top: 360,
    left: 0,
    right: 800,
    bottom: 720,
    width: 800,
    height: 360,
    toJSON() {
      return this;
    },
  } as DOMRect;
  const clarificationTitleRect = {
    x: 0,
    y: 412,
    top: 412,
    left: 0,
    right: 800,
    bottom: 448,
    width: 800,
    height: 36,
    toJSON() {
      return this;
    },
  } as DOMRect;

  Object.defineProperty(window, "scrollTo", {
    configurable: true,
    writable: true,
    value: scrollToSpy,
  });
  Object.defineProperty(Element.prototype, "getBoundingClientRect", {
    configurable: true,
    writable: true,
    value(this: Element) {
      if (this.getAttribute("data-research-top-stack") === "true") {
        return topStackRect;
      }

      if (this.getAttribute("data-research-status-bar") === "true") {
        return statusBarRect;
      }

      if (this.getAttribute("data-research-card-anchor") === "clarification") {
        return clarificationCardRect;
      }

      if (this.getAttribute("data-research-anchor-target") === "clarification-title") {
        return clarificationTitleRect;
      }

      return originalGetBoundingClientRect.call(this);
    },
  });

  try {
    const store = createResearchSessionStore(
      makeResearchSessionState({
        session: {
          taskId: "tsk_stage0",
          taskToken: "secret_stage0",
          sseState: "open",
        },
        remote: {
          snapshot: makeTaskSnapshot({
            phase: "clarifying",
            status: "running",
            clarification_mode: "natural",
          }),
        },
        stream: {
          clarificationText: "",
        },
      }),
    );

    render(<ResearchPageClient store={store} />);

    scrollToSpy.mockClear();

    act(() => {
      store.setState((state) => ({
        ...state,
        stream: {
          ...state.stream,
          clarificationText: "请补充希望聚焦的市场范围。",
        },
      }));
    });

    expect(scrollToSpy).toHaveBeenCalledWith({
      behavior: "smooth",
      top: 212,
    });
  } finally {
    Object.defineProperty(window, "scrollTo", {
      configurable: true,
      writable: true,
      value: originalScrollTo,
    });
    Object.defineProperty(Element.prototype, "getBoundingClientRect", {
      configurable: true,
      writable: true,
      value: originalGetBoundingClientRect,
    });
  }
});

test("reanchors the clarification title when options clarification questions become ready", () => {
  const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;
  const originalScrollTo = window.scrollTo;
  const scrollToSpy = vi.fn();
  const topStackRect = {
    x: 0,
    y: 0,
    top: 0,
    left: 0,
    right: 800,
    bottom: 176,
    width: 800,
    height: 176,
    toJSON() {
      return this;
    },
  } as DOMRect;
  const statusBarRect = {
    x: 0,
    y: 0,
    top: 0,
    left: 0,
    right: 800,
    bottom: 104,
    width: 800,
    height: 104,
    toJSON() {
      return this;
    },
  } as DOMRect;
  const clarificationCardRect = {
    x: 0,
    y: 360,
    top: 360,
    left: 0,
    right: 800,
    bottom: 720,
    width: 800,
    height: 360,
    toJSON() {
      return this;
    },
  } as DOMRect;
  const clarificationTitleRect = {
    x: 0,
    y: 412,
    top: 412,
    left: 0,
    right: 800,
    bottom: 448,
    width: 800,
    height: 36,
    toJSON() {
      return this;
    },
  } as DOMRect;

  Object.defineProperty(window, "scrollTo", {
    configurable: true,
    writable: true,
    value: scrollToSpy,
  });
  Object.defineProperty(Element.prototype, "getBoundingClientRect", {
    configurable: true,
    writable: true,
    value(this: Element) {
      if (this.getAttribute("data-research-top-stack") === "true") {
        return topStackRect;
      }

      if (this.getAttribute("data-research-status-bar") === "true") {
        return statusBarRect;
      }

      if (this.getAttribute("data-research-card-anchor") === "clarification") {
        return clarificationCardRect;
      }

      if (this.getAttribute("data-research-anchor-target") === "clarification-title") {
        return clarificationTitleRect;
      }

      return originalGetBoundingClientRect.call(this);
    },
  });

  try {
    const store = createResearchSessionStore(
      makeResearchSessionState({
        session: {
          taskId: "tsk_stage0",
          taskToken: "secret_stage0",
          sseState: "open",
        },
        remote: {
          snapshot: makeTaskSnapshot({
            phase: "clarifying",
            status: "awaiting_user_input",
            clarification_mode: "options",
            available_actions: ["submit_clarification"],
          }),
        },
        stream: {
          clarificationText: "请回答以下问题。",
          questionSet: null,
        },
      }),
    );

    render(<ResearchPageClient store={store} />);

    scrollToSpy.mockClear();

    act(() => {
      store.setState((state) => ({
        ...state,
        stream: {
          ...state.stream,
          questionSet: {
            questions: [
              {
                question_id: "q1",
                question: "研究范围？",
                options: [
                  { option_id: "o_auto", label: "自动决定" },
                  { option_id: "o_1", label: "国内市场" },
                ],
              },
            ],
          },
        },
      }));
    });

    expect(scrollToSpy).toHaveBeenCalledWith({
      behavior: "smooth",
      top: 212,
    });
  } finally {
    Object.defineProperty(window, "scrollTo", {
      configurable: true,
      writable: true,
      value: originalScrollTo,
    });
    Object.defineProperty(Element.prototype, "getBoundingClientRect", {
      configurable: true,
      writable: true,
      value: originalGetBoundingClientRect,
    });
  }
});

test("reanchors the requirement summary content when requirement detail becomes ready", () => {
  const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;
  const originalScrollTo = window.scrollTo;
  const scrollToSpy = vi.fn();
  const topStackRect = {
    x: 0,
    y: 0,
    top: 0,
    left: 0,
    right: 800,
    bottom: 176,
    width: 800,
    height: 176,
    toJSON() {
      return this;
    },
  } as DOMRect;
  const statusBarRect = {
    x: 0,
    y: 0,
    top: 0,
    left: 0,
    right: 800,
    bottom: 104,
    width: 800,
    height: 104,
    toJSON() {
      return this;
    },
  } as DOMRect;
  const requirementCardRect = {
    x: 0,
    y: 520,
    top: 520,
    left: 0,
    right: 800,
    bottom: 900,
    width: 800,
    height: 380,
    toJSON() {
      return this;
    },
  } as DOMRect;
  const requirementContentRect = {
    x: 0,
    y: 584,
    top: 584,
    left: 0,
    right: 800,
    bottom: 904,
    width: 800,
    height: 320,
    toJSON() {
      return this;
    },
  } as DOMRect;

  Object.defineProperty(window, "scrollTo", {
    configurable: true,
    writable: true,
    value: scrollToSpy,
  });
  Object.defineProperty(Element.prototype, "getBoundingClientRect", {
    configurable: true,
    writable: true,
    value(this: Element) {
      if (this.getAttribute("data-research-top-stack") === "true") {
        return topStackRect;
      }

      if (this.getAttribute("data-research-status-bar") === "true") {
        return statusBarRect;
      }

      if (this.getAttribute("data-research-card-anchor") === "requirementSummary") {
        return requirementCardRect;
      }

      if (
        this.getAttribute("data-research-anchor-target") ===
        "requirement-summary-content"
      ) {
        return requirementContentRect;
      }

      return originalGetBoundingClientRect.call(this);
    },
  });

  try {
    const store = createResearchSessionStore(
      makeResearchSessionState({
        session: {
          taskId: "tsk_stage0",
          taskToken: "secret_stage0",
          sseState: "open",
        },
        remote: {
          snapshot: makeTaskSnapshot({
            phase: "analyzing_requirement",
            status: "running",
          }),
          currentRevision: makeRevisionSummary({
            requirement_detail: null,
          }),
        },
      }),
    );

    render(<ResearchPageClient store={store} />);

    scrollToSpy.mockClear();

    act(() => {
      store.setState((state) => ({
        ...state,
        remote: {
          ...state.remote,
          currentRevision: makeRevisionSummary({
            requirement_detail: {
              research_goal: "分析中国 AI 搜索产品竞争格局",
              domain: "互联网 / AI 产品",
              requirement_details: "聚焦中国市场，偏商业分析，覆盖近两年变化。",
              output_format: "business_report",
              freshness_requirement: "high",
              language: "zh-CN",
            },
          }),
        },
      }));
    });

    expect(scrollToSpy).toHaveBeenCalledWith({
      behavior: "smooth",
      top: 384,
    });
  } finally {
    Object.defineProperty(window, "scrollTo", {
      configurable: true,
      writable: true,
      value: originalScrollTo,
    });
    Object.defineProperty(Element.prototype, "getBoundingClientRect", {
      configurable: true,
      writable: true,
      value: originalGetBoundingClientRect,
    });
  }
});

test("reanchors the current card when the same anchor key stays active but report content becomes ready", () => {
  const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;
  const originalScrollTo = window.scrollTo;
  const scrollToSpy = vi.fn();
  const statusBarRect = {
    x: 0,
    y: 0,
    top: 0,
    left: 0,
    right: 800,
    bottom: 104,
    width: 800,
    height: 104,
    toJSON() {
      return this;
    },
  } as DOMRect;
  const reportCardRect = {
    x: 0,
    y: 420,
    top: 420,
    left: 0,
    right: 800,
    bottom: 820,
    width: 800,
    height: 400,
    toJSON() {
      return this;
    },
  } as DOMRect;

  Object.defineProperty(window, "scrollTo", {
    configurable: true,
    writable: true,
    value: scrollToSpy,
  });
  Object.defineProperty(Element.prototype, "getBoundingClientRect", {
    configurable: true,
    writable: true,
    value(this: Element) {
      if (this.getAttribute("data-research-status-bar") === "true") {
        return statusBarRect;
      }

      if (this.getAttribute("data-research-card-anchor") === "report") {
        return reportCardRect;
      }

      return originalGetBoundingClientRect.call(this);
    },
  });

  try {
    const store = createResearchSessionStore(
      makeResearchSessionState({
        session: {
          taskId: "tsk_stage0",
          taskToken: "secret_stage0",
          sseState: "open",
        },
        remote: {
          snapshot: makeTaskSnapshot({
            phase: "writing_report",
            status: "running",
          }),
        },
        stream: {
          reportMarkdown: "",
        },
      }),
    );

    render(<ResearchPageClient store={store} />);

    scrollToSpy.mockClear();

    act(() => {
      store.setState((state) => ({
        ...state,
        stream: {
          ...state.stream,
          reportMarkdown: "# 标题\n\n正文。",
        },
      }));
    });

    expect(scrollToSpy).toHaveBeenCalledWith({
      behavior: "smooth",
      top: 292,
    });
  } finally {
    Object.defineProperty(window, "scrollTo", {
      configurable: true,
      writable: true,
      value: originalScrollTo,
    });
    Object.defineProperty(Element.prototype, "getBoundingClientRect", {
      configurable: true,
      writable: true,
      value: originalGetBoundingClientRect,
    });
  }
});

test("keeps the report anchor when report canvas and delivery appear together", () => {
  const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;
  const originalScrollTo = window.scrollTo;
  const scrollToSpy = vi.fn();
  const statusBarRect = {
    x: 0,
    y: 0,
    top: 0,
    left: 0,
    right: 800,
    bottom: 104,
    width: 800,
    height: 104,
    toJSON() {
      return this;
    },
  } as DOMRect;
  const reportCardRect = {
    x: 0,
    y: 420,
    top: 420,
    left: 0,
    right: 800,
    bottom: 820,
    width: 800,
    height: 400,
    toJSON() {
      return this;
    },
  } as DOMRect;
  const deliveryCardRect = {
    x: 0,
    y: 860,
    top: 860,
    left: 0,
    right: 800,
    bottom: 1160,
    width: 800,
    height: 300,
    toJSON() {
      return this;
    },
  } as DOMRect;

  Object.defineProperty(window, "scrollTo", {
    configurable: true,
    writable: true,
    value: scrollToSpy,
  });
  Object.defineProperty(Element.prototype, "getBoundingClientRect", {
    configurable: true,
    writable: true,
    value(this: Element) {
      if (this.getAttribute("data-research-status-bar") === "true") {
        return statusBarRect;
      }

      if (this.getAttribute("data-research-card-anchor") === "report") {
        return reportCardRect;
      }

      if (this.getAttribute("data-research-card-anchor") === "delivery") {
        return deliveryCardRect;
      }

      return originalGetBoundingClientRect.call(this);
    },
  });

  try {
    const store = createResearchSessionStore(
      makeResearchSessionState({
        session: {
          taskId: "tsk_stage0",
          taskToken: "secret_stage0",
          sseState: "open",
        },
        remote: {
          snapshot: makeTaskSnapshot({
            phase: "delivered",
            status: "awaiting_feedback",
            available_actions: ["download_markdown", "download_pdf"],
          }),
          delivery: makeDeliverySummary({
            artifact_count: 1,
            artifacts: [
              makeArtifactSummary({
                filename: "chart_market_share.png",
                url: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAE/wJ/lL0uWQAAAABJRU5ErkJggg==",
              }),
            ],
          }),
        },
        stream: {
          outline: makeResearchOutline(),
          outlineReady: true,
          reportMarkdown: "# 标题\n\n正文。",
          artifacts: [
            makeArtifactSummary({
              filename: "chart_market_share.png",
              url: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAE/wJ/lL0uWQAAAABJRU5ErkJggg==",
            }),
          ],
        },
      }),
    );

    render(<ResearchPageClient store={store} />);

    expect(scrollToSpy).toHaveBeenCalledWith({
      behavior: "smooth",
      top: 292,
    });
  } finally {
    Object.defineProperty(window, "scrollTo", {
      configurable: true,
      writable: true,
      value: originalScrollTo,
    });
    Object.defineProperty(Element.prototype, "getBoundingClientRect", {
      configurable: true,
      writable: true,
      value: originalGetBoundingClientRect,
    });
  }
});

test("recomputes the shared card-height token when the workspace becomes active", () => {
  const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;

  const statusBarRect = {
    x: 0,
    y: 0,
    top: 0,
    left: 0,
    right: 800,
    bottom: 112,
    width: 800,
    height: 112,
    toJSON() {
      return this;
    },
  } as DOMRect;
  const inputBarRect = {
    x: 0,
    y: 712,
    top: 712,
    left: 0,
    right: 800,
    bottom: 792,
    width: 800,
    height: 80,
    toJSON() {
      return this;
    },
  } as DOMRect;

  Object.defineProperty(Element.prototype, "getBoundingClientRect", {
    configurable: true,
    writable: true,
    value(this: Element) {
      if (this.getAttribute("data-research-status-bar") === "true") {
        return statusBarRect;
      }

      if (this.getAttribute("data-research-input-bar") === "true") {
        return inputBarRect;
      }

      return originalGetBoundingClientRect.call(this);
    },
  });

  try {
    const store = createResearchSessionStore(
      makeResearchSessionState({
        session: {
          taskId: null,
          taskToken: null,
          sseState: "idle",
        },
        remote: {
          snapshot: null,
        },
      }),
    );

    render(<ResearchPageClient store={store} />);

    expect(screen.getByRole("main").style.getPropertyValue("--research-card-max-h")).toBe("");

    act(() => {
      store.setState((state) => ({
        ...state,
        session: {
          ...state.session,
          taskId: "tsk_stage0",
          taskToken: "secret_stage0",
          sseState: "open",
        },
        remote: {
          ...state.remote,
          snapshot: makeTaskSnapshot({
            phase: "collecting",
            status: "running",
          }),
        },
      }));
    });

    const expectedMaxHeight =
      window.innerHeight - 112 - 80 - RESEARCH_CARD_ANCHOR_GAP_PX * 2;

    expect(screen.getByRole("main")).toHaveStyle({
      "--research-card-max-h": `${expectedMaxHeight}px`,
    });
  } finally {
    Object.defineProperty(Element.prototype, "getBoundingClientRect", {
      configurable: true,
      writable: true,
      value: originalGetBoundingClientRect,
    });
  }
});

test("does not render the feedback composer even during task.awaiting_feedback", () => {
  const runningStore = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        eventsUrl: "/api/v1/tasks/tsk_stage0/events",
        heartbeatUrl: "/api/v1/tasks/tsk_stage0/heartbeat",
        disconnectUrl: "/api/v1/tasks/tsk_stage0/disconnect",
        sseState: "idle",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "delivered",
          status: "running",
          available_actions: [],
        }),
        delivery: makeDeliverySummary({
          artifact_count: 0,
          artifacts: [],
        }),
      },
    }),
  );

  const awaitingFeedbackStore = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        eventsUrl: "/api/v1/tasks/tsk_stage0/events",
        heartbeatUrl: "/api/v1/tasks/tsk_stage0/heartbeat",
        disconnectUrl: "/api/v1/tasks/tsk_stage0/disconnect",
        sseState: "idle",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "delivered",
          status: "awaiting_feedback",
          available_actions: [
            "submit_feedback",
            "download_markdown",
            "download_pdf",
          ],
        }),
        delivery: makeDeliverySummary({
          artifact_count: 0,
          artifacts: [],
        }),
      },
    }),
  );

  const { unmount } = render(<ResearchPageClient store={runningStore} />);

  expect(
    screen.queryByRole("textbox", { name: "反馈意见" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "提交反馈" }),
  ).not.toBeInTheDocument();

  unmount();
  render(<ResearchPageClient store={awaitingFeedbackStore} />);

  expect(
    screen.queryByRole("textbox", { name: "反馈意见" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "提交反馈" }),
  ).not.toBeInTheDocument();
});

test("does not render revision transition overlay when revision state exists", () => {
  const store = createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        eventsUrl: "/api/v1/tasks/tsk_stage0/events",
        heartbeatUrl: "/api/v1/tasks/tsk_stage0/heartbeat",
        disconnectUrl: "/api/v1/tasks/tsk_stage0/disconnect",
        sseState: "idle",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "delivered",
          status: "awaiting_feedback",
          available_actions: [
            "submit_feedback",
            "download_markdown",
            "download_pdf",
          ],
        }),
        delivery: makeDeliverySummary({
          artifact_count: 0,
          artifacts: [],
        }),
      },
      ui: {
        revisionTransition: {
          status: "waiting_next_revision",
          pendingRevisionId: "rev_stage1",
          pendingRevisionNumber: 2,
        },
      },
    }),
  );

  render(<ResearchPageClient store={store} />);

  expect(
    screen.queryByText("正在处理反馈并准备新一轮研究..."),
  ).not.toBeInTheDocument();
  expect(screen.queryByText(/等待第 2 轮/)).not.toBeInTheDocument();
});
