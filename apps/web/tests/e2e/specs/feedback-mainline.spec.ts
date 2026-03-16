import { expect, test } from "@playwright/test";
import type { CreateTaskResponse } from "@/lib/contracts";

const createTaskResponse = {
  task_id: "tsk_stage7",
  task_token: "secret_stage7",
  trace_id: "trc_stage7",
  snapshot: {
    task_id: "tsk_stage7",
    status: "running",
    phase: "clarifying",
    active_revision_id: "rev_stage0",
    active_revision_number: 1,
    clarification_mode: "natural",
    created_at: "2026-03-16T00:00:00+08:00",
    updated_at: "2026-03-16T00:00:00+08:00",
    expires_at: null,
    available_actions: [],
  },
  urls: {
    events: "/api/v1/tasks/tsk_stage7/events",
    heartbeat: "/api/v1/tasks/tsk_stage7/heartbeat",
    disconnect: "/api/v1/tasks/tsk_stage7/disconnect",
  },
  connect_deadline_at: "2026-03-16T00:01:00+08:00",
} satisfies CreateTaskResponse;

test("drives the feedback revision mainline with the scripted browser runtime", async ({
  page,
}) => {
  await page.addInitScript((response) => {
    const runtimeHarness = {
      connectArgs: null as null | {
        onOpen: () => void;
        onEvent: (event: unknown) => void;
      },
      feedbackRequests: [] as Array<{ feedback_text: string }>,
      taskApiClient: {
        createTask: async () => ({
          response,
          requestId: "req_create_stage7",
          traceId: "trc_create_stage7",
        }),
        getTaskDetail: async () => ({
          task_id: response.task_id,
          snapshot: response.snapshot,
          current_revision: {
            revision_id: "rev_stage0",
            revision_number: 1,
            revision_status: "completed",
            started_at: "2026-03-16T00:00:00+08:00",
            finished_at: null,
            requirement_detail: null,
          },
          delivery: null,
          requestId: "req_detail_stage7",
          traceId: "trc_detail_stage7",
        }),
        submitClarification: async () => ({
          accepted: true,
          snapshot: response.snapshot,
          requestId: "req_clarification_stage7",
          traceId: "trc_clarification_stage7",
        }),
        submitFeedback: async ({
          request,
        }: {
          request: { feedback_text: string };
        }) => {
          runtimeHarness.feedbackRequests.push(request);

          return {
            accepted: true,
            revision_id: "rev_stage1",
            revision_number: 2,
            requestId: "req_feedback_stage7",
            traceId: "trc_feedback_stage7",
          };
        },
        sendHeartbeat: async () => ({
          requestId: "req_heartbeat_stage7",
          traceId: "trc_heartbeat_stage7",
        }),
        disconnectTask: async () => ({
          accepted: true,
          requestId: "req_disconnect_stage7",
          traceId: "trc_disconnect_stage7",
        }),
      },
      taskEventSource: {
        connect(args: {
          onOpen: () => void;
          onEvent: (event: unknown) => void;
        }) {
          runtimeHarness.connectArgs = args;
          return () => {
            if (runtimeHarness.connectArgs === args) {
              runtimeHarness.connectArgs = null;
            }
          };
        },
      },
      open() {
        runtimeHarness.connectArgs?.onOpen();
      },
      emit(event: unknown) {
        runtimeHarness.connectArgs?.onEvent(event);
      },
    };

    Reflect.set(window, "__MIMIR_E2E__", runtimeHarness);
    Reflect.set(window, "__MIMIR_TEST_RUNTIME__", {
      taskApiClient: runtimeHarness.taskApiClient as unknown,
      taskEventSource: runtimeHarness.taskEventSource as unknown,
    });
  }, createTaskResponse);

  await page.goto("/");

  await page.getByLabel("研究主题").fill("研究中国 AI 搜索产品的竞争格局");
  await page.getByRole("button", { name: "开始研究" }).click();
  await expect(page.getByText("活跃工作台")).toBeVisible();
  await page.waitForFunction(() => {
    return Boolean(
      (
        window as typeof window & {
          __MIMIR_TEST_STORE__?: unknown;
        }
      ).__MIMIR_TEST_STORE__,
    );
  });

  await page.evaluate(() => {
    (
      window as typeof window & {
        __MIMIR_TEST_STORE__: {
          getState: () => {
            setSessionContext: (patch: Record<string, unknown>) => void;
            applyEvent: (event: unknown) => void;
          };
        };
      }
    ).__MIMIR_TEST_STORE__.getState().setSessionContext({
      sseState: "open",
    });
    (
      window as typeof window & {
        __MIMIR_TEST_STORE__: {
          getState: () => {
            applyEvent: (event: unknown) => void;
          };
        };
      }
    ).__MIMIR_TEST_STORE__.getState().applyEvent({
      seq: 40,
      event: "writer.delta",
      task_id: "tsk_stage7",
      revision_id: "rev_stage0",
      phase: "writing_report",
      timestamp: "2026-03-16T00:00:20+08:00",
      payload: {
        delta: "# 第一轮报告\n\n旧报告正文。",
      },
    });
    (
      window as typeof window & {
        __MIMIR_TEST_STORE__: {
          getState: () => {
            applyEvent: (event: unknown) => void;
          };
        };
      }
    ).__MIMIR_TEST_STORE__.getState().applyEvent({
      seq: 41,
      event: "report.completed",
      task_id: "tsk_stage7",
      revision_id: "rev_stage0",
      phase: "delivered",
      timestamp: "2026-03-16T00:00:25+08:00",
      payload: {
        delivery: {
          revision_id: "rev_stage0",
          revision_number: 1,
          word_count: 1800,
          artifact_count: 0,
          markdown_zip_url:
            "/api/v1/tasks/tsk_stage7/downloads/markdown.zip?access_token=zip_stage7",
          pdf_url:
            "/api/v1/tasks/tsk_stage7/downloads/report.pdf?access_token=pdf_stage7",
          artifacts: [],
        },
      },
    });
    (
      window as typeof window & {
        __MIMIR_TEST_STORE__: {
          getState: () => {
            applyEvent: (event: unknown) => void;
          };
        };
      }
    ).__MIMIR_TEST_STORE__.getState().applyEvent({
      seq: 42,
      event: "task.awaiting_feedback",
      task_id: "tsk_stage7",
      revision_id: "rev_stage0",
      phase: "delivered",
      timestamp: "2026-03-16T00:00:26+08:00",
      payload: {
        expires_at: "2026-03-16T01:00:00+08:00",
        available_actions: [
          "submit_feedback",
          "download_markdown",
          "download_pdf",
        ],
      },
    });
  });

  await expect(page.getByText("旧报告正文。")).toBeVisible();
  await expect(page.getByRole("textbox", { name: "反馈意见" })).toBeVisible();

  await page.getByRole("textbox", { name: "反馈意见" }).fill("请增加竞品商业化对比。");
  await page.getByRole("button", { name: "提交反馈" }).click();

  await expect(
    page.getByText("正在处理反馈并准备新一轮研究..."),
  ).toBeVisible();
  await expect(page.getByText("旧报告正文。")).toBeVisible();

  await page.evaluate(() => {
    (
      window as typeof window & {
        __MIMIR_TEST_STORE__: {
          getState: () => {
            applyEvent: (event: unknown) => void;
          };
        };
      }
    ).__MIMIR_TEST_STORE__.getState().applyEvent({
      seq: 43,
      event: "phase.changed",
      task_id: "tsk_stage7",
      revision_id: "rev_stage1",
      phase: "processing_feedback",
      timestamp: "2026-03-16T00:00:30+08:00",
      payload: {
        from_phase: "delivered",
        to_phase: "processing_feedback",
        status: "running",
      },
    });
    (
      window as typeof window & {
        __MIMIR_TEST_STORE__: {
          getState: () => {
            applyEvent: (event: unknown) => void;
          };
        };
      }
    ).__MIMIR_TEST_STORE__.getState().applyEvent({
      seq: 44,
      event: "analysis.completed",
      task_id: "tsk_stage7",
      revision_id: "rev_stage1",
      phase: "processing_feedback",
      timestamp: "2026-03-16T00:00:34+08:00",
      payload: {
        requirement_detail: {
          research_goal: "增加竞品商业化对比",
          domain: "互联网 / AI 产品",
          requirement_details: "重点补充竞品差异、商业化路径和机会。",
          output_format: "business_report",
          freshness_requirement: "high",
          language: "zh-CN",
        },
      },
    });
    (
      window as typeof window & {
        __MIMIR_TEST_STORE__: {
          getState: () => {
            applyEvent: (event: unknown) => void;
          };
        };
      }
    ).__MIMIR_TEST_STORE__.getState().applyEvent({
      seq: 45,
      event: "phase.changed",
      task_id: "tsk_stage7",
      revision_id: "rev_stage1",
      phase: "planning_collection",
      timestamp: "2026-03-16T00:00:38+08:00",
      payload: {
        from_phase: "processing_feedback",
        to_phase: "planning_collection",
        status: "running",
      },
    });
  });

  await expect(
    page.getByText("正在处理反馈并准备新一轮研究..."),
  ).toHaveCount(0);
  await expect(page.getByText("第 2 轮研究开始")).toBeVisible();
  await expect(page.getByText("新一轮研究已进入规划阶段")).toBeVisible();
});
