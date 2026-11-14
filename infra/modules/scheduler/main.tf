# Lancement mensuel des deux jobs par Cloud Scheduler (étape 7), sans orchestrateur (ADR-002, ADR-010) :
# l'ingestion le 5 du mois à 3 h, la transformation à 5 h, heure de Paris. Si l'ingestion échoue, la
# transformation repart des données bronze déjà présentes : elle est idempotente et ne perd rien.
#
# Le compte sa-scheduler n'a qu'un droit : lancer les jobs Cloud Run du projet.

resource "google_service_account" "scheduler" {
  project      = var.project_id
  account_id   = "sa-scheduler"
  display_name = "Cloud Scheduler (lancement des jobs)"
}

resource "google_project_iam_member" "run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.scheduler.email}"
}

resource "google_cloud_scheduler_job" "monthly" {
  for_each         = var.schedules
  project          = var.project_id
  region           = var.region
  name             = "${each.value.job_name}-mensuel"
  description      = "Lance ${each.value.job_name} chaque mois"
  schedule         = each.value.cron
  time_zone        = "Europe/Paris"
  paused           = var.paused
  attempt_deadline = "180s"

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${each.value.job_name}:run"

    oauth_token {
      service_account_email = google_service_account.scheduler.email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }

  depends_on = [google_project_iam_member.run_invoker]
}
