import { screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { TerminalBanner } from "@/features/research/components/terminal-banner";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makeResearchSessionState,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";
import { renderWithStore } from "@/tests/fixtures/render";
import type { TerminationReason } from "@/lib/contracts";

function createTerminalStoreWithDetail(
  terminalReason: "failed" | "terminated" | "expired",
  terminationDetail: TerminationReason | null = null,
) {
  return createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        sseState: "closed",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "delivered",
          status: terminalReason,
        }),
      },
      ui: {
        terminalReason,
        terminationDetail,
      },
    }),
  );
}

test("shows risk control message when terminationDetail is 'risk_control_limit'", () => {
  const store = createTerminalStoreWithDetail("terminated", "risk_control_limit");
  renderWithStore(<TerminalBanner />, { store });

  expect(
    screen.getByRole("heading", { level: 2, name: "任务已终止" }),
  ).toBeInTheDocument();
  expect(
    screen.getByText("研究内容触发了平台内容安全策略，当前任务已停止。请调整研究主题后重新创建研究。"),
  ).toBeInTheDocument();
});

test.each([
  [
    "sendbeacon_received",
    "系统已收到页面关闭信号，当前任务已停止。旧任务操作不可恢复，请重新创建研究。",
  ],
  [
    "client_disconnected",
    "当前页面已主动断开连接，任务已停止。旧任务操作不可恢复，请重新创建研究。",
  ],
  [
    "heartbeat_timeout",
    "任务因长时间未收到心跳而停止。旧任务操作不可恢复，请重新创建研究。",
  ],
  [
    "sse_connect_timeout",
    "任务因长时间未建立事件连接而停止。旧任务操作不可恢复，请重新创建研究。",
  ],
  [
    "server_shutdown",
    "服务端连接已中断，当前任务被终止。旧任务操作不可恢复，请重新创建研究。",
  ],
  [
    "risk_control_limit",
    "研究内容触发了平台内容安全策略，当前任务已停止。请调整研究主题后重新创建研究。",
  ],
] satisfies [TerminationReason, string][])(
  "shows mapped terminated detail for %s",
  (terminationDetail, expectedDetail) => {
    const store = createTerminalStoreWithDetail("terminated", terminationDetail);
    renderWithStore(<TerminalBanner />, { store });

    expect(
      screen.getByRole("heading", { level: 2, name: "任务已终止" }),
    ).toBeInTheDocument();
    expect(screen.getByText(expectedDetail)).toBeInTheDocument();
  },
);

test("falls back to generic terminated detail when terminationDetail is missing", () => {
  const store = createTerminalStoreWithDetail("terminated", null);
  renderWithStore(<TerminalBanner />, { store });

  expect(
    screen.getByText("当前任务已停止，旧任务操作不可恢复，请重新创建研究。"),
  ).toBeInTheDocument();
});

test("shows failed message regardless of terminationDetail", () => {
  const store = createTerminalStoreWithDetail("failed");
  renderWithStore(<TerminalBanner />, { store });

  expect(screen.getByText("任务已失败，旧任务操作已禁用。")).toBeInTheDocument();
});
