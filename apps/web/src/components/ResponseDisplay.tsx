"use client";

import ReactMarkdown from "react-markdown";
import type { ReviewResponse } from "@/lib/types";

interface ResponseDisplayProps {
  response: ReviewResponse;
  isActive: boolean;
  onClick: () => void;
}

export function ResponseDisplay({
  response,
  isActive,
  onClick,
}: ResponseDisplayProps) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-5 rounded-lg border transition-all ${
        isActive
          ? "border-primary bg-card shadow-sm"
          : "border-border/60 bg-card/50 hover:bg-card/80 hover:border-border"
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <span
          className={`text-sm font-semibold ${
            isActive ? "text-primary" : "text-muted-foreground"
          }`}
        >
          {response.label}
        </span>
        {isActive && (
          <span className="text-xs text-primary bg-primary/10 px-2 py-0.5 rounded-full">
            Scoring
          </span>
        )}
      </div>
      <div className="prose prose-sm max-w-none text-foreground/90 leading-relaxed">
        <ReactMarkdown>{response.response_text}</ReactMarkdown>
      </div>
    </button>
  );
}
