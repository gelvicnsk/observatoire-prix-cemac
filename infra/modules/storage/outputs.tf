output "raw_bucket" {
  value = google_storage_bucket.raw.name
}

output "reports_bucket" {
  value = google_storage_bucket.reports.name
}
