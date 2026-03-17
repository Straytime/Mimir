import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { createFetchTaskApiClient } from "@/lib/api/task-api-client";

/**
 * Tests for resolveBaseUrl logic inside createFetchTaskApiClient.
 *
 * The resolve order is:
 *   1. Explicit baseUrl option
 *   2. NEXT_PUBLIC_API_BASE_URL env var
 *   3. window.location.origin (browser)
 *   4. "http://localhost" (server-side fallback)
 */
describe("resolveBaseUrl", () => {
  const originalEnv = process.env.NEXT_PUBLIC_API_BASE_URL;

  beforeEach(() => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
  });

  afterEach(() => {
    if (originalEnv !== undefined) {
      process.env.NEXT_PUBLIC_API_BASE_URL = originalEnv;
    } else {
      delete process.env.NEXT_PUBLIC_API_BASE_URL;
    }
  });

  it("uses explicit baseUrl option when provided", async () => {
    const mockFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ task_id: "t1", task_token: "tok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const client = createFetchTaskApiClient({
      baseUrl: "http://explicit:9999",
      fetchImpl: mockFetch,
    });

    await client.createTask({ initial_query: "test", config: { clarification_mode: "natural" }, client: { timezone: "UTC", locale: "en" } });

    expect(mockFetch).toHaveBeenCalledWith(
      "http://explicit:9999/api/v1/tasks",
      expect.any(Object),
    );
  });

  it("uses NEXT_PUBLIC_API_BASE_URL env var when no explicit baseUrl", async () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://env-api:8000";

    const mockFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ task_id: "t1", task_token: "tok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const client = createFetchTaskApiClient({ fetchImpl: mockFetch });

    await client.createTask({ initial_query: "test", config: { clarification_mode: "natural" }, client: { timezone: "UTC", locale: "en" } });

    expect(mockFetch).toHaveBeenCalledWith(
      "http://env-api:8000/api/v1/tasks",
      expect.any(Object),
    );
  });

  it("falls back to window.location.origin when env var is not set", async () => {
    const mockFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ task_id: "t1", task_token: "tok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const client = createFetchTaskApiClient({ fetchImpl: mockFetch });

    await client.createTask({ initial_query: "test", config: { clarification_mode: "natural" }, client: { timezone: "UTC", locale: "en" } });

    // jsdom window.location.origin is "http://localhost"
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/tasks"),
      expect.any(Object),
    );
  });
});
