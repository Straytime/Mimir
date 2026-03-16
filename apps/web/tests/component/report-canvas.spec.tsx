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

test("shows outline overview, renders streamed markdown, and blocks raw HTML", () => {
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

  expect(screen.getByText("中国 AI 搜索产品竞争格局研究")).toBeInTheDocument();
  expect(screen.getByText("研究背景与问题定义")).toBeInTheDocument();
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
