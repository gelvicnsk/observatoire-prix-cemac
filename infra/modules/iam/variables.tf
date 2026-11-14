variable "project_id" {
  type = string
}

variable "raw_bucket" {
  type        = string
  description = "Nom du bucket raw (sortie du module storage)"
}

variable "dataset_ids" {
  type        = map(string)
  description = "Datasets par couche (sortie du module bigquery)"
}

variable "reports_bucket" {
  type        = string
  description = "Nom du bucket des rapports (sortie du module storage)"
}
