"use client";

import { useCallback, useEffect, useState } from "react";

import { accessApi } from "@/lib/api";
import type { AccessStatus, AccessUser } from "@/lib/types";

const FILTERS: Array<AccessStatus | "all"> = [
  "pending",
  "not_requested",
  "approved",
  "rejected",
  "all",
];

export default function AdminAccessPage() {
  const [filter, setFilter] = useState<AccessStatus | "all">("pending");
  const [users, setUsers] = useState<AccessUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (nextFilter = filter) => {
    setLoading(true);
    setError(null);
    try {
      const data = await accessApi.list(nextFilter);
      setUsers(data.users);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  const act = async (userId: string, action: "approve" | "reject") => {
    try {
      if (action === "approve") {
        await accessApi.approve(userId);
      } else {
        await accessApi.reject(userId);
      }
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-light tracking-tight mb-2">Access Requests</h1>
      <p className="text-sm text-muted-foreground mb-6">
        Approve or reject beta access requests.
      </p>

      <div className="flex gap-2 mb-6 flex-wrap">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-md text-sm border ${
              filter === f
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border text-muted-foreground"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {loading && <div className="py-10 text-muted-foreground">Loading...</div>}
      {error && <div className="py-6 text-destructive">{error}</div>}

      {!loading && !error && users.length === 0 && (
        <div className="py-10 text-muted-foreground">No users found for this filter.</div>
      )}

      {!loading && !error && users.length > 0 && (
        <div className="space-y-3">
          {users.map((user) => (
            <div
              key={user.id}
              className="p-4 rounded-md border border-border bg-card/50 flex items-center justify-between gap-4"
            >
              <div className="min-w-0">
                <p className="font-medium truncate">{user.email}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  status: {user.access_status}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => act(user.id, "approve")}
                  className="px-3 py-1.5 rounded-md text-sm bg-emerald-600 text-white"
                >
                  Approve
                </button>
                <button
                  onClick={() => act(user.id, "reject")}
                  className="px-3 py-1.5 rounded-md text-sm bg-rose-600 text-white"
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
