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

  expect(firstCard).toHaveClass("transition-[background-color,color,outline-color]");
  expect(firstCard).toHaveClass("duration-150");
  expect(firstCard).toHaveClass("outline");
  expect(firstCard).toHaveClass("outline-1");
  expect(firstCard).toHaveClass("outline-transparent");
  expect(firstCard).toHaveClass("bg-surface-container-lowest");
  expect(firstCard).toHaveClass("before:opacity-0");
  expect(firstCard).toHaveClass("before:transition-opacity");
  expect(firstCard).toHaveClass("hover:bg-surface-container-low");
  expect(firstCard).toHaveClass("hover:outline-outline-variant/15");
  expect(firstCard).toHaveClass("hover:text-primary");
  expect(firstCard).toHaveClass("hover:before:opacity-100");
  expect(firstCard).toHaveClass("focus-visible:bg-surface-container-low");
  expect(firstCard).toHaveClass("focus-visible:text-primary");
  expect(firstCard).toHaveClass("focus-visible:outline-surface-tint/25");
  expect(firstCard).toHaveClass("focus-visible:before:opacity-100");
  expect(firstCard).toHaveClass("before:bg-surface-tint");
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
