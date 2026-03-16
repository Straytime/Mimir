import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { expect, test, vi } from "vitest";

import { DeliveryActions } from "@/features/research/components/delivery-actions";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makeDeliverySummary,
  makeResearchSessionState,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";
import { mswServer } from "@/tests/fixtures/msw-server";
import { renderWithStore } from "@/tests/fixtures/render";

function createDeferredResponse() {
  let resolve!: (response: Response) => void;
  const promise = new Promise<Response>((resolver) => {
    resolve = resolver;
  });

  return { promise, resolve };
}

function createDeliveryStore() {
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
          available_actions: ["download_markdown", "download_pdf", "submit_feedback"],
        }),
        delivery: makeDeliverySummary(),
      },
    }),
  );
}

test("disables download buttons while delivery refresh is in progress", () => {
  const store = createDeliveryStore();

  store.setState((state) => ({
    ...state,
    deliveryUi: {
      ...state.deliveryUi,
      refreshingDelivery: true,
    },
  }));

  renderWithStore(<DeliveryActions />, { store });

  expect(screen.getByRole("button", { name: "下载 Markdown Zip" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "下载 PDF" })).toBeDisabled();
});

test("shows independent loading state for markdown zip and pdf downloads", async () => {
  const user = userEvent.setup();
  const store = createDeliveryStore();
  const markdownDeferred = createDeferredResponse();
  const pdfDeferred = createDeferredResponse();
  const anchorClickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

  mswServer.use(
    http.get("*/api/v1/tasks/tsk_stage0/downloads/markdown.zip", () =>
      markdownDeferred.promise,
    ),
    http.get("*/api/v1/tasks/tsk_stage0/downloads/report.pdf", () =>
      pdfDeferred.promise,
    ),
  );

  renderWithStore(<DeliveryActions />, { store });

  const markdownButton = screen.getByRole("button", { name: "下载 Markdown Zip" });
  const pdfButton = screen.getByRole("button", { name: "下载 PDF" });

  await user.click(markdownButton);

  expect(markdownButton).toBeDisabled();
  expect(markdownButton).toHaveTextContent("下载中...");
  expect(pdfButton).toBeEnabled();

  markdownDeferred.resolve(
    new HttpResponse(new Uint8Array([80, 75, 3, 4]), {
      status: 200,
      headers: {
        "Content-Type": "application/zip",
      },
    }),
  );

  await waitFor(() => {
    expect(markdownButton).toHaveTextContent("下载 Markdown Zip");
  });

  await user.click(pdfButton);

  expect(pdfButton).toHaveTextContent("下载中...");

  pdfDeferred.resolve(
    new HttpResponse(new Uint8Array([37, 80, 68, 70]), {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
      },
    }),
  );

  await waitFor(() => {
    expect(pdfButton).toHaveTextContent("下载 PDF");
  });
  expect(anchorClickSpy).toHaveBeenCalled();
});
