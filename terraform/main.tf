terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "gcs" {
    bucket = "biblical-evals-tfstate"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# --- Remote State: Foundation Network ---

data "terraform_remote_state" "foundation" {
  backend = "gcs"
  config = {
    bucket = "my-gcp-foundation-tfstate"
    prefix = "environments/biblical-evals-prod"
  }
}

locals {
  vpc_id    = data.terraform_remote_state.foundation.outputs.vpc_id
  subnet_id = data.terraform_remote_state.foundation.outputs.subnet_id
}

# --- Enable APIs ---

resource "google_project_service" "apis" {
  for_each = toset([
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# --- Artifact Registry ---

resource "google_artifact_registry_repository" "api" {
  project       = var.project_id
  location      = var.region
  repository_id = "biblical-evals-api"
  format        = "DOCKER"
  description   = "Biblical Evals API container images"

  depends_on = [google_project_service.apis]
}

# --- Service Account ---

resource "google_service_account" "api" {
  project      = var.project_id
  account_id   = "biblical-evals-api"
  display_name = "Biblical Evals API"
}

resource "google_project_iam_member" "api_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "api_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.api.email}"
}

# --- Secrets ---

resource "random_password" "db_password" {
  length  = 32
  special = false
}

resource "google_secret_manager_secret" "db_password" {
  project   = var.project_id
  secret_id = "biblical-evals-db-password"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

resource "google_secret_manager_secret" "nextauth_secret" {
  project   = var.project_id
  secret_id = "biblical-evals-nextauth-secret"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "openai_api_key" {
  project   = var.project_id
  secret_id = "biblical-evals-openai-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "anthropic_api_key" {
  project   = var.project_id
  secret_id = "biblical-evals-anthropic-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "google_ai_api_key" {
  project   = var.project_id
  secret_id = "biblical-evals-google-ai-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

# --- Cloud SQL ---

module "cloud_sql" {
  source = "./modules/cloud_sql"

  project_id        = var.project_id
  region            = var.region
  instance_name     = "biblical-evals-db"
  tier              = var.db_tier
  disk_size         = var.db_disk_size
  vpc_id            = local.vpc_id
  database_name     = "biblical_evals"
  app_user_name     = "biblical_evals_app"
  app_user_password = random_password.db_password.result
  availability_type = var.environment == "prod" ? "REGIONAL" : "ZONAL"

  point_in_time_recovery = var.environment == "prod"
  backup_retention_days  = var.environment == "prod" ? 14 : 7

  labels = {
    app         = "biblical-evals"
    environment = var.environment
  }

  depends_on = [google_project_service.apis]
}

# --- Cloud Run ---

module "cloud_run" {
  source = "./modules/cloud_run"

  project_id   = var.project_id
  region       = var.region
  service_name = "biblical-evals-api"
  image        = var.api_image

  service_account_email = google_service_account.api.email
  subnet_id             = local.subnet_id

  env_vars = {
    ENVIRONMENT  = var.environment
    DATABASE_URL = module.cloud_sql.database_url
    CORS_ORIGINS = var.cors_origins
  }

  secret_env_vars = {
    DATABASE_PASSWORD = {
      secret_id = google_secret_manager_secret.db_password.secret_id
      version   = "latest"
    }
    NEXTAUTH_SECRET = {
      secret_id = google_secret_manager_secret.nextauth_secret.secret_id
      version   = "latest"
    }
    OPENAI_API_KEY = {
      secret_id = google_secret_manager_secret.openai_api_key.secret_id
      version   = "latest"
    }
    ANTHROPIC_API_KEY = {
      secret_id = google_secret_manager_secret.anthropic_api_key.secret_id
      version   = "latest"
    }
    GOOGLE_AI_API_KEY = {
      secret_id = google_secret_manager_secret.google_ai_api_key.secret_id
      version   = "latest"
    }
  }

  depends_on_resources = [
    google_project_service.apis,
    google_project_iam_member.api_cloudsql,
    google_project_iam_member.api_secrets,
  ]
}
