variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "environment" {
  type = string
  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment doit valoir dev ou prod."
  }
}
