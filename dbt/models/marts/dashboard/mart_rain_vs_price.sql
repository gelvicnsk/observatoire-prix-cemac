{{ config(
    partition_by={'field': 'month', 'data_type': 'date', 'granularity': 'month'},
    cluster_by=['country_iso3', 'market_key']
) }}

-- Un marché, un mois : la pluie du district du marché à côté de l'évolution de ses prix au détail.
--
-- price_index_median : pour chaque série au détail du marché (un produit, une unité de base), prix du mois
--   rapporté à la moyenne des 24 mois précédents (100 = prix habituel), puis médiane sur les séries.
--   La médiane résiste à un produit isolé qui s'envole. Séries sans historique suffisant ou relevés suspects exclus
--   (mêmes règles que les alertes, ADR-009).
-- rainfall_*_pct_of_normal : pluie du mois et des 3 derniers mois en % de la normale 1989-2018 (ADR-007),
--   au niveau du district, ou de la région quand le district n'existe pas dans CHIRPS. Null sans pluie rattachée.
with prices as (
    select
        market_key,
        price_month                                                         as month,
        count(*)                                                            as n_series,
        approx_quantiles(100 * price_xaf_per_unit / reference_mean, 2)[offset(1)] as price_index_median,
        countif(alert_level is not null)                                    as n_alerts
    from {{ ref('mart_price_metrics') }}
    where has_enough_history
      and price_type = 'Retail'
      and reference_mean > 0
    group by market_key, price_month
)

select
    p.market_key,
    p.month,
    m.country_iso3,
    m.market_name,
    m.adm1_name,
    m.adm2_name,
    concat(cast(m.latitude as string), ',', cast(m.longitude as string))   as market_location,
    m.rainfall_pcode,
    m.rainfall_admin_level,
    p.n_series,
    p.price_index_median,
    p.n_alerts,
    r.rainfall_mm,
    r.rainfall_pct_of_normal,
    r.rainfall_3m_pct_of_normal,
    r.is_complete                                                           as is_rainfall_month_complete
from prices as p
inner join {{ ref('dim_market') }} as m on m.market_key = p.market_key
left join {{ ref('int_chirps__rainfall_monthly') }} as r
    on  r.country_iso3 = m.country_iso3
    and r.pcode = m.rainfall_pcode
    and r.rainfall_month = p.month
