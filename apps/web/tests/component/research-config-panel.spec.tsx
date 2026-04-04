import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test } from "vitest";

import { ResearchConfigPanel } from "@/features/research/components/research-config-panel";
import { renderWithStore } from "@/tests/fixtures/render";

test("ResearchConfigPanel defaults to options clarification mode", () => {
  renderWithStore(<ResearchConfigPanel />);

  expect(screen.getByRole("radio", { name: "选项式" })).toBeChecked();
  expect(screen.getByRole("radio", { name: "问答式" })).not.toBeChecked();
});

test("ResearchConfigPanel reveals only the active mode hint on hover and keeps it visible when moving into the tooltip", async () => {
  const user = userEvent.setup();

  renderWithStore(<ResearchConfigPanel />);

  const options = screen.getByRole("radio", { name: "选项式" });
  const natural = screen.getByRole("radio", { name: "问答式" });
  const selectorRegion = screen.getByTestId("research-config-selector-region");

  await user.hover(options);
  const optionsHintText = screen.getByText(
    "通过自动生成的选单直接向我提供预设建议，适合快速启动",
  );
  const optionsHint = screen.getByRole("note", { name: "选项式提示" });

  expect(selectorRegion).toContainElement(optionsHint);
  expect(selectorRegion).not.toHaveClass("pb-[70px]");
  expect(optionsHint).toBeInTheDocument();
  expect(
    screen.queryByText(
      "通过自然对话，开放式地向我反馈需求细节，适合复杂、需要详细说明的研究任务",
    ),
  ).not.toBeInTheDocument();

  fireEvent.mouseLeave(selectorRegion, { relatedTarget: optionsHint });
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

  fireEvent.mouseLeave(selectorRegion);
  expect(
    screen.queryByText(
      "通过自动生成的选单直接向我提供预设建议，适合快速启动",
    ),
  ).not.toBeInTheDocument();

  await user.unhover(optionsHintText);
  fireEvent.focus(natural);
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
