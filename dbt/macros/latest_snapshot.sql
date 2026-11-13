{#
  Les fichiers bronze sont des historiques complets, adressés par leur empreinte (ADR-005).
  Pour chaque valeur de la clé de partition (pays, indicateur…), on ne garde que les lignes
  de la version la plus récente : celle dont l'ingestion est la plus tardive.
#}
{% macro latest_snapshot(relation, partition_by) -%}
    with versions as (
        select
            {{ partition_by }} as partition_value,
            source_sha256,
            max(ingested_at) as ingested_at
        from {{ relation }}
        group by 1, 2
    ),

    latest as (
        select partition_value, source_sha256
        from versions
        qualify row_number() over (partition by partition_value order by ingested_at desc) = 1
    )

    select data.*
    from {{ relation }} as data
    inner join latest
        on data.{{ partition_by }} = latest.partition_value
        and data.source_sha256 = latest.source_sha256
{%- endmacro %}
