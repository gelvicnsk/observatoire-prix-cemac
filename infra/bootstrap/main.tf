# Lancé UNE fois en local : bucket de l'état Terraform (versionné)
# et Workload Identity Federation pour GitHub Actions. Implémenté à l'étape 2.
terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
