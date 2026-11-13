variable "project_id" {
  type        = string
  description = "Identifiant du projet GCP"
}

variable "region" {
  type    = string
  default = "europe-west1"
}

variable "github_repository" {
  type        = string
  description = "Dépôt autorisé, par exemple gelvicnsk/observatoire-prix-cemac"
}
