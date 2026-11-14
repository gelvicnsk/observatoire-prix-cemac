-- Grain : un pays, un indicateur (inflation, population), une année. Jamais mélangé aux prix (ADR-003).
select
    {{ dbt_utils.generate_surrogate_key(['country_iso3', 'indicator_code', 'year']) }} as indicator_yearly_id,
    country_iso3,
    indicator_code,
    indicator_id                            as world_bank_indicator_id,
    year,
    value,
    obs_status
from {{ ref('stg_world_bank__indicators') }}
where value is not null
