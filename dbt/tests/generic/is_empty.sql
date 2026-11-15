{#
  Test générique : la table doit être vide. Utilisé en « warn » sur chaque table de quarantaine (ADR-012) :
  le run continue, mais le nombre de lignes en quarantaine apparaît dans le résultat et dans Elementary.
#}
{% test is_empty(model) %}
    select * from {{ model }}
{% endtest %}
