"""Rejoue les fichiers en quarantaine (ADR-012).

Pour chaque objet sous `_quarantine/`, reconstruit le fichier d'origine et le retraite avec le pipeline normal.
S'il passe, il est enregistré comme n'importe quel fichier, journalisé `success`, et retiré de la quarantaine.
S'il est encore refusé, il reste en quarantaine (journalisé `quarantined` une nouvelle fois).

Le job d'ingestion lance ce rejeu avant la collecte du mois : une correction déployée fait donc sortir les
fichiers de quarantaine à la prochaine exécution, sans intervention.

Usage : python -m ingestion.replay [--target local|gcp] [--local-root data/lake]
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import date
from pathlib import Path

from ingestion.config import Settings
from ingestion.pipeline import QUARANTINE_PREFIX, Outcome, process, quarantine, raw_from_quarantine_path


def replay(store, meta, run_id: str, today: date) -> list[Outcome]:
    outcomes = []
    for path in store.list(QUARANTINE_PREFIX):
        raw = raw_from_quarantine_path(path, store.read_bytes(path))
        try:
            outcome = process(raw, store, meta, today, run_id)
        except Exception as error:  # noqa: BLE001 - toujours refusé : il reste en quarantaine
            outcome = quarantine(raw, error, store, meta, today, run_id)
            if not outcome.message.endswith(path):
                store.delete(path)  # même fichier, nouveau chemin daté : on ne garde qu'une copie
        else:
            store.delete(path)
        outcomes.append(outcome)
    return outcomes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", choices=["local", "gcp"], default="local")
    parser.add_argument("--local-root", default="data/lake")
    args = parser.parse_args(argv)

    run_id = f"replay-{uuid.uuid4().hex[:8]}"
    if args.target == "gcp":
        from ingestion.meta import BigQueryMeta
        from ingestion.storage import GcsStore

        settings = Settings()
        store = GcsStore(settings.gcs_raw_bucket, project=settings.gcp_project_id)
        meta = BigQueryMeta(settings.gcp_project_id, settings.bq_location)
    else:
        from ingestion.meta import LocalMeta
        from ingestion.storage import LocalStore

        root = Path(args.local_root)
        store, meta = LocalStore(root), LocalMeta(root / "_meta")

    outcomes = replay(store, meta, run_id, date.today())
    print(f"Rejeu {run_id} : {len(outcomes)} fichier(s) en quarantaine")
    for outcome in outcomes:
        print(f"  {outcome.status:<11} {outcome.source:<11} {outcome.partition_key:<20} {outcome.message[:100]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
