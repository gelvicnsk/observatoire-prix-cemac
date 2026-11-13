"""Tests du profilage : lecture en texte, ligne HXL, statut actif / historique, comptages."""

from datetime import date
from pathlib import Path

import pandas as pd

from ingestion.profiling import (
    commodity_inventory,
    months_between,
    profile_generic,
    profile_wfp,
    read_csv_as_text,
    unit_inventory,
)

FIXTURE = Path(__file__).parent / "fixtures" / "wfp_sample.csv"


def test_hxl_row_is_removed_and_everything_is_text():
    frame = read_csv_as_text(FIXTURE)
    assert len(frame) == 6
    assert not frame["date"].str.startswith("#").any()
    assert all(pd.api.types.is_string_dtype(dtype) for dtype in frame.dtypes)


def test_profile_counts_and_active_status():
    frame = read_csv_as_text(FIXTURE)
    profile = profile_wfp(frame, "COG", today=date(2025, 6, 1))
    assert profile.status == "actif"
    assert profile.first_month == "2025-01"
    assert profile.last_month == "2025-04"
    assert profile.months_covered == 4
    assert profile.months_since_last == 2
    assert profile.markets == 2
    assert profile.markets_without_coordinates == 1
    assert profile.unparsable_dates == 1
    assert profile.unparsable_prices == 1
    assert profile.non_positive_prices == 1
    assert profile.units == {"KG": 4, "50 KG": 1, "L": 1}


def test_old_series_is_historical():
    frame = read_csv_as_text(FIXTURE)
    profile = profile_wfp(frame, "GAB", today=date(2026, 11, 13))
    assert profile.status == "historique"


def test_missing_columns_are_reported_not_guessed():
    frame = pd.DataFrame({"date": ["2025-01-15"], "price": ["10"]})
    profile = profile_wfp(frame, "COG", today=date(2025, 6, 1))
    assert profile.status == "format inattendu"
    assert "market" in profile.missing_columns


def test_months_between():
    assert months_between(date(2024, 11, 15), date(2025, 2, 1)) == 3


def test_generic_profile_finds_period():
    frame = pd.DataFrame({"year": ["2019", "2021", "2020"], "value": ["1", "2", "3"]})
    profile = profile_generic(frame, "GNQ")
    assert (profile.first_period, profile.last_period) == ("2019", "2021")


def test_inventories_across_countries():
    frame = read_csv_as_text(FIXTURE)
    units = unit_inventory({"COG": frame, "CMR": frame.head(1)})
    kg = units.set_index("unit").loc["KG"]
    assert kg["rows"] == 5 and kg["countries"] == "CMR,COG"
    commodities = commodity_inventory({"COG": frame})
    assert set(commodities.columns) == {"commodity", "category", "rows", "countries"}
