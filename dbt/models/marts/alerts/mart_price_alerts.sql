-- Un marché, un produit, un type de prix, un mois en alerte : hausse anormale par rapport à l'historique
-- du même marché (règle et seuils : mart_price_metrics et dbt_project.yml). Noms joints pour le tableau de bord.
select
    a.price_monthly_id,
    a.price_month,
    a.alert_level,
    a.country_iso3,
    c.country_name_fr,
    a.market_key,
    m.market_name,
    m.adm1_name,
    m.latitude,
    m.longitude,
    a.commodity_key,
    p.commodity_name_fr,
    p.commodity_group_fr,
    a.price_type,
    a.base_unit,
    a.price_xaf_per_unit,
    a.price_prev_1m,
    a.change_1m_pct,
    a.change_12m_pct,
    a.reference_mean,
    a.reference_months,
    a.z_score
from {{ ref('mart_price_metrics') }} as a
inner join {{ ref('dim_market') }} as m on m.market_key = a.market_key
inner join {{ ref('dim_commodity') }} as p on p.commodity_key = a.commodity_key
inner join {{ ref('dim_country') }} as c on c.country_iso3 = a.country_iso3
where a.alert_level is not null
