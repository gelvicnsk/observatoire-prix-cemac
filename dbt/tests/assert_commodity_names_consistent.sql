-- Les noms du PAM regroupés sous un même nom français doivent avoir le même groupe et la même inclusion
-- dans l'indice ; sinon dim_commodity choisirait au hasard.
select name_fr, count(distinct group_fr) as n_groups,
       logical_or(include_in_index) as any_included, logical_and(include_in_index) as all_included
from {{ ref('commodity_mapping') }}
group by name_fr
having count(distinct group_fr) > 1 or logical_or(include_in_index) != logical_and(include_in_index)
