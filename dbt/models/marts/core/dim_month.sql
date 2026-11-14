-- Un mois, de janvier 2000 (début de la série de change BCE) au mois en cours.
select
    m                                       as month,
    extract(year from m)                    as year,
    extract(quarter from m)                 as quarter,
    extract(month from m)                   as month_number,
    format_date('%Y-%m', m)                 as month_label
from unnest(generate_date_array(date '2000-01-01', date_trunc(current_date(), month), interval 1 month)) as m
