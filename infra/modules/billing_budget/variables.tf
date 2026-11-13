variable "billing_account" {
  type      = string
  sensitive = true
}

variable "project_number" {
  type = string
}

variable "environment" {
  type = string
}

variable "amount" {
  type        = number
  description = "Montant mensuel, en unités entières de la devise"
}

variable "currency" {
  type        = string
  description = "Doit être la devise du compte de facturation (EUR, USD…)"
}
