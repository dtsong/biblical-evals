"use client";

import { useState } from "react";
import type { Score, ScoringDimension } from "@/lib/types";

interface ScoringFormProps {
  dimensions: ScoringDimension[];
  onSubmit: (scores: Score[]) => void;
  submitting: boolean;
  responseLabel: string;
}

const SCORE_COLORS = [
  "",
  "score-bg-1",
  "score-bg-2",
  "score-bg-3",
  "score-bg-4",
  "score-bg-5",
];

export function ScoringForm({
  dimensions,
  onSubmit,
  submitting,
  responseLabel,
}: ScoringFormProps) {
  const [scores, setScores] = useState<Record<string, number>>({});
  const [comments, setComments] = useState<Record<string, string>>({});

  const allScored = dimensions.every((d) => scores[d.name] !== undefined);
  const lowScoresNeedComments = dimensions.every((d) => {
    const val = scores[d.name];
    if (val !== undefined && val <= 3) {
      return (comments[d.name] || "").trim().length > 0;
    }
    return true;
  });

  const handleSubmit = () => {
    const scoreList: Score[] = dimensions.map((d) => ({
      dimension: d.name,
      value: scores[d.name] || 3,
      comment: comments[d.name] || "",
    }));
    onSubmit(scoreList);
  };

  return (
    <div className="space-y-5">
      <h3
        className="text-sm font-medium text-muted-foreground uppercase tracking-wider"
      >
        Score {responseLabel}
      </h3>

      {dimensions.map((dim) => (
        <div key={dim.name} className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium">{dim.label}</label>
            <span className="text-xs text-muted-foreground">
              {scores[dim.name] || "—"} / {dim.max_value}
            </span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            {dim.description}
          </p>

          {/* Score buttons */}
          <div className="flex gap-1.5">
            {Array.from(
              { length: dim.max_value - dim.min_value + 1 },
              (_, i) => dim.min_value + i
            ).map((val) => (
              <button
                key={val}
                type="button"
                onClick={() =>
                  setScores((prev) => ({ ...prev, [dim.name]: val }))
                }
                className={`flex-1 py-2 rounded text-sm font-medium transition-all ${
                  scores[dim.name] === val
                    ? `${SCORE_COLORS[val]} text-white shadow-sm`
                    : "bg-secondary text-secondary-foreground hover:bg-accent"
                }`}
              >
                {val}
              </button>
            ))}
          </div>

          {/* Comment field (required for scores <= 3) */}
          {scores[dim.name] !== undefined && scores[dim.name] <= 3 && (
            <div className="mt-1">
              <textarea
                value={comments[dim.name] || ""}
                onChange={(e) =>
                  setComments((prev) => ({
                    ...prev,
                    [dim.name]: e.target.value,
                  }))
                }
                placeholder="Comment required for scores 3 or below..."
                className="w-full px-3 py-2 rounded-md border border-input bg-card text-sm resize-none h-20 focus:outline-none focus:ring-2 focus:ring-ring/30"
              />
            </div>
          )}

          {/* Optional comment for higher scores */}
          {scores[dim.name] !== undefined && scores[dim.name] > 3 && (
            <div className="mt-1">
              <textarea
                value={comments[dim.name] || ""}
                onChange={(e) =>
                  setComments((prev) => ({
                    ...prev,
                    [dim.name]: e.target.value,
                  }))
                }
                placeholder="Optional comment..."
                className="w-full px-3 py-2 rounded-md border border-input bg-card text-sm resize-none h-16 focus:outline-none focus:ring-2 focus:ring-ring/30"
              />
            </div>
          )}
        </div>
      ))}

      <button
        type="button"
        onClick={handleSubmit}
        disabled={!allScored || !lowScoresNeedComments || submitting}
        className="w-full px-4 py-2.5 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {submitting ? "Submitting..." : "Submit Scores"}
      </button>

      {!lowScoresNeedComments && allScored && (
        <p className="text-xs text-destructive">
          Comments are required for scores of 3 or below.
        </p>
      )}
    </div>
  );
}
