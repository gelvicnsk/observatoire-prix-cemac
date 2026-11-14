-- Pluie CHIRPS par unité administrative et par décade, dernière version publiée pour chaque pays.
-- Le fichier « adm2 » contient aussi des lignes de niveau région à côté des districts. Chaque pays a
-- exactement deux formes de code, mais pas la même longueur d'un pays à l'autre :
--   CG01 / CG0101, CF11 / CF111, CM001 / CM001001, GQ198 / GQ198002, TCD01 / TCD0101.
-- Règle : dans chaque pays, la forme qui a le moins de chiffres est la région (1), l'autre le district (2).
with latest as (
    {{ latest_snapshot(source('bronze', 'rainfall_adm2'), 'country') }}
),

coded as (
    select *, length(regexp_replace(pcode, r'^[A-Z]+', '')) as pcode_digits
    from latest
)

select
    date                                    as dekad_start_date,
    date_trunc(date, month)                 as rainfall_month,
    country_iso3,
    pcode,
    case pcode_digits
        when min(pcode_digits) over (partition by country_iso3) then 1
        when max(pcode_digits) over (partition by country_iso3) then 2
    end                                     as admin_level,
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
from coded
