"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, FileText, Download } from "lucide-react";
import type { Evaluation } from "@/lib/types";
import { evaluationsApi } from "@/lib/api";
import { ReportCharts } from "@/components/ReportCharts";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ReportPage() {
  const params = useParams();
  const id = params.id as string;
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);

  useEffect(() => {
    evaluationsApi.get(id).then(setEvaluation).catch(() => {});
  }, [id]);

  const handleExport = async (format: "html" | "markdown") => {
    try {
      const tokenRes = await fetch("/api/auth/token");
      const { token } = await tokenRes.json();
      const res = await fetch(
        `${API_BASE_URL}/api/v1/reports/${id}/generate?format=${format}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (!res.ok) return;

      const text = await res.text();
      const ext = format === "html" ? "html" : "md";
      const blob = new Blob([text], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report-${id.slice(0, 8)}.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // silently fail
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <Link
          href={`/evaluations/${id}`}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Evaluation
        </Link>

        <div className="flex items-center gap-2">
          <button
            onClick={() => handleExport("markdown")}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors"
          >
            <FileText className="h-3 w-3" />
            Markdown
          </button>
          <button
            onClick={() => handleExport("html")}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors"
          >
            <Download className="h-3 w-3" />
            HTML
          </button>
        </div>
      </div>

      <h1
        className="text-3xl font-light tracking-tight mb-2 animate-fade-in-up"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {evaluation?.name ?? "Evaluation"} Report
      </h1>

      {evaluation && (
        <div className="flex items-center gap-2 mb-8 text-sm text-muted-foreground animate-fade-in-up">
          <span className="px-2 py-0.5 bg-secondary rounded text-xs">
            {evaluation.perspective}
          </span>
          <span className="px-2 py-0.5 bg-secondary rounded text-xs">
            {evaluation.review_mode} review
          </span>
          <span>&middot;</span>
          <span>{evaluation.model_list.length} models</span>
        </div>
      )}

      <div className="animate-fade-in-up animate-delay-1">
        <ReportCharts evaluationId={id} />
      </div>
    </div>
  );
}
