-- Fraîcheur des prix par pays : un pays actif sans nouveau relevé depuis {{ var('freshness_stale_months') }} mois
-- est signalé (is_stale), dans le tableau de bord et par un contrôle en « warn ».
select
    country_iso3,
    country_name_fr,
    data_status,
    last_price_month,
    date_diff(date_trunc(current_date(), month), last_price_month, month) as months_since_last_price,
    coalesce(
        data_status = 'actif'
        and date_diff(date_trunc(current_date(), month), last_price_month, month)
            >= {{ var('freshness_stale_months') }},
        false
    )                                       as is_stale
from {{ ref('dim_country') }}
