-- Rapprochement : chaque relevé retenu dans int_wfp__prices_normalized est compté une fois, et une seule,
-- dans fct_price_monthly (ni perdu, ni dupliqué par une jointure). Par pays, pour situer un écart.
with source as (
    select country_iso3, count(*) as n
    from {{ ref('int_wfp__prices_normalized') }}
    where exclusion_reason is null
    group by 1
),

facts as (
    select country_iso3, sum(n_observations) as n
    from {{ ref('fct_price_monthly') }}
    group by 1
)

select coalesce(s.country_iso3, f.country_iso3) as country_iso3, s.n as source_rows, f.n as fact_rows
from source as s
full outer join facts as f using (country_iso3)
where s.n is distinct from f.n
