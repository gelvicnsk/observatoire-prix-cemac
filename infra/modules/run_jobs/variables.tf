variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "environment" {
  type = string
}

variable "raw_bucket" {
  type = string
}

variable "bq_location" {
  type = string
}

variable "dbt_target" {
  type        = string
  description = "Cible dbt du job transform (dev ou prod)"
}

variable "service_accounts" {
  type        = object({ ingestion = string, dbt = string })
  description = "Comptes de service des jobs (sortie du module iam)"
}

variable "initial_image" {
  type        = string
  description = "Image de départ, remplacée par le CD à chaque déploiement"
  default     = "us-docker.pkg.dev/cloudrun/container/job:latest"
}
