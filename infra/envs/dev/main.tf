# Environnement dev : appelle les modules partagés avec ses propres variables.

data "google_project" "this" {
  project_id = var.project_id
}

module "storage" {
  source      = "../../modules/storage"
  project_id  = var.project_id
  region      = var.region
  environment = "dev"
}

module "bigquery" {
  source      = "../../modules/bigquery"
  project_id  = var.project_id
  location    = var.bq_location
  environment = "dev"
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
  environment     = "dev"
  amount          = var.budget_amount
  currency        = var.budget_currency
}

module "ci_dbt" {
  source            = "../../modules/ci_dbt"
  project_id        = var.project_id
  project_number    = data.google_project.this.number
  raw_bucket        = module.storage.raw_bucket
  dataset_ids       = module.bigquery.dataset_ids
  github_repository = var.github_repository
}

module "artifact_registry" {
  source      = "../../modules/artifact_registry"
  project_id  = var.project_id
  region      = var.region
  environment = "dev"
}

module "run_jobs" {
  source           = "../../modules/run_jobs"
  project_id       = var.project_id
  region           = var.region
  environment      = "dev"
  raw_bucket       = module.storage.raw_bucket
  bq_location      = var.bq_location
  dbt_target       = "dev"
  service_accounts = module.iam.service_accounts
}

module "scheduler" {
  source     = "../../modules/scheduler"
  project_id = var.project_id
  region     = var.region
  paused     = true

  schedules = {
    ingestion = { job_name = module.run_jobs.job_names["ingestion"], cron = "0 3 5 * *" }
    transform = { job_name = module.run_jobs.job_names["transform"], cron = "0 5 5 * *" }
  }
}
