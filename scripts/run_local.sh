#!/usr/bin/env bash
# Ingestion puis dbt pour un mois, sur l'environnement dev. Implémenté à l'étape 4.
set -euo pipefail
MONTH="${1:?Usage : run_local.sh AAAA-MM}"
echo "Exécution locale pour $MONTH : étape 4"
