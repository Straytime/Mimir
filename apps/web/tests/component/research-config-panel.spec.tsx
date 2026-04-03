import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test } from "vitest";

import { ResearchConfigPanel } from "@/features/research/components/research-config-panel";
import { renderWithStore } from "@/tests/fixtures/render";

test("ResearchConfigPanel defaults to options clarification mode", () => {
  renderWithStore(<ResearchConfigPanel />);

  expect(screen.getByRole("radio", { name: "选项" })).toBeChecked();
  expect(screen.getByRole("radio", { name: "问答" })).not.toBeChecked();
});

test("ResearchConfigPanel reveals only the active mode hint on hover and focus", async () => {
  const user = userEvent.setup();

  renderWithStore(<ResearchConfigPanel />);

  const options = screen.getByRole("radio", { name: "选项" });
  const natural = screen.getByRole("radio", { name: "问答" });

  await user.hover(options);
  expect(
    screen.getByText(
      "通过自动生成的选单直接向我提供预设建议，适合快速启动",
    ),
  ).toBeInTheDocument();
  expect(
    screen.queryByText(
      "通过自然对话，开放式地向我反馈需求细节，适合复杂、需要详细说明的研究任务",
    ),
  ).not.toBeInTheDocument();

  await user.unhover(options);
  await user.click(natural);
  expect(
    screen.getByText(
      "通过自然对话，开放式地向我反馈需求细节，适合复杂、需要详细说明的研究任务",
    ),
  ).toBeInTheDocument();
  expect(
    screen.queryByText(
      "通过自动生成的选单直接向我提供预设建议，适合快速启动",
    ),
  ).not.toBeInTheDocument();
});
