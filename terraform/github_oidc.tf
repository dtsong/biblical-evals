# Workload Identity Federation for GitHub Actions
# Separate pool from trainerlab's "github-actions" to avoid collisions.

data "google_project" "current" {
  project_id = var.project_id
}

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = "github-biblical-evals"
  display_name              = "GitHub Actions (Biblical Evals)"
  description               = "Workload Identity Pool for Biblical Evals CI/CD"

  depends_on = [google_project_service.apis]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-oidc"
  display_name                       = "GitHub OIDC (Biblical Evals)"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  attribute_condition = "assertion.repository == '${var.github_repo}'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Separate service account (avoid collision with trainerlab's "github-actions")
resource "google_service_account" "github_actions" {
  project      = var.project_id
  account_id   = "gh-biblical-evals"
  display_name = "GitHub Actions CI/CD (Biblical Evals)"
}

# Allow GitHub Actions to impersonate the service account
resource "google_service_account_iam_member" "github_workload_identity" {
  service_account_id = google_service_account.github_actions.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repo}"
}

# Artifact Registry push
resource "google_project_iam_member" "github_registry" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# Cloud Run deploy
resource "google_project_iam_member" "github_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# Cloud Run invoke (for migrations)
resource "google_project_iam_member" "github_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# Act as the API service account during deployment
resource "google_service_account_iam_member" "github_act_as_api" {
  service_account_id = google_service_account.api.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.github_actions.email}"
}

# --- Outputs ---

output "github_workload_identity_provider" {
  description = "Full provider resource name for GitHub Actions auth"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "github_service_account_email" {
  description = "Service account email for GitHub Actions"
  value       = google_service_account.github_actions.email
}
