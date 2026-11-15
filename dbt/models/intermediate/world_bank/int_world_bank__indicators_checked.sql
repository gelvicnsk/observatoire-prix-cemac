{{ config(materialized='view', docs={'node_color': '#f29900'}) }}

-- Aiguillage des indicateurs de la Banque mondiale (ADR-012).
-- Une valeur absente n'est pas une erreur (année non publiée) : elle est seulement filtrée dans le fait.
with indicators as (
    select
        *,
        count(*) over (partition by country_iso3, indicator_id, year) as n_same_key
    from {{ ref('stg_world_bank__indicators') }}
)

select
    i.* except (n_same_key),
    case
        when i.indicator_code is null                                 then 'indicateur_inconnu'
        when c.iso3 is null                                           then 'pays_hors_cemac'
        when i.n_same_key > 1                                         then 'doublon'
    end                                         as quarantine_reason
from indicators as i
left join {{ ref('country') }} as c on c.iso3 = i.country_iso3
