-- Taux EUR/USD moyens mensuels de la BCE (dernière version). Le franc CFA est à parité fixe :
-- 1 EUR = 655,957 XAF, d'où le taux XAF/USD.
with versions as (
    select source_sha256, max(ingested_at) as ingested_at
    from {{ source('bronze', 'fx_eur_usd') }}
    group by 1
),

latest as (
    select source_sha256
    from versions
    qualify row_number() over (order by ingested_at desc) = 1
)

select
    fx.month,
    fx.usd_per_eur,
    cast(655.957 as numeric)                            as xaf_per_eur,
    round(cast(655.957 as numeric) / fx.usd_per_eur, 6) as xaf_per_usd,
    fx.source_sha256,
    fx.ingested_at
from {{ source('bronze', 'fx_eur_usd') }} as fx
inner join latest using (source_sha256)
