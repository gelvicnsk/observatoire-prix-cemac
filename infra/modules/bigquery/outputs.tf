output "dataset_ids" {
  description = "Identifiants des datasets par couche (bronze, silver, gold, meta, ci)"
  value       = { for name, dataset in google_bigquery_dataset.layer : name => dataset.dataset_id }
}
