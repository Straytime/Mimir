import { act, fireEvent, screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { afterEach, expect, test, vi } from "vitest";

import { ReportCanvas } from "@/features/research/components/report-canvas";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makeArtifactSummary,
  makeDeliverySummary,
  makeResearchOutline,
  makeResearchSessionState,
  makeRevisionSummary,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";
import { mswServer } from "@/tests/fixtures/msw-server";
import { renderWithStore } from "@/tests/fixtures/render";

function createStage6Store() {
  return createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "writing_report",
          status: "running",
          available_actions: [],
        }),
        currentRevision: makeRevisionSummary({
          revision_number: 2,
        }),
      },
    }),
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

test("does not render outline section even when outline is ready", () => {
  const store = createStage6Store();

  store.setState((state) => ({
    ...state,
    stream: {
      ...state.stream,
      outlineReady: true,
      outline: makeResearchOutline(),
      reportMarkdown:
        "# 报告标题\n\n## 第一章\n\n市场概览\n\n<div>危险原始 HTML</div>",
    },
  }));

  renderWithStore(<ReportCanvas />, { store });

  expect(screen.queryByText("中国 AI 搜索产品竞争格局研究")).not.toBeInTheDocument();
  expect(screen.queryByText("研究背景与问题定义")).not.toBeInTheDocument();
  expect(screen.queryByText("Outline")).not.toBeInTheDocument();
});

test("renders streamed markdown and blocks raw HTML", () => {
  const store = createStage6Store();

  store.setState((state) => ({
    ...state,
    stream: {
      ...state.stream,
      reportMarkdown:
        "# 报告标题\n\n## 第一章\n\n市场概览\n\n<div>危险原始 HTML</div>",
    },
  }));

  renderWithStore(<ReportCanvas />, { store });

  expect(
    screen.getByRole("heading", { level: 1, name: "报告标题" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { level: 2, name: "第一章" }),
  ).toBeInTheDocument();
  expect(screen.getByText("市场概览")).toBeInTheDocument();
  expect(screen.queryByText("危险原始 HTML")).not.toBeInTheDocument();
});

test("pauses auto-scroll on manual upward scroll and resumes on click", () => {
  const scrollIntoViewSpy = vi.fn();
  const originalScrollIntoView = Element.prototype.scrollIntoView;

  Object.defineProperty(Element.prototype, "scrollIntoView", {
    configurable: true,
    writable: true,
    value: scrollIntoViewSpy,
  });

  const store = createStage6Store();
  store.setState((state) => ({
    ...state,
    stream: {
      ...state.stream,
      reportMarkdown: "# 标题\n\n初始正文。",
    },
  }));

  renderWithStore(<ReportCanvas />, { store });

  const reportBody = screen.getByRole("region", { name: "报告正文" });
  expect(scrollIntoViewSpy).toHaveBeenCalled();

  scrollIntoViewSpy.mockClear();

  Object.defineProperties(reportBody, {
    scrollHeight: {
      configurable: true,
      value: 600,
    },
    clientHeight: {
      configurable: true,
      value: 400,
    },
    scrollTop: {
      configurable: true,
      writable: true,
      value: 100,
    },
  });

  fireEvent.scroll(reportBody);

  expect(screen.getByRole("button", { name: "回到底部" })).toBeInTheDocument();

  act(() => {
    store.setState((state) => ({
      ...state,
      stream: {
        ...state.stream,
        reportMarkdown: `${state.stream.reportMarkdown}\n\n第二段正文。`,
      },
    }));
  });

  expect(scrollIntoViewSpy).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: "回到底部" }));

  expect(scrollIntoViewSpy).toHaveBeenCalled();
  expect(screen.queryByRole("button", { name: "回到底部" })).not.toBeInTheDocument();

  Object.defineProperty(Element.prototype, "scrollIntoView", {
    configurable: true,
    writable: true,
    value: originalScrollIntoView,
  });
});

test("uses the shared workspace card height token for report scrolling", () => {
  const store = createStage6Store();

  store.setState((state) => ({
    ...state,
    stream: {
      ...state.stream,
      reportMarkdown: "# 标题\n\n初始正文。",
    },
  }));

  renderWithStore(<ReportCanvas />, { store });

  expect(screen.getByRole("region", { name: "报告画布" })).toHaveStyle({
    maxHeight: "var(--research-card-max-h)",
  });

  expect(screen.getByRole("region", { name: "报告正文" })).toHaveClass(
    "flex-1",
    "min-h-0",
    "overflow-y-auto",
  );
});

test("only renders markdown images from current task artifact urls", async () => {
  const artifact = makeArtifactSummary({
    artifact_id: "art_stage0_chart",
    url: "/api/v1/tasks/tsk_stage0/artifacts/art_stage0_chart?access_token=fresh",
  });
  const store = createStage6Store();

  store.setState((state) => ({
    ...state,
    remote: {
      ...state.remote,
      delivery: makeDeliverySummary({
        artifacts: [artifact],
      }),
    },
    stream: {
      ...state.stream,
      reportMarkdown: [
        "![合法](/api/v1/tasks/tsk_stage0/artifacts/art_stage0_chart?access_token=stale)",
        "![非法](https://evil.test/image.png)",
        "![跨任务](/api/v1/tasks/tsk_other/artifacts/art_stage0_other?access_token=123)",
      ].join("\n\n"),
    },
  }));

  mswServer.use(
    http.get("*/api/v1/tasks/tsk_stage0/artifacts/art_stage0_chart", () => {
      return new HttpResponse(new Uint8Array([137, 80, 78, 71]), {
        status: 200,
        headers: {
          "Content-Type": "image/png",
        },
      });
    }),
  );

  renderWithStore(<ReportCanvas />, { store });

  expect(await screen.findByAltText("合法")).toBeInTheDocument();
  expect(screen.queryByAltText("非法")).not.toBeInTheDocument();
  expect(screen.queryByAltText("跨任务")).not.toBeInTheDocument();
});

test("renders markdown images from canonical artifact paths using the latest artifact url", async () => {
  const artifact = makeArtifactSummary({
    artifact_id: "art_stage0_chart",
    url: "/api/v1/tasks/tsk_stage0/artifacts/art_stage0_chart?access_token=fresh",
  });
  const store = createStage6Store();

  store.setState((state) => ({
    ...state,
    remote: {
      ...state.remote,
      delivery: makeDeliverySummary({
        artifacts: [artifact],
      }),
    },
    stream: {
      ...state.stream,
      reportMarkdown: [
        "![合法](mimir://artifact/art_stage0_chart)",
        "![未知](mimir://artifact/art_missing_chart)",
        "![非法](https://evil.test/image.png)",
      ].join("\n\n"),
    },
  }));

  mswServer.use(
    http.get("*/api/v1/tasks/tsk_stage0/artifacts/art_stage0_chart", () => {
      return new HttpResponse(new Uint8Array([137, 80, 78, 71]), {
        status: 200,
        headers: {
          "Content-Type": "image/png",
        },
      });
    }),
  );

  renderWithStore(<ReportCanvas />, { store });

  expect(await screen.findByAltText("合法")).toBeInTheDocument();
  expect(screen.queryByAltText("未知")).not.toBeInTheDocument();
  expect(screen.queryByAltText("非法")).not.toBeInTheDocument();
});

test("does not render delivery word count chips even when delivery metadata contains word_count", () => {
  const store = createStage6Store();

  store.setState((state) => ({
    ...state,
    remote: {
      ...state.remote,
      delivery: makeDeliverySummary({
        word_count: 6800,
        artifact_count: 2,
      }),
    },
    stream: {
      ...state.stream,
      reportMarkdown: "# 标题\n\n正文。",
    },
  }));

  renderWithStore(<ReportCanvas />, { store });

  expect(screen.queryByText("6800 字")).not.toBeInTheDocument();
  expect(screen.getByText("02 张配图")).toBeInTheDocument();
});

test("renders footnote references and definitions from [^ref_n] syntax", () => {
  const store = createStage6Store();

  const markdown = [
    "核心结论[^ref_1]与扩展[^ref_2]",
    "",
    "[^ref_1]: [来源一](https://example.com/1)",
    "[^ref_2]: [来源二](https://example.com/2)",
  ].join("\n");

  store.setState((state) => ({
    ...state,
    stream: {
      ...state.stream,
      reportMarkdown: markdown,
    },
  }));

  renderWithStore(<ReportCanvas />, { store });

  // 1. Footnote section exists
  const footnoteSection = document.querySelector("section[data-footnotes]");
  expect(footnoteSection).toBeInTheDocument();

  // 2. Inline references rendered as superscript links
  const supElements = document.querySelectorAll("sup a");
  expect(supElements.length).toBe(2);

  // 3. Footnote definitions contain source text with links
  expect(screen.getByRole("link", { name: "来源一" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "来源二" })).toBeInTheDocument();
});

test("omits visible footnote backref symbols while keeping sources and superscripts", () => {
  const store = createStage6Store();

  const markdown = [
    "核心结论[^ref_1]与扩展[^ref_2]以及补充[^ref_3]",
    "",
    "[^ref_1]: [来源一](https://example.com/1)",
    "[^ref_2]: [来源二](https://example.com/2)",
    "[^ref_3]: [来源三](https://example.com/3)",
  ].join("\n");

  store.setState((state) => ({
    ...state,
    stream: {
      ...state.stream,
      reportMarkdown: markdown,
    },
  }));

  renderWithStore(<ReportCanvas />, { store });

  expect(document.querySelectorAll("sup a")).toHaveLength(3);
  expect(document.querySelectorAll("a[data-footnote-backref]")).toHaveLength(0);
  expect(document.querySelector("section[data-footnotes]")).not.toHaveTextContent("↩");
  expect(screen.getByRole("link", { name: "来源一" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "来源二" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "来源三" })).toBeInTheDocument();
});

test("keeps distinct footnote keys separate when ref_1 and ref1 both exist", () => {
  const store = createStage6Store();

  const markdown = [
    "A[^ref_1]与B[^ref1]同时引用",
    "",
    "[^ref_1]: [来源A](https://example.com/a)",
    "[^ref1]: [来源B](https://example.com/b)",
  ].join("\n");

  store.setState((state) => ({
    ...state,
    stream: {
      ...state.stream,
      reportMarkdown: markdown,
    },
  }));

  renderWithStore(<ReportCanvas />, { store });

  expect(document.querySelectorAll("sup a")).toHaveLength(2);
  expect(screen.getByRole("link", { name: "来源A" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "来源B" })).toBeInTheDocument();
});

test("does not fabricate placeholder footnotes when definition is missing", () => {
  const store = createStage6Store();

  store.setState((state) => ({
    ...state,
    stream: {
      ...state.stream,
      reportMarkdown: "结论[^ref_49]没有对应 definition。",
    },
  }));

  renderWithStore(<ReportCanvas />, { store });

  expect(screen.queryByText("(来源缺失)")).not.toBeInTheDocument();
  expect(document.querySelector("section[data-footnotes]")).not.toBeInTheDocument();
});

test("keeps multiline footnote continuation inside the footnote block", () => {
  const store = createStage6Store();

  const markdown = [
    "结论[^ref_1]带有多行来源",
    "",
    "[^ref_1]: 第一行",
    "    第二行延续",
  ].join("\n");

  store.setState((state) => ({
    ...state,
    stream: {
      ...state.stream,
      reportMarkdown: markdown,
    },
  }));

  renderWithStore(<ReportCanvas />, { store });

  const leakedParagraph = Array.from(document.querySelectorAll("p")).find((node) =>
    node.textContent?.includes("第二行延续") &&
    node.closest("section[data-footnotes]") === null,
  );
  expect(leakedParagraph).toBeUndefined();
  expect(document.querySelector("section[data-footnotes]")).toHaveTextContent(
    "第二行延续",
  );
});
