-- Branche rouge (ADR-012) : taux de change BCE refusés par int_*_checked, avec leur motif.
-- Recalculée à chaque run : une ligne disparaît d'ici dès que sa cause est corrigée.
select *
from {{ ref('int_ecb__fx_checked') }}
where quarantine_reason is not null
