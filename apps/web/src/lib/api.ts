/**
 * API client for Biblical Evals backend.
 */

import type {
  Evaluation,
  ReviewData,
  ReviewProgress,
  Question,
  Score,
  Perspective,
  ScoringDimension,
  ReportData,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function getAuthToken(): Promise<string | null> {
  try {
    const res = await fetch("/api/auth/token");
    if (!res.ok) return null;
    const data = await res.json();
    return data.token ?? null;
  } catch {
    return null;
  }
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.detail || res.statusText, res.status);
  }

  return res.json();
}

async function fetchApiAuth<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const token = await getAuthToken();
  if (!token) {
    throw new ApiError("Not authenticated", 401);
  }

  return fetchApi<T>(endpoint, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      ...options?.headers,
    },
  });
}

// --- Evaluations ---

export const evaluationsApi = {
  list: () => fetchApiAuth<Evaluation[]>("/api/v1/evaluations"),

  get: (id: string) => fetchApiAuth<Evaluation>(`/api/v1/evaluations/${id}`),

  create: (body: {
    name: string;
    model_list: string[];
    perspective?: string;
    scoring_dimensions?: string[];
    prompt_template?: string;
    review_mode?: "blind" | "labeled";
  }) =>
    fetchApiAuth<Evaluation>("/api/v1/evaluations", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  run: (id: string) =>
    fetchApiAuth<{ message: string }>(`/api/v1/evaluations/${id}/run`, {
      method: "POST",
    }),

  import: (
    id: string,
    responses: Array<{
      question_id: string;
      model_name: string;
      response_text: string;
      metadata?: Record<string, unknown>;
    }>
  ) =>
    fetchApiAuth<{ message: string; count: number }>(
      `/api/v1/evaluations/${id}/import`,
      {
        method: "POST",
        body: JSON.stringify({ responses }),
      }
    ),

  getReview: (id: string) =>
    fetchApiAuth<ReviewData>(`/api/v1/evaluations/${id}/review`),

  getProgress: (id: string) =>
    fetchApiAuth<ReviewProgress>(`/api/v1/evaluations/${id}/progress`),
};

// --- Reviews ---

export const reviewsApi = {
  submit: (response_id: string, scores: Score[]) =>
    fetchApiAuth<unknown>("/api/v1/reviews", {
      method: "POST",
      body: JSON.stringify({ response_id, scores }),
    }),
};

// --- Questions ---

export const questionsApi = {
  list: () => fetchApiAuth<Question[]>("/api/v1/questions"),
};

// --- Config ---

// --- Reports ---

export const reportsApi = {
  get: (evaluationId: string) =>
    fetchApiAuth<ReportData>(`/api/v1/reports/${evaluationId}`),
};

// --- Config ---

export const configApi = {
  perspectives: () =>
    fetchApiAuth<{ perspectives: Perspective[] }>(
      "/api/v1/config/perspectives"
    ),
  dimensions: () =>
    fetchApiAuth<{ dimensions: ScoringDimension[] }>(
      "/api/v1/config/dimensions"
    ),
};
