-- Un produit normalisé (nom français). Plusieurs noms du PAM peuvent y correspondre
-- (« Groundnuts » et « Peanut » → Arachide) : ils sont listés dans source_names.
select
    {{ dbt_utils.generate_surrogate_key(['name_fr']) }} as commodity_key,
    name_fr                                 as commodity_name_fr,
    any_value(group_fr)                     as commodity_group_fr,
    logical_and(include_in_index)           as include_in_index,
    string_agg(commodity_raw, ' | ' order by commodity_raw) as source_names,
    count(*)                                as n_source_names
from {{ ref('commodity_mapping') }}
group by name_fr
