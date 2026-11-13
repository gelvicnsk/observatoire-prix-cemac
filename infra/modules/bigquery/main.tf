# Un dataset par couche. Les noms sont identiques en dev et en prod : l'isolation vient du projet.
locals {
  datasets = {
    bronze = "Copie brute des sources, chargée par le job d'ingestion"
    silver = "Données normalisées (staging et intermediate dbt)"
    gold   = "Faits, dimensions et marts prêts à consommer"
    meta   = "Journal de chargement, fichiers traités, lignes mises de côté, contrôles"
    ci     = "Modèles dbt construits par la CI ; tables supprimées au bout de 7 jours"
  }
  seven_days_ms = 7 * 24 * 60 * 60 * 1000
}

resource "google_bigquery_dataset" "layer" {
  for_each    = local.datasets
  project     = var.project_id
  dataset_id  = each.key
  location    = var.location
  description = each.value

  default_table_expiration_ms = each.key == "ci" ? local.seven_days_ms : null

  # Comme pour le bucket : destruction complète possible en dev seulement
  delete_contents_on_destroy = var.environment != "prod"

  labels = {
    project     = "observatoire-cemac"
    environment = var.environment
    layer       = each.key
  }
}
