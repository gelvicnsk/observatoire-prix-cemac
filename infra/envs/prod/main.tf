# Environnement prod : appelle les modules de infra/modules avec ses propres variables.
# Implémenté à l'étape 2.
provider "google" {
  project = var.project_id
  region  = var.region
}
