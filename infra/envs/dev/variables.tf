variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "europe-west1"
}

variable "bq_location" {
  type    = string
  default = "EU"
}

variable "billing_account" {
  type        = string
  description = "Fourni par TF_VAR_billing_account (jamais versionné)"
  sensitive   = true
}

variable "budget_amount" {
  type    = number
  default = 5
}

variable "budget_currency" {
  type        = string
  description = "Devise du compte de facturation (TF_VAR_budget_currency)"
  default     = "EUR"
}
