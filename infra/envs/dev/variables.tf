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

variable "monthly_budget_eur" {
  type    = number
  default = 10
}
