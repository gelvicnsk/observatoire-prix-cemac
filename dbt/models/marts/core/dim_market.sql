-- Un marché du PAM, rattaché à son district officiel (COD-AB) et au code pluie CHIRPS (seed market_district,
-- étape 5B). Les marchés exclus (moyenne nationale du PAM) n'y figurent pas.
select
    {{ dbt_utils.generate_surrogate_key(['country_iso3', 'market_name']) }} as market_key,
    country_iso3,
    market_name,
    wfp_market_id,
    latitude,
    longitude,
    adm1_pcode,
    adm1_name,
    adm2_pcode,
    adm2_name,
    rainfall_pcode,
    rainfall_admin_level,
    method                                  as district_mapping_method,
    shared_coordinates
from {{ ref('market_district') }}
where status != 'exclu'
