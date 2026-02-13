"use client";

import { SessionProvider } from "next-auth/react";

import { AccessGate } from "./access-gate";

interface ProvidersProps {
  children: React.ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return (
    <SessionProvider>
      <AccessGate />
      {children}
    </SessionProvider>
  );
}
