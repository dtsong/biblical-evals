"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, CheckCircle2 } from "lucide-react";
import type {
  ReviewData,
  ReviewProgress,
  Score,
  ScoringDimension,
} from "@/lib/types";
import { evaluationsApi, reviewsApi, configApi } from "@/lib/api";
import { QuestionViewer } from "@/components/QuestionViewer";
import { ComparisonView } from "@/components/ComparisonView";
import { ScoringForm } from "@/components/ScoringForm";

export default function ReviewPage() {
  const params = useParams();
  const id = params.id as string;

  const [reviewData, setReviewData] = useState<ReviewData | null>(null);
  const [progress, setProgress] = useState<ReviewProgress | null>(null);
  const [dimensions, setDimensions] = useState<ScoringDimension[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadReview = async () => {
    try {
      const [review, prog, dimConfig] = await Promise.all([
        evaluationsApi.getReview(id),
        evaluationsApi.getProgress(id),
        configApi.dimensions(),
      ]);
      setReviewData(review);
      setProgress(prog);
      setDimensions(dimConfig.dimensions);
      setActiveIndex(0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReview();
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSubmitScores = async (scores: Score[]) => {
    if (!reviewData?.responses?.[activeIndex]) return;

    setSubmitting(true);
    try {
      await reviewsApi.submit(
        reviewData.responses[activeIndex].response_id,
        scores
      );

      // Move to next response or reload
      if (
        reviewData.responses &&
        activeIndex < reviewData.responses.length - 1
      ) {
        setActiveIndex((prev) => prev + 1);
      } else {
        // Reload to get next question batch
        setLoading(true);
        await loadReview();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to submit");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        Loading review...
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-16 text-destructive">{error}</div>
    );
  }

  // All done
  if (reviewData?.complete) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16 animate-fade-in-up">
        <CheckCircle2 className="h-12 w-12 text-primary mx-auto mb-4" />
        <h2
          className="text-2xl font-light mb-2"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Review Complete
        </h2>
        <p className="text-muted-foreground mb-6">
          You have scored all responses for this evaluation.
        </p>
        <Link
          href={`/evaluations/${id}`}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          Back to Evaluation
        </Link>
      </div>
    );
  }

  const currentResponse = reviewData?.responses?.[activeIndex];

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <Link
          href={`/evaluations/${id}`}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back
        </Link>

        {progress && (
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <span>
              {progress.scored_by_you} / {progress.total_responses} scored
            </span>
            <div className="w-24 h-1.5 bg-secondary rounded-full overflow-hidden">
              <div
                className="h-full bg-primary rounded-full transition-all"
                style={{ width: `${progress.percent_complete}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Question */}
      {reviewData?.question && (
        <div className="mb-6 animate-fade-in-up">
          <QuestionViewer
            id={reviewData.question.id}
            text={reviewData.question.text}
          />
        </div>
      )}

      {/* Responses + Scoring */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 animate-fade-in-up animate-delay-1">
          {reviewData?.responses && (
            <ComparisonView
              responses={reviewData.responses}
              activeIndex={activeIndex}
              onSelect={setActiveIndex}
            />
          )}
        </div>

        <div className="animate-fade-in-up animate-delay-2">
          <div className="sticky top-20 p-5 rounded-lg border border-border/60 bg-card/80">
            {currentResponse && dimensions.length > 0 && (
              <ScoringForm
                dimensions={dimensions}
                onSubmit={handleSubmitScores}
                submitting={submitting}
                responseLabel={currentResponse.label}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
