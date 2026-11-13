#!/usr/bin/env bash
# Rejoue chaque mois entre deux bornes. Implémenté à l'étape 4.
set -euo pipefail
FROM="${1:?Usage : backfill.sh AAAA-MM AAAA-MM}"
TO="${2:?Usage : backfill.sh AAAA-MM AAAA-MM}"
echo "Backfill de $FROM à $TO : étape 4"
