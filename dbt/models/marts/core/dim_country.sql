-- Un pays de la CEMAC, avec la profondeur réelle de ses prix.
-- data_status : actif (dernier prix il y a 6 mois ou moins), historique (plus ancien), absent (aucun prix).
with prices as (
    select
        country_iso3,
        min(price_month)                    as first_price_month,
        max(price_month)                    as last_price_month,
        count(distinct market_name)         as n_markets,
        count(distinct commodity_name_fr)   as n_commodities
    from {{ ref('int_wfp__prices_normalized') }}
    where exclusion_reason is null
    group by country_iso3
)

select
    c.iso3                                  as country_iso3,
    c.name_fr                               as country_name_fr,
    c.currency,
    p.first_price_month,
    p.last_price_month,
    coalesce(p.n_markets, 0)                as n_markets,
    coalesce(p.n_commodities, 0)            as n_commodities,
    case
        when p.last_price_month is null then 'absent'
        when p.last_price_month < date_sub(date_trunc(current_date(), month), interval 6 month) then 'historique'
        else 'actif'
    end                                     as data_status
from {{ ref('country') }} as c
left join prices as p on p.country_iso3 = c.iso3
