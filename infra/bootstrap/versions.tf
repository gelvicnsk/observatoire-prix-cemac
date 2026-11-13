terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
  # État local : le bootstrap crée justement le bucket qui stockera l'état des environnements.
}

provider "google" {
  project               = var.dev_project_id
  region                = var.region
  user_project_override = true
  billing_project       = var.dev_project_id
}
