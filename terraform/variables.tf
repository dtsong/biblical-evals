variable "project_id" {
  description = "GCP project ID (temporarily trainerlab-prod)"
  type        = string
  default     = "trainerlab-prod"
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-west1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "api_image" {
  description = "Container image URI for the API"
  type        = string
  default     = "us-west1-docker.pkg.dev/trainerlab-prod/biblical-evals-api/api:latest"
}

variable "cors_origins" {
  description = "Comma-separated list of allowed CORS origins"
  type        = string
  default     = "https://biblical-evals.vercel.app"
}

variable "db_tier" {
  description = "Cloud SQL machine type"
  type        = string
  default     = "db-f1-micro"
}

variable "db_disk_size" {
  description = "Cloud SQL disk size in GB"
  type        = number
  default     = 10
}

variable "github_repo" {
  description = "GitHub repository (owner/repo)"
  type        = string
  default     = "dtsong/biblical-evals"
}
