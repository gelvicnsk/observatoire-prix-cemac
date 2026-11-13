-- Indicateurs annuels de la Banque mondiale, dernière version de chaque indicateur.
with latest as (
    {{ latest_snapshot(source('bronze', 'world_bank_indicators'), 'indicator') }}
)

select
    country_iso3,
    indicator_id,
    case indicator_id
        when 'FP.CPI.TOTL.ZG' then 'inflation_pct'
        when 'SP.POP.TOTL' then 'population'
    end                                     as indicator_code,
    indicator_name,
    year,
    value,
    nullif(obs_status, '')                  as obs_status,
    source_sha256,
    ingested_at
from latest
