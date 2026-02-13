"use client";

import ReactMarkdown from "react-markdown";
import type { ReviewResponse } from "@/lib/types";

interface ComparisonViewProps {
  responses: ReviewResponse[];
  activeIndex: number;
  onSelect: (index: number) => void;
}

export function ComparisonView({
  responses,
  activeIndex,
  onSelect,
}: ComparisonViewProps) {
  if (responses.length <= 1) return null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {responses.map((resp, i) => (
        <button
          key={resp.response_id}
          onClick={() => onSelect(i)}
          className={`w-full text-left p-5 rounded-lg border transition-all ${
            activeIndex === i
              ? "border-primary bg-card shadow-sm ring-1 ring-primary/20"
              : "border-border/60 bg-card/50 hover:bg-card/80"
          }`}
        >
          <div className="flex items-center justify-between mb-3">
            <span
              className={`text-sm font-semibold ${
                activeIndex === i ? "text-primary" : "text-muted-foreground"
              }`}
            >
              {resp.label}
            </span>
            {activeIndex === i && (
              <span className="text-xs text-primary bg-primary/10 px-2 py-0.5 rounded-full">
                Scoring
              </span>
            )}
          </div>
          <div className="prose prose-sm max-w-none text-foreground/90 leading-relaxed max-h-96 overflow-y-auto">
            <ReactMarkdown>{resp.response_text}</ReactMarkdown>
          </div>
        </button>
      ))}
    </div>
  );
}
