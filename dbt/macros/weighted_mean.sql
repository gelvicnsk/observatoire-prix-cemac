{# Moyenne de `column` pondérée par `weight`, en ignorant les valeurs nulles (et leur poids). #}
{% macro weighted_mean(column, weight) -%}
    safe_divide(sum({{ column }} * {{ weight }}), sum(if({{ column }} is null, null, {{ weight }})))
{%- endmacro %}
