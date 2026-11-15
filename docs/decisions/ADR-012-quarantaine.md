# ADR-012 : une branche de quarantaine à chaque étape, au lieu d'arrêter le pipeline

Statut : accepté. Modifie l'ADR-005 (ingestion) et les contrôles de l'étape 5.

## Contexte

Jusqu'ici, une donnée invalide **arrêtait** le pipeline. À l'ingestion, un fichier aux colonnes inattendues
était journalisé `failed`, et son contenu était perdu. Dans dbt, un seul prix négatif, une devise inattendue ou
un produit absent du référentiel faisait échouer un contrôle en `error`, et plus rien n'était publié pour
aucun pays. Une anomalie sur une ligne bloquait les 240 000 autres.

## Décision

À chaque étape, les données valides continuent par la **branche verte**. Les données refusées partent dans une
**branche rouge** de quarantaine, avec leur motif, et le run continue.

| Étape | Aiguillage | Branche rouge | Retour automatique |
|---|---|---|---|
| Ingestion | `ingestion.pipeline.quarantine` | fichier d'origine dans `raw/_quarantine/`, statut `quarantined` dans `meta.load_log`, vue `quarantine.qrt_ingestion__files` | `ingestion.replay`, lancé au début de chaque job d'ingestion |
| Silver | `int_wfp__prices_checked`, `int_chirps__rainfall_checked`, `int_world_bank__indicators_checked`, `int_ecb__fx_checked` | `quarantine.qrt_*`, une table par source, avec `quarantine_reason` | tout est recalculé depuis bronze à chaque run |

- **Motifs de quarantaine (silver)**. Prix : champ obligatoire vide, prix nul ou négatif, devise autre que XAF,
  type de prix inconnu, doublon, produit, unité ou marché absent du référentiel. Pluie : champ vide, code
  administratif de forme inconnue, pluie négative, doublon. Banque mondiale : indicateur inconnu, pays hors
  CEMAC, doublon. Change : taux hors de [0,5 ; 2], doublon.
- **Quarantaine et exclusion ne se confondent pas.** Une ligne *exclue* est valide, mais hors du périmètre par
  choix (bétail sur pied, unité sans poids : `exclusion_reason`). Une ligne *en quarantaine* est une erreur à
  corriger (`quarantine_reason`).
- **Sortie de quarantaine sans intervention.** Une ligne refusée parce qu'un produit manque au référentiel
  passe d'elle-même au run suivant, une fois le référentiel complété (`make seeds-reference`, relecture, fusion).
  Un fichier refusé est rejoué au début de l'ingestion suivante, une fois le code corrigé et déployé.
- **Visibilité.**
  - Lineage dbt : la branche verte est en vert, les aiguillages en orange, la quarantaine en rouge. La documentation
    est publiée à chaque run dans `reports/dbt-docs/latest/report.html`.
  - Contrôles : chaque table de quarantaine a un test `is_empty` en `warn`. Le run continue, mais le nombre de
    lignes refusées apparaît dans le résultat de dbt et dans l'historique d'Elementary.
  - `gold.mart_pipeline_status` : par étape, source et motif, ce qui est passé (vert) et ce qui est en quarantaine
    (rouge), pour le tableau de bord.
- **Ce qui arrête encore le run.** Les erreurs qui révèlent un défaut du *code* et non des *données* :
  - une clé non unique dans les faits ;
  - le contrat de `fct_price_monthly` ;
  - le rapprochement Python ;
  - un échec de téléchargement, puisqu'il n'y a alors aucun contenu à mettre de côté.

  Une donnée refusée ne peut pas atteindre gold, puisqu'elle a été arrêtée en amont. Une erreur en gold est donc un défaut de code.

## Conséquences

- Les contrôles bloquants du staging (prix positif, devise XAF, type de prix, unicité) sont remplacés par
  l'aiguillage. Les mêmes contrôles restent en `error` sur les modèles en aval : ils passent par construction,
  et un échec révélerait un défaut de l'aiguillage lui-même.
- Le rapprochement Python applique les mêmes règles de quarantaine, écrites une seconde fois, pour rester indépendant.
- Un compte qui lit la quarantaine en CI (`sa-dbt-ci`) a besoin de `meta` et de `quarantine` en lecture.
- `fct_price_monthly` n'est plus incrémentale. Lors de l'essai (un produit retiré du référentiel), ses 1 273 prix
  sont bien partis en quarantaine, mais la table incrémentale gardait leurs anciennes lignes : aucune nouvelle
  version de source ne déclenchait le recalcul de ces mois. Deux contrôles l'ont détecté et ont arrêté le run.
  La table est désormais reconstruite à chaque run, ce qui coûte quelques Mo de lecture.
