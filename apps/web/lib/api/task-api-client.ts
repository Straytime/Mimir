import type {
  AcceptedResponse,
  ClarificationAcceptedResponse,
  ClarificationSubmission,
  CreateTaskRequest,
  CreateTaskResponse,
  DisconnectRequestReason,
  ErrorResponse,
  FeedbackAcceptedResponse,
  FeedbackRequest,
  HeartbeatRequest,
  TaskDetailResponse,
  ValidationErrorItem,
} from "@/lib/contracts";
import {
  normalizeDeliverySummary,
  normalizeTaskUrls,
  resolveApiBaseUrl,
  resolveApiUrl,
} from "@/lib/api/backend-url";

export type CreateTaskResult = {
  response: CreateTaskResponse;
  requestId: string | null;
  traceId: string | null;
};

export type RequestMetadata = {
  requestId: string | null;
  traceId: string | null;
};

export type TaskDetailResult = TaskDetailResponse & RequestMetadata;

export type TaskApiClient = {
  createTask: (request: CreateTaskRequest) => Promise<CreateTaskResult>;
  getTaskDetail: (args: {
    taskId: string;
    token: string;
  }) => Promise<TaskDetailResult>;
  submitClarification: (args: {
    taskId: string;
    token: string;
    request: ClarificationSubmission;
  }) => Promise<ClarificationAcceptedResponse & RequestMetadata>;
  submitFeedback: (args: {
    taskId: string;
    token: string;
    request: FeedbackRequest;
  }) => Promise<FeedbackAcceptedResponse & RequestMetadata>;
  sendHeartbeat: (args: {
    url: string;
    token: string;
    request: HeartbeatRequest;
  }) => Promise<RequestMetadata>;
  disconnectTask: (args: {
    url: string;
    token: string;
    reason: DisconnectRequestReason;
  }) => Promise<AcceptedResponse & RequestMetadata>;
};

type TaskApiClientErrorArgs = {
  status: number;
  code: string;
  message: string;
  detail: Record<string, unknown>;
  requestId: string | null;
  traceId: string | null;
  retryAfterSeconds: number | null;
};

export class TaskApiClientError extends Error {
  readonly status: number;
  readonly code: string;
  readonly detail: Record<string, unknown>;
  readonly requestId: string | null;
  readonly traceId: string | null;
  readonly retryAfterSeconds: number | null;

  constructor(args: TaskApiClientErrorArgs) {
    super(args.message);
    this.name = "TaskApiClientError";
    this.status = args.status;
    this.code = args.code;
    this.detail = args.detail;
    this.requestId = args.requestId;
    this.traceId = args.traceId;
    this.retryAfterSeconds = args.retryAfterSeconds;
  }
}

type FetchTaskApiClientOptions = {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
};

type ParsedResponse = {
  requestId: string | null;
  traceId: string | null;
  responseJson: unknown;
};

function resolveRequestUrl(baseUrl: string, url: string) {
  return resolveApiUrl(url, baseUrl);
}

async function parseResponse(response: Response): Promise<ParsedResponse> {
  const requestId = response.headers.get("x-request-id");
  const traceId = response.headers.get("x-trace-id");
  const responseText = await response.text();

  return {
    requestId,
    traceId,
    responseJson: responseText.length > 0 ? JSON.parse(responseText) : null,
  };
}

function parseRetryAfterSeconds(headerValue: string | null): number | null {
  if (headerValue === null) {
    return null;
  }

  const parsed = Number(headerValue);

  return Number.isFinite(parsed) ? parsed : null;
}

function isErrorResponse(value: unknown): value is ErrorResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  return "error" in value;
}

function ensureOkResponse(
  response: Response,
  parsedResponse: ParsedResponse,
): ParsedResponse {
  if (response.ok) {
    return parsedResponse;
  }

  const errorResponse = isErrorResponse(parsedResponse.responseJson)
    ? parsedResponse.responseJson
    : {
        error: {
          code: "unknown",
          message: "请求失败。",
          detail: {},
          request_id: parsedResponse.requestId,
          trace_id: parsedResponse.traceId,
        },
      };

  throw new TaskApiClientError({
    status: response.status,
    code: errorResponse.error.code,
    message: errorResponse.error.message,
    detail: errorResponse.error.detail,
    requestId: errorResponse.error.request_id,
    traceId: errorResponse.error.trace_id,
    retryAfterSeconds: parseRetryAfterSeconds(
      response.headers.get("retry-after"),
    ),
  });
}

export function isValidationErrorItemArray(
  value: unknown,
): value is ValidationErrorItem[] {
  return Array.isArray(value);
}

export function createFetchTaskApiClient(
  options: FetchTaskApiClientOptions = {},
): TaskApiClient {
  const fetchImpl = options.fetchImpl ?? fetch;
  const baseUrl = resolveApiBaseUrl(options.baseUrl ?? "");

  return {
    async createTask(request: CreateTaskRequest) {
      const response = await fetchImpl(resolveRequestUrl(baseUrl, "/api/v1/tasks"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(request),
      });
      const parsedResponse = ensureOkResponse(response, await parseResponse(response));
      const successResponse = parsedResponse.responseJson as CreateTaskResponse;
      const normalizedResponse: CreateTaskResponse = {
        ...successResponse,
        urls: normalizeTaskUrls(successResponse.urls, baseUrl),
      };

      return {
        response: normalizedResponse,
        requestId: parsedResponse.requestId,
        traceId: parsedResponse.traceId,
      };
    },

    async getTaskDetail({ taskId, token }) {
      const response = await fetchImpl(
        resolveRequestUrl(baseUrl, `/api/v1/tasks/${taskId}`),
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: "application/json",
          },
        },
      );
      const parsedResponse = ensureOkResponse(response, await parseResponse(response));
      const successResponse = parsedResponse.responseJson as TaskDetailResponse;
      const normalizedResponse: TaskDetailResponse = {
        ...successResponse,
        delivery:
          successResponse.delivery === null
            ? null
            : normalizeDeliverySummary(successResponse.delivery, baseUrl),
      };

      return {
        ...normalizedResponse,
        requestId: parsedResponse.requestId,
        traceId: parsedResponse.traceId,
      };
    },

    async submitClarification({ taskId, token, request }) {
      const response = await fetchImpl(
        resolveRequestUrl(baseUrl, `/api/v1/tasks/${taskId}/clarification`),
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify(request),
        },
      );
      const parsedResponse = ensureOkResponse(response, await parseResponse(response));
      const successResponse =
        parsedResponse.responseJson as ClarificationAcceptedResponse;

      return {
        ...successResponse,
        requestId: parsedResponse.requestId,
        traceId: parsedResponse.traceId,
      };
    },

    async submitFeedback({ taskId, token, request }) {
      const response = await fetchImpl(
        resolveRequestUrl(baseUrl, `/api/v1/tasks/${taskId}/feedback`),
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify(request),
        },
      );
      const parsedResponse = ensureOkResponse(response, await parseResponse(response));
      const successResponse = parsedResponse.responseJson as FeedbackAcceptedResponse;

      return {
        ...successResponse,
        requestId: parsedResponse.requestId,
        traceId: parsedResponse.traceId,
      };
    },

    async sendHeartbeat({ url, token, request }) {
      const response = await fetchImpl(resolveRequestUrl(baseUrl, url), {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
      });
      const parsedResponse = ensureOkResponse(response, await parseResponse(response));

      return {
        requestId: parsedResponse.requestId,
        traceId: parsedResponse.traceId,
      };
    },

    async disconnectTask({ url, token, reason }) {
      const response = await fetchImpl(resolveRequestUrl(baseUrl, url), {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          reason,
        }),
      });
      const parsedResponse = ensureOkResponse(response, await parseResponse(response));

      return {
        accepted: (parsedResponse.responseJson as AcceptedResponse | null)?.accepted ?? true,
        requestId: parsedResponse.requestId,
        traceId: parsedResponse.traceId,
      };
    },
  };
}
