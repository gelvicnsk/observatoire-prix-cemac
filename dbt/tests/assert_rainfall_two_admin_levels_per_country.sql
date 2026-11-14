-- Chaque pays de la pluie CHIRPS doit avoir des régions ET des districts. Si un pays n'avait qu'une forme de
-- code, la règle de staging classerait tout en région (1) sans erreur : ce test le signale.
select country_iso3, count(distinct admin_level) as levels
from {{ ref('stg_chirps__rainfall_dekads') }}
group by country_iso3
having count(distinct admin_level) != 2
