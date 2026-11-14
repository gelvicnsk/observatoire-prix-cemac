{{ config(
    partition_by={'field': 'rainfall_month', 'data_type': 'date', 'granularity': 'month'},
    cluster_by=['country_iso3', 'pcode']
) }}

-- Pluie mensuelle par code administratif : somme des trois décades du mois, et cumul sur 3 mois glissants.
-- rainfall_pct_of_normal = 100 × pluie / normale 1989-2018, null si la normale est inférieure à 1 mm (ADR-007).
-- is_complete = faux pour un mois dont toutes les décades ne sont pas encore publiées (le mois en cours).
with monthly as (
    select
        country_iso3,
        pcode,
        any_value(admin_level)              as admin_level,
        rainfall_month,
        count(*)                            as n_dekads,
        sum(rainfall_mm)                    as rainfall_mm,
        sum(rainfall_lta_mm)                as rainfall_lta_mm
    from {{ ref('int_chirps__rainfall_dekads') }}
    group by country_iso3, pcode, rainfall_month
),

rolling as (
    select
        *,
        -- fenêtre sur les 3 mois civils (et non sur les 3 dernières lignes), au cas où un mois manquerait
        sum(rainfall_mm) over w3            as rainfall_3m_mm,
        sum(rainfall_lta_mm) over w3        as rainfall_3m_lta_mm,
        count(*) over w3                    as n_months_3m
    from monthly
    window w3 as (
        partition by country_iso3, pcode
        order by date_diff(rainfall_month, date '1980-01-01', month)
        range between 2 preceding and current row
    )
)

select
    country_iso3,
    pcode,
    admin_level,
    rainfall_month,
    n_dekads,
    n_dekads = 3                            as is_complete,
    rainfall_mm,
    rainfall_lta_mm,
    if(rainfall_lta_mm >= 1, 100 * rainfall_mm / rainfall_lta_mm, null)                 as rainfall_pct_of_normal,
    if(n_months_3m = 3, rainfall_3m_mm, null)                                           as rainfall_3m_mm,
    if(n_months_3m = 3, rainfall_3m_lta_mm, null)                                       as rainfall_3m_lta_mm,
    if(n_months_3m = 3 and rainfall_3m_lta_mm >= 1, 100 * rainfall_3m_mm / rainfall_3m_lta_mm, null)
                                                                                        as rainfall_3m_pct_of_normal
from rolling
