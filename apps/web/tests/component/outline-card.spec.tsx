import { screen, within } from "@testing-library/react";
import { expect, test } from "vitest";

import { OutlineCard } from "@/features/research/components/outline-card";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import { makeResearchOutline } from "@/tests/fixtures/builders";
import { renderWithStore } from "@/tests/fixtures/render";

test("does not render when outline is null", () => {
  const store = createResearchSessionStore();

  store.setState((state) => ({
    ...state,
    stream: {
      ...state.stream,
      outline: null,
      outlineReady: true,
    },
  }));

  renderWithStore(<OutlineCard />, { store });

  expect(screen.queryByLabelText("报告大纲")).not.toBeInTheDocument();
});

test("does not render when outlineReady is false", () => {
  const store = createResearchSessionStore();

  store.setState((state) => ({
    ...state,
    stream: {
      ...state.stream,
      outline: makeResearchOutline(),
      outlineReady: false,
    },
  }));

  renderWithStore(<OutlineCard />, { store });

  expect(screen.queryByLabelText("报告大纲")).not.toBeInTheDocument();
});

test("renders title and indexed section groups when ready", () => {
  const store = createResearchSessionStore();

  const outline = makeResearchOutline({
    title: "测试报告标题",
    sections: [
      {
        section_id: "s1",
        title: "第一章",
        description: "第一章描述",
        order: 1,
      },
      {
        section_id: "s2",
        title: "第二章",
        description: "第二章描述",
        order: 2,
      },
      {
        section_id: "s3",
        title: "第三章",
        description: "第三章描述",
        order: 3,
      },
    ],
  });

  store.setState((state) => ({
    ...state,
    stream: {
      ...state.stream,
      outline,
      outlineReady: true,
    },
  }));

  renderWithStore(<OutlineCard />, { store });

  expect(screen.getByLabelText("报告大纲")).toBeInTheDocument();
  expect(screen.getByText("测试报告标题")).toBeInTheDocument();
  const sectionList = screen.getByRole("list", { name: "章节序列" });
  expect(sectionList).toBeInTheDocument();
  expect(within(sectionList).getAllByRole("listitem")).toHaveLength(3);
  expect(screen.getByText("章节 01 / Report Flow")).toBeInTheDocument();
  expect(screen.getByText("章节 02 / Report Flow")).toBeInTheDocument();
  expect(screen.getByText("章节 03 / Report Flow")).toBeInTheDocument();
  expect(screen.getByText("第一章")).toBeInTheDocument();
  expect(screen.getByText("第二章")).toBeInTheDocument();
  expect(screen.getByText("第三章")).toBeInTheDocument();
  expect(screen.getByText("第一章描述")).toBeInTheDocument();
  expect(screen.getByText("第二章描述")).toBeInTheDocument();
  expect(screen.getByText("第三章描述")).toBeInTheDocument();
});
