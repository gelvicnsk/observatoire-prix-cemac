"""Étape 5B — propose les seeds unit_conversion et commodity_mapping à partir des prix réellement chargés.

Lit les unités et les produits distincts de silver.stg_wfp__prices (ou des CSV de l'inventaire de
l'étape 1 avec --from-profile), applique les règles ci-dessous et met à jour :

- dbt/seeds/unit_conversion.csv     une ligne par unité du PAM
- dbt/seeds/commodity_mapping.csv   une ligne par produit du PAM

Les lignes déjà présentes ne sont jamais modifiées : on peut corriger un seed à la main, puis relancer
le script quand une nouvelle unité ou un nouveau produit apparaît. Toute ligne au statut « a_verifier »
doit être relue avant l'étape 5C.

Usage :
    python -m scripts.build_reference_seeds                     # depuis BigQuery (GCP_PROJECT_ID)
    python -m scripts.build_reference_seeds --from-profile data/profile
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from scripts.seed_files import update_seed

SEEDS_DIR = Path("dbt/seeds")

# --------------------------------------------------------------------------------------------------
# Unités
# --------------------------------------------------------------------------------------------------

# Facteur vers l'unité de base (kg pour les masses, l pour les volumes)
_MEASURES: dict[str, tuple[str, float]] = {
    "kg": ("kg", 1.0),
    "g": ("kg", 0.001),
    "mt": ("kg", 1000.0),
    "pound": ("kg", 0.45359237),
    "lb": ("kg", 0.45359237),
    "l": ("l", 1.0),
    "litre": ("l", 1.0),
    "ml": ("l", 0.001),
    "cl": ("l", 0.01),
}
_MEASURE_PATTERN = "|".join(sorted(_MEASURES, key=len, reverse=True))
_QUANTITY = r"(\d+(?:[.,]\d+)?)"
_PLAIN = re.compile(rf"^{_QUANTITY}?\s*({_MEASURE_PATTERN})s?$", re.IGNORECASE)
_EMBEDDED = re.compile(rf"\(\s*{_QUANTITY}\s*({_MEASURE_PATTERN})s?\s*\)", re.IGNORECASE)
_COUNT = re.compile(r"^(?:(\d+)\s*)?(units?|pieces?|pcs)$", re.IGNORECASE)

# Unités de comptage ou mesures locales sans poids connu : prix conservé, hors comparaison au kg
_NO_WEIGHT = {
    "unit",
    "piece",
    "loaf",
    "bunch",
    "bundle",
    "heap",
    "tuber",
    "cuvette",
    "tin",
    "bowl",
    "packet",
    "bag",
    "sack",
    "box",
    "bottle",
    "cup",
    "basket",
    "tas",
    "coro",
    "mudd",
    "koro",
    "pot",
    "glass",
}
# Unités exclues de l'observatoire (bétail vendu sur pied)
_EXCLUDED = {"head": "bétail vendu sur pied, hors panier alimentaire"}

UNIT_COLUMNS = ["unit_raw", "quantity", "base_unit", "factor_to_base", "status", "note"]


def _number(text: str | None) -> float:
    return float(text.replace(",", ".")) if text else 1.0


def classify_unit(unit_raw: str) -> dict[str, object]:
    """Règle de conversion proposée pour une unité du PAM."""
    text = " ".join(unit_raw.split())
    lowered = text.lower()
    row: dict[str, object] = {"unit_raw": unit_raw, "quantity": None, "base_unit": None, "factor_to_base": None}

    if lowered in _EXCLUDED:
        return row | {"status": "exclu", "note": _EXCLUDED[lowered]}

    if match := _PLAIN.match(text):
        quantity = _number(match.group(1))
        base, factor = _MEASURES[match.group(2).lower()]
        return row | {
            "quantity": quantity,
            "base_unit": base,
            "factor_to_base": round(quantity * factor, 6),
            "status": "converti",
            "note": "",
        }

    if match := _EMBEDDED.search(text):
        quantity = _number(match.group(1))
        base, factor = _MEASURES[match.group(2).lower()]
        return row | {
            "quantity": quantity,
            "base_unit": base,
            "factor_to_base": round(quantity * factor, 6),
            "status": "a_verifier",
            "note": "poids lu entre parenthèses",
        }

    if lowered == "dozen":
        return row | {
            "quantity": 12,
            "base_unit": "piece",
            "factor_to_base": 12,
            "status": "sans_poids",
            "note": "comptage",
        }

    if match := _COUNT.match(text):
        quantity = _number(match.group(1))
        return row | {
            "quantity": quantity,
            "base_unit": "piece",
            "factor_to_base": quantity,
            "status": "sans_poids",
            "note": "comptage",
        }

    if lowered.rstrip("s") in _NO_WEIGHT or lowered in _NO_WEIGHT:
        return row | {"base_unit": "piece", "status": "sans_poids", "note": "mesure locale, poids inconnu"}

    return row | {"status": "a_verifier", "note": "unité non reconnue"}


# --------------------------------------------------------------------------------------------------
# Produits
# --------------------------------------------------------------------------------------------------

CATEGORY_GROUPS: dict[str, tuple[str, bool]] = {
    "cereals and tubers": ("Céréales et tubercules", True),
    "pulses and nuts": ("Légumineuses et oléagineux", True),
    "oil and fats": ("Huiles et graisses", True),
    "meat, fish and eggs": ("Viande, poisson et œufs", True),
    "milk and dairy": ("Lait et produits laitiers", True),
    "vegetables and fruits": ("Fruits et légumes", True),
    "miscellaneous food": ("Autres produits alimentaires", True),
    "non-food": ("Non alimentaire", False),
}

_BASES: dict[str, str] = {
    "maize": "Maïs",
    "maize flour": "Farine de maïs",
    "maize meal": "Farine de maïs",
    "rice": "Riz",
    "sorghum": "Sorgho",
    "millet": "Mil",
    "wheat": "Blé",
    "wheat flour": "Farine de blé",
    "bread": "Pain",
    "pasta": "Pâtes alimentaires",
    "spaghetti": "Spaghetti",
    "cassava": "Manioc",
    "cassava flour": "Farine de manioc",
    "cassava leaves": "Feuilles de manioc",
    "gari": "Gari",
    "yam": "Igname",
    "yams": "Igname",
    "plantains": "Banane plantain",
    "plantain": "Banane plantain",
    "bananas": "Banane",
    "potatoes": "Pomme de terre",
    "irish potatoes": "Pomme de terre",
    "sweet potatoes": "Patate douce",
    "taro": "Taro",
    "cocoyam": "Macabo",
    "macabo": "Macabo",
    "beans": "Haricots",
    "cowpeas": "Niébé",
    "groundnuts": "Arachide",
    "peas": "Pois",
    "lentils": "Lentilles",
    "sesame": "Sésame",
    "soybeans": "Soja",
    "oil": "Huile",
    "sugar": "Sucre",
    "salt": "Sel",
    "meat": "Viande",
    "fish": "Poisson",
    "eggs": "Œufs",
    "milk": "Lait",
    "onions": "Oignons",
    "tomatoes": "Tomates",
    "tomato paste": "Concentré de tomate",
    "peppers": "Poivrons",
    "chili": "Piment",
    "okra": "Gombo",
    "cabbage": "Chou",
    "carrots": "Carottes",
    "garlic": "Ail",
    "eggplants": "Aubergines",
    "lettuce": "Laitue",
    "avocados": "Avocats",
    "oranges": "Oranges",
    "mangoes": "Mangues",
    "pineapples": "Ananas",
    "dates": "Dattes",
    "groundnut paste": "Pâte d'arachide",
    "shea butter": "Beurre de karité",
    "tea": "Thé",
    "coffee": "Café",
    "fuel": "Carburant",
    "soap": "Savon",
    "charcoal": "Charbon de bois",
    "firewood": "Bois de chauffe",
    "livestock": "Bétail",
    "wage": "Salaire journalier",
    "water": "Eau",
    "gum arabic": "Gomme arabique",
}

_QUALIFIERS: dict[str, str] = {
    "imported": "importé",
    "local": "local",
    "white": "blanc",
    "yellow": "jaune",
    "red": "rouge",
    "black": "noir",
    "brown": "roux",
    "broken": "brisé",
    "paddy": "paddy",
    "milled": "usiné",
    "long grain": "long",
    "vegetable": "végétale",
    "palm": "palme",
    "groundnut": "arachide",
    "cottonseed": "coton",
    "sunflower": "tournesol",
    "beef": "bœuf",
    "goat": "chèvre",
    "mutton": "mouton",
    "chicken": "poulet",
    "pork": "porc",
    "smoked": "fumé",
    "dried": "séché",
    "dry": "sec",
    "fresh": "frais",
    "frozen": "congelé",
    "powder": "en poudre",
    "powdered": "en poudre",
    "fermented": "fermenté",
    "shelled": "décortiquée",
    "unshelled": "en coque",
    "diesel": "gazole",
    "petrol-gasoline": "essence",
    "kerosene": "pétrole lampant",
    "refined": "raffiné",
    "granulated": "en poudre",
    "cossettes": "cossettes",
    "chikwangue": "chikwangue",
    "fufu": "foufou",
    "tubers": "tubercules",
    "leaves": "feuilles",
    "flour": "farine",
    "cattle": "bovin",
    "sheep": "mouton",
    "goats": "chèvre",
    "unskilled": "non qualifié",
    "non-agricultural": "non agricole",
    "agricultural": "agricole",
    "mixed": "mélangé",
    "whole": "entier",
    "small": "petit",
    "large": "gros",
    "loose": "en vrac",
    "iodised": "iodé",
    "sweet": "doux",
    "fresh milk": "frais",
}

COMMODITY_COLUMNS = ["commodity_raw", "wfp_category", "name_fr", "group_fr", "include_in_index", "status"]
_NAME = re.compile(r"^(?P<base>[^(]+?)\s*(?:\((?P<qualifiers>.*)\))?\s*$")


def translate_commodity(commodity_raw: str) -> tuple[str, bool]:
    """Nom français proposé et indique s'il a été entièrement traduit."""
    match = _NAME.match(commodity_raw.strip())
    if not match:
        return commodity_raw, False
    base = match.group("base").strip()
    base_fr = _BASES.get(base.lower())
    qualifiers = [q.strip() for q in re.split(r"[,;]", match.group("qualifiers") or "") if q.strip()]
    qualifiers_fr = [_QUALIFIERS.get(q.lower()) for q in qualifiers]
    complete = base_fr is not None and all(qualifiers_fr)
    name = base_fr or base
    parts = [fr or q for fr, q in zip(qualifiers_fr, qualifiers, strict=True)]
    return (f"{name} ({', '.join(parts)})" if parts else name), complete


def classify_commodity(commodity_raw: str, wfp_category: str) -> dict[str, object]:
    group, include = CATEGORY_GROUPS.get(wfp_category.strip().lower(), (None, True))
    name_fr, complete = translate_commodity(commodity_raw)
    return {
        "commodity_raw": commodity_raw,
        "wfp_category": wfp_category,
        "name_fr": name_fr,
        "group_fr": group or "",
        "include_in_index": str(include).lower(),
        "status": "auto" if complete and group else "a_verifier",
    }


# --------------------------------------------------------------------------------------------------
# Lecture des valeurs distinctes
# --------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Distinct:
    units: list[str]
    commodities: list[tuple[str, str]]


def from_bigquery(project: str) -> Distinct:
    from google.cloud import bigquery

    client = bigquery.Client(project=project)
    units = client.query("select distinct unit_raw from silver.stg_wfp__prices where unit_raw is not null").result()
    commodities = client.query(
        "select distinct commodity_name, commodity_category from silver.stg_wfp__prices"
        " where commodity_name is not null"
    ).result()
    return Distinct(
        units=sorted(row.unit_raw for row in units),
        commodities=sorted((row.commodity_name, row.commodity_category or "") for row in commodities),
    )


def from_profile(directory: Path) -> Distinct:
    units = pd.read_csv(directory / "units.csv", dtype=str)
    commodities = pd.read_csv(directory / "commodities.csv", dtype=str).fillna("")
    return Distinct(
        units=sorted(units["unit"].dropna().unique()),
        commodities=sorted(set(zip(commodities["commodity"], commodities["category"], strict=True))),
    )


def build(distinct: Distinct, seeds_dir: Path) -> dict[str, int]:
    unit_rows = [classify_unit(u) for u in distinct.units]
    commodity_rows = [classify_commodity(c, cat) for c, cat in distinct.commodities]
    added_units = update_seed(seeds_dir / "unit_conversion.csv", unit_rows, ("unit_raw",), UNIT_COLUMNS)
    added_commodities = update_seed(
        seeds_dir / "commodity_mapping.csv", commodity_rows, ("commodity_raw",), COMMODITY_COLUMNS
    )
    to_review = sum(r["status"] == "a_verifier" for r in unit_rows + commodity_rows)
    return {"unites_ajoutees": added_units, "produits_ajoutes": added_commodities, "a_verifier": to_review}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", default=os.environ.get("GCP_PROJECT_ID"))
    parser.add_argument("--from-profile", type=Path, help="dossier de l'inventaire (units.csv, commodities.csv)")
    parser.add_argument("--seeds-dir", type=Path, default=SEEDS_DIR)
    args = parser.parse_args(argv)

    if args.from_profile:
        distinct = from_profile(args.from_profile)
    elif args.project:
        distinct = from_bigquery(args.project)
    else:
        parser.error("indiquer --project (ou GCP_PROJECT_ID) ou --from-profile")

    summary = build(distinct, args.seeds_dir)
    print(f"{len(distinct.units)} unités, {len(distinct.commodities)} produits lus.")
    print(", ".join(f"{k} : {v}" for k, v in summary.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
