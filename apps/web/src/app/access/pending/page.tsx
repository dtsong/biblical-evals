"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";

import { accessApi } from "@/lib/api";
import type { AccessUser } from "@/lib/types";

export default function AccessPendingPage() {
  const { status } = useSession();
  const [me, setMe] = useState<AccessUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (status !== "authenticated") {
      setLoading(false);
      return;
    }

    accessApi
      .me()
      .then(setMe)
      .catch(() => setMessage("Could not load access status."))
      .finally(() => setLoading(false));
  }, [status]);

  const onRequest = async () => {
    setSubmitting(true);
    setMessage(null);
    try {
      const result = await accessApi.request();
      setMessage(result.message);
      const refreshed = await accessApi.me();
      setMe(refreshed);
    } catch {
      setMessage("Could not submit request. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div className="py-16 text-center text-muted-foreground">Loading...</div>;
  }

  if (status !== "authenticated") {
    return (
      <div className="max-w-xl mx-auto py-16 text-center">
        <h1 className="text-3xl font-light tracking-tight mb-3">Access Required</h1>
        <p className="text-muted-foreground mb-6">Please sign in to request access.</p>
        <Link
          href="/auth/login"
          className="inline-flex px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm"
        >
          Go to Sign In
        </Link>
      </div>
    );
  }

  const statusLabel = me?.is_admin
    ? "admin"
    : me?.access_status ?? "not_requested";

  return (
    <div className="max-w-xl mx-auto py-16">
      <h1 className="text-3xl font-light tracking-tight mb-3">Access Pending</h1>
      <p className="text-muted-foreground mb-4">
        Your account is signed in but not approved yet.
      </p>
      <div className="mb-6 rounded-md border border-border p-4 bg-card/50">
        <p className="text-sm">
          <span className="text-muted-foreground">Email: </span>
          {me?.email ?? "Unknown"}
        </p>
        <p className="text-sm mt-1">
          <span className="text-muted-foreground">Status: </span>
          <span className="font-medium">{statusLabel}</span>
        </p>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={onRequest}
          disabled={submitting || me?.is_admin || me?.access_status === "approved"}
          className="px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm disabled:opacity-50"
        >
          {submitting ? "Submitting..." : "Request Access"}
        </button>
        <Link href="/" className="text-sm text-muted-foreground hover:text-foreground">
          Back to home
        </Link>
      </div>

      {message && <p className="mt-4 text-sm text-muted-foreground">{message}</p>}
    </div>
  );
}
