output "instance_name" {
  description = "Cloud SQL instance name"
  value       = google_sql_database_instance.this.name
}

output "instance_connection_name" {
  description = "Instance connection name for Cloud SQL Proxy"
  value       = google_sql_database_instance.this.connection_name
}

output "private_ip_address" {
  description = "Private IP address of the instance"
  value       = google_sql_database_instance.this.private_ip_address
}

output "database_name" {
  description = "Database name"
  value       = google_sql_database.this.name
}

output "database_url" {
  description = "Database connection URL (without password)"
  value       = "postgresql+asyncpg://${var.app_user_name}@${google_sql_database_instance.this.private_ip_address}:5432/${google_sql_database.this.name}"
  sensitive   = true
}
