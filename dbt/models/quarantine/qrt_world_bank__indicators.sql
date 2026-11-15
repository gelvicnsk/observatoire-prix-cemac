-- Branche rouge (ADR-012) : indicateurs de la Banque mondiale refusés par int_*_checked, avec leur motif.
-- Recalculée à chaque run : une ligne disparaît d'ici dès que sa cause est corrigée.
select *
from {{ ref('int_world_bank__indicators_checked') }}
where quarantine_reason is not null
