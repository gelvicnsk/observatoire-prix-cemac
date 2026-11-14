variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "schedules" {
  type        = map(object({ job_name = string, cron = string }))
  description = "Un déclenchement par job : nom du job Cloud Run et expression cron (heure de Paris)"
}

variable "paused" {
  type        = bool
  description = "true en dev : les jobs n'y tournent que lors du déploiement (test de fumée)"
  default     = false
}
