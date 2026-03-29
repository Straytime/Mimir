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

  expect(screen.getByText("任务因内容安全审查被终止")).toBeInTheDocument();
  expect(
    screen.getByText("研究内容触发了平台内容安全策略，当前任务已停止。请调整研究主题后重试。"),
  ).toBeInTheDocument();
});

test("shows generic terminated message when terminationDetail is 'client_disconnected'", () => {
  const store = createTerminalStoreWithDetail("terminated", "client_disconnected");
  renderWithStore(<TerminalBanner />, { store });

  expect(screen.getByText("任务已终止，旧任务操作已禁用。")).toBeInTheDocument();
});

test("shows failed message regardless of terminationDetail", () => {
  const store = createTerminalStoreWithDetail("failed");
  renderWithStore(<TerminalBanner />, { store });

  expect(screen.getByText("任务已失败，旧任务操作已禁用。")).toBeInTheDocument();
});
