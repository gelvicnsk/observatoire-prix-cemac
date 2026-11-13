# Bucket raw : les fichiers sources convertis en Parquet, partitionnés par source, pays et mois.
resource "google_storage_bucket" "raw" {
  name                        = "${var.project_id}-raw"
  project                     = var.project_id
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  # En dev, `terraform destroy` doit pouvoir tout supprimer ; en prod, jamais avec des données dedans.
  force_destroy = var.environment != "prod"

  versioning {
    enabled = false
  }

  labels = {
    project     = "observatoire-cemac"
    environment = var.environment
    layer       = "raw"
  }
}
