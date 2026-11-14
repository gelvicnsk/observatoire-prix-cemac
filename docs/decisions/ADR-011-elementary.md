# ADR-011 : Elementary pour l'historique des contrôles et la détection d'anomalies de volume

Statut : accepté (étape 8).

## Contexte

Les 118 contrôles dbt et le rapprochement Python vérifient que les données sont **cohérentes** : clés uniques,
relations, prix positifs, mêmes chiffres par deux calculs indépendants. Ils ne vérifient pas qu'elles sont
**complètes**. Si le PAM publiait pour un pays un fichier tronqué à moitié, toutes les lignes restantes
seraient cohérentes et chaque contrôle passerait. Seule une comparaison avec les exécutions précédentes
peut le voir.

Par ailleurs, les résultats des contrôles ne sont conservés que dans les journaux Cloud Run : on ne peut pas
dire depuis quand un avertissement est présent, ni suivre leur évolution.

## Décision

- Le paquet dbt **Elementary 0.26.1** (dbt Hub, version figée), dont les tables sont écrites dans un dataset
  `elementary` créé par Terraform. Seul `sa-dbt` y écrit.
- **Désactivé dans la cible `ci`** (modèles et tests) : la CI ne doit pas remplir l'historique de dev.
- Six tests, en `warn` le temps de constituer l'historique (une exécution par mois) :

| Test | Sur | Ce qu'il détecte |
|---|---|---|
| `dimension_anomalies` par pays | `stg_wfp__prices`, `stg_chirps__rainfall_dekads` | un pays dont le nombre de lignes chute ou bondit |
| `volume_anomalies` | `fct_price_monthly`, `mart_price_alerts` | un volume de faits ou d'alertes inhabituel |
| `schema_changes` | `fct_price_monthly`, `mart_price_alerts` | une colonne ajoutée, retirée ou retypée |

- Le **rapport HTML** (`edr report`) est produit à la fin du job `obs-transform`, puis déposé dans le bucket
  privé `<projet>-reports`, en deux copies : une datée, et `elementary/latest/`. Son échec ne fait jamais
  échouer le job, puisque tous les contrôles ont déjà tourné.
- Pas d'alerte Slack : le rythme est mensuel, et le rapport suffit.

## Conséquences

- Les tests d'anomalie n'apprennent qu'au fil des exécutions : il leur faut plusieurs mois d'historique avant
  de signaler quoi que ce soit. Ils passeront en `error` une fois cet historique constitué.
- `dbt_utils` passe lui aussi par le dbt Hub, et non plus par Git : Elementary en dépend par le Hub, et dbt
  refuse le même paquet venu de deux sources.
- L'image du pipeline grossit (client `edr` et ses dépendances). Le temps d'exécution n'augmente que de quelques secondes.
