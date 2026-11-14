# Identité de la CI dbt (étape 5, dernière partie).
#
# Chaque pull request construit les modèles modifiés dans le dataset ci (tables effacées après 7 jours),
# et lit le reste dans l'environnement dev (--defer). Le compte n'écrit donc que dans ci :
#
#   lit                                    écrit
#   bronze, silver, gold, bucket raw       ci
#
# Il est utilisable depuis n'importe quelle branche du dépôt, par le pool github-plan (sans clé).

resource "google_service_account" "dbt_ci" {
  project      = var.project_id
  account_id   = "sa-dbt-ci"
  display_name = "CI dbt (pull requests)"
}

locals {
  member    = "serviceAccount:${google_service_account.dbt_ci.email}"
  principal = "principalSet://iam.googleapis.com/projects/${var.project_number}/locations/global/workloadIdentityPools/${var.workload_identity_pool}/attribute.repository/${var.github_repository}"

  datasets = {
    bronze = "roles/bigquery.dataViewer"
    silver = "roles/bigquery.dataViewer"
    gold   = "roles/bigquery.dataViewer"
    ci     = "roles/bigquery.dataEditor"
  }
}

resource "google_project_iam_member" "job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = local.member
}

resource "google_bigquery_dataset_iam_member" "layer" {
  for_each   = local.datasets
  project    = var.project_id
  dataset_id = var.dataset_ids[each.key]
  role       = each.value
  member     = local.member
}

# Les tables bronze sont externes : les lire, c'est lire les Parquet du bucket raw
resource "google_storage_bucket_iam_member" "raw_reader" {
  bucket = var.raw_bucket
  role   = "roles/storage.objectViewer"
  member = local.member
}

resource "google_service_account_iam_member" "github" {
  service_account_id = google_service_account.dbt_ci.name
  role               = "roles/iam.workloadIdentityUser"
  member             = local.principal
}
