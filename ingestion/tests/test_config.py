"""Premier test : la liste des pays CEMAC est complète."""

from ingestion.config import CEMAC_COUNTRIES, Settings


def test_six_cemac_countries():
    assert set(CEMAC_COUNTRIES) == {"COG", "CMR", "CAF", "TCD", "GAB", "GNQ"}


def test_country_list_from_settings():
    settings = Settings(countries="COG, CMR")
    assert settings.country_list == ["COG", "CMR"]
