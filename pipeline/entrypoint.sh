#!/usr/bin/env bash
# Point d'entrée de l'image (étape 7). Une étape par Cloud Run Job :
#   ingest     sources publiques -> bucket raw, tables externes bronze, journal meta
#   ingest     rejoue d'abord la quarantaine, puis collecte les sources (ADR-012)
#   transform  dbt (seeds, modèles, contrôles) puis rapprochement Python indépendant, puis rapport Elementary
#              et documentation dbt (lineage)
# Toute erreur arrête le job avec un code non nul : l'exécution apparaît en échec dans Cloud Run.
# Variables attendues : GCP_PROJECT_ID, GCS_RAW_BUCKET, BQ_LOCATION, DBT_TARGET (dev ou prod).
set -euo pipefail

step="${1:-}"
: "${GCP_PROJECT_ID:?GCP_PROJECT_ID manquant}"
: "${GCS_RAW_BUCKET:?GCS_RAW_BUCKET manquant}"

case "$step" in
  ingest)
    # D'abord les fichiers en quarantaine : une correction déployée les fait passer sans attendre (ADR-012)
    echo "== rejeu de la quarantaine"
    python -m ingestion.replay --target gcp
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
    # Le rapport ne doit jamais faire échouer le job : les contrôles ont déjà tous tourné
    echo "== rapport Elementary"
    if edr report --project-dir /app/dbt --profiles-dir /app/dbt --profile-target "$target" \
         --file-path /tmp/elementary_report.html --open-browser false; then
      python -m pipeline.publish_report /tmp/elementary_report.html elementary || echo "rapport : envoi impossible"
    else
      echo "rapport : génération impossible, voir ci-dessus"
    fi
    # Documentation et lineage dbt, en une seule page : branche verte et branche rouge (quarantaine)
    echo "== documentation dbt"
    if (cd /app/dbt && dbt docs generate --target "$target" --static > /dev/null); then
      python -m pipeline.publish_report /app/dbt/target/static_index.html dbt-docs || echo "docs : envoi impossible"
    else
      echo "docs : génération impossible"
    fi
    ;;
  *)
    echo "usage : entrypoint.sh ingest|transform" >&2
    exit 2
    ;;
esac
