import type {
  ClarificationDeltaEventEnvelope,
  CreateTaskResponse,
  ErrorResponse,
  EventEnvelope,
  HeartbeatEventEnvelope,
  PhaseChangedEventEnvelope,
  RevisionSummary,
  TaskCreatedEventEnvelope,
  TaskDetailResponse,
  TaskExpiredEventEnvelope,
  TaskFailedEventEnvelope,
  TaskSnapshot,
  TaskTerminatedEventEnvelope,
} from "@/lib/contracts";
import { createResearchSessionState } from "@/features/research/store/research-session-store.types";
import type { ResearchSessionState } from "@/features/research/store/research-session-store.types";

type ResearchSessionStateOverrides = {
  session?: Partial<ResearchSessionState["session"]>;
  remote?: Partial<ResearchSessionState["remote"]>;
  stream?: Partial<ResearchSessionState["stream"]>;
  ui?: Partial<ResearchSessionState["ui"]>;
  deliveryUi?: Partial<ResearchSessionState["deliveryUi"]>;
};

export function makeTaskSnapshot(
  overrides: Partial<TaskSnapshot> = {},
): TaskSnapshot {
  return {
    task_id: "tsk_stage0",
    status: "running",
    phase: "clarifying",
    active_revision_id: "rev_stage0",
    active_revision_number: 1,
    clarification_mode: "natural",
    created_at: "2026-03-13T14:30:00+08:00",
    updated_at: "2026-03-13T14:30:00+08:00",
    expires_at: null,
    available_actions: [],
    ...overrides,
  };
}

export function makeRevisionSummary(
  overrides: Partial<RevisionSummary> = {},
): RevisionSummary {
  return {
    revision_id: "rev_stage0",
    revision_number: 1,
    revision_status: "in_progress",
    started_at: "2026-03-13T14:30:00+08:00",
    finished_at: null,
    requirement_detail: null,
    ...overrides,
  };
}

export function makeTaskDetailResponse(
  overrides: Partial<TaskDetailResponse> = {},
): TaskDetailResponse {
  return {
    task_id: "tsk_stage0",
    snapshot: makeTaskSnapshot(),
    current_revision: makeRevisionSummary(),
    delivery: null,
    ...overrides,
  };
}

export function makeCreateTaskResponse(
  overrides: Partial<CreateTaskResponse> = {},
): CreateTaskResponse {
  return {
    task_id: "tsk_stage0",
    task_token: "secret_stage0",
    trace_id: "trc_stage0",
    snapshot: makeTaskSnapshot(),
    urls: {
      events: "/api/v1/tasks/tsk_stage0/events",
      heartbeat: "/api/v1/tasks/tsk_stage0/heartbeat",
      disconnect: "/api/v1/tasks/tsk_stage0/disconnect",
    },
    connect_deadline_at: "2026-03-13T14:30:10+08:00",
    ...overrides,
  };
}

export function makeValidationErrorResponse(
  overrides: Partial<ErrorResponse> = {},
): ErrorResponse {
  return {
    error: {
      code: "validation_error",
      message: "请求参数不合法。",
      detail: {
        errors: [
          {
            loc: ["body", "initial_query"],
            msg: "研究主题不能为空。",
            type: "value_error",
          },
        ],
      },
      request_id: "req_stage0",
      trace_id: null,
    },
    ...overrides,
  };
}

export function makeResourceBusyErrorResponse(
  overrides: Partial<ErrorResponse> = {},
): ErrorResponse {
  return {
    error: {
      code: "resource_busy",
      message: "当前系统正处理另一项研究，请稍后重试。",
      detail: {},
      request_id: "req_busy",
      trace_id: null,
    },
    ...overrides,
  };
}

export function makeQuotaExceededErrorResponse(
  overrides: Partial<ErrorResponse> = {},
): ErrorResponse {
  return {
    error: {
      code: "ip_quota_exceeded",
      message: "24 小时内创建任务次数已达上限，请稍后再试。",
      detail: {
        quota_limit: 3,
        quota_used: 3,
        next_available_at: "2026-03-14T02:15:00+08:00",
      },
      request_id: "req_quota",
      trace_id: null,
    },
    ...overrides,
  };
}

export function makeTaskCreatedEvent(
  overrides: Partial<TaskCreatedEventEnvelope> = {},
): TaskCreatedEventEnvelope {
  return {
    seq: 1,
    event: "task.created",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "clarifying",
    timestamp: "2026-03-13T14:30:00+08:00",
    payload: {
      snapshot: makeTaskSnapshot(overrides.payload?.snapshot),
    },
    ...overrides,
  };
}

export function makePhaseChangedEvent(
  overrides: Partial<PhaseChangedEventEnvelope> = {},
): PhaseChangedEventEnvelope {
  return {
    seq: 2,
    event: "phase.changed",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "analyzing_requirement",
    timestamp: "2026-03-13T14:31:11+08:00",
    payload: {
      from_phase: "clarifying",
      to_phase: "analyzing_requirement",
      status: "running",
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makeHeartbeatEvent(
  overrides: Partial<HeartbeatEventEnvelope> = {},
): HeartbeatEventEnvelope {
  return {
    seq: 3,
    event: "heartbeat",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "analyzing_requirement",
    timestamp: "2026-03-13T14:35:30+08:00",
    payload: {
      server_time: "2026-03-13T14:35:30+08:00",
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makeTaskFailedEvent(
  overrides: Partial<TaskFailedEventEnvelope> = {},
): TaskFailedEventEnvelope {
  return {
    seq: 4,
    event: "task.failed",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "writing_report",
    timestamp: "2026-03-13T14:45:00+08:00",
    payload: {
      error: {
        code: "upstream_service_error",
        message: "上游服务异常",
      },
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makeTaskTerminatedEvent(
  overrides: Partial<TaskTerminatedEventEnvelope> = {},
): TaskTerminatedEventEnvelope {
  return {
    seq: 5,
    event: "task.terminated",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "writing_report",
    timestamp: "2026-03-13T14:45:10+08:00",
    payload: {
      reason: "client_disconnected",
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makeTaskExpiredEvent(
  overrides: Partial<TaskExpiredEventEnvelope> = {},
): TaskExpiredEventEnvelope {
  return {
    seq: 6,
    event: "task.expired",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "delivered",
    timestamp: "2026-03-13T15:25:00+08:00",
    payload: {
      expired_at: "2026-03-13T15:25:00+08:00",
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makeClarificationDeltaEvent(
  overrides: Partial<ClarificationDeltaEventEnvelope> = {},
): ClarificationDeltaEventEnvelope {
  return {
    seq: 7,
    event: "clarification.delta",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "clarifying",
    timestamp: "2026-03-13T14:30:30+08:00",
    payload: {
      delta: "1. 请确认你更想关注行业现状还是竞争格局。",
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makeResearchSessionState(
  overrides: ResearchSessionStateOverrides = {},
): ResearchSessionState {
  const baseState = createResearchSessionState();
  const createTaskOverrides = overrides.ui?.createTask ?? {};

  return {
    session: {
      ...baseState.session,
      ...overrides.session,
    },
    remote: {
      ...baseState.remote,
      snapshot: overrides.remote?.snapshot ?? makeTaskSnapshot(),
      currentRevision:
        overrides.remote?.currentRevision ?? baseState.remote.currentRevision,
      delivery: overrides.remote?.delivery ?? baseState.remote.delivery,
      ...overrides.remote,
    },
    stream: {
      ...baseState.stream,
      ...overrides.stream,
    },
    ui: {
      ...baseState.ui,
      ...overrides.ui,
      createTask: {
        ...baseState.ui.createTask,
        ...createTaskOverrides,
      },
    },
    deliveryUi: {
      ...baseState.deliveryUi,
      ...overrides.deliveryUi,
    },
  };
}

export function makeEventEnvelopeFixtureSet(): EventEnvelope[] {
  return [
    makeTaskCreatedEvent(),
    makePhaseChangedEvent(),
    makeHeartbeatEvent(),
    makeTaskFailedEvent(),
    makeTaskTerminatedEvent(),
    makeTaskExpiredEvent(),
    makeClarificationDeltaEvent(),
  ];
}
