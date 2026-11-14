{{ config(severity='warn') }}
-- Contrôle de fraîcheur (README, section 7) : un pays actif sans nouveau relevé depuis 3 mois est signalé.
-- « warn » et non « error » : le retard vient de la source (le PAM), pas du pipeline.
select country_iso3, last_price_month, months_since_last_price
from {{ ref('mart_data_freshness') }}
where is_stale
