{#
  Noms de datasets : les couches utilisent directement le nom demandé (silver, gold),
  sans le préfixe que dbt ajoute par défaut (silver_gold…). En dev et en prod, l'isolation
  vient du projet GCP. En CI, tout est écrit dans le dataset ci, effacé au bout de 7 jours.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if target.name == 'ci' or custom_schema_name is none -%}
        {{ target.dataset }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
