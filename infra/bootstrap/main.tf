# Lancé UNE fois en local, avec ton compte (propriétaire des projets).
# Crée ce dont la CI aura besoin avant de pouvoir lancer Terraform elle-même :
#   1. les API des deux projets ;
#   2. le bucket qui stocke l'état Terraform des environnements ;
#   3. l'accès GitHub sans clé (Workload Identity Federation), en deux pools :
#        - github-plan  : n'importe quelle branche du dépôt  -> compte tf-plan  (lecture seule)
#        - github-apply : uniquement la branche main          -> compte tf-apply (écriture)

locals {
  projects = {
    dev  = var.dev_project_id
    prod = var.prod_project_id
  }

  apis = [
    "artifactregistry.googleapis.com",
    "bigquery.googleapis.com",
    "billingbudgets.googleapis.com",
    "cloudbilling.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudscheduler.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "serviceusage.googleapis.com",
    "storage.googleapis.com",
    "sts.googleapis.com",
  ]

  project_apis = {
    for pair in setproduct(keys(local.projects), local.apis) :
    "${pair[0]}-${pair[1]}" => { project = local.projects[pair[0]], api = pair[1] }
  }

  # Rôles du compte tf-plan : lire toute la configuration, y compris les politiques IAM
  plan_roles = [
    "roles/viewer",
    "roles/iam.securityReviewer",
  ]

  # Rôles du compte tf-apply : créer et modifier l'infrastructure décrite dans infra/
  apply_roles = [
    "roles/editor",
    "roles/bigquery.admin",
    "roles/storage.admin",
    "roles/iam.serviceAccountAdmin",
    "roles/resourcemanager.projectIamAdmin",
    "roles/serviceusage.serviceUsageAdmin",
  ]
}


# ---------------------------------------------------------------- API
resource "google_project_service" "apis" {
  for_each           = local.project_apis
  project            = each.value.project
  service            = each.value.api
  disable_on_destroy = false
}

# ---------------------------------------------------------------- État Terraform
resource "google_storage_bucket" "tfstate" {
  name                        = "${var.dev_project_id}-tfstate"
  project                     = var.dev_project_id
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning {
    enabled = true
  }

  # On garde les 10 dernières versions de chaque état
  lifecycle_rule {
    condition {
      num_newer_versions = 10
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    project = "observatoire-cemac"
    usage   = "terraform-state"
  }

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------- Comptes de service de la CI
resource "google_service_account" "tf_plan" {
  project      = var.dev_project_id
  account_id   = "tf-plan"
  display_name = "Terraform plan (CI, lecture seule)"
  depends_on   = [google_project_service.apis]
}

resource "google_service_account" "tf_apply" {
  project      = var.dev_project_id
  account_id   = "tf-apply"
  display_name = "Terraform apply (CI, branche main uniquement)"
  depends_on   = [google_project_service.apis]
}

resource "google_project_iam_member" "plan" {
  for_each = {
    for pair in setproduct(keys(local.projects), local.plan_roles) :
    "${pair[0]}-${pair[1]}" => { project = local.projects[pair[0]], role = pair[1] }
  }
  project = each.value.project
  role    = each.value.role
  member  = "serviceAccount:${google_service_account.tf_plan.email}"
}

resource "google_project_iam_member" "apply" {
  for_each = {
    for pair in setproduct(keys(local.projects), local.apply_roles) :
    "${pair[0]}-${pair[1]}" => { project = local.projects[pair[0]], role = pair[1] }
  }
  project = each.value.project
  role    = each.value.role
  member  = "serviceAccount:${google_service_account.tf_apply.email}"
}

# Les deux comptes lisent et verrouillent l'état (le verrou est un fichier dans le bucket)
resource "google_storage_bucket_iam_member" "tfstate" {
  for_each = {
    plan  = google_service_account.tf_plan.email
    apply = google_service_account.tf_apply.email
  }
  bucket = google_storage_bucket.tfstate.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${each.value}"
}

# Budgets : tf-plan lit, tf-apply gère
resource "google_billing_account_iam_member" "plan" {
  billing_account_id = var.billing_account
  role               = "roles/billing.viewer"
  member             = "serviceAccount:${google_service_account.tf_plan.email}"
}

resource "google_billing_account_iam_member" "apply" {
  billing_account_id = var.billing_account
  role               = "roles/billing.costsManager"
  member             = "serviceAccount:${google_service_account.tf_apply.email}"
}

# ---------------------------------------------------------------- Workload Identity Federation
resource "google_iam_workload_identity_pool" "github" {
  for_each                  = toset(["github-plan", "github-apply"])
  project                   = var.dev_project_id
  workload_identity_pool_id = each.key
  display_name              = each.key
  description               = each.key == "github-apply" ? "GitHub Actions, branche main uniquement" : "GitHub Actions, toutes les branches"
  depends_on                = [google_project_service.apis]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  for_each                           = google_iam_workload_identity_pool.github
  project                            = var.dev_project_id
  workload_identity_pool_id          = each.value.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-oidc"
  display_name                       = "GitHub OIDC"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  # Seul ce dépôt est accepté ; le pool apply exige en plus la branche main
  attribute_condition = (
    each.key == "github-apply"
    ? "assertion.repository == '${var.github_repository}' && assertion.ref == 'refs/heads/main'"
    : "assertion.repository == '${var.github_repository}'"
  )

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "plan_wif" {
  service_account_id = google_service_account.tf_plan.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github["github-plan"].name}/attribute.repository/${var.github_repository}"
}

resource "google_service_account_iam_member" "apply_wif" {
  service_account_id = google_service_account.tf_apply.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github["github-apply"].name}/attribute.repository/${var.github_repository}"
}
