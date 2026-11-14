output "repository_url" {
  description = "Préfixe des images, ex. europe-west1-docker.pkg.dev/<projet>/observatoire"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}
