variable "project_id" {
  type = string
}

variable "project_number" {
  type        = string
  description = "Numéro du projet qui porte le pool Workload Identity (créé par le bootstrap)"
}

variable "raw_bucket" {
  type = string
}

variable "dataset_ids" {
  type        = map(string)
  description = "Datasets par couche (sortie du module bigquery)"
}

variable "github_repository" {
  type        = string
  description = "Dépôt autorisé, au format propriétaire/nom"
}

variable "workload_identity_pool" {
  type    = string
  default = "github-plan"
}
