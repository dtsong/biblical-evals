"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { evaluationsApi } from "@/lib/api";

const AVAILABLE_MODELS = [
  "gpt-4o",
  "gpt-4o-mini",
  "claude-sonnet-4-5",
  "claude-haiku-3.5",
  "gemini-2.0-flash",
];

export default function NewEvaluationPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [selectedModels, setSelectedModels] = useState<string[]>([
    "gpt-4o",
    "claude-sonnet-4-5",
  ]);
  const [reviewMode, setReviewMode] = useState<"blind" | "labeled">("blind");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleModel = (model: string) => {
    setSelectedModels((prev) =>
      prev.includes(model)
        ? prev.filter((m) => m !== model)
        : [...prev, model]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || selectedModels.length === 0) return;

    setSubmitting(true);
    setError(null);

    try {
      const evaluation = await evaluationsApi.create({
        name: name.trim(),
        model_list: selectedModels,
        review_mode: reviewMode,
      });
      router.push(`/evaluations/${evaluation.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1
        className="text-3xl font-light tracking-tight mb-8 animate-fade-in-up"
        style={{ fontFamily: "var(--font-display)" }}
      >
        New Evaluation
      </h1>

      <form onSubmit={handleSubmit} className="space-y-8">
        <div className="animate-fade-in-up animate-delay-1">
          <label
            htmlFor="name"
            className="block text-sm font-medium mb-2"
          >
            Evaluation Name
          </label>
          <input
            id="name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Soteriology Deep Dive — March 2025"
            className="w-full px-3 py-2 rounded-md border border-input bg-card text-sm focus:outline-none focus:ring-2 focus:ring-ring/30"
            required
          />
        </div>

        <div className="animate-fade-in-up animate-delay-2">
          <label className="block text-sm font-medium mb-3">
            Models to Evaluate
          </label>
          <div className="grid grid-cols-2 gap-2">
            {AVAILABLE_MODELS.map((model) => (
              <button
                key={model}
                type="button"
                onClick={() => toggleModel(model)}
                className={`px-3 py-2.5 rounded-md border text-sm text-left transition-colors ${
                  selectedModels.includes(model)
                    ? "border-primary bg-primary/5 text-primary font-medium"
                    : "border-border bg-card text-muted-foreground hover:bg-accent"
                }`}
              >
                {model}
              </button>
            ))}
          </div>
        </div>

        <div className="animate-fade-in-up animate-delay-2">
          <label className="block text-sm font-medium mb-3">
            Review Mode
          </label>
          <div className="flex gap-3">
            {(["blind", "labeled"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setReviewMode(mode)}
                className={`flex-1 px-3 py-2.5 rounded-md border text-sm transition-colors ${
                  reviewMode === mode
                    ? "border-primary bg-primary/5 text-primary font-medium"
                    : "border-border bg-card text-muted-foreground hover:bg-accent"
                }`}
              >
                {mode === "blind" ? "Blind Review" : "Labeled Review"}
                <span className="block text-xs mt-0.5 opacity-70">
                  {mode === "blind"
                    ? "Model names hidden during scoring"
                    : "Model names visible to reviewers"}
                </span>
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="text-sm text-destructive bg-destructive/5 px-3 py-2 rounded-md">
            {error}
          </div>
        )}

        <div className="animate-fade-in-up animate-delay-3">
          <button
            type="submit"
            disabled={submitting || !name.trim() || selectedModels.length === 0}
            className="w-full px-4 py-2.5 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? "Creating..." : "Create Evaluation"}
          </button>
        </div>
      </form>
    </div>
  );
}
