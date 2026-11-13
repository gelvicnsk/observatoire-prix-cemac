variable "dev_project_id" {
  type        = string
  description = "Projet GCP de développement (héberge aussi l'état Terraform et l'accès GitHub)"
}

variable "prod_project_id" {
  type        = string
  description = "Projet GCP de production"
}

variable "region" {
  type    = string
  default = "europe-west1"
}

variable "github_repository" {
  type        = string
  description = "Seul dépôt autorisé à s'authentifier, au format propriétaire/nom"
  default     = "gelvicnsk/observatoire-prix-cemac"
}

variable "billing_account" {
  type        = string
  description = "Identifiant du compte de facturation (fourni par TF_VAR_billing_account, jamais versionné)"
  sensitive   = true
}
