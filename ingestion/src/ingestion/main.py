"""Point d'entrée du job d'ingestion.

    python -m ingestion.main --target local            # écrit dans data/lake (aucun accès GCP)
    python -m ingestion.main --target gcp              # bucket raw + dataset meta + tables bronze
    python -m ingestion.main --sources wfp --countries COG,CMR

Chaque run télécharge l'historique complet publié par chaque source ; seuls les fichiers dont
l'empreinte a changé sont écrits. Code de sortie 1 si au moins un fichier a échoué.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import date
from pathlib import Path

import httpx

from ingestion.config import CEMAC_COUNTRIES, HTTP_USER_AGENT, Settings
from ingestion.hdx import HdxClient
from ingestion.meta import BigQueryMeta, LocalMeta
from ingestion.pipeline import Outcome, fail, process
from ingestion.sources import exchange_rates, hdx_rainfall, hdx_wfp, world_bank
from ingestion.storage import GcsStore, LocalStore

ALL_SOURCES = ("wfp", "rainfall", "world_bank", "fx")


def build_http() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": HTTP_USER_AGENT}, timeout=httpx.Timeout(60.0), follow_redirects=True)


def run(
    sources: list[str],
    countries: list[str],
    store,
    meta,
    ingest_date: date,
    run_id: str,
    hdx: HdxClient,
    http: httpx.Client,
) -> list[Outcome]:
    outcomes: list[Outcome] = []

    def attempt(source: str, partition_key: str, fetch) -> None:
        try:
            raw = fetch()
        except hdx_wfp.DatasetNotFound as error:
            outcomes.append(Outcome(source, partition_key, "skipped", 0, str(error)))
            return
        except Exception as error:  # noqa: BLE001 - un échec de source ne doit pas arrêter les autres
            outcomes.append(fail(source, partition_key, error, meta, run_id))
            return
        try:
            outcomes.append(process(raw, store, meta, ingest_date, run_id))
        except Exception as error:  # noqa: BLE001
            outcomes.append(fail(source, partition_key, error, meta, run_id))

    if "wfp" in sources:
        for iso3 in countries:
            attempt("wfp", f"country={iso3}", lambda iso3=iso3: hdx_wfp.fetch(hdx, iso3))
    if "rainfall" in sources:
        for iso3 in countries:
            attempt("rainfall", f"country={iso3}", lambda iso3=iso3: hdx_rainfall.fetch(hdx, iso3))
    if "world_bank" in sources:
        for indicator in world_bank.INDICATORS:
            attempt(
                "world_bank",
                f"indicator={indicator}",
                lambda indicator=indicator: world_bank.fetch(http, countries, indicator),
            )
    if "fx" in sources:
        attempt("fx", "all", lambda: exchange_rates.fetch(http))
    return outcomes


def main(argv: list[str] | None = None, hdx: HdxClient | None = None, http: httpx.Client | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingestion des sources publiques CEMAC")
    parser.add_argument("--target", choices=["local", "gcp"], default="local")
    parser.add_argument("--sources", default=",".join(ALL_SOURCES))
    parser.add_argument("--countries", default=",".join(CEMAC_COUNTRIES))
    parser.add_argument("--ingest-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--local-root", default="data/lake", help="dossier du mode local")
    args = parser.parse_args(argv)

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    countries = [c.strip().upper() for c in args.countries.split(",") if c.strip()]
    unknown = [s for s in sources if s not in ALL_SOURCES] + [c for c in countries if c not in CEMAC_COUNTRIES]
    if unknown:
        print(f"Valeurs inconnues : {', '.join(unknown)}", file=sys.stderr)
        return 2

    run_id = uuid.uuid4().hex
    settings = Settings()
    if args.target == "gcp":
        if not settings.gcp_project_id or not settings.gcs_raw_bucket:
            print("GCP_PROJECT_ID et GCS_RAW_BUCKET doivent être définis (fichier .env).", file=sys.stderr)
            return 2
        store = GcsStore(settings.gcs_raw_bucket, project=settings.gcp_project_id)
        meta = BigQueryMeta(settings.gcp_project_id, settings.bq_location)
    else:
        root = Path(args.local_root)
        store = LocalStore(root)
        meta = LocalMeta(root / "_meta")

    own_hdx, own_http = hdx is None, http is None
    hdx = hdx or HdxClient()
    http = http or build_http()
    try:
        outcomes = run(sources, countries, store, meta, args.ingest_date, run_id, hdx, http)
    finally:
        if own_hdx:
            hdx.close()
        if own_http:
            http.close()

    print(f"Run {run_id} — {args.target} — ingest_date={args.ingest_date.isoformat()}")
    for outcome in outcomes:
        print(f"  {outcome.status:<8} {outcome.source:<11} {outcome.partition_key:<28} {outcome.message}")

    if args.target == "gcp":
        from ingestion.bigquery_tables import ensure_external_tables

        written = sorted({o.source for o in outcomes if o.status in ("success", "skipped")})
        try:
            tables = ensure_external_tables(
                settings.gcp_project_id, settings.bq_location, settings.gcs_raw_bucket, written
            )
            print(f"Tables externes à jour : {', '.join(tables)}")
        except Exception as error:  # noqa: BLE001
            print(f"Tables externes non mises à jour : {error}", file=sys.stderr)
            return 1

    failed = [o for o in outcomes if o.status == "failed"]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
