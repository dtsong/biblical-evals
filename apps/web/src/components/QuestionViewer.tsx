"use client";

import { BookOpen } from "lucide-react";

interface QuestionViewerProps {
  id: string;
  text: string;
}

export function QuestionViewer({ id, text }: QuestionViewerProps) {
  return (
    <div className="p-5 rounded-lg border border-primary/20 bg-primary/[0.03]">
      <div className="flex items-start gap-3">
        <BookOpen className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
        <div>
          <span className="text-xs font-medium text-primary/70 uppercase tracking-wider">
            {id}
          </span>
          <p
            className="text-lg leading-relaxed mt-1"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {text}
          </p>
        </div>
      </div>
    </div>
  );
}
