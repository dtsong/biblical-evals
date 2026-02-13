import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/auth", () => ({
  auth: (handler: (req: any) => unknown) => handler,
}));

import middleware from "./middleware";

describe("middleware auth gating", () => {
  it("allows public paths", () => {
    const req = {
      nextUrl: { pathname: "/auth/login" },
      url: "http://localhost/auth/login",
      auth: null,
    };
    const res = middleware(req as never, {} as never) as Response;
    expect(res.status).toBe(200);
  });

  it("redirects protected paths when unauthenticated", () => {
    const req = {
      nextUrl: { pathname: "/evaluations" },
      url: "http://localhost/evaluations",
      auth: null,
    };
    const res = middleware(req as never, {} as never) as Response;
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toContain("/auth/login");
    expect(res.headers.get("location")).toContain("callbackUrl=%2Fevaluations");
  });

  it("allows protected paths when authenticated", () => {
    const req = {
      nextUrl: { pathname: "/evaluations" },
      url: "http://localhost/evaluations",
      auth: { user: { id: "u1" } },
    };
    const res = middleware(req as never, {} as never) as Response;
    expect(res.status).toBe(200);
  });
});
