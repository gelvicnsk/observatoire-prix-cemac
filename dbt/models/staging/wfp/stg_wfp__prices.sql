-- Prix du PAM, dernière version publiée pour chaque pays. Renommage et typage uniquement :
-- aucune règle métier ici (normalisation des unités et des noms : étapes 5B et 5C).
with latest as (
    {{ latest_snapshot(source('bronze', 'wfp_prices'), 'country') }}
)

select
    {{ dbt_utils.generate_surrogate_key([
        'country_iso3', 'market', 'commodity', 'unit', 'pricetype', 'priceflag', 'date'
    ]) }}                                   as price_observation_id,
    date                                    as price_date,
    date_trunc(date, month)                 as price_month,
    country_iso3,
    admin1                                  as admin1_name,
    admin2                                  as admin2_name,
    market                                  as market_name,
    market_id                               as wfp_market_id,
    latitude,
    longitude,
    category                                as commodity_category,
    commodity                               as commodity_name,
    commodity_id                            as wfp_commodity_id,
    unit                                    as unit_raw,
    pricetype                               as price_type,
    priceflag                               as price_flag,
    currency                                as currency_code,
    price                                   as price_local,
    usdprice                                as price_usd,
    source_sha256,
    ingested_at
from latest
