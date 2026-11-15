{{ config(materialized='view', docs={'node_color': '#f29900'}) }}

-- Aiguillage des prix du PAM (ADR-012) : chaque ligne reçoit un motif de quarantaine, ou null si elle passe.
--   null              -> int_wfp__prices_normalized (branche verte)
--   motif renseigné   -> qrt_wfp__prices            (branche rouge)
-- Rien n'est supprimé : une ligne en quarantaine en sort d'elle-même au run suivant dès que la cause est
-- corrigée (référentiel complété, nouvelle version du fichier), puisque tout est recalculé depuis bronze.
-- Le premier motif rencontré l'emporte, dans l'ordre ci-dessous.
with prices as (
    select
        *,
        count(*) over (partition by price_observation_id) as n_same_key
    from {{ ref('stg_wfp__prices') }}
)

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
    end                                         as quarantine_reason
from prices as p
left join {{ ref('commodity_mapping') }} as c on c.commodity_raw = p.commodity_name
left join {{ ref('unit_conversion') }} as u on u.unit_raw = p.unit_raw
left join {{ ref('market_district') }} as m
    on m.country_iso3 = p.country_iso3 and m.market_name = p.market_name
