-- Branche rouge de l'ingestion (ADR-012) : fichiers dont la DERNIÈRE tentative a échoué.
--   quarantined : fichier reçu mais refusé ; son contenu d'origine est dans le bucket raw, sous _quarantine/
--   failed      : téléchargement impossible ; rien à garder, la source sera de nouveau interrogée au run suivant
-- Un fichier qui passe ensuite (rejeu ou nouvelle version) a une dernière tentative en succès : il sort d'ici.
with attempts as (
    select
        *,
        row_number() over (partition by source, partition_key order by finished_at desc) as attempt_rank
    from {{ source('meta', 'load_log') }}
)

select
    source,
    partition_key,
    status,
    regexp_extract(message, r'quarantaine=(\S+)$')                  as quarantine_path,
    regexp_replace(message, r' \| quarantaine=\S+$', '')            as error_message,
    finished_at                                                     as last_attempt_at,
    run_id
from attempts
where attempt_rank = 1
  and status in ('quarantined', 'failed')
