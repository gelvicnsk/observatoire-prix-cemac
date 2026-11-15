{{ config(materialized='view', docs={'node_color': '#f29900'}) }}

-- Aiguillage de la pluie CHIRPS (ADR-012) : null -> int_chirps__rainfall_dekads, sinon -> qrt_chirps__rainfall.
with rainfall as (
    select
        *,
        count(*) over (partition by country_iso3, wfp_admin_id, dekad_start_date) as n_same_key
    from {{ ref('stg_chirps__rainfall_dekads') }}
)

select
    * except (n_same_key),
    case
        when dekad_start_date is null or pcode is null                then 'champ_obligatoire_vide'
        when admin_level is null                                      then 'code_administratif_de_forme_inconnue'
        when rainfall_mm < 0                                          then 'pluie_negative'
        when n_same_key > 1                                           then 'doublon'
    end                                         as quarantine_reason
from rainfall
