output "tfstate_bucket" {
  description = "Bucket de l'état Terraform (à reporter dans infra/envs/*/backend.hcl)"
  value       = google_storage_bucket.tfstate.name
}

output "tf_plan_service_account" {
  value = google_service_account.tf_plan.email
}

output "tf_apply_service_account" {
  value = google_service_account.tf_apply.email
}

output "wif_provider_plan" {
  description = "À utiliser dans GitHub Actions pour les pull requests (étape 3)"
  value       = google_iam_workload_identity_pool_provider.github["github-plan"].name
}

output "wif_provider_apply" {
  description = "À utiliser dans GitHub Actions sur la branche main (étape 3)"
  value       = google_iam_workload_identity_pool_provider.github["github-apply"].name
}
