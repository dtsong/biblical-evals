import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  configApi,
  evaluationsApi,
  questionsApi,
  reportsApi,
  reviewsApi,
} from "./api";

describe("api client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("throws when auth token is missing", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url === "/api/auth/token") {
          return {
            ok: false,
            json: async () => ({ error: "Not authenticated" }),
          };
        }
        return {
          ok: true,
          json: async () => [],
        };
      })
    );

    await expect(evaluationsApi.list()).rejects.toMatchObject({
      message: "Not authenticated",
      status: 401,
    });
  });

  it("passes bearer token and body for authenticated POST", async () => {
    const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
      if (url === "/api/auth/token") {
        return {
          ok: true,
          json: async () => ({ token: "jwt-123" }),
        };
      }
      return {
        ok: true,
        json: async () => ({ message: "ok", count: 1 }),
      };
    });
    vi.stubGlobal("fetch", fetchMock);

    const payload = [{ dimension: "accuracy", value: 5, comment: "great" }];
    await reviewsApi.submit("resp-1", payload);

    const secondCall = fetchMock.mock.calls[1];
    expect(secondCall?.[0]).toMatch(/\/api\/v1\/reviews$/);
    const options = secondCall?.[1] as RequestInit;
    const headers = options.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer jwt-123");
    expect(headers["Content-Type"]).toBe("application/json");
    expect(options.body).toContain("resp-1");
  });

  it("uses backend error detail when response is not ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url === "/api/auth/token") {
          return {
            ok: true,
            json: async () => ({ token: "jwt-123" }),
          };
        }
        return {
          ok: false,
          status: 500,
          statusText: "Internal Server Error",
          json: async () => ({ detail: "backend exploded" }),
        };
      })
    );

    await expect(configApi.dimensions()).rejects.toMatchObject({
      message: "backend exploded",
      status: 500,
    });
  });

  it("supports all typed endpoint helpers", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (url === "/api/auth/token") {
        return {
          ok: true,
          json: async () => ({ token: "jwt-123" }),
        };
      }
      return {
        ok: true,
        json: async () => ({ ok: true }),
      };
    });
    vi.stubGlobal("fetch", fetchMock);

    await evaluationsApi.get("1");
    await evaluationsApi.create({ name: "e", model_list: ["m"] });
    await evaluationsApi.run("1");
    await evaluationsApi.import("1", [
      { question_id: "Q1", model_name: "m", response_text: "r" },
    ]);
    await evaluationsApi.getReview("1");
    await evaluationsApi.getProgress("1");
    await questionsApi.list();
    await reportsApi.get("1");
    await configApi.perspectives();
    await configApi.dimensions();
    expect(fetchMock).toHaveBeenCalled();
  });
});
