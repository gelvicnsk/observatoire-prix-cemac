# ADR-010 : une image, deux Cloud Run Jobs, un déclenchement mensuel, la même image en dev puis en prod

Statut : accepté (étape 7).

## Contexte

Le pipeline doit tourner chaque mois sans intervention : ingestion des sources publiques, puis dbt
(modèles et 118 contrôles), puis le rapprochement Python. Il faut aussi pouvoir déployer chaque fusion,
la tester, et revenir en arrière. L'ADR-002 exclut un orchestrateur de type Composer : son coût est
disproportionné pour deux étapes par mois.

## Décision

- **Une seule image** (`Dockerfile` à la racine), construite une fois par commit et étiquetée avec son numéro.
  Elle contient l'ingestion, dbt avec ses paquets figés, et le rapprochement.
- **Deux Cloud Run Jobs** sur cette image, chacun avec son compte de service. Les droits restent séparés comme
  à l'étape 2 :
  - `obs-ingestion` (`sa-ingestion`) écrit dans raw, bronze et meta ;
  - `obs-transform` (`sa-dbt`) lit bronze et raw, et écrit dans silver, gold et meta.
- **Cloud Scheduler** lance l'ingestion le 5 du mois à 3 h, et la transformation à 5 h (heure de Paris). On n'enchaîne
  pas les deux jobs : si l'ingestion échoue, la transformation repart des données bronze existantes, ce qui
  est sans risque puisqu'elle est idempotente. Le compte `sa-scheduler` n'a que le droit de lancer les jobs.
  En dev, le déclenchement est en pause : les jobs n'y tournent qu'au déploiement.
- **CD** (`cd.yml`) après chaque fusion sur `main`, par le pool `github-apply` :
  1. dev : `terraform apply`, construction et envoi de l'image, mise à jour des jobs, puis exécution des
     deux jobs jusqu'au bout. C'est le test de fumée : un contrôle dbt en erreur ou un rapprochement en échec arrête le déploiement.
  2. prod, après validation manuelle (environnement GitHub `prod`) : `terraform apply`, **copie de l'image
     testée en dev** (sans reconstruction), mise à jour des jobs et exécution complète.
- **Retour arrière** : relancer `cd` à la main avec `image_sha` = un commit déjà déployé. Artifact Registry garde
  les 10 dernières images.
- Terraform crée les jobs avec une image publique de départ et **ignore ensuite l'image**, qui appartient au CD.
  Sans cela, chaque `apply` reviendrait à l'image de départ.

## Conséquences

- Deux heures d'écart entre les jobs suffisent largement : l'ingestion prend quelques minutes.
- La prod exécute exactement l'image validée en dev, jamais une reconstruction.
- Chaque fusion relance une ingestion et un build complets en dev, puis en prod après validation. Le coût reste
  négligeable : les fichiers déjà ingérés sont reconnus à leur empreinte (ADR-005), et dbt traite moins
  d'un Go par exécution.
