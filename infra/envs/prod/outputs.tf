output "raw_bucket" {
  value = module.storage.raw_bucket
}

output "datasets" {
  value = module.bigquery.dataset_ids
}

output "service_accounts" {
  value = module.iam.service_accounts
}

output "image_repository" {
  value = module.artifact_registry.repository_url
}

output "run_jobs" {
  value = module.run_jobs.job_names
}
