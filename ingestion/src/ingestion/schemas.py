"""Schémas explicites des fichiers Parquet écrits dans le bucket raw.

Chaque source est lue en texte puis convertie colonne par colonne. Une valeur non convertible
ou une colonne attendue absente lève SchemaError : le fichier n'est pas chargé, au lieu d'être chargé faux.
Les montants sont en décimal (jamais en flottant).
"""

from __future__ import annotations

import io
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from ingestion.config import WFP_REQUIRED_COLUMNS

MONEY = pa.decimal128(18, 4)
RATE = pa.decimal128(18, 6)

# Colonnes techniques ajoutées à chaque ligne
LINEAGE_FIELDS = [
    pa.field("source_sha256", pa.string(), nullable=False),
    pa.field("ingested_at", pa.timestamp("us", tz="UTC"), nullable=False),
    pa.field("run_id", pa.string(), nullable=False),
]

WFP_SCHEMA = pa.schema(
    [
        pa.field("date", pa.date32(), nullable=False),
        pa.field("country_iso3", pa.string(), nullable=False),
        pa.field("admin1", pa.string()),
        pa.field("admin2", pa.string()),
        pa.field("market", pa.string(), nullable=False),
        pa.field("market_id", pa.string()),
        pa.field("latitude", pa.float64()),
        pa.field("longitude", pa.float64()),
        pa.field("category", pa.string()),
        pa.field("commodity", pa.string(), nullable=False),
        pa.field("commodity_id", pa.string()),
        pa.field("unit", pa.string(), nullable=False),
        pa.field("priceflag", pa.string()),
        pa.field("pricetype", pa.string()),
        pa.field("currency", pa.string()),
        pa.field("price", MONEY, nullable=False),
        pa.field("usdprice", MONEY),
        *LINEAGE_FIELDS,
    ]
)

WORLD_BANK_SCHEMA = pa.schema(
    [
        pa.field("country_iso3", pa.string(), nullable=False),
        pa.field("indicator_id", pa.string(), nullable=False),
        pa.field("indicator_name", pa.string()),
        pa.field("year", pa.int64(), nullable=False),
        pa.field("value", pa.float64()),
        pa.field("obs_status", pa.string()),
        *LINEAGE_FIELDS,
    ]
)

FX_SCHEMA = pa.schema(
    [
        pa.field("month", pa.date32(), nullable=False),
        pa.field("usd_per_eur", RATE, nullable=False),
        *LINEAGE_FIELDS,
    ]
)


class SchemaError(ValueError):
    """Le fichier source ne respecte pas le contrat attendu."""


def _fail_if_any(mask: pd.Series, values: pd.Series, column: str, what: str) -> None:
    if mask.any():
        examples = ", ".join(repr(v) for v in values[mask].head(3))
        raise SchemaError(f"{int(mask.sum())} {what} dans la colonne « {column} » (ex. : {examples})")


def _text(series: pd.Series) -> list[str | None]:
    return [value.strip() or None for value in series.astype(str)]


def _decimals(series: pd.Series, column: str, places: int, required: bool) -> list[Decimal | None]:
    quantum = Decimal(1).scaleb(-places)
    result: list[Decimal | None] = []
    bad: list[str] = []
    for raw in series.astype(str):
        value = raw.strip().replace(",", ".")
        if not value:
            if required:
                bad.append(raw)
            result.append(None)
            continue
        try:
            result.append(Decimal(value).quantize(quantum))
        except InvalidOperation:
            bad.append(raw)
            result.append(None)
    if bad:
        raise SchemaError(f"{len(bad)} valeur(s) illisible(s) dans « {column} » (ex. : {bad[:3]})")
    return result


def _floats(series: pd.Series, column: str) -> list[float | None]:
    text = series.astype(str).str.strip()
    numbers = pd.to_numeric(text, errors="coerce")
    _fail_if_any(numbers.isna() & (text != ""), series, column, "valeur(s) non numérique(s)")
    return [None if pd.isna(v) else float(v) for v in numbers]


def _lineage(rows: int, sha256: str, ingested_at: datetime, run_id: str) -> dict[str, list]:
    return {"source_sha256": [sha256] * rows, "ingested_at": [ingested_at] * rows, "run_id": [run_id] * rows}


def wfp_to_table(frame: pd.DataFrame, iso3: str, sha256: str, ingested_at: datetime, run_id: str) -> pa.Table:
    missing = [column for column in WFP_REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise SchemaError(f"colonnes attendues absentes : {', '.join(missing)}")

    dates = pd.to_datetime(frame["date"].str.strip(), format="%Y-%m-%d", errors="coerce")
    _fail_if_any(dates.isna(), frame["date"], "date", "date(s) illisible(s)")
    for column in ("market", "commodity", "unit"):
        _fail_if_any(frame[column].str.strip() == "", frame[column], column, "valeur(s) vide(s)")

    def optional(column: str) -> list[str | None]:
        return _text(frame[column]) if column in frame.columns else [None] * len(frame)

    usd = frame["usdprice"] if "usdprice" in frame.columns else pd.Series([""] * len(frame))
    data = {
        "date": [d.date() for d in dates],
        "country_iso3": [iso3] * len(frame),
        "admin1": _text(frame["admin1"]),
        "admin2": _text(frame["admin2"]),
        "market": _text(frame["market"]),
        "market_id": optional("market_id"),
        "latitude": _floats(frame["latitude"], "latitude"),
        "longitude": _floats(frame["longitude"], "longitude"),
        "category": _text(frame["category"]),
        "commodity": _text(frame["commodity"]),
        "commodity_id": optional("commodity_id"),
        "unit": _text(frame["unit"]),
        "priceflag": _text(frame["priceflag"]),
        "pricetype": _text(frame["pricetype"]),
        "currency": _text(frame["currency"]),
        "price": _decimals(frame["price"], "price", 4, required=True),
        "usdprice": _decimals(usd, "usdprice", 4, required=False),
        **_lineage(len(frame), sha256, ingested_at, run_id),
    }
    return pa.Table.from_pydict(data, schema=WFP_SCHEMA)


def world_bank_to_table(records: list[dict], sha256: str, ingested_at: datetime, run_id: str) -> pa.Table:
    rows = []
    for record in records:
        try:
            rows.append(
                {
                    "country_iso3": record["countryiso3code"],
                    "indicator_id": record["indicator"]["id"],
                    "indicator_name": record["indicator"].get("value"),
                    "year": int(record["date"]),
                    "value": None if record.get("value") is None else float(record["value"]),
                    "obs_status": record.get("obs_status") or None,
                }
            )
        except (KeyError, TypeError, ValueError) as error:
            raise SchemaError(f"enregistrement Banque mondiale inattendu : {record!r}") from error
    if any(not row["country_iso3"] for row in rows):
        raise SchemaError("code pays ISO3 manquant dans la réponse de la Banque mondiale")
    data = {key: [row[key] for row in rows] for key in WORLD_BANK_SCHEMA.names[:6]}
    data.update(_lineage(len(rows), sha256, ingested_at, run_id))
    return pa.Table.from_pydict(data, schema=WORLD_BANK_SCHEMA)


def fx_to_table(frame: pd.DataFrame, sha256: str, ingested_at: datetime, run_id: str) -> pa.Table:
    # read_csv_as_text met les noms de colonnes en minuscules
    missing = [column for column in ("time_period", "obs_value") if column not in frame.columns]
    if missing:
        raise SchemaError(f"colonnes attendues absentes dans le fichier de la BCE : {', '.join(missing)}")
    months = pd.to_datetime(frame["time_period"].str.strip() + "-01", format="%Y-%m-%d", errors="coerce")
    _fail_if_any(months.isna(), frame["time_period"], "time_period", "mois illisible(s)")
    data = {
        "month": [m.date() for m in months],
        "usd_per_eur": _decimals(frame["obs_value"], "obs_value", 6, required=True),
        **_lineage(len(frame), sha256, ingested_at, run_id),
    }
    return pa.Table.from_pydict(data, schema=FX_SCHEMA)


def to_parquet_bytes(table: pa.Table) -> bytes:
    buffer = io.BytesIO()
    pq.write_table(table, buffer, compression="snappy")
    return buffer.getvalue()


def json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
