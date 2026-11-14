{{ config(
    partition_by={'field': 'rainfall_month', 'data_type': 'date', 'granularity': 'month'},
    cluster_by=['country_iso3', 'pcode']
) }}

-- Pluie CHIRPS : une ligne par pays, code administratif et décade.
--
-- Au Tchad, deux codes (TCD0703 et TCD2201) sont portés chacun par deux zones distinctes du PAM, sur toute
-- la période (identifiants, nombres de pixels et valeurs différents). On les fusionne : moyenne pondérée par
-- le nombre de pixels, c'est-à-dire la pluie sur la réunion des deux zones.
--
-- Écarts à la normale : la formule exacte du PAM (rfq, r1q, r3q) n'est pas 100 × pluie / normale (vérifié :
-- 22 % des lignes seulement). On garde donc la valeur publiée (moyenne pondérée pour les lignes fusionnées)
-- et on calcule notre propre indicateur, documenté, rainfall_pct_of_normal, utilisé dans gold.
with source as (
    select *, coalesce(n_pixels, 1) as weight
    from {{ ref('stg_chirps__rainfall_dekads') }}
),

merged as (
    select
        country_iso3,
        pcode,
        dekad_start_date,
        any_value(rainfall_month)                                as rainfall_month,
        any_value(admin_level)                                   as admin_level,
        count(*)                                                 as n_source_areas,
        sum(n_pixels)                                            as n_pixels,
        {{ weighted_mean('rainfall_mm', 'weight') }}             as rainfall_mm,
        {{ weighted_mean('rainfall_lta_mm', 'weight') }}         as rainfall_lta_mm,
        {{ weighted_mean('rainfall_1m_mm', 'weight') }}          as rainfall_1m_mm,
        {{ weighted_mean('rainfall_1m_lta_mm', 'weight') }}      as rainfall_1m_lta_mm,
        {{ weighted_mean('rainfall_3m_mm', 'weight') }}          as rainfall_3m_mm,
        {{ weighted_mean('rainfall_3m_lta_mm', 'weight') }}      as rainfall_3m_lta_mm,
        {{ weighted_mean('rainfall_anomaly_pct', 'weight') }}    as published_anomaly_pct,
        {{ weighted_mean('rainfall_1m_anomaly_pct', 'weight') }} as published_1m_anomaly_pct,
        {{ weighted_mean('rainfall_3m_anomaly_pct', 'weight') }} as published_3m_anomaly_pct,
        any_value(data_version)                                  as data_version,
        max(ingested_at)                                         as ingested_at
    from source
    group by country_iso3, pcode, dekad_start_date
)

select
    country_iso3,
    pcode,
    admin_level,
    dekad_start_date,
    rainfall_month,
    n_source_areas,
    n_pixels,
    rainfall_mm,
    rainfall_lta_mm,
    rainfall_1m_mm,
    rainfall_1m_lta_mm,
    rainfall_3m_mm,
    rainfall_3m_lta_mm,
    published_anomaly_pct,
    published_1m_anomaly_pct,
    published_3m_anomaly_pct,
    -- notre indicateur : pluie en % de la normale 1989-2018 (null si la normale est inférieure à 1 mm,
    -- où le rapport n'a pas de sens : saison sèche)
    if(rainfall_lta_mm >= 1, 100 * rainfall_mm / rainfall_lta_mm, null)             as rainfall_pct_of_normal,
    if(rainfall_1m_lta_mm >= 1, 100 * rainfall_1m_mm / rainfall_1m_lta_mm, null)    as rainfall_1m_pct_of_normal,
    if(rainfall_3m_lta_mm >= 1, 100 * rainfall_3m_mm / rainfall_3m_lta_mm, null)    as rainfall_3m_pct_of_normal,
    data_version,
    ingested_at
from merged
