import { act, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { ResearchWorkspaceShell } from "@/features/research/components/research-workspace-shell";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makeCollectionPlanRoundNode,
  makeCollectionTraceRoot,
  makeDeliverySummary,
  makeResearchOutline,
  makeResearchSessionState,
  makeRevisionSummary,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";
import { renderWithStore } from "@/tests/fixtures/render";

function buildActiveWorkspaceStore(
  overrides: Parameters<typeof makeResearchSessionState>[0] = {},
) {
  return createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        sseState: "closed",
      },
      ...overrides,
    }),
  );
}

test("hides clarification until text or question set content is ready", () => {
  const store = buildActiveWorkspaceStore({
    remote: {
      snapshot: makeTaskSnapshot({
        phase: "clarifying",
        status: "running",
        clarification_mode: "natural",
      }),
    },
    stream: {
      clarificationText: "",
      questionSet: null,
    },
  });

  renderWithStore(<ResearchWorkspaceShell />, { store });

  expect(screen.queryByText("澄清详情")).not.toBeInTheDocument();

  act(() => {
    store.setState((state) => ({
      ...state,
      stream: {
        ...state.stream,
        clarificationText: "为了更好地理解需求，请先确认几个问题。",
      },
    }));
  });

  expect(screen.getByText("澄清详情")).toBeInTheDocument();

  act(() => {
    store.setState((state) => ({
      ...state,
      stream: {
        ...state.stream,
        clarificationText: "",
        questionSet: {
          questions: [
            {
              question_id: "q_0",
              question: "你更关心技术还是商业影响？",
              options: [
                { option_id: "o_1", label: "技术" },
                { option_id: "o_2", label: "商业" },
              ],
            },
          ],
        },
      },
    }));
  });

  expect(screen.getByText("澄清详情")).toBeInTheDocument();
});

test("hides requirement summary until requirement detail is ready", () => {
  const store = buildActiveWorkspaceStore({
    remote: {
      snapshot: makeTaskSnapshot({
        phase: "analyzing_requirement",
        status: "running",
      }),
      currentRevision: makeRevisionSummary({
        requirement_detail: null,
      }),
    },
  });

  renderWithStore(<ResearchWorkspaceShell />, { store });

  expect(screen.queryByText("Requirement Summary")).not.toBeInTheDocument();
  expect(screen.queryByText("需求摘要已生成")).not.toBeInTheDocument();

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

  expect(screen.getByText("需求摘要已生成")).toBeInTheDocument();
});

test("hides collection trace until at least one trace node exists", () => {
  const store = buildActiveWorkspaceStore({
    remote: {
      snapshot: makeTaskSnapshot({
        phase: "planning_collection",
        status: "running",
      }),
    },
    stream: {
      collectionTrace: makeCollectionTraceRoot({
        nodes: [],
      }),
    },
  });

  renderWithStore(<ResearchWorkspaceShell />, { store });

  expect(
    screen.queryByRole("region", { name: "Collection Trace" }),
  ).not.toBeInTheDocument();

  act(() => {
    store.setState((state) => ({
      ...state,
      stream: {
        ...state.stream,
        collectionTrace: makeCollectionTraceRoot({
          nodes: [makeCollectionPlanRoundNode()],
        }),
      },
    }));
  });

  expect(screen.getByRole("region", { name: "Collection Trace" })).toBeInTheDocument();
});

test("hides outline until it is ready and has sections", () => {
  const store = buildActiveWorkspaceStore({
    remote: {
      snapshot: makeTaskSnapshot({
        phase: "preparing_outline",
        status: "running",
      }),
    },
    stream: {
      outline: makeResearchOutline(),
      outlineReady: false,
    },
  });

  renderWithStore(<ResearchWorkspaceShell />, { store });

  expect(screen.queryByLabelText("报告大纲")).not.toBeInTheDocument();

  act(() => {
    store.setState((state) => ({
      ...state,
      stream: {
        ...state.stream,
        outline: makeResearchOutline({
          sections: [],
        }),
        outlineReady: true,
      },
    }));
  });

  expect(screen.queryByLabelText("报告大纲")).not.toBeInTheDocument();

  act(() => {
    store.setState((state) => ({
      ...state,
      stream: {
        ...state.stream,
        outline: makeResearchOutline(),
        outlineReady: true,
      },
    }));
  });

  expect(screen.getByLabelText("报告大纲")).toBeInTheDocument();
});

test("hides report until markdown content is ready", () => {
  const store = buildActiveWorkspaceStore({
    remote: {
      snapshot: makeTaskSnapshot({
        phase: "writing_report",
        status: "running",
      }),
    },
    stream: {
      reportMarkdown: "",
    },
  });

  renderWithStore(<ResearchWorkspaceShell />, { store });

  expect(screen.queryByRole("region", { name: "报告画布" })).not.toBeInTheDocument();

  act(() => {
    store.setState((state) => ({
      ...state,
      stream: {
        ...state.stream,
        reportMarkdown: "# 标题\n\n正文。",
      },
    }));
  });

  expect(screen.getByRole("region", { name: "报告画布" })).toBeInTheDocument();
});

test("hides delivery actions until delivery payload is ready even after delivered", () => {
  const store = buildActiveWorkspaceStore({
    remote: {
      snapshot: makeTaskSnapshot({
        phase: "delivered",
        status: "awaiting_feedback",
        available_actions: ["download_markdown", "download_pdf"],
      }),
      delivery: null,
    },
    stream: {
      reportMarkdown: "# 标题\n\n正文。",
    },
  });

  renderWithStore(<ResearchWorkspaceShell />, { store });

  expect(screen.queryByLabelText("交付操作")).not.toBeInTheDocument();

  act(() => {
    store.setState((state) => ({
      ...state,
      remote: {
        ...state.remote,
        delivery: makeDeliverySummary({
          artifact_count: 0,
          artifacts: [],
        }),
      },
    }));
  });

  expect(screen.getByLabelText("交付操作")).toBeInTheDocument();
});
