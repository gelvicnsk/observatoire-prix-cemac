"""Étape 5B — applique la relecture manuelle des seeds générés.

Chaque fichier reference/review/<seed>.csv contient les colonnes clés du seed, les colonnes à corriger et
une colonne review_note (la justification, gardée dans le fichier de relecture). Pour chaque ligne :

- les valeurs non vides remplacent celles du seed ;
- le statut passe à « relu », sauf si la relecture indique un autre statut ;
- une clé absente du seed ou une colonne inconnue arrête le script (faute de frappe probable).

La relecture est donc versionnée et rejouable : on peut régénérer un seed puis réappliquer ce fichier.

Usage : python -m scripts.apply_review [--review-dir reference/review] [--seeds-dir dbt/seeds]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.seed_files import read_seed, write_seed

KEYS: dict[str, tuple[str, ...]] = {
    "unit_conversion": ("unit_raw",),
    "commodity_mapping": ("commodity_raw",),
    "market_district": ("country_iso3", "market_name"),
}
IGNORED = {"review_note"}


class ReviewError(ValueError):
    pass


def apply(seed_path: Path, review_path: Path, key: tuple[str, ...]) -> int:
    seed = read_seed(seed_path)
    if not seed:
        raise ReviewError(f"{seed_path} absent ou vide : générer le seed avant la relecture")
    columns = list(seed[0].keys())
    index = {tuple(row[k] for k in key): row for row in seed}

    review = read_seed(review_path)
    unknown_columns = set(review[0].keys()) - set(columns) - IGNORED if review else set()
    if unknown_columns:
        raise ReviewError(f"{review_path} : colonnes inconnues du seed : {sorted(unknown_columns)}")

    for line, change in enumerate(review, start=2):
        row = index.get(tuple(change[k] for k in key))
        if row is None:
            raise ReviewError(f"{review_path}:{line} : clé {[change[k] for k in key]} absente du seed")
        for column, value in change.items():
            if column not in IGNORED and column not in key and value != "":
                row[column] = value
        if not change.get("status"):
            row["status"] = "relu"

    write_seed(seed_path, seed, columns)
    return len(review)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--review-dir", type=Path, default=Path("reference/review"))
    parser.add_argument("--seeds-dir", type=Path, default=Path("dbt/seeds"))
    args = parser.parse_args(argv)

    try:
        for name, key in KEYS.items():
            review_path = args.review_dir / f"{name}.csv"
            if review_path.exists():
                count = apply(args.seeds_dir / f"{name}.csv", review_path, key)
                print(f"{name} : {count} lignes relues appliquées")
    except ReviewError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
