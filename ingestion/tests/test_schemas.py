"""Contrat des fichiers sources : types explicites, refus de charger faux."""

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pytest

from ingestion.profiling import read_csv_as_text
from ingestion.schemas import (
    SchemaError,
    fx_to_table,
    to_parquet_bytes,
    wfp_to_table,
    world_bank_to_table,
)

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 11, 13, 20, 0, tzinfo=UTC)


def clean_wfp() -> pd.DataFrame:
    frame = read_csv_as_text(FIXTURES / "wfp_sample.csv")
    # Le fichier d'exemple contient volontairement des valeurs invalides : on garde les lignes valides
    return frame[frame["date"].str.match(r"\d{4}-\d{2}-\d{2}") & (frame["price"] != "abc")].reset_index(drop=True)


def test_wfp_types_are_explicit():
    table = wfp_to_table(clean_wfp(), "COG", "a" * 64, NOW, "run1")
    assert table.schema.field("date").type == pa.date32()
    assert table.schema.field("price").type == pa.decimal128(18, 4)
    assert table.column("price")[0].as_py() == Decimal("600.0000")
    assert table.column("country_iso3")[0].as_py() == "COG"
    assert table.column("latitude")[2].as_py() is None  # coordonnées absentes : nul, pas zéro


def test_wfp_missing_column_is_refused():
    frame = clean_wfp().drop(columns=["unit"])
    with pytest.raises(SchemaError, match="unit"):
        wfp_to_table(frame, "COG", "a" * 64, NOW, "run1")


def test_wfp_unreadable_price_is_refused():
    frame = read_csv_as_text(FIXTURES / "wfp_sample.csv")
    frame = frame[frame["date"].str.match(r"\d{4}")]
    with pytest.raises(SchemaError, match="price"):
        wfp_to_table(frame, "COG", "a" * 64, NOW, "run1")


def test_wfp_unreadable_date_is_refused():
    frame = read_csv_as_text(FIXTURES / "wfp_sample.csv")
    frame = frame[frame["price"] != "abc"]
    with pytest.raises(SchemaError, match="date"):
        wfp_to_table(frame, "COG", "a" * 64, NOW, "run1")


def test_world_bank_keeps_missing_values_as_null():
    records = json.loads((FIXTURES / "world_bank_sample.json").read_text())[1]
    table = world_bank_to_table(records, "b" * 64, NOW, "run1")
    assert table.num_rows == 3
    assert table.column("year")[0].as_py() == 2024
    assert table.column("value")[1].as_py() is None


def test_fx_monthly_rates():
    frame = read_csv_as_text(FIXTURES / "ecb_sample.csv")
    table = fx_to_table(frame, "c" * 64, NOW, "run1")
    assert table.column("month")[1].as_py() == date(2026, 9, 1)
    assert table.column("usd_per_eur")[1].as_py() == Decimal("1.173120")


def test_parquet_round_trip():
    table = wfp_to_table(clean_wfp(), "COG", "a" * 64, NOW, "run1")
    assert len(to_parquet_bytes(table)) > 0
