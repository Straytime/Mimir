import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test } from "vitest";

import { ExamplePrompts } from "@/features/research/components/example-prompts";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import { renderWithStore } from "@/tests/fixtures/render";

test("renders the updated first two example prompts and preserves the third", () => {
  renderWithStore(<ExamplePrompts />);

  const buttons = screen.getAllByRole("button");
  expect(buttons).toHaveLength(3);
  expect(buttons[0]).toHaveTextContent("从心理学角度解析 openclaw 爆火的原因");
  expect(buttons[1]).toHaveTextContent("一级方程式赛车 26 年新规的争议与影响");
  expect(buttons[2]).toHaveTextContent(
    "新能源汽车电池技术路线对比：磷酸铁锂 vs 三元锂 vs 固态电池",
  );
});

test("example prompt cards use the refined docked hover and focus treatment", () => {
  renderWithStore(<ExamplePrompts />);

  const firstCard = screen.getAllByRole("button")[0]!;

  expect(firstCard).toHaveClass("transition-[background-color,color]");
  expect(firstCard).toHaveClass("duration-150");
  expect(firstCard).toHaveClass("bg-surface-container");
  expect(firstCard).toHaveClass("before:opacity-0");
  expect(firstCard).toHaveClass("before:transition-opacity");
  expect(firstCard).toHaveClass("hover:bg-surface-container-high");
  expect(firstCard).toHaveClass("hover:text-primary");
  expect(firstCard).toHaveClass("hover:before:opacity-100");
  expect(firstCard).toHaveClass("focus-visible:bg-surface-container-high");
  expect(firstCard).toHaveClass("focus-visible:text-primary");
  expect(firstCard).toHaveClass("focus-visible:before:opacity-100");
  expect(firstCard).toHaveClass("focus-visible:shadow-[0_0_0_2px_rgba(255,173,58,0.2)]");
  expect(firstCard).toHaveClass("before:bg-primary");
  // No-Line Rule: no outline or border classes
  expect(firstCard).not.toHaveClass("outline");
  expect(firstCard).not.toHaveClass("outline-1");
  expect(firstCard).not.toHaveClass("outline-transparent");
  expect(firstCard).not.toHaveClass("shadow-glow-sm");
  expect(firstCard).not.toHaveClass("shadow-glow-md");
  expect(firstCard).not.toHaveClass("shadow-ghost");
  expect(firstCard).not.toHaveClass("hover:bg-surface");
  expect(firstCard).not.toHaveClass("focus-visible:bg-surface");
  expect(firstCard).not.toHaveClass("hover:-translate-y-px");
  expect(firstCard).not.toHaveClass("focus-visible:-translate-y-px");
  expect(firstCard).not.toHaveClass("hover:-translate-y-0.5");
  expect(firstCard).not.toHaveClass("focus-visible:-translate-y-0.5");
});

test("clicking an example card fills the initialPromptDraft in store", async () => {
  const user = userEvent.setup();
  const store = createResearchSessionStore();

  renderWithStore(<ExamplePrompts />, { store });

  const firstCard = screen.getAllByRole("button")[0]!;
  const cardText = firstCard.textContent!;

  await user.click(firstCard);

  expect(store.getState().ui.initialPromptDraft).toBe(cardText);
});
