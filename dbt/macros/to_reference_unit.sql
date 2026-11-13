{# Convertit un prix vers l'unité de référence à partir du seed unit_conversion. Étape 5. #}
{% macro to_reference_unit(price_column, factor_column) %}
    safe_divide({{ price_column }}, {{ factor_column }})
{% endmacro %}
