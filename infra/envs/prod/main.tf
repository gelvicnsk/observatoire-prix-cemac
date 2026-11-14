# Environnement prod : appelle les modules partagés avec ses propres variables.

data "google_project" "this" {
  project_id = var.project_id
}

module "storage" {
  source      = "../../modules/storage"
  project_id  = var.project_id
  region      = var.region
  environment = "prod"
}

module "bigquery" {
  source      = "../../modules/bigquery"
  project_id  = var.project_id
  location    = var.bq_location
  environment = "prod"
}

module "iam" {
  source      = "../../modules/iam"
  project_id  = var.project_id
  raw_bucket  = module.storage.raw_bucket
  dataset_ids = module.bigquery.dataset_ids
}

module "budget" {
  source          = "../../modules/billing_budget"
  billing_account = var.billing_account
  project_number  = data.google_project.this.number
  environment     = "prod"
  amount          = var.budget_amount
  currency        = var.budget_currency
}

module "artifact_registry" {
  source      = "../../modules/artifact_registry"
  project_id  = var.project_id
  region      = var.region
  environment = "prod"
}

module "run_jobs" {
  source           = "../../modules/run_jobs"
  project_id       = var.project_id
  region           = var.region
  environment      = "prod"
  raw_bucket       = module.storage.raw_bucket
  bq_location      = var.bq_location
  dbt_target       = "prod"
  service_accounts = module.iam.service_accounts
}

module "scheduler" {
  source     = "../../modules/scheduler"
  project_id = var.project_id
  region     = var.region
  paused     = false

  schedules = {
    ingestion = { job_name = module.run_jobs.job_names["ingestion"], cron = "0 3 5 * *" }
    transform = { job_name = module.run_jobs.job_names["transform"], cron = "0 5 5 * *" }
  }
}
