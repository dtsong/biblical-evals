locals {
  api_host = replace(module.cloud_run.service_url, "https://", "")
}

resource "google_monitoring_uptime_check_config" "api_ready" {
  display_name = "biblical-evals-api ready"
  timeout      = "10s"
  period       = "60s"

  selected_regions = var.uptime_check_regions

  http_check {
    path         = var.uptime_check_path
    port         = 443
    use_ssl      = true
    validate_ssl = true

    accepted_response_status_codes {
      status_class = "STATUS_CLASS_2XX"
    }
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = local.api_host
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_monitoring_notification_channel" "email" {
  for_each = toset(var.alert_notification_emails)

  display_name = "Biblical Evals API Alerts (${each.value})"
  type         = "email"

  labels = {
    email_address = each.value
  }
}

resource "google_monitoring_alert_policy" "api_uptime" {
  display_name = "biblical-evals-api uptime check failing"
  combiner     = "OR"

  notification_channels = [
    for c in google_monitoring_notification_channel.email : c.name
  ]

  conditions {
    display_name = "Uptime check passed"

    condition_threshold {
      filter = join(
        " AND ",
        [
          "resource.type=\"uptime_url\"",
          "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\"",
          "metric.label.check_id=\"${google_monitoring_uptime_check_config.api_ready.uptime_check_id}\"",
        ]
      )

      comparison      = "COMPARISON_LT"
      threshold_value = 1
      duration        = "120s"

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_NEXT_OLDER"
      }

      trigger {
        count = 1
      }
    }
  }

  documentation {
    content = <<-EOT
      Uptime check failing for `${module.cloud_run.service_url}${var.uptime_check_path}`.

      This alert triggers when the Cloud Monitoring uptime check does not receive a 2xx
      response for at least 2 minutes.
    EOT

    mime_type = "text/markdown"
  }

  enabled = var.enable_uptime_alerts

  depends_on = [google_monitoring_uptime_check_config.api_ready]
}
