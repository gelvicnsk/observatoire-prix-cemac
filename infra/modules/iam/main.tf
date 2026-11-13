# Un compte de service par usage, avec le strict nécessaire :
#
#   compte      lit                      écrit
#   ingestion   sources publiques        bucket raw, bronze, meta
#   dbt         raw, bronze              silver, gold, meta
#   dashboard   gold                     rien

resource "google_service_account" "ingestion" {
  project      = var.project_id
  account_id   = "sa-ingestion"
  display_name = "Job d'ingestion"
}

resource "google_service_account" "dbt" {
  project      = var.project_id
  account_id   = "sa-dbt"
  display_name = "Job dbt"
}

resource "google_service_account" "dashboard" {
  project      = var.project_id
  account_id   = "sa-dashboard"
  display_name = "Lecture du tableau de bord"
}

locals {
  sa = {
    ingestion = "serviceAccount:${google_service_account.ingestion.email}"
    dbt       = "serviceAccount:${google_service_account.dbt.email}"
    dashboard = "serviceAccount:${google_service_account.dashboard.email}"
  }

  dataset_bindings = {
    ingestion_bronze = { dataset = "bronze", role = "roles/bigquery.dataEditor", member = local.sa.ingestion }
    ingestion_meta   = { dataset = "meta", role = "roles/bigquery.dataEditor", member = local.sa.ingestion }
    dbt_bronze       = { dataset = "bronze", role = "roles/bigquery.dataViewer", member = local.sa.dbt }
    dbt_silver       = { dataset = "silver", role = "roles/bigquery.dataEditor", member = local.sa.dbt }
    dbt_gold         = { dataset = "gold", role = "roles/bigquery.dataEditor", member = local.sa.dbt }
    dbt_meta         = { dataset = "meta", role = "roles/bigquery.dataEditor", member = local.sa.dbt }
    dashboard_gold   = { dataset = "gold", role = "roles/bigquery.dataViewer", member = local.sa.dashboard }
  }
}

# Lancer des requêtes BigQuery (facturées au projet) : nécessaire aux trois comptes
resource "google_project_iam_member" "job_user" {
  for_each = local.sa
  project  = var.project_id
  role     = "roles/bigquery.jobUser"
  member   = each.value
}

resource "google_bigquery_dataset_iam_member" "layer" {
  for_each   = local.dataset_bindings
  project    = var.project_id
  dataset_id = var.dataset_ids[each.value.dataset]
  role       = each.value.role
  member     = each.value.member
}

# Bucket raw : l'ingestion écrit, dbt lit (tables externes sur les Parquet)
resource "google_storage_bucket_iam_member" "raw_writer" {
  bucket = var.raw_bucket
  role   = "roles/storage.objectAdmin"
  member = local.sa.ingestion
}

resource "google_storage_bucket_iam_member" "raw_reader" {
  bucket = var.raw_bucket
  role   = "roles/storage.objectViewer"
  member = local.sa.dbt
}
