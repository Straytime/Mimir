import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { expect, test, vi } from "vitest";

import { DeliveryActions } from "@/features/research/components/delivery-actions";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import type {
  TaskApiClient,
  TaskDetailResult,
} from "@/lib/api/task-api-client";
import {
  makeDeliverySummary,
  makeResearchSessionState,
  makeRevisionSummary,
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

function createTaskApiClientMock(overrides: Partial<TaskApiClient> = {}): TaskApiClient {
  return {
    createTask: vi.fn(),
    getTaskDetail: vi.fn(),
    submitClarification: vi.fn(),
    submitFeedback: vi.fn(),
    sendHeartbeat: vi.fn(),
    disconnectTask: vi.fn(),
    ...overrides,
  };
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

test("does not render delivery word count in the action panel", () => {
  const store = createDeliveryStore();

  store.setState((state) => ({
    ...state,
    remote: {
      ...state.remote,
      delivery: makeDeliverySummary({
        ...state.remote.delivery!,
        word_count: 6800,
        artifact_count: 3,
      }),
    },
  }));

  renderWithStore(<DeliveryActions />, { store });

  expect(screen.queryByText("6800 字")).not.toBeInTheDocument();
  expect(screen.getByText("3 张配图")).toBeInTheDocument();
});

test("disables download buttons while waiting for the next revision after feedback submission", () => {
  const store = createDeliveryStore();

  store.setState((state) => ({
    ...state,
    ui: {
      ...state.ui,
      revisionTransition: {
        status: "waiting_next_revision",
        pendingRevisionId: "rev_stage1",
        pendingRevisionNumber: 2,
      },
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

test.each([
  {
    format: "markdown" as const,
    buttonName: "下载 Markdown Zip",
    staleUrl: "/api/v1/tasks/tsk_stage0/downloads/markdown.zip?access_token=zip_stale",
    freshUrl: "/api/v1/tasks/tsk_stage0/downloads/markdown.zip?access_token=zip_fresh",
    filename: "report-markdown.zip",
    mimeType: "application/zip",
    bytes: new Uint8Array([80, 75, 3, 4]),
  },
  {
    format: "pdf" as const,
    buttonName: "下载 PDF",
    staleUrl: "/api/v1/tasks/tsk_stage0/downloads/report.pdf?access_token=pdf_stale",
    freshUrl: "/api/v1/tasks/tsk_stage0/downloads/report.pdf?access_token=pdf_fresh",
    filename: "report.pdf",
    mimeType: "application/pdf",
    bytes: new Uint8Array([37, 80, 68, 70]),
  },
])(
  "refreshes %s delivery after access_token_invalid and retries with the fresh url",
  async ({ buttonName, staleUrl, freshUrl, filename, mimeType, bytes }) => {
    const user = userEvent.setup();
    const store = createDeliveryStore();
    const clickedAnchors: HTMLAnchorElement[] = [];
    const anchorClickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(function (this: HTMLAnchorElement) {
        clickedAnchors.push(this);
      });
    let staleCalls = 0;
    let freshCalls = 0;
    const getTaskDetail = vi.fn<TaskApiClient["getTaskDetail"]>().mockResolvedValue({
      task_id: "tsk_stage0",
      snapshot: makeTaskSnapshot({
        task_id: "tsk_stage0",
        phase: "delivered",
        status: "awaiting_feedback",
        available_actions: [
          "download_markdown",
          "download_pdf",
          "submit_feedback",
        ],
      }),
      current_revision: makeRevisionSummary(),
      delivery: makeDeliverySummary({
        markdown_zip_url:
          buttonName === "下载 Markdown Zip"
            ? freshUrl
            : staleUrl,
        pdf_url:
          buttonName === "下载 PDF"
            ? freshUrl
            : staleUrl,
      }),
      requestId: "req_delivery_detail",
      traceId: "trc_delivery_detail",
    } satisfies TaskDetailResult);

    store.setState((state) => ({
      ...state,
      remote: {
        ...state.remote,
        delivery: makeDeliverySummary({
          ...state.remote.delivery!,
          markdown_zip_url:
            buttonName === "下载 Markdown Zip"
              ? staleUrl
              : state.remote.delivery!.markdown_zip_url,
          pdf_url:
            buttonName === "下载 PDF"
              ? staleUrl
              : state.remote.delivery!.pdf_url,
        }),
      },
    }));

    mswServer.use(
      http.get("*/api/v1/tasks/tsk_stage0/downloads/markdown.zip", ({ request }) => {
        const accessToken = new URL(request.url).searchParams.get("access_token");

        if (accessToken === "zip_fresh") {
          freshCalls += 1;
          return new HttpResponse(bytes, {
            status: 200,
            headers: {
              "Content-Type": mimeType,
            },
          });
        }

        staleCalls += 1;
        return HttpResponse.json(
          {
            error: {
              code: "access_token_invalid",
              message: "链接已失效。",
              detail: {},
              request_id: "req_zip_stale",
              trace_id: null,
            },
          },
          { status: 401 },
        );
      }),
      http.get("*/api/v1/tasks/tsk_stage0/downloads/report.pdf", ({ request }) => {
        const accessToken = new URL(request.url).searchParams.get("access_token");

        if (accessToken === "pdf_fresh") {
          freshCalls += 1;
          return new HttpResponse(bytes, {
            status: 200,
            headers: {
              "Content-Type": mimeType,
            },
          });
        }

        staleCalls += 1;
        return HttpResponse.json(
          {
            error: {
              code: "access_token_invalid",
              message: "链接已失效。",
              detail: {},
              request_id: "req_pdf_stale",
              trace_id: null,
            },
          },
          { status: 401 },
        );
      }),
    );

    renderWithStore(<DeliveryActions />, {
      store,
      runtime: {
        taskApiClient: createTaskApiClientMock({
          getTaskDetail,
        }),
      },
    });

    await user.click(screen.getByRole("button", { name: buttonName }));

    await waitFor(() => {
      expect(getTaskDetail).toHaveBeenCalledTimes(1);
      expect(staleCalls).toBe(1);
      expect(freshCalls).toBe(1);
      expect(anchorClickSpy).toHaveBeenCalledTimes(1);
    });

    expect(clickedAnchors[0]?.download).toBe(filename);
    expect(screen.queryByText("交付链接已失效或任务已清理。")).not.toBeInTheDocument();
  },
);

test("does not refresh delivery on non-access_token_invalid errors", async () => {
  const user = userEvent.setup();
  const store = createDeliveryStore();
  const getTaskDetail = vi.fn();

  mswServer.use(
    http.get("*/api/v1/tasks/tsk_stage0/downloads/markdown.zip", () =>
      HttpResponse.json(
        {
          error: {
            code: "artifact_not_found",
            message: "文件不存在。",
            detail: {},
            request_id: "req_download_missing",
            trace_id: null,
          },
        },
        { status: 404 },
      ),
    ),
  );

  renderWithStore(<DeliveryActions />, {
    store,
    runtime: {
      taskApiClient: createTaskApiClientMock({
        getTaskDetail,
      }),
    },
  });

  await user.click(screen.getByRole("button", { name: "下载 Markdown Zip" }));

  await screen.findByText("交付链接已失效或任务已清理。");
  expect(getTaskDetail).not.toHaveBeenCalled();
});

test("stops after one refresh attempt when delivery refresh fails", async () => {
  const user = userEvent.setup();
  const store = createDeliveryStore();
  let staleCalls = 0;
  const getTaskDetail = vi
    .fn<TaskApiClient["getTaskDetail"]>()
    .mockRejectedValue(new Error("refresh_failed"));

  store.setState((state) => ({
    ...state,
    remote: {
      ...state.remote,
      delivery: makeDeliverySummary({
        ...state.remote.delivery!,
        markdown_zip_url:
          "/api/v1/tasks/tsk_stage0/downloads/markdown.zip?access_token=zip_stale",
      }),
    },
  }));

  mswServer.use(
    http.get("*/api/v1/tasks/tsk_stage0/downloads/markdown.zip", () => {
      staleCalls += 1;
      return HttpResponse.json(
        {
          error: {
            code: "access_token_invalid",
            message: "链接已失效。",
            detail: {},
            request_id: "req_zip_stale",
            trace_id: null,
          },
        },
        { status: 401 },
      );
    }),
  );

  renderWithStore(<DeliveryActions />, {
    store,
    runtime: {
      taskApiClient: createTaskApiClientMock({
        getTaskDetail,
      }),
    },
  });

  await user.click(screen.getByRole("button", { name: "下载 Markdown Zip" }));

  await screen.findByText("交付链接已失效或任务已清理。");
  expect(staleCalls).toBe(1);
  expect(getTaskDetail).toHaveBeenCalledTimes(1);
});
