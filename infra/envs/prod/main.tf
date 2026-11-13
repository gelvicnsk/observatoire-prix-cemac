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
