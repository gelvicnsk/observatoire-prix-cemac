"""Rapprochement Python / dbt (étape 6), sur des fichiers et des référentiels fictifs."""

import io
from datetime import UTC, date, datetime
from decimal import Decimal

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from quality.reconcile import KEY, compare, expected_monthly, latest_snapshots


def _parquet(rows, ingested_at):
    table = pa.table(
        {
            "date": pa.array([r[0] for r in rows], pa.date32()),
            "country_iso3": ["COG"] * len(rows),
            "market": [r[1] for r in rows],
            "commodity": [r[2] for r in rows],
            "unit": [r[3] for r in rows],
            "priceflag": [r[4] for r in rows],
            "pricetype": ["Retail"] * len(rows),
            "price": pa.array([Decimal(r[5]) for r in rows], pa.decimal128(18, 4)),
            "ingested_at": pa.array([ingested_at] * len(rows), pa.timestamp("us", tz="UTC")),
        }
    )
    buffer = io.BytesIO()
    pq.write_table(table, buffer)
    return buffer.getvalue()


SEEDS = {
    "commodity_mapping": pd.DataFrame(
        {"commodity_raw": ["Rice", "Fuel"], "name_fr": ["Riz", "Carburant"], "include_in_index": ["true", "false"]}
    ),
    "unit_conversion": pd.DataFrame(
        {
            "unit_raw": ["KG", "50 KG", "Sack"],
            "base_unit": ["kg", "kg", "piece"],
            "factor_to_base": ["1.0", "50.0", ""],
            "status": ["converti", "converti", "sans_poids"],
        }
    ),
    "market_district": pd.DataFrame(
        {"country_iso3": ["COG", "COG"], "market_name": ["Total", "National Average"], "status": ["auto", "exclu"]}
    ),
}

OLD = datetime(2026, 1, 1, tzinfo=UTC)
NEW = datetime(2026, 2, 1, tzinfo=UTC)
ROWS = [
    (date(2025, 1, 15), "Total", "Rice", "KG", "actual", "600"),
    (date(2025, 1, 15), "Total", "Rice", "50 KG", "actual", "27500"),  # 550 par kg
    (date(2025, 1, 15), "Total", "Rice", "Sack", "actual", "9000"),  # sans poids : écarté
    (date(2025, 1, 15), "Total", "Fuel", "KG", "actual", "800"),  # hors panier : écarté
    (date(2025, 1, 15), "National Average", "Rice", "KG", "actual", "610"),  # marché exclu
    (date(2025, 2, 15), "Total", "Rice", "KG", "forecast", "700"),  # prévision : écartée
    (date(2025, 2, 15), "Total", "Rice", "50 KG", "aggregate", "32516.6675"),  # 650,33335 -> 650,3334
]


def _expected():
    files = [
        ("wfp/country=COG/ingest_date=2026-01-01/a.parquet", _parquet([ROWS[0]], OLD)),
        ("wfp/country=COG/ingest_date=2026-02-01/b.parquet", _parquet(ROWS, NEW)),
    ]
    return expected_monthly(latest_snapshots(files), SEEDS)


def test_expected_monthly_applies_the_rules():
    expected = _expected()
    assert len(expected) == 2
    january, february = expected.to_dict("records")
    assert (january["price_month"], january["n_observations"], january["price_xaf_per_unit"]) == (
        date(2025, 1, 1),
        2,
        Decimal("575.0000"),
    )
    assert (february["n_observations"], february["price_xaf_per_unit"]) == (1, Decimal("650.3334"))


def test_compare_detects_every_kind_of_difference():
    expected = _expected()
    assert compare(expected, expected.copy()).ok

    actual = expected.copy()
    actual.loc[0, "price_xaf_per_unit"] = Decimal("575.0002")
    actual.loc[1, "n_observations"] = 3
    extra = pd.DataFrame(
        [["COG", "Total", "Riz", "Retail", "kg", date(2025, 3, 1), 1, Decimal("1")]],
        columns=[*KEY, "n_observations", "price_xaf_per_unit"],
    )
    report = compare(expected, pd.concat([actual, extra], ignore_index=True))

    assert not report.ok
    assert (len(report.price_mismatch), len(report.count_mismatch), len(report.extra_in_dbt)) == (1, 1, 1)
    assert report.missing_in_dbt.empty


def test_tolerance_absorbs_a_rounding_step():
    expected = _expected()
    actual = expected.copy()
    actual.loc[0, "price_xaf_per_unit"] = Decimal("575.0001")
    assert compare(expected, actual).ok
