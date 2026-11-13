provider "google" {
  project = var.project_id
  region  = var.region

  # Les appels (budgets notamment) sont comptés sur ce projet, pas sur un projet partagé
  user_project_override = true
  billing_project       = var.project_id
}
