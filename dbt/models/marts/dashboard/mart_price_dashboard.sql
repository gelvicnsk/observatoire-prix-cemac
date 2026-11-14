{{ config(
    partition_by={'field': 'price_month', 'data_type': 'date', 'granularity': 'month'},
    cluster_by=['country_iso3', 'commodity_name_fr']
) }}

-- Table « large » pour le tableau de bord : un prix mensuel (grain de fct_price_monthly) avec les noms du pays,
-- du marché et du produit, sa position (champ géographique « latitude,longitude » de Looker Studio) et ses
-- indicateurs d'évolution. Évite les fusions de sources dans Looker Studio, lentes et fragiles.
select
    f.price_monthly_id,
    f.price_month,
    f.country_iso3,
    c.country_name_fr,
    f.market_key,
    m.market_name,
    m.adm1_name,
    concat(cast(m.latitude as string), ',', cast(m.longitude as string))   as market_location,
    p.commodity_name_fr,
    p.commodity_group_fr,
    f.price_type,
    f.base_unit,
    f.price_xaf_per_unit,
    f.price_eur_per_unit,
    f.price_usd_per_unit,
    f.n_observations,
    f.is_suspect,
    mt.change_1m_pct,
    mt.change_12m_pct,
    mt.z_score,
    mt.alert_level
from {{ ref('fct_price_monthly') }} as f
inner join {{ ref('dim_country') }} as c on c.country_iso3 = f.country_iso3
inner join {{ ref('dim_market') }} as m on m.market_key = f.market_key
inner join {{ ref('dim_commodity') }} as p on p.commodity_key = f.commodity_key
left join {{ ref('mart_price_metrics') }} as mt on mt.price_monthly_id = f.price_monthly_id
