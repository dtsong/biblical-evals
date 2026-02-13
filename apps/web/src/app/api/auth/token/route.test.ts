import { describe, expect, it } from "vitest";

import { GET } from "./route";

function makeRequest(cookies: Record<string, string>) {
  return {
    cookies: {
      get(name: string) {
        const value = cookies[name];
        return value ? { value } : undefined;
      },
    },
  };
}

describe("auth token route", () => {
  it("returns 401 when no recognized session cookie exists", async () => {
    const res = await GET(makeRequest({}) as never);
    expect(res.status).toBe(401);
    const body = await res.json();
    expect(body.error).toBe("Not authenticated");
  });

  it("returns token from recognized cookie", async () => {
    const res = await GET(
      makeRequest({ "__Secure-authjs.session-token": "jwt-value" }) as never
    );
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.token).toBe("jwt-value");
    expect(res.headers.get("cache-control")).toContain("no-store");
  });
});
