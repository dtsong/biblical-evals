"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Play,
  ClipboardCheck,
  BarChart3,
  ArrowLeft,
} from "lucide-react";
import type { Evaluation, ReviewProgress } from "@/lib/types";
import { evaluationsApi } from "@/lib/api";

export default function EvaluationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [progress, setProgress] = useState<ReviewProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      evaluationsApi.get(id),
      evaluationsApi.getProgress(id).catch(() => null),
    ])
      .then(([eval_, prog]) => {
        setEvaluation(eval_);
        setProgress(prog);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const handleRun = async () => {
    setRunning(true);
    try {
      await evaluationsApi.run(id);
      const updated = await evaluationsApi.get(id);
      setEvaluation(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to run");
    } finally {
      setRunning(false);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        Loading evaluation...
      </div>
    );
  }

  if (error || !evaluation) {
    return (
      <div className="text-center py-16 text-destructive">
        {error || "Evaluation not found"}
      </div>
    );
  }

  const canRun = evaluation.status === "created";
  const canReview = ["reviewing", "running"].includes(evaluation.status);

  return (
    <div className="max-w-4xl mx-auto">
      <Link
        href="/evaluations"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-6 transition-colors"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        All Evaluations
      </Link>

      <div className="animate-fade-in-up">
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1
              className="text-3xl font-light tracking-tight mb-2"
              style={{ fontFamily: "var(--font-display)" }}
            >
              {evaluation.name}
            </h1>
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <span className="capitalize">{evaluation.status}</span>
              <span className="text-border">|</span>
              <span>{evaluation.review_mode} review</span>
              <span className="text-border">|</span>
              <span>{evaluation.perspective}</span>
            </div>
          </div>
        </div>

        {/* Models */}
        <div className="mb-8 p-5 rounded-lg border border-border/60 bg-card/50">
          <h3
            className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-3"
          >
            Models
          </h3>
          <div className="flex flex-wrap gap-2">
            {evaluation.model_list.map((model) => (
              <span
                key={model}
                className="px-2.5 py-1 rounded-md bg-secondary text-secondary-foreground text-sm"
              >
                {model}
              </span>
            ))}
          </div>
        </div>

        {/* Progress */}
        {progress && progress.total_responses > 0 && (
          <div className="mb-8 p-5 rounded-lg border border-border/60 bg-card/50 animate-fade-in-up animate-delay-1">
            <h3
              className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-4"
            >
              Review Progress
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              <div>
                <div className="text-2xl font-light" style={{ fontFamily: "var(--font-display)" }}>
                  {progress.total_responses}
                </div>
                <div className="text-xs text-muted-foreground">Total Responses</div>
              </div>
              <div>
                <div className="text-2xl font-light" style={{ fontFamily: "var(--font-display)" }}>
                  {progress.scored_by_you}
                </div>
                <div className="text-xs text-muted-foreground">Scored by You</div>
              </div>
              <div>
                <div className="text-2xl font-light" style={{ fontFamily: "var(--font-display)" }}>
                  {progress.total_reviewers}
                </div>
                <div className="text-xs text-muted-foreground">Reviewers</div>
              </div>
              <div>
                <div className="text-2xl font-light" style={{ fontFamily: "var(--font-display)" }}>
                  {progress.model_count}
                </div>
                <div className="text-xs text-muted-foreground">Models</div>
              </div>
            </div>
            {/* Progress bar */}
            <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
              <div
                className="h-full bg-primary rounded-full transition-all duration-500"
                style={{ width: `${progress.percent_complete}%` }}
              />
            </div>
            <div className="text-xs text-muted-foreground mt-1.5">
              {progress.percent_complete}% complete — {progress.remaining_for_you} remaining
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3 animate-fade-in-up animate-delay-2">
          {canRun && (
            <button
              onClick={handleRun}
              disabled={running}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              <Play className="h-4 w-4" />
              {running ? "Starting..." : "Run Evaluation"}
            </button>
          )}

          {canReview && (
            <Link
              href={`/evaluations/${id}/review`}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
            >
              <ClipboardCheck className="h-4 w-4" />
              Start Reviewing
            </Link>
          )}

          <Link
            href={`/reports/${id}`}
            className="inline-flex items-center gap-2 px-5 py-2.5 border border-border rounded-md text-sm font-medium hover:bg-accent transition-colors"
          >
            <BarChart3 className="h-4 w-4" />
            View Report
          </Link>
        </div>
      </div>
    </div>
  );
}
