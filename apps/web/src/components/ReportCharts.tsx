"use client";

import { useEffect, useState } from "react";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { Trophy, TrendingUp, TrendingDown } from "lucide-react";
import type { ReportData } from "@/lib/types";
import { reportsApi } from "@/lib/api";

/** Warm, earthy palette matching the editorial aesthetic. */
const MODEL_COLORS = [
  "#8B5E34", // burnt sienna
  "#6B7F4E", // olive sage
  "#4A6B8A", // dusty slate
  "#A0522D", // sienna
  "#5C6B7E", // cool charcoal
  "#9B7653", // chamois
  "#6E5B4E", // walnut
];

function formatDimension(dim: string): string {
  return dim
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

interface ReportChartsProps {
  evaluationId: string;
}

export function ReportCharts({ evaluationId }: ReportChartsProps) {
  const [data, setData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    reportsApi
      .get(evaluationId)
      .then(setData)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load report")
      )
      .finally(() => setLoading(false));
  }, [evaluationId]);

  if (loading) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        Loading report data...
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-16 text-destructive">{error}</div>
    );
  }

  if (!data || data.total_scores === 0) {
    return (
      <div className="text-center py-16 border border-dashed border-border rounded-lg">
        <p className="text-muted-foreground">
          No scores recorded yet. Complete reviews to generate a report.
        </p>
      </div>
    );
  }

  const models = Object.keys(data.model_averages);
  const dimensions = models.length > 0
    ? Object.keys(data.model_averages[models[0]])
    : [];

  // --- Radar chart data ---
  const radarData = dimensions.map((dim) => {
    const entry: Record<string, string | number> = {
      dimension: formatDimension(dim),
    };
    for (const model of models) {
      entry[model] = data.model_averages[model]?.[dim] ?? 0;
    }
    return entry;
  });

  // --- Overall bar chart data ---
  const overallData = data.rankings.map((r) => ({
    model: r.model,
    score: r.overall_score,
  }));

  // --- Head-to-head data ---
  const h2hPairs: Array<{
    modelA: string;
    modelB: string;
    dims: Record<string, number>;
  }> = [];
  for (const [modelA, comparisons] of Object.entries(data.head_to_head)) {
    for (const [modelB, dims] of Object.entries(comparisons)) {
      h2hPairs.push({ modelA, modelB, dims });
    }
  }

  return (
    <div className="space-y-10">
      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard
          label="Responses"
          value={data.total_responses}
        />
        <StatCard
          label="Scores"
          value={data.total_scores}
        />
        <StatCard
          label="Reviewers"
          value={data.reviewer_count}
        />
      </div>

      {/* Rankings */}
      <Section title="Model Rankings">
        <div className="space-y-3">
          {data.rankings.map((r) => (
            <div
              key={r.model}
              className="flex items-center gap-4 p-4 rounded-lg border border-border/60 bg-card/80"
            >
              <div
                className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold ${
                  r.rank === 1
                    ? "bg-[#fef3c7] text-[#92400e]"
                    : r.rank === 2
                      ? "bg-[#f3f4f6] text-[#374151]"
                      : r.rank === 3
                        ? "bg-[#fed7aa] text-[#9a3412]"
                        : "bg-secondary text-secondary-foreground"
                }`}
              >
                {r.rank === 1 ? (
                  <Trophy className="h-4 w-4" />
                ) : (
                  r.rank
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{r.model}</p>
                {data.strengths_weaknesses[r.model] && (
                  <div className="flex gap-3 mt-1 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <TrendingUp className="h-3 w-3 text-[hsl(var(--score-5))]" />
                      {data.strengths_weaknesses[r.model].strengths
                        .map(formatDimension)
                        .join(", ")}
                    </span>
                    <span className="flex items-center gap-1">
                      <TrendingDown className="h-3 w-3 text-[hsl(var(--score-1))]" />
                      {data.strengths_weaknesses[r.model].weaknesses
                        .map(formatDimension)
                        .join(", ")}
                    </span>
                  </div>
                )}
              </div>
              <div
                className="text-lg font-light tabular-nums"
                style={{ fontFamily: "var(--font-display)" }}
              >
                {r.overall_score}{" "}
                <span className="text-xs text-muted-foreground">/ 5.0</span>
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* Radar Chart — Dimension Comparison */}
      {dimensions.length >= 3 && (
        <Section title="Dimension Comparison">
          <div className="h-[380px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
                <PolarGrid stroke="hsl(30 15% 85%)" />
                <PolarAngleAxis
                  dataKey="dimension"
                  tick={{ fontSize: 11, fill: "hsl(24 5% 50%)" }}
                />
                <PolarRadiusAxis
                  domain={[0, 5]}
                  tickCount={6}
                  tick={{ fontSize: 10, fill: "hsl(24 5% 50%)" }}
                />
                {models.map((model, i) => (
                  <Radar
                    key={model}
                    name={model}
                    dataKey={model}
                    stroke={MODEL_COLORS[i % MODEL_COLORS.length]}
                    fill={MODEL_COLORS[i % MODEL_COLORS.length]}
                    fillOpacity={0.1}
                    strokeWidth={2}
                  />
                ))}
                <Legend
                  wrapperStyle={{ fontSize: 12, paddingTop: 16 }}
                />
                <Tooltip
                  contentStyle={{
                    background: "hsl(36 33% 99%)",
                    border: "1px solid hsl(30 15% 85%)",
                    borderRadius: 6,
                    fontSize: 12,
                  }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </Section>
      )}

      {/* Overall Score Bar Chart */}
      <Section title="Overall Scores">
        <div className="h-[280px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={overallData}
              layout="vertical"
              margin={{ left: 120, right: 24, top: 8, bottom: 8 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(30 15% 90%)"
                horizontal={false}
              />
              <XAxis
                type="number"
                domain={[0, 5]}
                tickCount={6}
                tick={{ fontSize: 11, fill: "hsl(24 5% 50%)" }}
              />
              <YAxis
                type="category"
                dataKey="model"
                tick={{ fontSize: 12, fill: "hsl(24 10% 25%)" }}
                width={110}
              />
              <Tooltip
                contentStyle={{
                  background: "hsl(36 33% 99%)",
                  border: "1px solid hsl(30 15% 85%)",
                  borderRadius: 6,
                  fontSize: 12,
                }}
                formatter={(value) => [
                  `${value} / 5.0`,
                  "Overall Score",
                ]}
              />
              <Bar
                dataKey="score"
                radius={[0, 4, 4, 0]}
                fill="#8B5E34"
                barSize={24}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Section>

      {/* Per-dimension grouped bar chart */}
      {dimensions.length > 0 && (
        <Section title="Scores by Dimension">
          <div className="h-[320px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={radarData}
                margin={{ left: 12, right: 24, top: 8, bottom: 8 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="hsl(30 15% 90%)"
                />
                <XAxis
                  dataKey="dimension"
                  tick={{ fontSize: 10, fill: "hsl(24 5% 50%)" }}
                  angle={-20}
                  textAnchor="end"
                  height={60}
                />
                <YAxis
                  domain={[0, 5]}
                  tickCount={6}
                  tick={{ fontSize: 11, fill: "hsl(24 5% 50%)" }}
                />
                <Tooltip
                  contentStyle={{
                    background: "hsl(36 33% 99%)",
                    border: "1px solid hsl(30 15% 85%)",
                    borderRadius: 6,
                    fontSize: 12,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                {models.map((model, i) => (
                  <Bar
                    key={model}
                    dataKey={model}
                    fill={MODEL_COLORS[i % MODEL_COLORS.length]}
                    radius={[3, 3, 0, 0]}
                    barSize={18}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Section>
      )}

      {/* Head-to-Head */}
      {h2hPairs.length > 0 && (
        <Section title="Head-to-Head Comparisons">
          <div className="space-y-6">
            {h2hPairs.map(({ modelA, modelB, dims }) => (
              <div
                key={`${modelA}-${modelB}`}
                className="p-4 rounded-lg border border-border/60 bg-card/80"
              >
                <h4
                  className="text-sm font-medium mb-3"
                  style={{ fontFamily: "var(--font-display)" }}
                >
                  {modelA}{" "}
                  <span className="text-muted-foreground font-normal">vs</span>{" "}
                  {modelB}
                </h4>
                <div className="space-y-2">
                  {Object.entries(dims).map(([dim, diff]) => (
                    <div
                      key={dim}
                      className="flex items-center gap-3 text-sm"
                    >
                      <span className="w-36 text-muted-foreground truncate">
                        {formatDimension(dim)}
                      </span>
                      <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden relative">
                        <div
                          className="absolute top-0 h-full rounded-full transition-all"
                          style={{
                            backgroundColor:
                              diff > 0
                                ? "hsl(var(--score-5))"
                                : diff < 0
                                  ? "hsl(var(--score-1))"
                                  : "hsl(var(--score-3))",
                            width: `${Math.min(Math.abs(diff) * 20, 100)}%`,
                            left: diff >= 0 ? "50%" : undefined,
                            right: diff < 0 ? "50%" : undefined,
                          }}
                        />
                        <div className="absolute left-1/2 top-0 w-px h-full bg-border" />
                      </div>
                      <span
                        className={`w-14 text-right tabular-nums font-medium ${
                          diff > 0
                            ? "text-[hsl(var(--score-5))]"
                            : diff < 0
                              ? "text-[hsl(var(--score-1))]"
                              : "text-muted-foreground"
                        }`}
                      >
                        {diff > 0 ? "+" : ""}
                        {diff}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h2
        className="text-xl font-light tracking-tight mb-4"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {title}
      </h2>
      {children}
    </section>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="p-4 rounded-lg border border-border/60 bg-card/80 text-center">
      <p
        className="text-2xl font-light tabular-nums"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {value}
      </p>
      <p className="text-xs text-muted-foreground uppercase tracking-wider mt-1">
        {label}
      </p>
    </div>
  );
}
