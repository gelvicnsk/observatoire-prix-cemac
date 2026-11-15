{{ config(
    materialized='table',
    partition_by={'field': 'price_month', 'data_type': 'date', 'granularity': 'month'},
    cluster_by=['country_iso3', 'commodity_key'],
    contract={'enforced': true}
) }}

-- Grain : un marché, un produit, un type de prix (détail ou gros), une unité de base (kg ou l), un mois.
-- Le détail et le gros ne sont jamais moyennés ensemble (README, section 7). L'unité de base fait partie
-- du grain : un produit vendu au kg et au litre donne deux lignes, jamais une moyenne des deux.
--
-- Reconstruite entièrement à chaque run (ADR-012). Une table incrémentale ne recalculait que les mois touchés
-- par une nouvelle version de source : une ligne partie en quarantaine sans nouvelle version (référentiel
-- modifié) restait dans les faits. À 240 000 lignes, la reconstruction complète coûte quelques Mo de lecture.
with source as (
    select *
    from {{ ref('int_wfp__prices_normalized') }}
    where exclusion_reason is null
),

monthly as (
    select
        country_iso3,
        market_name,
        commodity_name_fr,
        price_type,
        base_unit,
        price_month,
        count(*)                                                as n_observations,
        countif(is_suspect)                                     as n_suspect_observations,
        avg(price_xaf_per_unit)                                 as price_xaf_per_unit,
        string_agg(distinct unit_raw, ', ' order by unit_raw)   as units_raw,
        logical_or(lower(price_flag) like '%aggregate%')        as has_aggregate,
        max(ingested_at)                                        as source_ingested_at
    from source
    group by country_iso3, market_name, commodity_name_fr, price_type, base_unit, price_month
),

fx as (
    select month, xaf_per_usd from {{ ref('int_ecb__fx_checked') }}
    where quarantine_reason is null
)

select
    cast({{ dbt_utils.generate_surrogate_key(
        ['m.country_iso3', 'm.market_name', 'm.commodity_name_fr', 'm.price_type', 'm.base_unit', 'm.price_month']
    ) }} as string)                                                     as price_monthly_id,
    m.price_month,
    m.country_iso3,
    cast({{ dbt_utils.generate_surrogate_key(['m.country_iso3', 'm.market_name']) }} as string) as market_key,
    cast({{ dbt_utils.generate_surrogate_key(['m.commodity_name_fr']) }} as string)            as commodity_key,
    m.price_type,
    m.base_unit,
    m.n_observations,
    m.n_suspect_observations,
    m.n_suspect_observations > 0                                        as is_suspect,
    m.units_raw,
    m.has_aggregate,
    cast(round(m.price_xaf_per_unit, 4) as numeric)              as price_xaf_per_unit,
    cast(round(m.price_xaf_per_unit / numeric '655.957', 4) as numeric) as price_eur_per_unit,
    cast(round(m.price_xaf_per_unit / fx.xaf_per_usd, 4) as numeric)    as price_usd_per_unit,
    cast(fx.xaf_per_usd as numeric)                              as xaf_per_usd,
    m.source_ingested_at
from monthly as m
left join fx on fx.month = m.price_month
