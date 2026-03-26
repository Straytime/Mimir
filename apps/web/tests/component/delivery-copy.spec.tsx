"use client";

import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";

import { DeliveryActions } from "@/features/research/components/delivery-actions";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import type { AvailableAction } from "@/lib/contracts";
import {
  makeDeliverySummary,
  makeResearchSessionState,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";
import { renderWithStore } from "@/tests/fixtures/render";

function createDeliveryStoreWithMarkdown(
  overrides: {
    reportMarkdown?: string;
    available_actions?: AvailableAction[];
  } = {},
) {
  return createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "delivered",
          status: "awaiting_feedback",
          available_actions: overrides.available_actions ?? [
            "download_markdown",
            "download_pdf",
            "submit_feedback",
          ],
        }),
        delivery: makeDeliverySummary(),
      },
      stream: {
        reportMarkdown: overrides.reportMarkdown ?? "# 报告标题\n\n正文内容。",
      },
    }),
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

test("renders enabled '复制 Markdown' button when available_actions includes download_markdown and reportMarkdown is non-empty", () => {
  const store = createDeliveryStoreWithMarkdown();

  renderWithStore(<DeliveryActions />, { store });

  const copyButton = screen.getByRole("button", { name: "复制 Markdown" });
  expect(copyButton).toBeInTheDocument();
  expect(copyButton).toBeEnabled();
});

test("calls navigator.clipboard.writeText with reportMarkdown on click", async () => {
  const user = userEvent.setup();
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText },
  });

  const store = createDeliveryStoreWithMarkdown({
    reportMarkdown: "# 测试报告\n\n段落一。",
  });

  renderWithStore(<DeliveryActions />, { store });

  await user.click(screen.getByRole("button", { name: "复制 Markdown" }));

  expect(writeText).toHaveBeenCalledWith("# 测试报告\n\n段落一。");
});

test("shows '已复制 ✓' after successful copy", async () => {
  const user = userEvent.setup();
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText: vi.fn().mockResolvedValue(undefined) },
  });

  const store = createDeliveryStoreWithMarkdown();

  renderWithStore(<DeliveryActions />, { store });

  await user.click(screen.getByRole("button", { name: "复制 Markdown" }));

  await waitFor(() => {
    expect(screen.getByRole("button", { name: "已复制 ✓" })).toBeInTheDocument();
  });
});

test("disables '复制 Markdown' button when available_actions does not include download_markdown", () => {
  const store = createDeliveryStoreWithMarkdown({
    available_actions: ["download_pdf", "submit_feedback"],
  });

  renderWithStore(<DeliveryActions />, { store });

  expect(screen.getByRole("button", { name: "复制 Markdown" })).toBeDisabled();
});
