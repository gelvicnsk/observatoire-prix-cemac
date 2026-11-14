"""Relecture manuelle des seeds (étape 5B)."""

import pytest

from scripts.apply_review import ReviewError, apply
from scripts.map_markets_to_districts import Market, apply_coordinates
from scripts.seed_files import read_seed

SEED = "commodity_raw,name_fr,include_in_index,status\nPeanut,Peanut,true,a_verifier\nRice,Riz,true,auto\n"


def _write(path, text):
    path.write_text(text, encoding="utf-8")
    return path


def test_apply_overrides_given_values_and_marks_reviewed(tmp_path):
    seed = _write(tmp_path / "seed.csv", SEED)
    review = _write(
        tmp_path / "review.csv", "commodity_raw,name_fr,include_in_index,review_note\nPeanut,Arachide,,ok\n"
    )

    assert apply(seed, review, ("commodity_raw",)) == 1

    rows = {r["commodity_raw"]: r for r in read_seed(seed)}
    assert rows["Peanut"] == {
        "commodity_raw": "Peanut",
        "name_fr": "Arachide",
        "include_in_index": "true",
        "status": "relu",
    }
    assert rows["Rice"]["status"] == "auto"


def test_apply_keeps_an_explicit_status(tmp_path):
    seed = _write(tmp_path / "seed.csv", SEED)
    review = _write(tmp_path / "review.csv", "commodity_raw,status\nPeanut,a_verifier\n")
    apply(seed, review, ("commodity_raw",))
    assert read_seed(seed)[0]["status"] == "a_verifier"


@pytest.mark.parametrize(
    "review_text",
    ["commodity_raw,name_fr\nUnknown,X\n", "commodity_raw,colonne_inconnue\nPeanut,X\n"],
)
def test_apply_rejects_typos(tmp_path, review_text):
    seed = _write(tmp_path / "seed.csv", SEED)
    review = _write(tmp_path / "review.csv", review_text)
    with pytest.raises(ReviewError):
        apply(seed, review, ("commodity_raw",))


def test_apply_coordinates(tmp_path):
    markets = [
        Market("TCD", "Oum Hadjer", None, None, None, None, None),
        Market("TCD", "Sarh", None, None, None, 9.1, 18.4),
    ]
    fixes = _write(
        tmp_path / "c.csv", "country_iso3,market_name,latitude,longitude,source\nTCD,Oum Hadjer,13.3,19.7,x\n"
    )

    fixed, count = apply_coordinates(markets, fixes)

    assert count == 1
    assert (fixed[0].latitude, fixed[0].longitude) == (13.3, 19.7)
    assert fixed[1] == markets[1]

    _write(fixes, "country_iso3,market_name,latitude,longitude,source\nTCD,Inconnu,1,1,x\n")
    with pytest.raises(ValueError):
        apply_coordinates(markets, fixes)
