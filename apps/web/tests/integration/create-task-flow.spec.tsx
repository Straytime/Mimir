import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { expect, test, vi } from "vitest";

import { ResearchPageClient } from "@/features/research/components/research-page-client";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import { createFetchTaskApiClient } from "@/lib/api/task-api-client";
import {
  makeCreateTaskResponse,
  makeQuotaExceededErrorResponse,
  makeResourceBusyErrorResponse,
  makeValidationErrorResponse,
} from "@/tests/fixtures/builders";
import { mswServer } from "@/tests/fixtures/msw-server";

const TASKS_API_URL = new URL("/api/v1/tasks", window.location.origin).toString();
const TASK_DETAILS_API_URL = new URL(
  "/api/v1/tasks/:taskId",
  window.location.origin,
).toString();

function createIntegrationRuntime(overrides: {
  connect?: ReturnType<typeof vi.fn>;
} = {}) {
  return {
    taskApiClient: createFetchTaskApiClient({
      baseUrl: window.location.origin,
      fetchImpl: window.fetch.bind(window),
    }),
    taskEventSource: {
      connect: overrides.connect ?? vi.fn(() => vi.fn()),
    },
  };
}

function createDeferred() {
  let resolve!: () => void;
  const promise = new Promise<void>((resolver) => {
    resolve = resolver;
  });

  return { promise, resolve };
}

test("creates a task, writes session context, and immediately starts the SSE connect action", async () => {
  const user = userEvent.setup();
  const store = createResearchSessionStore();
  const connect = vi.fn(() => vi.fn());
  const deferred = createDeferred();
  const createTaskResponse = makeCreateTaskResponse();
  const recordedBodies: unknown[] = [];
  let getTaskCalls = 0;

  mswServer.use(
    http.post(TASKS_API_URL, async ({ request }) => {
      recordedBodies.push(await request.json());
      await deferred.promise;

      return HttpResponse.json(createTaskResponse, {
        status: 201,
        headers: {
          "x-request-id": "req_stage2",
          "x-trace-id": createTaskResponse.trace_id,
        },
      });
    }),
    http.get(TASK_DETAILS_API_URL, () => {
      getTaskCalls += 1;
      return HttpResponse.json({}, { status: 500 });
    }),
  );

  render(
    <ResearchPageClient
      runtime={createIntegrationRuntime({ connect })}
      store={store}
    />,
  );

  await user.type(screen.getByLabelText("研究主题"), "研究中国 AI 搜索产品竞争格局");
  await user.click(screen.getByRole("button", { name: "开始研究" }));

  expect(store.getState().ui.pendingAction).toBe("creating_task");
  expect(screen.getByLabelText("研究主题")).toBeDisabled();
  expect(screen.getByRole("radio", { name: /自然澄清/i })).toBeDisabled();
  expect(screen.getByRole("radio", { name: /选单澄清/i })).toBeDisabled();

  deferred.resolve();

  await screen.findByRole("heading", { name: "活跃工作台" });

  expect(recordedBodies).toHaveLength(1);
  expect(recordedBodies[0]).toMatchObject({
    initial_query: "研究中国 AI 搜索产品竞争格局",
    config: {
      clarification_mode: "natural",
    },
  });
  expect(store.getState().session).toMatchObject({
    taskId: createTaskResponse.task_id,
    taskToken: createTaskResponse.task_token,
    traceId: createTaskResponse.trace_id,
    requestId: "req_stage2",
    eventsUrl: createTaskResponse.urls.events,
    heartbeatUrl: createTaskResponse.urls.heartbeat,
    disconnectUrl: createTaskResponse.urls.disconnect,
    connectDeadlineAt: createTaskResponse.connect_deadline_at,
    sseState: "connecting",
  });
  expect(store.getState().remote.snapshot).toEqual(createTaskResponse.snapshot);
  expect(store.getState().ui.pendingAction).toBeNull();
  expect(connect).toHaveBeenCalledTimes(1);
  expect(connect).toHaveBeenCalledWith({
    url: createTaskResponse.urls.events,
    token: createTaskResponse.task_token,
    onOpen: expect.any(Function),
    onEvent: expect.any(Function),
    onError: expect.any(Function),
    onClose: expect.any(Function),
  });
  expect(getTaskCalls).toBe(0);
});

test("shows an inline validation error for 422 responses and keeps the draft", async () => {
  const user = userEvent.setup();
  const store = createResearchSessionStore();

  mswServer.use(
    http.post(TASKS_API_URL, () => {
      return HttpResponse.json(makeValidationErrorResponse(), {
        status: 422,
      });
    }),
  );

  render(
    <ResearchPageClient runtime={createIntegrationRuntime()} store={store} />,
  );

  const textarea = screen.getByLabelText("研究主题");
  await user.type(textarea, "保留这段输入");
  await user.click(screen.getByRole("button", { name: "开始研究" }));

  await screen.findByText("研究主题不能为空。");

  expect(textarea).toHaveValue("保留这段输入");
  expect(textarea).toHaveAttribute("aria-invalid", "true");
  expect(store.getState().ui.pendingAction).toBeNull();
});

test("shows the contract message for 409 resource_busy", async () => {
  const user = userEvent.setup();
  const store = createResearchSessionStore();

  mswServer.use(
    http.post(TASKS_API_URL, () => {
      return HttpResponse.json(makeResourceBusyErrorResponse(), {
        status: 409,
      });
    }),
  );

  render(
    <ResearchPageClient runtime={createIntegrationRuntime()} store={store} />,
  );

  await user.type(screen.getByLabelText("研究主题"), "研究另一个主题");
  await user.click(screen.getByRole("button", { name: "开始研究" }));

  await screen.findByText("当前系统正处理另一项研究，请稍后重试。");

  expect(store.getState().ui.pendingAction).toBeNull();
});

test("shows quota timing copy for 429 ip_quota_exceeded", async () => {
  const user = userEvent.setup();
  const store = createResearchSessionStore();

  mswServer.use(
    http.post(TASKS_API_URL, () => {
      return HttpResponse.json(makeQuotaExceededErrorResponse(), {
        status: 429,
        headers: {
          "Retry-After": "37800",
        },
      });
    }),
  );

  render(
    <ResearchPageClient runtime={createIntegrationRuntime()} store={store} />,
  );

  await user.type(screen.getByLabelText("研究主题"), "研究配额错误提示");
  await user.click(screen.getByRole("button", { name: "开始研究" }));

  await screen.findByText("24 小时内创建任务次数已达上限，请稍后再试。");

  expect(
    screen.getByText("下次可创建时间：2026-03-14T02:15:00+08:00"),
  ).toBeInTheDocument();
  expect(screen.getByText("约 10小时30分钟 后可再次创建。")).toBeInTheDocument();
  expect(store.getState().ui.pendingAction).toBeNull();
});
