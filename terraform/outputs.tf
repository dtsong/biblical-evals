output "api_url" {
  description = "Cloud Run API URL"
  value       = module.cloud_run.service_url
}

output "api_service_name" {
  description = "Cloud Run service name"
  value       = module.cloud_run.service_name
}

output "api_image" {
  description = "Container image URI"
  value       = var.api_image
}

output "database_instance_name" {
  description = "Cloud SQL instance name"
  value       = module.cloud_sql.instance_name
}

output "database_connection_name" {
  description = "Cloud SQL connection name for Cloud Run"
  value       = module.cloud_sql.instance_connection_name
}

output "artifact_registry_url" {
  description = "Artifact Registry URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.api.repository_id}"
}

output "project_number" {
  description = "GCP project number (for GitHub OIDC)"
  value       = data.google_project.current.number
}
