# Dépôt des images Docker du pipeline (étape 7). Un dépôt par projet : dev reçoit chaque image construite
# par le CD, prod reçoit une copie de la même image une fois la validation donnée.

resource "google_artifact_registry_repository" "images" {
  project       = var.project_id
  location      = var.region
  repository_id = "observatoire"
  format        = "DOCKER"
  description   = "Images du pipeline (ingestion, dbt, rapprochement), étiquetées par commit"

  # On garde les 10 images les plus récentes ; les autres sont effacées après 30 jours
  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "garder-10-recentes"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }

  cleanup_policies {
    id     = "effacer-anciennes"
    action = "DELETE"
    condition {
      older_than = "2592000s"
    }
  }

  labels = {
    project     = "observatoire-cemac"
    environment = var.environment
  }
}
