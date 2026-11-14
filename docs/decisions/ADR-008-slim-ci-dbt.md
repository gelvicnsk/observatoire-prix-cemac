# ADR-008 : dbt en CI, modèles modifiés seulement, dans un dataset isolé

Statut : accepté (étape 5).

## Contexte

Les 102 contrôles dbt ne tournaient que sur le poste du développeur. Une pull request pouvait donc casser
un modèle ou un test sans que la CI le voie. Reconstruire tout le projet à chaque pull request serait
simple, mais inutile : la plupart des pull requests ne touchent pas dbt, ou n'en touchent qu'une partie.

## Décision

- Un job `dbt` dans `ci.yml`, sur chaque pull request :
  1. il lit le projet tel qu'il est sur `main` et en produit le manifeste (`dbt parse`, sans accès à BigQuery) ;
  2. il construit dans le dataset `ci` les seuls modèles modifiés et leurs descendants (`state:modified+`) ;
  3. il lit les parents inchangés dans dev, sans les reconstruire (`--defer`).
- Une identité dédiée, `sa-dbt-ci`, joignable depuis n'importe quelle branche du dépôt par le pool
  `github-plan`, sans clé. Elle lit `bronze`, `silver`, `gold` et le bucket raw, mais n'écrit que dans `ci`,
  dont les tables expirent au bout de 7 jours.
- Un lancement manuel (`workflow_dispatch`) accepte une autre sélection, par exemple `+fct_price_monthly`
  pour tout reconstruire depuis bronze.

## Conséquences

- Une pull request sans changement dbt passe en quelques secondes (« Nothing to do »).
- Les parents sont lus dans dev : si dev est en retard sur `main`, la CI compare à un état ancien.
  En pratique, dev est reconstruit à chaque étape. Le déploiement continu (étape 7) le garantira.
- Une erreur de manipulation en CI ne peut pas abîmer silver ni gold : le compte n'a pas le droit d'y écrire.
