import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { ResearchPageClient } from "@/features/research/components/research-page-client";

test("renders the idle workspace shell before a task is created", () => {
  render(<ResearchPageClient />);

  expect(screen.getByRole("heading", { name: "AI 研究工作台" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "输入研究主题" })).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "从空态进入研究工作台" }),
  ).toBeInTheDocument();
});
