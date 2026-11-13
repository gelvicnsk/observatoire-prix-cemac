{# z-score d'une valeur par rapport à une fenêtre. Étape 6. #}
{% macro zscore(value, mean, stddev) %}
    safe_divide({{ value }} - {{ mean }}, nullif({{ stddev }}, 0))
{% endmacro %}
