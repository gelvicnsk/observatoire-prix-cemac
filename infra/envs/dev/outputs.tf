output "raw_bucket" {
  value = module.storage.raw_bucket
}

output "datasets" {
  value = module.bigquery.dataset_ids
}

output "service_accounts" {
  value = module.iam.service_accounts
}

output "dbt_ci_service_account" {
  description = "À copier dans la variable GitHub DBT_CI_SA"
  value       = module.ci_dbt.service_account
}
