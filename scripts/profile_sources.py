"""Étape 1 — inventaire des données des 6 pays CEMAC.

Pour chaque pays : retrouve sur HDX le jeu de prix du PAM et celui de FAOSTAT, télécharge le CSV
principal (avec son empreinte sha256), le profile, puis écrit :

- docs/data_profile.md          la fiche de profondeur par pays (versionnée)
- data/profile/profile.json     le profil détaillé (non versionné)
- data/profile/units.csv        toutes les unités rencontrées  -> base du seed unit_conversion
- data/profile/commodities.csv  tous les produits rencontrés   -> base du seed commodity_mapping

Usage : python scripts/profile_sources.py [--countries COG,CMR] [--root .]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd

from ingestion.config import CEMAC_COUNTRIES
from ingestion.hdx import HdxClient
from ingestion.profiling import (
    commodity_inventory,
    profile_generic,
    profile_wfp,
    read_csv_as_text,
    unit_inventory,
)


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return cleaned if cleaned.lower().endswith(".csv") else f"{cleaned}.csv"


def _markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join("" if cell is None else str(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)


def _top(counts: dict[str, int], limit: int = 8) -> str:
    items = list(counts.items())[:limit]
    text = ", ".join(f"{key} ({value})" for key, value in items)
    return text + (" …" if len(counts) > limit else "")


def collect(client: HdxClient, countries: list[str], root: Path, today: date) -> dict:
    """Télécharge et profile ; renvoie un dictionnaire sérialisable."""
    report: dict = {"generated_at": datetime.now(UTC).isoformat(timespec="seconds"), "countries": {}}
    wfp_frames: dict[str, pd.DataFrame] = {}

    for iso3 in countries:
        entry: dict = {"name": CEMAC_COUNTRIES.get(iso3, iso3)}
        for kind in ("wfp", "faostat"):
            print(f"[{iso3}] {kind} : recherche sur HDX…", flush=True)
            dataset = client.find_dataset(iso3, kind)
            if not dataset:
                entry[kind] = {"found": False}
                print(f"[{iso3}] {kind} : aucun jeu trouvé", flush=True)
                continue
            resource = client.main_csv_resource(dataset)
            if not resource:
                entry[kind] = {"found": True, "dataset": dataset.get("name"), "csv": False}
                continue

            destination = root / "data" / "raw" / "inventory" / iso3 / kind / _safe_filename(resource.resource_name)
            download = client.download(resource.url, destination)
            frame = read_csv_as_text(download.path)
            source_info = {
                "found": True,
                "csv": True,
                "dataset": resource.dataset_name,
                "dataset_url": f"https://data.humdata.org/dataset/{resource.dataset_name}",
                "resource": resource.resource_name,
                "resource_last_modified": resource.last_modified,
                "file": str(download.path.relative_to(root)),
                "sha256": download.sha256,
                "size_bytes": download.size_bytes,
            }
            if kind == "wfp":
                source_info["profile"] = profile_wfp(frame, iso3, today).to_dict()
                wfp_frames[iso3] = frame
            else:
                source_info["profile"] = profile_generic(frame, iso3).to_dict()
            entry[kind] = source_info
            print(f"[{iso3}] {kind} : {len(frame)} lignes, sha256 {download.sha256[:12]}…", flush=True)
        report["countries"][iso3] = entry

    report["units"] = unit_inventory(wfp_frames).to_dict(orient="records")
    report["commodities"] = commodity_inventory(wfp_frames).to_dict(orient="records")
    return report


def render_markdown(report: dict, today: date) -> str:
    countries: dict = report["countries"]
    summary_rows = []
    for iso3, entry in countries.items():
        wfp = entry.get("wfp", {})
        profile = wfp.get("profile") or {}
        faostat = entry.get("faostat", {})
        fao_profile = faostat.get("profile") or {}
        summary_rows.append(
            [
                f"{entry['name']} ({iso3})",
                profile.get("status", "absent") if wfp.get("found") else "absent",
                profile.get("first_month"),
                profile.get("last_month"),
                profile.get("months_covered"),
                profile.get("markets"),
                profile.get("commodities"),
                profile.get("rows"),
                "oui" if faostat.get("found") else "non",
                f"{fao_profile.get('first_period', '')} → {fao_profile.get('last_period', '')}" if fao_profile else "",
            ]
        )

    parts = [
        "# Profondeur des données par pays",
        "",
        f"Généré le {today.isoformat()} par `scripts/profile_sources.py`. "
        f"« actif » = dernier relevé PAM il y a 6 mois ou moins ; « historique » = plus ancien.",
        "",
        "## Synthèse",
        "",
        _markdown_table(
            [
                "Pays",
                "Prix PAM",
                "Premier mois",
                "Dernier mois",
                "Mois couverts",
                "Marchés",
                "Produits",
                "Lignes",
                "FAOSTAT",
                "Période FAOSTAT",
            ],
            summary_rows,
        ),
        "",
        "## Détail par pays",
    ]

    for iso3, entry in countries.items():
        parts += ["", f"### {entry['name']} ({iso3})", ""]
        wfp = entry.get("wfp", {})
        profile = wfp.get("profile")
        if not wfp.get("found"):
            parts.append("- Aucun jeu de prix du PAM trouvé sur HDX.")
        elif not profile:
            parts.append(f"- Jeu PAM trouvé ({wfp.get('dataset')}) mais sans CSV exploitable.")
        else:
            parts += [
                f"- Source : [{wfp['dataset']}]({wfp['dataset_url']}), ressource « {wfp['resource']} », "
                + (
                    f"modifiée le {wfp['resource_last_modified'][:10]}"
                    if wfp.get("resource_last_modified")
                    else "date de modification inconnue"
                ),
                f"- Empreinte sha256 : `{wfp['sha256']}`",
                f"- Statut : **{profile['status']}**"
                + (
                    f", dernier relevé il y a {profile['months_since_last']} mois"
                    if profile.get("months_since_last") is not None
                    else ""
                ),
            ]
            if profile["missing_columns"]:
                parts.append(f"- Colonnes manquantes : {', '.join(profile['missing_columns'])}")
            else:
                parts += [
                    f"- Marchés : {profile['markets']} "
                    f"(dont {profile['markets_without_coordinates']} sans coordonnées)",
                    f"- Unités : {_top(profile['units'])}",
                    f"- Types de prix : {_top(profile['price_types'])}",
                    f"- Monnaies : {_top(profile['currencies'])}",
                    f"- Indicateurs de prix (priceflag) : {_top(profile['price_flags'])}",
                    f"- Produits les plus relevés : {_top(profile['top_commodities'])}",
                    f"- Dates illisibles : {profile['unparsable_dates']} · prix illisibles : "
                    f"{profile['unparsable_prices']} · prix nuls ou négatifs : {profile['non_positive_prices']}",
                ]
            if profile.get("extra_columns"):
                parts.append(f"- Colonnes supplémentaires : {', '.join(profile['extra_columns'])}")

        faostat = entry.get("faostat", {})
        if faostat.get("found") and faostat.get("profile"):
            fao = faostat["profile"]
            parts.append(
                f"- FAOSTAT : [{faostat['dataset']}]({faostat['dataset_url']}), {fao['rows']} lignes, "
                f"colonnes : {', '.join(fao['columns'][:10])}"
            )
        else:
            parts.append("- FAOSTAT : aucun jeu trouvé.")

    units = report.get("units", [])
    parts += [
        "",
        "## Unités rencontrées (base du seed `unit_conversion`)",
        "",
        _markdown_table(["Unité", "Lignes", "Pays"], [[u["unit"], u["rows"], u["countries"]] for u in units[:40]]),
        "",
        f"{len(units)} unités au total ; liste complète : `data/profile/units.csv`.",
        "",
        f"{len(report.get('commodities', []))} produits au total ; liste complète : `data/profile/commodities.csv`.",
        "",
    ]
    return "\n".join(parts)


def write_outputs(report: dict, root: Path, today: date) -> None:
    profile_dir = root / "data" / "profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / "profile.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(report["units"], columns=["unit", "rows", "countries"]).to_csv(profile_dir / "units.csv", index=False)
    pd.DataFrame(report["commodities"], columns=["commodity", "category", "rows", "countries"]).to_csv(
        profile_dir / "commodities.csv", index=False
    )
    docs = root / "docs" / "data_profile.md"
    docs.parent.mkdir(parents=True, exist_ok=True)
    docs.write_text(render_markdown(report, today), encoding="utf-8")


def main(argv: list[str] | None = None, client: HdxClient | None = None, today: date | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inventaire des données CEMAC sur HDX")
    parser.add_argument("--countries", default=",".join(CEMAC_COUNTRIES), help="codes ISO3 séparés par des virgules")
    parser.add_argument("--root", default=".", help="racine du projet")
    args = parser.parse_args(argv)

    countries = [code.strip().upper() for code in args.countries.split(",") if code.strip()]
    unknown = [code for code in countries if code not in CEMAC_COUNTRIES]
    if unknown:
        print(f"Codes pays inconnus : {', '.join(unknown)}", file=sys.stderr)
        return 2

    root = Path(args.root).resolve()
    today = today or date.today()
    own_client = client is None
    client = client or HdxClient()
    try:
        report = collect(client, countries, root, today)
    finally:
        if own_client:
            client.close()
    write_outputs(report, root, today)
    print(f"Fiche écrite : {root / 'docs' / 'data_profile.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
