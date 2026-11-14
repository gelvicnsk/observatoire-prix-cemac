"""Règles des seeds unit_conversion et commodity_mapping (étape 5B)."""

import csv

import pytest

from scripts.build_reference_seeds import Distinct, build, classify_commodity, classify_unit


@pytest.mark.parametrize(
    ("unit", "base", "factor", "status"),
    [
        ("KG", "kg", 1.0, "converti"),
        ("50 KG", "kg", 50.0, "converti"),
        ("100 KG", "kg", 100.0, "converti"),
        ("400 G", "kg", 0.4, "converti"),
        ("L", "l", 1.0, "converti"),
        ("1.5 L", "l", 1.5, "converti"),
        ("750 ML", "l", 0.75, "converti"),
        ("MT", "kg", 1000.0, "converti"),
        ("Pound", "kg", 0.453592, "converti"),
        ("Cuvette (2.5 KG)", "kg", 2.5, "a_verifier"),
        ("Dozen", "piece", 12, "sans_poids"),
        ("Unit", "piece", 1.0, "sans_poids"),
        ("Bunch", "piece", None, "sans_poids"),
        ("Head", None, None, "exclu"),
        ("Mystère", None, None, "a_verifier"),
    ],
)
def test_classify_unit(unit, base, factor, status):
    row = classify_unit(unit)
    assert row["base_unit"] == base
    assert row["status"] == status
    if factor is None:
        assert row["factor_to_base"] is None
    else:
        assert row["factor_to_base"] == pytest.approx(factor, rel=1e-6)


def test_classify_commodity_translates_known_names():
    row = classify_commodity("Rice (imported)", "cereals and tubers")
    assert row["name_fr"] == "Riz (importé)"
    assert row["group_fr"] == "Céréales et tubercules"
    assert row["include_in_index"] == "true"
    assert row["status"] == "auto"


def test_classify_commodity_flags_unknown_parts_and_non_food():
    unknown = classify_commodity("Cassava (bâton)", "cereals and tubers")
    assert unknown["name_fr"] == "Manioc (bâton)"
    assert unknown["status"] == "a_verifier"

    fuel = classify_commodity("Fuel (diesel)", "non-food")
    assert fuel["name_fr"] == "Carburant (gazole)"
    assert fuel["include_in_index"] == "false"


def test_build_keeps_manual_corrections(tmp_path):
    seeds = tmp_path / "seeds"
    seeds.mkdir()
    (seeds / "unit_conversion.csv").write_text(
        "unit_raw,quantity,base_unit,factor_to_base,status,note\nCuvette (2.5 KG),2.5,kg,2.5,converti,relu\n",
        encoding="utf-8",
    )
    distinct = Distinct(units=["Cuvette (2.5 KG)", "KG"], commodities=[("Maize (white)", "cereals and tubers")])

    summary = build(distinct, seeds)

    assert summary["unites_ajoutees"] == 1
    with (seeds / "unit_conversion.csv").open(encoding="utf-8") as handle:
        rows = {r["unit_raw"]: r for r in csv.DictReader(handle)}
    assert rows["Cuvette (2.5 KG)"]["note"] == "relu"
    assert rows["KG"]["status"] == "converti"
    assert (seeds / "commodity_mapping.csv").read_text(encoding="utf-8").count("Maïs (blanc)") == 1
