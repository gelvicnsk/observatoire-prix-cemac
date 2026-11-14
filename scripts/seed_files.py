"""Écriture des seeds générés sans écraser les corrections faites à la main.

Règle : une ligne déjà présente dans le seed versionné est conservée telle quelle (elle a peut-être
été relue et corrigée). Seules les clés nouvelles sont ajoutées, avec le statut proposé par le script.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path


def read_seed(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def merge_rows(
    existing: list[dict[str, str]], proposed: Iterable[dict[str, object]], key: tuple[str, ...]
) -> tuple[list[dict[str, object]], int]:
    """Renvoie (lignes fusionnées triées par clé, nombre de lignes ajoutées)."""
    merged: dict[tuple, dict[str, object]] = {tuple(row[k] for k in key): dict(row) for row in existing}
    added = 0
    for row in proposed:
        row_key = tuple("" if row[k] is None else str(row[k]) for k in key)
        if row_key not in merged:
            merged[row_key] = row
            added += 1
    return [merged[k] for k in sorted(merged)], added


def write_seed(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: "" if row.get(c) is None else row.get(c) for c in columns})


def update_seed(path: Path, proposed: Iterable[dict[str, object]], key: tuple[str, ...], columns: list[str]) -> int:
    rows, added = merge_rows(read_seed(path), proposed, key)
    write_seed(path, rows, columns)
    return added
