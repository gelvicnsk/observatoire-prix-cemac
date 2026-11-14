output "service_account" {
  value = google_service_account.dbt_ci.email
}
