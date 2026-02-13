import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => {
  return {
    useSession: vi.fn(),
    signIn: vi.fn(),
    signOut: vi.fn(),
  };
});

vi.mock("next-auth/react", () => ({
  useSession: mocks.useSession,
  signIn: mocks.signIn,
  signOut: mocks.signOut,
}));

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: any) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

import { Nav } from "./Nav";

describe("Nav", () => {
  it("shows sign in button when user is unauthenticated", () => {
    mocks.useSession.mockReturnValue({ data: null });
    render(<Nav />);

    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(mocks.signIn).toHaveBeenCalledWith("google");
  });

  it("shows evaluations link and sign out when authenticated", () => {
    mocks.useSession.mockReturnValue({
      data: { user: { id: "u1", name: "User" } },
    });
    render(<Nav />);

    expect(screen.getByRole("link", { name: /evaluations/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /sign out/i }));
    expect(mocks.signOut).toHaveBeenCalled();
  });
});
