#!/usr/bin/env bash
# Point d'entrée de l'image (étape 7). Une étape par Cloud Run Job :
#   ingest     sources publiques -> bucket raw, tables externes bronze, journal meta
#   transform  dbt (seeds, modèles, 118 contrôles) puis rapprochement Python indépendant
# Toute erreur arrête le job avec un code non nul : l'exécution apparaît en échec dans Cloud Run.
# Variables attendues : GCP_PROJECT_ID, GCS_RAW_BUCKET, BQ_LOCATION, DBT_TARGET (dev ou prod).
set -euo pipefail

step="${1:-}"
: "${GCP_PROJECT_ID:?GCP_PROJECT_ID manquant}"
: "${GCS_RAW_BUCKET:?GCS_RAW_BUCKET manquant}"

case "$step" in
  ingest)
    echo "== ingestion ($GCP_PROJECT_ID)"
    python -m ingestion.main --target gcp
    ;;
  transform)
    target="${DBT_TARGET:?DBT_TARGET manquant}"
    cd /app/dbt
    echo "== fraîcheur des sources (avertissement seulement)"
    dbt source freshness --target "$target" || echo "fraîcheur : au moins une source en retard, voir ci-dessus"
    echo "== dbt build --target $target"
    dbt build --target "$target"
    cd /app
    echo "== rapprochement Python / dbt"
    python -m quality.reconcile --project "$GCP_PROJECT_ID" --bucket "$GCS_RAW_BUCKET"
    ;;
  *)
    echo "usage : entrypoint.sh ingest|transform" >&2
    exit 2
    ;;
esac
