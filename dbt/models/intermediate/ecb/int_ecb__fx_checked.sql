{{ config(materialized='view', docs={'node_color': '#f29900'}) }}

-- Aiguillage du change EUR/USD de la BCE (ADR-012). Un taux hors de [0,5 ; 2] est une erreur de source :
-- il fausserait tous les prix en dollars du mois.
with fx as (
    select *, count(*) over (partition by month) as n_same_key
    from {{ ref('stg_ecb__fx_monthly') }}
)

select
    * except (n_same_key),
    case
        when month is null or usd_per_eur is null                     then 'champ_obligatoire_vide'
        when usd_per_eur not between 0.5 and 2                        then 'taux_aberrant'
        when n_same_key > 1                                           then 'doublon'
    end                                         as quarantine_reason
from fx
