/** Shared types for the frontend. */

export interface Evaluation {
  id: string;
  name: string;
  status: "created" | "running" | "collecting" | "reviewing" | "complete";
  perspective: string;
  scoring_dimensions: string[];
  model_list: string[];
  prompt_template: string;
  review_mode: "blind" | "labeled";
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface Question {
  id: string;
  text: string;
  type: "theological" | "factual" | "interpretive";
  difficulty: string;
  scripture_references: string[];
  tags: string[];
}

export interface ReviewResponse {
  response_id: string;
  label: string;
  response_text: string;
  question_id: string;
  model_name?: string;
}

export interface ReviewData {
  complete: boolean;
  message?: string;
  question?: { id: string; text: string };
  responses?: ReviewResponse[];
  review_mode?: string;
}

export interface ReviewProgress {
  evaluation_id: string;
  total_responses: number;
  scored_by_you: number;
  remaining_for_you: number;
  percent_complete: number;
  total_reviewers: number;
  model_count: number;
  question_count: number;
}

export interface Score {
  dimension: string;
  value: number;
  comment: string;
}

export interface Perspective {
  id: string;
  name: string;
  description: string;
}

export interface ScoringDimension {
  name: string;
  label: string;
  description: string;
  min_value: number;
  max_value: number;
}

export interface ModelRanking {
  rank: number;
  model: string;
  overall_score: number;
}

export interface ReportData {
  evaluation: {
    id: string;
    name: string;
    perspective: string;
    review_mode: string;
    model_list: string[];
  };
  rankings: ModelRanking[];
  strengths_weaknesses: Record<
    string,
    { strengths: string[]; weaknesses: string[] }
  >;
  model_averages: Record<string, Record<string, number>>;
  model_overall: Record<string, number>;
  dimension_averages: Record<string, Record<string, number>>;
  head_to_head: Record<string, Record<string, Record<string, number>>>;
  question_scores: Record<
    string,
    Record<string, Record<string, number>>
  >;
  total_responses: number;
  total_scores: number;
  reviewer_count: number;
}
