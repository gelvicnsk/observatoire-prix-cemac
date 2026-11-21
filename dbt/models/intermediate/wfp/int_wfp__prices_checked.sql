{{ config(materialized='view', docs={'node_color': '#f29900'}) }}

-- Aiguillage des prix du PAM (ADR-012) : chaque ligne reçoit un motif de quarantaine, ou null si elle passe.
--   null              -> int_wfp__prices_normalized (branche verte)
--   motif renseigné   -> qrt_wfp__prices            (branche rouge)
-- Rien n'est supprimé : une ligne en quarantaine en sort d'elle-même au run suivant dès que la cause est
-- corrigée (référentiel complété, nouvelle version du fichier), puisque tout est recalculé depuis bronze.
-- Le premier motif rencontré l'emporte, dans l'ordre ci-dessous.
--
-- Dernier motif, pic_isole_suspect (ADR-013) : le prix mensuel d'une série (pays, marché, produit, type de
-- prix, unité de base) est au moins spike_factor fois plus haut (ou plus bas) que le mois d'avant ET que le
-- mois d'après, alors que ces deux voisins sont proches l'un de l'autre. Un aller-retour d'un seul mois de
-- cette ampleur ressemble à une erreur de saisie de la source (exemple : sel, Centrafrique, décembre 2025).
-- Le dernier mois d'une série n'a pas de voisin suivant : il ne peut être signalé qu'au run suivant.
with prices as (
    select
        *,
        count(*) over (partition by price_observation_id) as n_same_key
    from {{ ref('stg_wfp__prices') }}
),

joined as (
    select
        p.* except (n_same_key),
        c.name_fr                                   as commodity_name_fr,
        c.group_fr                                  as commodity_group_fr,
        c.include_in_index,
        u.base_unit,
        u.factor_to_base,
        u.status                                    as unit_status,
        m.status                                    as market_status,
        case
            when p.price_date is null or p.market_name is null or p.commodity_name is null
              or p.unit_raw is null or p.price_local is null              then 'champ_obligatoire_vide'
            when p.price_local <= 0                                       then 'prix_nul_ou_negatif'
            when p.currency_code is null or p.currency_code != 'XAF'     then 'devise_inattendue'
            when p.price_type is null or p.price_type not in ('Retail', 'Wholesale') then 'type_de_prix_inconnu'
            when p.n_same_key > 1                                         then 'doublon'
            when c.commodity_raw is null                                  then 'produit_absent_du_referentiel'
            when u.unit_raw is null                                       then 'unite_absente_du_referentiel'
            when m.market_name is null                                    then 'marche_absent_du_referentiel'
        end                                         as row_reason,
        -- lignes qui entrent dans le calcul des pics : valides, convertibles, et pas une prévision
        coalesce(u.status = 'converti' and not coalesce(lower(p.price_flag) like '%forecast%', false), false)
                                                    as is_spike_candidate
    from prices as p
    left join {{ ref('commodity_mapping') }} as c on c.commodity_raw = p.commodity_name
    left join {{ ref('unit_conversion') }} as u on u.unit_raw = p.unit_raw
    left join {{ ref('market_district') }} as m
        on m.country_iso3 = p.country_iso3 and m.market_name = p.market_name
),

-- prix mensuel de chaque série, calculé comme dans fct_price_monthly
monthly as (
    select
        country_iso3,
        market_name,
        commodity_name_fr,
        price_type,
        base_unit,
        price_month,
        round(avg(round(price_local / cast(factor_to_base as numeric), 4)), 4) as month_price
    from joined
    where row_reason is null and is_spike_candidate
    group by 1, 2, 3, 4, 5, 6
),

neighbours as (
    select
        *,
        lag(month_price) over series   as prev_price,
        lag(price_month) over series   as prev_month,
        lead(month_price) over series  as next_price,
        lead(price_month) over series  as next_month
    from monthly
    window series as (
        partition by country_iso3, market_name, commodity_name_fr, price_type, base_unit
        order by price_month
    )
),

spikes as (
    select country_iso3, market_name, commodity_name_fr, price_type, base_unit, price_month
    from neighbours
    where prev_month = date_sub(price_month, interval 1 month)
      and next_month = date_add(price_month, interval 1 month)
      -- les deux voisins se ressemblent : le mois testé est bien un aller-retour isolé
      and greatest(prev_price, next_price)
          <= cast('{{ var("spike_neighbours_max_ratio") }}' as numeric) * least(prev_price, next_price)
      and (
            (month_price >= cast('{{ var("spike_factor") }}' as numeric) * prev_price
             and month_price >= cast('{{ var("spike_factor") }}' as numeric) * next_price)
         or (month_price * cast('{{ var("spike_factor") }}' as numeric) <= prev_price
             and month_price * cast('{{ var("spike_factor") }}' as numeric) <= next_price)
      )
)

select
    j.* except (row_reason, is_spike_candidate),
    coalesce(
        j.row_reason,
        if(s.price_month is not null, 'pic_isole_suspect', null)
    )                                               as quarantine_reason
from joined as j
left join spikes as s
    on  j.is_spike_candidate
    and j.row_reason is null
    and s.country_iso3 = j.country_iso3
    and s.market_name = j.market_name
    and s.commodity_name_fr = j.commodity_name_fr
    and s.price_type = j.price_type
    and s.base_unit = j.base_unit
    and s.price_month = j.price_month
