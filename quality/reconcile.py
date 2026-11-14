"""Étape 6 — rapprochement indépendant de dbt : recalcule en Python le prix mensuel au kg ou au litre et le
compare, ligne à ligne, à gold.fct_price_monthly.

Le calcul ne réutilise rien du SQL de dbt. Il repart des fichiers Parquet bronze (dernière version de chaque
pays, comme le prévoit l'ADR-005) et des trois référentiels versionnés (dbt/seeds), puis applique les mêmes
règles, écrites une seconde fois :

- lignes écartées : marché exclu, produit hors panier, unité exclue ou sans poids, prévision du PAM,
  ou sans correspondance dans un référentiel ;
- prix au kg ou au litre = prix / facteur de l'unité, arrondi à 4 décimales ;
- une ligne par pays, marché, produit (nom français), type de prix, unité de base et mois : moyenne arrondie.

Écart toléré : 0,0001 XAF par kg ou par litre (deux arrondis successifs). Toute clé manquante ou en trop,
tout nombre de relevés différent ou tout écart de prix fait échouer le script (code 1).

Usage :
    python -m quality.reconcile --project obs-cemac-dev-11259 --bucket obs-cemac-dev-11259-raw
    python -m quality.reconcile --local-root data/lake ...   (Parquet locaux, make ingest-local)
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

KEY = ["country_iso3", "market_name", "commodity_name_fr", "price_type", "base_unit", "price_month"]
FOUR_PLACES = Decimal("0.0001")
DEFAULT_TOLERANCE = Decimal("0.0001")


def _round4(value: Decimal) -> Decimal:
    # ROUND de BigQuery arrondit au plus loin de zéro : identique à ROUND_HALF_UP pour des prix positifs
    return value.quantize(FOUR_PLACES, rounding=ROUND_HALF_UP)


# --------------------------------------------------------------------------------------------------
# Lecture des Parquet bronze : dernière version par pays
# --------------------------------------------------------------------------------------------------


def _country_from_path(path: str) -> str | None:
    for part in path.split("/"):
        if part.startswith("country="):
            return part.split("=", 1)[1]
    return None


def latest_snapshots(files: Iterable[tuple[str, bytes]]) -> pd.DataFrame:
    """Lit les fichiers (chemin, contenu) et garde, pour chaque pays, la version ingérée en dernier."""
    best: dict[str, tuple[pd.Timestamp, pd.DataFrame]] = {}
    for path, content in files:
        country = _country_from_path(path)
        if country is None:
            continue
        frame = pq.read_table(io.BytesIO(content)).to_pandas()
        if frame.empty:
            continue
        ingested_at = frame["ingested_at"].max()
        if country not in best or ingested_at > best[country][0]:
            best[country] = (ingested_at, frame)
    if not best:
        raise RuntimeError("aucun fichier Parquet du PAM trouvé")
    return pd.concat([frame for _, frame in best.values()], ignore_index=True)


def local_files(root: Path) -> Iterator[tuple[str, bytes]]:
    for path in sorted(root.glob("wfp/country=*/ingest_date=*/*.parquet")):
        yield path.relative_to(root).as_posix(), path.read_bytes()


def gcs_files(bucket: str, project: str | None) -> Iterator[tuple[str, bytes]]:
    from google.cloud import storage

    client = storage.Client(project=project)
    for blob in client.list_blobs(bucket, prefix="wfp/"):
        if blob.name.endswith(".parquet"):
            yield blob.name, blob.download_as_bytes()


# --------------------------------------------------------------------------------------------------
# Recalcul
# --------------------------------------------------------------------------------------------------


def load_seeds(seeds_dir: Path) -> dict[str, pd.DataFrame]:
    return {
        name: pd.read_csv(seeds_dir / f"{name}.csv", dtype=str, keep_default_na=False)
        for name in ("commodity_mapping", "unit_conversion", "market_district")
    }


def expected_monthly(prices: pd.DataFrame, seeds: dict[str, pd.DataFrame]) -> pd.DataFrame:
    commodities = seeds["commodity_mapping"][["commodity_raw", "name_fr", "include_in_index"]]
    units = seeds["unit_conversion"][["unit_raw", "base_unit", "factor_to_base", "status"]]
    markets = seeds["market_district"][["country_iso3", "market_name", "status"]].rename(
        columns={"status": "market_status"}
    )

    frame = (
        prices.rename(columns={"market": "market_name", "pricetype": "price_type"})
        .merge(commodities, left_on="commodity", right_on="commodity_raw", how="inner")
        .merge(units, left_on="unit", right_on="unit_raw", how="inner")
        .merge(markets, on=["country_iso3", "market_name"], how="inner")
    )
    flag = frame["priceflag"].fillna("").str.lower()
    kept = frame[
        (frame["market_status"] != "exclu")
        & (frame["include_in_index"] == "true")
        & (frame["status"] == "converti")
        & ~flag.str.contains("forecast")
    ].copy()

    kept["price_xaf_per_unit"] = [
        _round4(Decimal(price) / Decimal(factor))
        for price, factor in zip(kept["price"], kept["factor_to_base"], strict=True)
    ]
    kept["price_month"] = [date(d.year, d.month, 1) for d in pd.to_datetime(kept["date"])]
    kept = kept.rename(columns={"name_fr": "commodity_name_fr"})

    rows = []
    for key, group in kept.groupby(KEY, sort=True):
        values = list(group["price_xaf_per_unit"])
        rows.append((*key, len(values), _round4(sum(values, Decimal(0)) / len(values))))
    return pd.DataFrame(rows, columns=[*KEY, "n_observations", "price_xaf_per_unit"])


# --------------------------------------------------------------------------------------------------
# Comparaison
# --------------------------------------------------------------------------------------------------

_ACTUAL_SQL = """
select f.country_iso3, m.market_name, c.commodity_name_fr, f.price_type, f.base_unit, f.price_month,
       f.n_observations, f.price_xaf_per_unit
from gold.fct_price_monthly as f
join gold.dim_market as m using (market_key)
join gold.dim_commodity as c using (commodity_key)
"""


def actual_monthly(project: str) -> pd.DataFrame:
    from google.cloud import bigquery

    rows = bigquery.Client(project=project).query(_ACTUAL_SQL).result()
    return pd.DataFrame([dict(row.items()) for row in rows], columns=[*KEY, "n_observations", "price_xaf_per_unit"])


@dataclass
class Report:
    expected_rows: int
    actual_rows: int
    missing_in_dbt: pd.DataFrame = field(repr=False)
    extra_in_dbt: pd.DataFrame = field(repr=False)
    count_mismatch: pd.DataFrame = field(repr=False)
    price_mismatch: pd.DataFrame = field(repr=False)

    @property
    def ok(self) -> bool:
        return all(f.empty for f in (self.missing_in_dbt, self.extra_in_dbt, self.count_mismatch, self.price_mismatch))


def compare(expected: pd.DataFrame, actual: pd.DataFrame, tolerance: Decimal = DEFAULT_TOLERANCE) -> Report:
    merged = expected.merge(actual, on=KEY, how="outer", suffixes=("_python", "_dbt"), indicator=True)
    both = merged[merged["_merge"] == "both"].copy()
    both["ecart"] = [
        abs(Decimal(str(a)) - Decimal(str(b)))
        for a, b in zip(both["price_xaf_per_unit_python"], both["price_xaf_per_unit_dbt"], strict=True)
    ]
    return Report(
        expected_rows=len(expected),
        actual_rows=len(actual),
        missing_in_dbt=merged[merged["_merge"] == "left_only"][KEY],
        extra_in_dbt=merged[merged["_merge"] == "right_only"][KEY],
        count_mismatch=both[both["n_observations_python"] != both["n_observations_dbt"]],
        price_mismatch=both[both["ecart"] > tolerance],
    )


def print_report(report: Report) -> None:
    print(
        f"lignes recalculées en Python : {report.expected_rows}, lignes dans fct_price_monthly : {report.actual_rows}"
    )
    for label, frame in (
        ("absentes de dbt", report.missing_in_dbt),
        ("en trop dans dbt", report.extra_in_dbt),
        ("nombre de relevés différent", report.count_mismatch),
        ("prix différent", report.price_mismatch),
    ):
        print(f"  {label:30} {len(frame)}")
        if not frame.empty:
            print(frame.head(10).to_string(index=False))
    print("RAPPROCHEMENT OK" if report.ok else "RAPPROCHEMENT EN ÉCHEC")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", default=os.environ.get("GCP_PROJECT_ID"))
    parser.add_argument("--bucket", default=os.environ.get("GCS_RAW_BUCKET"))
    parser.add_argument("--local-root", type=Path, help="lire les Parquet en local plutôt que dans le bucket")
    parser.add_argument("--seeds-dir", type=Path, default=Path("dbt/seeds"))
    parser.add_argument("--tolerance", type=Decimal, default=DEFAULT_TOLERANCE)
    args = parser.parse_args(argv)
    if not args.project or not (args.bucket or args.local_root):
        parser.error("indiquer --project et --bucket (ou --local-root)")

    files = local_files(args.local_root) if args.local_root else gcs_files(args.bucket, args.project)
    expected = expected_monthly(latest_snapshots(files), load_seeds(args.seeds_dir))
    report = compare(expected, actual_monthly(args.project), args.tolerance)
    print_report(report)
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
