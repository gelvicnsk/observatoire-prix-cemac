output "service_accounts" {
  value = {
    ingestion = google_service_account.ingestion.email
    dbt       = google_service_account.dbt.email
    dashboard = google_service_account.dashboard.email
  }
}
