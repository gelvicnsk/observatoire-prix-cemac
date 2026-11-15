-- État du pipeline à chaque étape (ADR-012) : ce qui est passé (vert) et ce qui est en quarantaine (rouge),
-- par source et par motif. Une ligne = une étape, une source, un résultat.
--   ingestion : fichiers, selon leur DERNIÈRE tentative (meta.load_log)
--   silver    : lignes, selon l'aiguillage int_*_checked
{% set checks = [
    ('wfp_prices', 'int_wfp__prices_checked'),
    ('rainfall', 'int_chirps__rainfall_checked'),
    ('world_bank', 'int_world_bank__indicators_checked'),
    ('fx', 'int_ecb__fx_checked'),
] %}

with latest_attempts as (
    select
        source,
        status,
        row_number() over (partition by source, partition_key order by finished_at desc) as attempt_rank
    from {{ source('meta', 'load_log') }}
),

ingestion as (
    select
        'ingestion'                                         as stage,
        source,
        'fichiers'                                          as unit,
        if(status in ('quarantined', 'failed'), status, 'passe') as outcome,
        count(*)                                            as n
    from latest_attempts
    where attempt_rank = 1
    group by source, outcome
),

silver as (
    {% for name, model in checks %}
    select
        'silver'                                            as stage,
        '{{ name }}'                                        as source,
        'lignes'                                            as unit,
        coalesce(quarantine_reason, 'passe')                as outcome,
        count(*)                                            as n
    from {{ ref(model) }}
    group by outcome
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
)

select
    stage,
    source,
    unit,
    outcome,
    n,
    outcome != 'passe'                                      as is_quarantined,
    if(outcome = 'passe', 'vert', 'rouge')                  as color,
    current_timestamp()                                     as computed_at
from (
    select * from ingestion
    union all
    select * from silver
)
