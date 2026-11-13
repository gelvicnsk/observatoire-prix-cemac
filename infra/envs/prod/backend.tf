# Configuration partielle : bucket et préfixe sont dans backend.hcl
# (terraform init -backend-config=backend.hcl, lancé par `make tf-plan`).
terraform {
  backend "gcs" {}
}
