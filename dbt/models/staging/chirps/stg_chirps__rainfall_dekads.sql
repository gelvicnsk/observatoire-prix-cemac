-- Pluie CHIRPS par unité administrative et par décade, dernière version publiée pour chaque pays.
-- Le fichier « adm2 » contient aussi des lignes de niveau région (code à 4 caractères, ex. CG01)
-- à côté des districts (6 caractères, ex. CG0101) : le niveau est déduit de la longueur du code.
with latest as (
    {{ latest_snapshot(source('bronze', 'rainfall_adm2'), 'country') }}
)

select
    date                                    as dekad_start_date,
    date_trunc(date, month)                 as rainfall_month,
    country_iso3,
    pcode,
    case length(pcode) when 4 then 1 when 6 then 2 end as admin_level,
    adm2_id                                 as wfp_admin_id,
    n_pixels,
    rfh                                     as rainfall_mm,
    rfh_avg                                 as rainfall_lta_mm,
    r1h                                     as rainfall_1m_mm,
    r1h_avg                                 as rainfall_1m_lta_mm,
    r3h                                     as rainfall_3m_mm,
    r3h_avg                                 as rainfall_3m_lta_mm,
    rfq                                     as rainfall_anomaly_pct,
    r1q                                     as rainfall_1m_anomaly_pct,
    r3q                                     as rainfall_3m_anomaly_pct,
    version                                 as data_version,
    source_sha256,
    ingested_at
from latest
