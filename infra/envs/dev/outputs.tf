output "raw_bucket" {
  value = module.storage.raw_bucket
}

output "datasets" {
  value = module.bigquery.dataset_ids
}

output "service_accounts" {
  value = module.iam.service_accounts
}
