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

test("renders title and indexed section groups without section descriptions", () => {
  const store = createResearchSessionStore();

  const outline = makeResearchOutline({
    title: "测试报告标题",
    sections: [
      {
        section_id: "s3",
        title: "第三章",
        description: "第三章描述",
        order: 3,
      },
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

  const outlineCard = screen.getByRole("region", { name: "报告大纲" });
  const title = screen.getByRole("heading", { name: "测试报告标题" });
  const sectionList = screen.getByRole("list", { name: "章节序列" });
  const sectionItems = within(sectionList).getAllByRole("listitem");
  const sectionTitles = within(sectionList).getAllByRole("heading", { level: 4 });
  const sectionsSummary = screen.getByText("Sections").closest("div");

  expect(outlineCard).toBeInTheDocument();
  expect(outlineCard).toHaveClass("bg-surface-container");
  expect(outlineCard).toHaveClass("outline");
  expect(outlineCard).toHaveClass("outline-outline-variant/15");
  expect(outlineCard).not.toHaveClass("bg-primary");
  expect(title).toHaveClass("text-white");
  expect(title).not.toHaveClass("text-primary");
  expect(sectionsSummary).not.toBeNull();
  expect(sectionsSummary).toHaveClass("bg-surface-container-lowest");
  expect(sectionList).toBeInTheDocument();
  expect(sectionItems).toHaveLength(3);
  expect(sectionTitles.map((node) => node.textContent)).toEqual([
    "第一章",
    "第二章",
    "第三章",
  ]);
  expect(screen.getByText("Section 01")).toBeInTheDocument();
  expect(screen.getByText("Section 02")).toBeInTheDocument();
  expect(screen.getByText("Section 03")).toBeInTheDocument();
  for (const item of sectionItems) {
    expect(item).toHaveClass("bg-surface-container-lowest");
    expect(item).toHaveClass("outline");
    expect(item).toHaveClass("outline-outline-variant/15");
    expect(item).not.toHaveClass("bg-primary");
  }
  expect(screen.queryByText("Report Flow")).not.toBeInTheDocument();
  expect(screen.queryByText("第一章描述")).not.toBeInTheDocument();
  expect(screen.queryByText("第二章描述")).not.toBeInTheDocument();
  expect(screen.queryByText("第三章描述")).not.toBeInTheDocument();
});
