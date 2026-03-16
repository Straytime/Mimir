export const TASK_STATUSES = [
  "running",
  "awaiting_user_input",
  "awaiting_feedback",
  "terminated",
  "failed",
  "expired",
  "purged",
] as const;

export const TASK_PHASES = [
  "clarifying",
  "analyzing_requirement",
  "planning_collection",
  "collecting",
  "summarizing_collection",
  "merging_sources",
  "preparing_outline",
  "writing_report",
  "delivered",
  "processing_feedback",
] as const;

export const CLARIFICATION_MODES = ["natural", "options"] as const;

export const OUTPUT_FORMATS = [
  "general",
  "research_report",
  "business_report",
  "academic_paper",
  "deep_article",
  "guide",
  "shopping_recommendation",
] as const;

export const FRESHNESS_REQUIREMENTS = ["high", "normal"] as const;

export const AVAILABLE_ACTIONS = [
  "submit_clarification",
  "submit_feedback",
  "download_markdown",
  "download_pdf",
] as const;

export const REVISION_STATUSES = [
  "in_progress",
  "completed",
  "failed",
  "terminated",
] as const;

export const TERMINAL_TASK_STATUSES = [
  "terminated",
  "failed",
  "expired",
] as const;

export const TERMINATION_REASONS = [
  "client_disconnected",
  "heartbeat_timeout",
  "sendbeacon_received",
  "risk_control_limit",
  "sse_connect_timeout",
  "server_shutdown",
] as const;

export const DISCONNECT_REQUEST_REASONS = [
  "pagehide",
  "beforeunload",
  "client_manual_abort",
  "network_lost",
] as const;

export type IsoDateTimeString = string;

export type TaskStatus = (typeof TASK_STATUSES)[number];
export type TaskPhase = (typeof TASK_PHASES)[number];
export type ClarificationMode = (typeof CLARIFICATION_MODES)[number];
export type OutputFormat = (typeof OUTPUT_FORMATS)[number];
export type FreshnessRequirement = (typeof FRESHNESS_REQUIREMENTS)[number];
export type AvailableAction = (typeof AVAILABLE_ACTIONS)[number];
export type RevisionStatus = (typeof REVISION_STATUSES)[number];
export type TerminalTaskStatus = (typeof TERMINAL_TASK_STATUSES)[number];
export type TerminationReason = (typeof TERMINATION_REASONS)[number];
export type DisconnectRequestReason =
  (typeof DISCONNECT_REQUEST_REASONS)[number];

export type RequirementDetail = {
  research_goal: string;
  domain: string;
  requirement_details: string;
  output_format: OutputFormat;
  freshness_requirement: FreshnessRequirement;
  language: string;
  raw_llm_output?: Record<string, unknown> | null;
};

export type RevisionSummary = {
  revision_id: string;
  revision_number: number;
  revision_status: RevisionStatus;
  started_at: IsoDateTimeString;
  finished_at: IsoDateTimeString | null;
  requirement_detail: RequirementDetail | null;
};

export type TaskSnapshot = {
  task_id: string;
  status: TaskStatus;
  phase: TaskPhase;
  active_revision_id: string;
  active_revision_number: number;
  clarification_mode: ClarificationMode;
  created_at: IsoDateTimeString;
  updated_at: IsoDateTimeString;
  expires_at: IsoDateTimeString | null;
  available_actions: AvailableAction[];
};

export type ClarificationQuestionOption = {
  option_id: string;
  label: string;
};

export type ClarificationQuestion = {
  question_id: string;
  question: string;
  options: ClarificationQuestionOption[];
};

export type ClarificationQuestionSet = {
  questions: ClarificationQuestion[];
};

export type ClarificationOptionAnswer = {
  question_id: string;
  selected_option_id: string;
  selected_label: string;
};

export type ArtifactSummary = {
  artifact_id: string;
  filename: string;
  mime_type: string;
  url: string;
  access_expires_at: IsoDateTimeString;
};

export type DeliverySummary = {
  revision_id: string;
  revision_number: number;
  word_count: number;
  artifact_count: number;
  markdown_zip_url: string;
  pdf_url: string;
  artifacts: ArtifactSummary[];
};

export type TaskDetailResponse = {
  task_id: string;
  snapshot: TaskSnapshot;
  current_revision: RevisionSummary;
  delivery: DeliverySummary | null;
};

export type ResearchConfig = {
  clarification_mode: ClarificationMode;
};

export type TaskClientInfo = {
  timezone: string;
  locale?: string;
};

export type CreateTaskRequest = {
  initial_query: string;
  config: ResearchConfig;
  client: TaskClientInfo;
};

export type TaskUrls = {
  events: string;
  heartbeat: string;
  disconnect: string;
};

export type CreateTaskResponse = {
  task_id: string;
  task_token: string;
  trace_id: string;
  snapshot: TaskSnapshot;
  urls: TaskUrls;
  connect_deadline_at: IsoDateTimeString;
};

export type HeartbeatRequest = {
  client_time: IsoDateTimeString;
};

export type NaturalClarificationSubmission = {
  mode: "natural";
  answer_text: string;
};

export type OptionsClarificationSubmission = {
  mode: "options";
  submitted_by_timeout: boolean;
  answers: ClarificationOptionAnswer[];
};

export type ClarificationSubmission =
  | NaturalClarificationSubmission
  | OptionsClarificationSubmission;

export type DisconnectRequest = {
  reason: DisconnectRequestReason;
  task_token?: string;
};

export type AcceptedResponse = {
  accepted: true;
};

export type ClarificationAcceptedResponse = AcceptedResponse & {
  snapshot: TaskSnapshot;
};

export type ApiError = {
  code: string;
  message: string;
  detail: Record<string, unknown>;
  request_id: string | null;
  trace_id: string | null;
};

export type ErrorResponse = {
  error: ApiError;
};

export type ValidationErrorItem = {
  type?: string;
  loc: Array<string | number>;
  msg: string;
  input?: unknown;
  ctx?: Record<string, unknown>;
};

export type BaseEventEnvelope<
  TEvent extends string,
  TPayload extends Record<string, unknown>,
> = {
  seq: number;
  event: TEvent;
  task_id: string;
  revision_id: string | null;
  phase: TaskPhase;
  timestamp: IsoDateTimeString;
  payload: TPayload;
};

export type TaskCreatedPayload = {
  snapshot: TaskSnapshot;
};

export type PhaseChangedPayload = {
  from_phase: TaskPhase;
  to_phase: TaskPhase;
  status: TaskStatus;
};

export type HeartbeatPayload = {
  server_time: IsoDateTimeString;
};

export type TaskFailedPayload = {
  error: {
    code: string;
    message: string;
  };
};

export type TaskTerminatedPayload = {
  reason: TerminationReason;
};

export type TaskExpiredPayload = {
  expired_at: IsoDateTimeString;
};

export type ClarificationDeltaPayload = {
  delta: string;
};

export type ClarificationReadyPayload = {
  status: Extract<TaskStatus, "awaiting_user_input">;
  available_actions: AvailableAction[];
};

export type ClarificationOptionsReadyPayload = ClarificationReadyPayload & {
  question_set: ClarificationQuestionSet;
};

export type ClarificationCountdownStartedPayload = {
  duration_seconds: number;
  started_at: IsoDateTimeString;
};

export type ClarificationFallbackToNaturalPayload = {
  reason: "parse_failed";
};

export type AnalysisDeltaPayload = {
  delta: string;
};

export type AnalysisCompletedPayload = {
  requirement_detail: RequirementDetail;
};

export type TaskCreatedEventEnvelope = BaseEventEnvelope<
  "task.created",
  TaskCreatedPayload
>;

export type PhaseChangedEventEnvelope = BaseEventEnvelope<
  "phase.changed",
  PhaseChangedPayload
>;

export type HeartbeatEventEnvelope = BaseEventEnvelope<
  "heartbeat",
  HeartbeatPayload
>;

export type TaskFailedEventEnvelope = BaseEventEnvelope<
  "task.failed",
  TaskFailedPayload
>;

export type TaskTerminatedEventEnvelope = BaseEventEnvelope<
  "task.terminated",
  TaskTerminatedPayload
>;

export type TaskExpiredEventEnvelope = BaseEventEnvelope<
  "task.expired",
  TaskExpiredPayload
>;

export type ClarificationDeltaEventEnvelope = BaseEventEnvelope<
  "clarification.delta",
  ClarificationDeltaPayload
>;

export type ClarificationNaturalReadyEventEnvelope = BaseEventEnvelope<
  "clarification.natural.ready",
  ClarificationReadyPayload
>;

export type ClarificationOptionsReadyEventEnvelope = BaseEventEnvelope<
  "clarification.options.ready",
  ClarificationOptionsReadyPayload
>;

export type ClarificationCountdownStartedEventEnvelope = BaseEventEnvelope<
  "clarification.countdown.started",
  ClarificationCountdownStartedPayload
>;

export type ClarificationFallbackToNaturalEventEnvelope = BaseEventEnvelope<
  "clarification.fallback_to_natural",
  ClarificationFallbackToNaturalPayload
>;

export type AnalysisDeltaEventEnvelope = BaseEventEnvelope<
  "analysis.delta",
  AnalysisDeltaPayload
>;

export type AnalysisCompletedEventEnvelope = BaseEventEnvelope<
  "analysis.completed",
  AnalysisCompletedPayload
>;

export type EventEnvelope =
  | TaskCreatedEventEnvelope
  | PhaseChangedEventEnvelope
  | HeartbeatEventEnvelope
  | TaskFailedEventEnvelope
  | TaskTerminatedEventEnvelope
  | TaskExpiredEventEnvelope
  | ClarificationDeltaEventEnvelope
  | ClarificationNaturalReadyEventEnvelope
  | ClarificationOptionsReadyEventEnvelope
  | ClarificationCountdownStartedEventEnvelope
  | ClarificationFallbackToNaturalEventEnvelope
  | AnalysisDeltaEventEnvelope
  | AnalysisCompletedEventEnvelope;
