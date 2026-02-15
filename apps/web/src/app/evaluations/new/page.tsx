"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { configApi, evaluationsApi } from "@/lib/api";
import type { ModelInfo, ModelTier } from "@/lib/types";

const TIER_ORDER: ModelTier[] = ["premium", "standard", "economy"];

const TIER_LABELS: Record<ModelTier, string> = {
  premium: "Premium",
  standard: "Standard",
  economy: "Economy",
};

const TIER_COLORS: Record<ModelTier, string> = {
  premium: "text-amber-700",
  standard: "text-primary",
  economy: "text-muted-foreground",
};

function formatCost(costPer1k: number): string {
  if (costPer1k < 0.001) return `$${(costPer1k * 1000).toFixed(2)}/M`;
  return `$${costPer1k.toFixed(4)}/1K`;
}

export default function NewEvaluationPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [reviewMode, setReviewMode] = useState<"blind" | "labeled">("blind");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingModels, setLoadingModels] = useState(true);

  useEffect(() => {
    configApi
      .models()
      .then(({ models: m }) => {
        setModels(m);
        // Default: select one premium + one standard if available
        const premium = m.find((x) => x.tier === "premium");
        const standard = m.find((x) => x.tier === "standard");
        const defaults = [premium?.name, standard?.name].filter(
          Boolean
        ) as string[];
        setSelectedModels(defaults.length > 0 ? defaults : [m[0]?.name].filter(Boolean));
      })
      .catch(() => setError("Failed to load models"))
      .finally(() => setLoadingModels(false));
  }, []);

  const modelsByTier = TIER_ORDER.reduce(
    (acc, tier) => {
      const tierModels = models.filter((m) => m.tier === tier);
      if (tierModels.length > 0) acc[tier] = tierModels;
      return acc;
    },
    {} as Record<ModelTier, ModelInfo[]>
  );

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
          {loadingModels ? (
            <div className="text-sm text-muted-foreground py-4 text-center">
              Loading models...
            </div>
          ) : (
            <div className="space-y-4">
              {(Object.entries(modelsByTier) as [ModelTier, ModelInfo[]][]).map(
                ([tier, tierModels]) => (
                  <div key={tier}>
                    <div className="flex items-center gap-2 mb-2">
                      <span
                        className={`text-xs font-semibold uppercase tracking-wider ${TIER_COLORS[tier]}`}
                      >
                        {TIER_LABELS[tier]}
                      </span>
                      <div className="flex-1 border-t border-border/50" />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      {tierModels.map((model) => (
                        <button
                          key={model.name}
                          type="button"
                          onClick={() => toggleModel(model.name)}
                          className={`px-3 py-2.5 rounded-md border text-sm text-left transition-colors ${
                            selectedModels.includes(model.name)
                              ? "border-primary bg-primary/5 text-primary font-medium"
                              : "border-border bg-card text-muted-foreground hover:bg-accent"
                          }`}
                        >
                          <span className="block">{model.name}</span>
                          <span className="block text-xs mt-0.5 opacity-60">
                            {model.provider} &middot;{" "}
                            {formatCost(model.cost_per_1k_input)} in /{" "}
                            {formatCost(model.cost_per_1k_output)} out
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                )
              )}
            </div>
          )}
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
