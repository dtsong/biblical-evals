"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus, ChevronRight } from "lucide-react";
import type { Evaluation } from "@/lib/types";
import { evaluationsApi } from "@/lib/api";

const STATUS_LABELS: Record<string, { label: string; className: string }> = {
  created: {
    label: "Created",
    className: "bg-secondary text-secondary-foreground",
  },
  collecting: {
    label: "Collecting",
    className: "bg-amber-100 text-amber-800",
  },
  running: {
    label: "Running",
    className: "bg-blue-100 text-blue-800",
  },
  reviewing: {
    label: "Reviewing",
    className: "bg-emerald-100 text-emerald-800",
  },
  complete: {
    label: "Complete",
    className: "bg-primary/10 text-primary",
  },
};

export default function EvaluationsPage() {
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    evaluationsApi
      .list()
      .then(setEvaluations)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-8 animate-fade-in-up">
        <div>
          <h1
            className="text-3xl font-light tracking-tight"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Evaluations
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage and review LLM evaluation runs.
          </p>
        </div>
        <Link
          href="/evaluations/new"
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Evaluation
        </Link>
      </div>

      {loading && (
        <div className="text-center py-16 text-muted-foreground">
          Loading evaluations...
        </div>
      )}

      {error && (
        <div className="text-center py-16 text-destructive">{error}</div>
      )}

      {!loading && !error && evaluations.length === 0 && (
        <div className="text-center py-16 border border-dashed border-border rounded-lg animate-fade-in-up">
          <p className="text-muted-foreground mb-4">
            No evaluations yet. Create your first one to get started.
          </p>
          <Link
            href="/evaluations/new"
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            <Plus className="h-4 w-4" />
            New Evaluation
          </Link>
        </div>
      )}

      <div className="space-y-3">
        {evaluations.map((evaluation, i) => {
          const status = STATUS_LABELS[evaluation.status] || {
            label: evaluation.status,
            className: "bg-secondary text-secondary-foreground",
          };
          return (
            <Link
              key={evaluation.id}
              href={`/evaluations/${evaluation.id}`}
              className="animate-fade-in-up block p-5 rounded-lg border border-border/60 bg-card/50 hover:bg-card/80 hover:border-border transition-all group"
              style={{ animationDelay: `${i * 0.05}s` }}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1.5">
                    <h3
                      className="text-lg font-medium truncate"
                      style={{ fontFamily: "var(--font-display)" }}
                    >
                      {evaluation.name}
                    </h3>
                    <span
                      className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${status.className}`}
                    >
                      {status.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span>
                      {evaluation.model_list.length} model
                      {evaluation.model_list.length !== 1 ? "s" : ""}
                    </span>
                    <span className="text-border">|</span>
                    <span>{evaluation.review_mode} review</span>
                    <span className="text-border">|</span>
                    <span>
                      {new Date(evaluation.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors flex-shrink-0" />
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
