"""Configuration de l'ingestion : pays, sources, emplacements GCP."""

from pydantic_settings import BaseSettings, SettingsConfigDict

# Pays CEMAC : code ISO3 -> nom en français
CEMAC_COUNTRIES: dict[str, str] = {
    "COG": "République du Congo",
    "CMR": "Cameroun",
    "CAF": "Centrafrique",
    "TCD": "Tchad",
    "GAB": "Gabon",
    "GNQ": "Guinée équatoriale",
}

# Suffixe utilisé dans les identifiants des jeux HDX (« wfp-food-prices-for-<suffixe> »).
# Ce ne sont que des candidats : si l'identifiant n'existe pas, le client HDX
# cherche le jeu par le groupe pays (code ISO3) et l'organisation.
HDX_COUNTRY_SLUGS: dict[str, str] = {
    "COG": "congo",
    "CMR": "cameroon",
    "CAF": "central-african-republic",
    "TCD": "chad",
    "GAB": "gabon",
    "GNQ": "equatorial-guinea",
}

HDX_BASE_URL = "https://data.humdata.org"
HTTP_USER_AGENT = "observatoire-prix-cemac/0.1 (projet personnel ; github.com/gelvicnsk)"

# Colonnes attendues dans les fichiers de prix du PAM publiés sur HDX
WFP_REQUIRED_COLUMNS: tuple[str, ...] = (
    "date",
    "admin1",
    "admin2",
    "market",
    "latitude",
    "longitude",
    "category",
    "commodity",
    "unit",
    "priceflag",
    "pricetype",
    "currency",
    "price",
)
WFP_OPTIONAL_COLUMNS: tuple[str, ...] = ("usdprice", "market_id", "commodity_id")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gcp_project_id: str = ""
    gcp_region: str = "europe-west1"
    bq_location: str = "EU"
    gcs_raw_bucket: str = ""
    countries: str = ",".join(CEMAC_COUNTRIES)

    @property
    def country_list(self) -> list[str]:
        return [c.strip() for c in self.countries.split(",") if c.strip()]
