{{ config(
    partition_by={'field': 'price_month', 'data_type': 'date', 'granularity': 'month'},
    cluster_by=['country_iso3', 'commodity_key']
) }}

-- Indicateurs d'évolution de chaque série de prix (un marché, un produit, un type de prix, une unité de base),
-- mois par mois. Sert aux alertes et à la calibration de leurs seuils.
--
-- Règles (README, section 7) :
--   - les relevés suspects sont retirés de la série : ni testés, ni utilisés comme référence ;
--   - période de référence : les {{ var('alert_reference_months') }} mois qui précèdent, SANS le mois testé ;
--   - fenêtres en mois civils (range), pas en lignes : un mois manquant n'est pas remplacé par un plus ancien ;
--   - moins de {{ var('alert_min_history_months') }} mois de référence : pas d'alerte ;
--   - une alerte exige les DEUX conditions : un écart anormal à l'historique (z-score) ET une hausse
--     sensible sur 1 mois. Avec « ou », la calibration donnait jusqu'à 176 alertes par mois au Tchad (ADR-009).
--     Un historique parfaitement stable (écart type nul) compte comme anormal dès que le prix le dépasse.
with series as (
    select
        price_monthly_id,
        price_month,
        country_iso3,
        market_key,
        commodity_key,
        price_type,
        base_unit,
        cast(price_xaf_per_unit as float64)                 as price,
        date_diff(price_month, date '2000-01-01', month)    as month_index
    from {{ ref('fct_price_monthly') }}
    where not is_suspect
),

windowed as (
    select
        *,
        max(price) over (s range between 1 preceding and 1 preceding)      as price_prev_1m,
        max(price) over (s range between 12 preceding and 12 preceding)    as price_prev_12m,
        avg(price) over reference                                           as reference_mean,
        stddev_samp(price) over reference                                   as reference_stddev,
        count(*) over reference                                             as reference_months
    from series
    window
        s as (partition by market_key, commodity_key, price_type, base_unit order by month_index),
        reference as (s range between {{ var('alert_reference_months') }} preceding and 1 preceding)
),

metrics as (
    select
        *,
        100 * (safe_divide(price, price_prev_1m) - 1)                       as change_1m_pct,
        100 * (safe_divide(price, price_prev_12m) - 1)                      as change_12m_pct,
        if(reference_stddev > 0, (price - reference_mean) / reference_stddev, null) as z_score,
        reference_stddev = 0 and price > reference_mean                     as is_above_flat_history,
        reference_months >= {{ var('alert_min_history_months') }}           as has_enough_history
    from windowed
)

select
    price_monthly_id,
    price_month,
    country_iso3,
    market_key,
    commodity_key,
    price_type,
    base_unit,
    price                                   as price_xaf_per_unit,
    price_prev_1m,
    price_prev_12m,
    change_1m_pct,
    change_12m_pct,
    reference_mean,
    reference_stddev,
    reference_months,
    z_score,
    is_above_flat_history,
    has_enough_history,
    case
        when not has_enough_history then null
        when coalesce(z_score >= {{ var('alert_z_strong') }}, is_above_flat_history)
         and change_1m_pct >= {{ var('alert_change_1m_strong_pct') }} then 'forte'
        when coalesce(z_score >= {{ var('alert_z_threshold') }}, is_above_flat_history)
         and change_1m_pct >= {{ var('alert_change_1m_pct') }} then 'moderee'
    end                                     as alert_level
from metrics
