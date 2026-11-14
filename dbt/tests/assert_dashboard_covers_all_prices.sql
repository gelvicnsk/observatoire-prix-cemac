-- Le tableau de bord montre tous les prix : aucune ligne de fct_price_monthly perdue par les jointures.
select
    (select count(*) from {{ ref('fct_price_monthly') }})      as fact_rows,
    (select count(*) from {{ ref('mart_price_dashboard') }})   as dashboard_rows
from (select 1)
where (select count(*) from {{ ref('fct_price_monthly') }})
   != (select count(*) from {{ ref('mart_price_dashboard') }})
