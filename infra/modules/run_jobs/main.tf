# Deux Cloud Run Jobs sur la même image (ADR-010), chacun avec son compte de service :
#   obs-ingestion  sa-ingestion  sources publiques -> raw, bronze, meta
#   obs-transform  sa-dbt        dbt build puis rapprochement Python
#
# Terraform crée les jobs avec une image de départ publique ; le CD y met ensuite l'image du commit
# (gcloud run jobs update). Terraform ignore donc l'image : sinon chaque apply reviendrait en arrière.

locals {
  jobs = {
    ingestion = { args = ["ingest"], service_account = var.service_accounts.ingestion }
    transform = { args = ["transform"], service_account = var.service_accounts.dbt }
  }

  env = {
    GCP_PROJECT_ID = var.project_id
    GCS_RAW_BUCKET = var.raw_bucket
    BQ_LOCATION    = var.bq_location
    DBT_TARGET     = var.dbt_target
  }
}

resource "google_cloud_run_v2_job" "job" {
  for_each            = local.jobs
  project             = var.project_id
  location            = var.region
  name                = "obs-${each.key}"
  deletion_protection = var.environment == "prod"

  labels = {
    project     = "observatoire-cemac"
    environment = var.environment
  }

  template {
    task_count = 1

    template {
      service_account = each.value.service_account
      timeout         = "1800s"
      max_retries     = 1

      containers {
        image = var.initial_image
        args  = each.value.args

        resources {
          limits = {
            cpu    = "1"
            memory = "2Gi"
          }
        }

        dynamic "env" {
          for_each = local.env
          content {
            name  = env.key
            value = env.value
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].template[0].containers[0].image,
      client,
      client_version,
    ]
  }
}
