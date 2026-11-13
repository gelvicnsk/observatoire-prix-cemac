"""Profilage des fichiers sources : ce que chaque pays fournit réellement.

Toutes les colonnes sont lues en texte, puis converties explicitement :
aucun type n'est deviné par pandas, et chaque valeur non convertible est comptée.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from ingestion.config import WFP_OPTIONAL_COLUMNS, WFP_REQUIRED_COLUMNS

ACTIVE_MAX_MONTHS = 6  # au-delà, la série est considérée comme historique


def read_csv_as_text(path: Path) -> pd.DataFrame:
    """Lit un CSV HDX en texte et retire la ligne de balises HXL (#date, #adm1+name…) si elle existe."""
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    if len(frame) and frame.iloc[0].astype(str).str.startswith("#").all():
        frame = frame.iloc[1:].reset_index(drop=True)
    return frame


def months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


@dataclass
class WfpProfile:
    iso3: str
    rows: int
    missing_columns: list[str]
    extra_columns: list[str]
    first_month: str | None
    last_month: str | None
    months_covered: int
    months_since_last: int | None
    status: str
    markets: int
    markets_without_coordinates: int
    commodities: int
    unparsable_dates: int
    unparsable_prices: int
    non_positive_prices: int
    units: dict[str, int] = field(default_factory=dict)
    price_types: dict[str, int] = field(default_factory=dict)
    currencies: dict[str, int] = field(default_factory=dict)
    price_flags: dict[str, int] = field(default_factory=dict)
    top_commodities: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _counts(series: pd.Series, limit: int | None = None) -> dict[str, int]:
    counts = series.replace("", "(vide)").value_counts()
    if limit:
        counts = counts.head(limit)
    return {str(key): int(value) for key, value in counts.items()}


def profile_wfp(frame: pd.DataFrame, iso3: str, today: date) -> WfpProfile:
    columns = set(frame.columns)
    missing = [column for column in WFP_REQUIRED_COLUMNS if column not in columns]
    known = set(WFP_REQUIRED_COLUMNS) | set(WFP_OPTIONAL_COLUMNS)
    extra = sorted(columns - known)
    if missing:
        return WfpProfile(
            iso3=iso3,
            rows=len(frame),
            missing_columns=missing,
            extra_columns=extra,
            first_month=None,
            last_month=None,
            months_covered=0,
            months_since_last=None,
            status="format inattendu",
            markets=0,
            markets_without_coordinates=0,
            commodities=0,
            unparsable_dates=0,
            unparsable_prices=0,
            non_positive_prices=0,
        )

    dates = pd.to_datetime(frame["date"], format="%Y-%m-%d", errors="coerce")
    prices = pd.to_numeric(frame["price"].str.replace(",", ".", regex=False), errors="coerce")
    latitudes = pd.to_numeric(frame["latitude"], errors="coerce")
    longitudes = pd.to_numeric(frame["longitude"], errors="coerce")

    valid_dates = dates.dropna()
    months = valid_dates.dt.to_period("M")
    first = valid_dates.min().date() if len(valid_dates) else None
    last = valid_dates.max().date() if len(valid_dates) else None
    since_last = months_between(last, today) if last else None

    if since_last is None:
        status = "aucune date exploitable"
    elif since_last <= ACTIVE_MAX_MONTHS:
        status = "actif"
    else:
        status = "historique"

    markets = frame.assign(_no_coords=latitudes.isna() | longitudes.isna()).groupby("market")["_no_coords"].all()

    return WfpProfile(
        iso3=iso3,
        rows=len(frame),
        missing_columns=[],
        extra_columns=extra,
        first_month=first.strftime("%Y-%m") if first else None,
        last_month=last.strftime("%Y-%m") if last else None,
        months_covered=int(months.nunique()),
        months_since_last=since_last,
        status=status,
        markets=int(frame["market"].nunique()),
        markets_without_coordinates=int(markets.sum()),
        commodities=int(frame["commodity"].nunique()),
        unparsable_dates=int(dates.isna().sum()),
        unparsable_prices=int(prices.isna().sum()),
        non_positive_prices=int((prices <= 0).sum()),
        units=_counts(frame["unit"]),
        price_types=_counts(frame["pricetype"]),
        currencies=_counts(frame["currency"]),
        price_flags=_counts(frame["priceflag"]),
        top_commodities=_counts(frame["commodity"], limit=15),
    )


@dataclass
class GenericProfile:
    iso3: str
    rows: int
    columns: list[str]
    period_column: str | None
    first_period: str | None
    last_period: str | None

    def to_dict(self) -> dict:
        return asdict(self)


def profile_generic(frame: pd.DataFrame, iso3: str) -> GenericProfile:
    """Profil d'un fichier au format inconnu (FAOSTAT) : colonnes et période couverte."""
    period_column = next(
        (column for column in ("date", "year", "année", "startdate", "start_date") if column in frame.columns),
        None,
    )
    first = last = None
    if period_column:
        values = sorted(value for value in frame[period_column].astype(str) if value and not value.startswith("#"))
        if values:
            first, last = values[0], values[-1]
    return GenericProfile(
        iso3=iso3,
        rows=len(frame),
        columns=list(frame.columns),
        period_column=period_column,
        first_period=first,
        last_period=last,
    )


def unit_inventory(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Toutes les unités rencontrées, avec leur nombre de lignes et les pays concernés (base du seed)."""
    parts = [frame[["unit"]].assign(iso3=iso3) for iso3, frame in frames.items() if "unit" in frame.columns]
    if not parts:
        return pd.DataFrame(columns=["unit", "rows", "countries"])
    stacked = pd.concat(parts, ignore_index=True)
    grouped = stacked.groupby("unit").agg(rows=("iso3", "size"), countries=("iso3", lambda s: ",".join(sorted(set(s)))))
    return grouped.sort_values("rows", ascending=False).reset_index()


def commodity_inventory(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Tous les produits rencontrés, avec leur catégorie, leur nombre de lignes et les pays (base du seed)."""
    parts = [
        frame[["commodity", "category"]].assign(iso3=iso3)
        for iso3, frame in frames.items()
        if {"commodity", "category"} <= set(frame.columns)
    ]
    if not parts:
        return pd.DataFrame(columns=["commodity", "category", "rows", "countries"])
    stacked = pd.concat(parts, ignore_index=True)
    grouped = stacked.groupby(["commodity", "category"]).agg(
        rows=("iso3", "size"), countries=("iso3", lambda s: ",".join(sorted(set(s))))
    )
    return grouped.sort_values("rows", ascending=False).reset_index()
