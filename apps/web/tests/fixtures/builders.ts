import type {
  AnalysisCompletedEventEnvelope,
  AnalysisDeltaEventEnvelope,
  ClarificationDeltaEventEnvelope,
  ClarificationFallbackToNaturalEventEnvelope,
  ClarificationNaturalReadyEventEnvelope,
  ClarificationOptionsReadyEventEnvelope,
  ClarificationCountdownStartedEventEnvelope,
  ClarificationAcceptedResponse,
  CollectorCompletedEventEnvelope,
  CollectorFetchCompletedEventEnvelope,
  CollectorFetchStartedEventEnvelope,
  CollectorReasoningDeltaEventEnvelope,
  CollectorSearchCompletedEventEnvelope,
  CollectorSearchStartedEventEnvelope,
  CreateTaskResponse,
  ErrorResponse,
  EventEnvelope,
  HeartbeatEventEnvelope,
  OutlineDeltaEventEnvelope,
  PlannerReasoningDeltaEventEnvelope,
  PlannerToolCallRequestedEventEnvelope,
  PhaseChangedEventEnvelope,
  RevisionSummary,
  SourcesMergedEventEnvelope,
  SummaryCompletedEventEnvelope,
  TaskCreatedEventEnvelope,
  TaskDetailResponse,
  TaskExpiredEventEnvelope,
  TaskFailedEventEnvelope,
  TaskSnapshot,
  TaskTerminatedEventEnvelope,
} from "@/lib/contracts";
import { createResearchSessionState } from "@/features/research/store/research-session-store.types";
import type {
  ResearchSessionState,
  TimelineItem,
} from "@/features/research/store/research-session-store.types";

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
    connect_deadline_at: new Date(Date.now() + 60_000).toISOString(),
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

export function makeClarificationValidationErrorResponse(
  overrides: Partial<ErrorResponse> = {},
): ErrorResponse {
  return {
    error: {
      code: "validation_error",
      message: "请求参数不合法。",
      detail: {
        errors: [
          {
            loc: ["body", "answer_text"],
            msg: "回答内容不能为空。",
            type: "value_error",
          },
        ],
      },
      request_id: "req_clarification_validation",
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

export function makeClarificationNaturalReadyEvent(
  overrides: Partial<ClarificationNaturalReadyEventEnvelope> = {},
): ClarificationNaturalReadyEventEnvelope {
  return {
    seq: 8,
    event: "clarification.natural.ready",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "clarifying",
    timestamp: "2026-03-13T14:30:35+08:00",
    payload: {
      status: "awaiting_user_input",
      available_actions: ["submit_clarification"],
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makeClarificationOptionsReadyEvent(
  overrides: Partial<ClarificationOptionsReadyEventEnvelope> = {},
): ClarificationOptionsReadyEventEnvelope {
  return {
    seq: 9,
    event: "clarification.options.ready",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "clarifying",
    timestamp: "2026-03-13T14:30:35+08:00",
    payload: {
      status: "awaiting_user_input",
      available_actions: ["submit_clarification"],
      question_set: {
        questions: [
          {
            question_id: "q_1",
            question: "这次研究更偏向哪个方向？",
            options: [
              { option_id: "o_1", label: "行业现状与趋势" },
              { option_id: "o_2", label: "主要参与者与格局" },
              { option_id: "o_auto", label: "自动" },
            ],
          },
        ],
      },
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makeClarificationCountdownStartedEvent(
  overrides: Partial<ClarificationCountdownStartedEventEnvelope> = {},
): ClarificationCountdownStartedEventEnvelope {
  return {
    seq: 10,
    event: "clarification.countdown.started",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "clarifying",
    timestamp: "2026-03-13T14:30:36+08:00",
    payload: {
      duration_seconds: 15,
      started_at: "2026-03-13T14:30:36+08:00",
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makeClarificationFallbackToNaturalEvent(
  overrides: Partial<ClarificationFallbackToNaturalEventEnvelope> = {},
): ClarificationFallbackToNaturalEventEnvelope {
  return {
    seq: 11,
    event: "clarification.fallback_to_natural",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "clarifying",
    timestamp: "2026-03-13T14:30:40+08:00",
    payload: {
      reason: "parse_failed",
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makeAnalysisDeltaEvent(
  overrides: Partial<AnalysisDeltaEventEnvelope> = {},
): AnalysisDeltaEventEnvelope {
  return {
    seq: 12,
    event: "analysis.delta",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "analyzing_requirement",
    timestamp: "2026-03-13T14:31:15+08:00",
    payload: {
      delta: '{\n  "研究目标": "分析中国 AI 搜索产品竞争格局"',
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makeAnalysisCompletedEvent(
  overrides: Partial<AnalysisCompletedEventEnvelope> = {},
): AnalysisCompletedEventEnvelope {
  return {
    seq: 13,
    event: "analysis.completed",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "analyzing_requirement",
    timestamp: "2026-03-13T14:31:20+08:00",
    payload: {
      requirement_detail: {
        research_goal: "分析中国 AI 搜索产品竞争格局",
        domain: "互联网 / AI 产品",
        requirement_details: "聚焦中国市场，偏商业分析，覆盖近两年变化。",
        output_format: "business_report",
        freshness_requirement: "high",
        language: "zh-CN",
      },
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makePlannerReasoningDeltaEvent(
  overrides: Partial<PlannerReasoningDeltaEventEnvelope> = {},
): PlannerReasoningDeltaEventEnvelope {
  return {
    seq: 14,
    event: "planner.reasoning.delta",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "planning_collection",
    timestamp: "2026-03-13T14:32:00+08:00",
    payload: {
      delta: "当前还缺少代表性玩家与市场趋势信息。",
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makePlannerToolCallRequestedEvent(
  overrides: Partial<PlannerToolCallRequestedEventEnvelope> = {},
): PlannerToolCallRequestedEventEnvelope {
  return {
    seq: 15,
    event: "planner.tool_call.requested",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "planning_collection",
    timestamp: "2026-03-13T14:32:05+08:00",
    payload: {
      tool_call_id: "call_ai_search",
      collect_target: "收集 2024-2026 年中国 AI 搜索产品的主要厂商与公开进展",
      additional_info: "优先官方发布与高可信媒体。",
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makeCollectorReasoningDeltaEvent(
  overrides: Partial<CollectorReasoningDeltaEventEnvelope> = {},
): CollectorReasoningDeltaEventEnvelope {
  return {
    seq: 16,
    event: "collector.reasoning.delta",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "collecting",
    timestamp: "2026-03-13T14:32:10+08:00",
    payload: {
      subtask_id: "sub_ai_search",
      tool_call_id: "call_ai_search",
      delta: "先做高时效搜索，再读取官方来源。",
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makeCollectorSearchStartedEvent(
  overrides: Partial<CollectorSearchStartedEventEnvelope> = {},
): CollectorSearchStartedEventEnvelope {
  return {
    seq: 17,
    event: "collector.search.started",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "collecting",
    timestamp: "2026-03-13T14:32:12+08:00",
    payload: {
      subtask_id: "sub_ai_search",
      tool_call_id: "call_ai_search",
      search_query: "中国 AI 搜索 产品 2025",
      search_recency_filter: "noLimit",
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makeCollectorSearchCompletedEvent(
  overrides: Partial<CollectorSearchCompletedEventEnvelope> = {},
): CollectorSearchCompletedEventEnvelope {
  return {
    seq: 18,
    event: "collector.search.completed",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "collecting",
    timestamp: "2026-03-13T14:32:16+08:00",
    payload: {
      subtask_id: "sub_ai_search",
      tool_call_id: "call_ai_search",
      search_query: "中国 AI 搜索 产品 2025",
      result_count: 10,
      titles: ["某公司发布会回顾", "2025 中国 AI 搜索市场观察"],
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makeCollectorFetchStartedEvent(
  overrides: Partial<CollectorFetchStartedEventEnvelope> = {},
): CollectorFetchStartedEventEnvelope {
  return {
    seq: 19,
    event: "collector.fetch.started",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "collecting",
    timestamp: "2026-03-13T14:32:20+08:00",
    payload: {
      subtask_id: "sub_ai_search",
      tool_call_id: "call_ai_search",
      url: "https://example.com/article",
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makeCollectorFetchCompletedEvent(
  overrides: Partial<CollectorFetchCompletedEventEnvelope> = {},
): CollectorFetchCompletedEventEnvelope {
  return {
    seq: 20,
    event: "collector.fetch.completed",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "collecting",
    timestamp: "2026-03-13T14:32:23+08:00",
    payload: {
      subtask_id: "sub_ai_search",
      tool_call_id: "call_ai_search",
      url: "https://example.com/article",
      success: true,
      title: "某公司发布会回顾",
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makeCollectorCompletedEvent(
  overrides: Partial<CollectorCompletedEventEnvelope> = {},
): CollectorCompletedEventEnvelope {
  return {
    seq: 21,
    event: "collector.completed",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "collecting",
    timestamp: "2026-03-13T14:32:30+08:00",
    payload: {
      subtask_id: "sub_ai_search",
      tool_call_id: "call_ai_search",
      status: "completed",
      item_count: 4,
      search_queries: [
        "中国 AI 搜索 产品 2025",
        "AI 搜索 中国 厂商 2024 2026",
      ],
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makeSummaryCompletedEvent(
  overrides: Partial<SummaryCompletedEventEnvelope> = {},
): SummaryCompletedEventEnvelope {
  return {
    seq: 22,
    event: "summary.completed",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "summarizing_collection",
    timestamp: "2026-03-13T14:32:40+08:00",
    payload: {
      subtask_id: "sub_ai_search",
      tool_call_id: "call_ai_search",
      collect_target: "收集 2024-2026 年中国 AI 搜索产品的主要厂商与公开进展",
      status: "completed",
      search_queries: ["中国 AI 搜索 产品 2025"],
      key_findings_markdown:
        "- 官方披露更多集中在 2025 年后。\n- 已出现多个垂直场景产品。",
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makeSourcesMergedEvent(
  overrides: Partial<SourcesMergedEventEnvelope> = {},
): SourcesMergedEventEnvelope {
  return {
    seq: 23,
    event: "sources.merged",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "merging_sources",
    timestamp: "2026-03-13T14:32:50+08:00",
    payload: {
      source_count_before_merge: 18,
      source_count_after_merge: 11,
      reference_count: 11,
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makeOutlineDeltaEvent(
  overrides: Partial<OutlineDeltaEventEnvelope> = {},
): OutlineDeltaEventEnvelope {
  return {
    seq: 24,
    event: "outline.delta",
    task_id: "tsk_stage0",
    revision_id: "rev_stage0",
    phase: "preparing_outline",
    timestamp: "2026-03-13T14:33:10+08:00",
    payload: {
      delta: '{\n  "research_outline": {',
      ...overrides.payload,
    },
    ...overrides,
  };
}

export function makeClarificationAcceptedResponse(
  overrides: Partial<ClarificationAcceptedResponse> = {},
): ClarificationAcceptedResponse {
  return {
    accepted: true,
    snapshot: makeTaskSnapshot({
      status: "running",
      phase: "analyzing_requirement",
      updated_at: "2026-03-13T14:31:10+08:00",
      available_actions: [],
    }),
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

export function makeTimelineItem(
  overrides: Partial<TimelineItem> = {},
): TimelineItem {
  return {
    id: "timeline_stage5",
    revisionId: "rev_stage0",
    kind: "system",
    label: "正在分析你的研究需求",
    status: "running",
    occurredAt: "2026-03-13T14:31:15+08:00",
    ...overrides,
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
    makeClarificationNaturalReadyEvent(),
    makeClarificationOptionsReadyEvent(),
    makeClarificationCountdownStartedEvent(),
    makeClarificationFallbackToNaturalEvent(),
    makeAnalysisDeltaEvent(),
    makeAnalysisCompletedEvent(),
    makePlannerReasoningDeltaEvent(),
    makePlannerToolCallRequestedEvent(),
    makeCollectorReasoningDeltaEvent(),
    makeCollectorSearchStartedEvent(),
    makeCollectorSearchCompletedEvent(),
    makeCollectorFetchStartedEvent(),
    makeCollectorFetchCompletedEvent(),
    makeCollectorCompletedEvent(),
    makeSummaryCompletedEvent(),
    makeSourcesMergedEvent(),
    makeOutlineDeltaEvent(),
    makeClarificationDeltaEvent(),
  ];
}
