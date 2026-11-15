{{ config(
    partition_by={'field': 'price_month', 'data_type': 'date', 'granularity': 'month'},
    cluster_by=['country_iso3', 'commodity_name_fr']
) }}

-- Prix du PAM qui ont passé l'aiguillage (int_wfp__prices_checked, ADR-012), ramenés au kg ou au litre.
-- Les lignes refusées (champ vide, prix négatif, produit absent du référentiel…) sont dans qrt_wfp__prices.
--
-- Parmi les lignes valides, certaines ne vont pas dans les faits, par choix et non par erreur : elles portent
-- un motif dans exclusion_reason (le premier rencontré, dans l'ordre ci-dessous). Les faits filtrent sur
-- exclusion_reason is null, et l'on peut toujours compter ce qui a été mis de côté, et pourquoi.
--
-- is_suspect : prix hors d'un facteur 10 de la médiane du même produit, type de prix et unité de base dans
-- le pays (sur tout l'historique). La ligne reste dans les faits, mais sera exclue des alertes (étape 6).
with joined as (
    select * from {{ ref('int_wfp__prices_checked') }}
    where quarantine_reason is null
),

classified as (
    select
        *,
        case
            when market_status = 'exclu' then 'marche_exclu'
            when not include_in_index then 'produit_hors_panier'
            when unit_status = 'exclu' then 'unite_exclue'
            when unit_status != 'converti' then 'unite_sans_poids'
            when lower(price_flag) like '%forecast%' then 'prevision'
        end                                         as exclusion_reason,
        case when unit_status = 'converti'
            then round(price_local / cast(factor_to_base as numeric), 4)
        end                                         as price_xaf_per_unit
    from joined
),

medians as (
    select
        country_iso3,
        commodity_name_fr,
        price_type,
        base_unit,
        approx_quantiles(price_xaf_per_unit, 2)[offset(1)] as median_xaf_per_unit
    from classified
    where exclusion_reason is null
    group by 1, 2, 3, 4
)

select
    c.price_observation_id,
    c.price_date,
    c.price_month,
    c.country_iso3,
    c.market_name,
    c.wfp_market_id,
    c.commodity_name                                as commodity_name_raw,
    c.commodity_name_fr,
    c.commodity_group_fr,
    c.unit_raw,
    c.base_unit,
    c.factor_to_base,
    c.price_type,
    c.price_flag,
    c.currency_code,
    c.price_local,
    c.price_xaf_per_unit,
    m.median_xaf_per_unit,
    coalesce(
        c.price_xaf_per_unit > 10 * m.median_xaf_per_unit or c.price_xaf_per_unit * 10 < m.median_xaf_per_unit,
        false
    )                                               as is_suspect,
    c.exclusion_reason,
    c.source_sha256,
    c.ingested_at
from classified as c
left join medians as m
    on  m.country_iso3 = c.country_iso3
    and m.commodity_name_fr = c.commodity_name_fr
    and m.price_type = c.price_type
    and m.base_unit = c.base_unit
    and c.exclusion_reason is null
