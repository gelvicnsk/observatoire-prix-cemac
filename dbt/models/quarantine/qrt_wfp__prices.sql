-- Branche rouge (ADR-012) : prix du PAM refusés par int_*_checked, avec leur motif.
-- Recalculée à chaque run : une ligne disparaît d'ici dès que sa cause est corrigée.
select *
from {{ ref('int_wfp__prices_checked') }}
where quarantine_reason is not null
