# Observatoire des prix alimentaires CEMAC

Pipeline batch mensuel sur Google Cloud qui rassemble les prix alimentaires publics
des 6 pays de la CEMAC (Congo, Cameroun, Centrafrique, Tchad, Gabon, Guinée équatoriale),
les normalise et signale les hausses anormales par marché et par produit.

Projet personnel. Données publiques : PAM (WFP) et FAO via HDX, Open-Meteo, Banque mondiale.
Licence des données PAM et FAO : Creative Commons Attribution pour les organisations intergouvernementales.

## Profondeur des données par pays

| Pays | Prix mensuels par marché | Indicateurs nationaux |
|---|---|---|
| Congo, Cameroun, Centrafrique, Tchad | Oui | Oui |
| Gabon | Historique (jusqu'en 2017) | Oui |
| Guinée équatoriale | Non | Oui |

Détail : `docs/data_profile.md` (rempli à l'étape 1).

## Architecture

Cloud Scheduler → Cloud Run Job d'ingestion → Cloud Storage (Parquet) → BigQuery
(bronze → silver → gold, avec dbt) → Looker Studio.
Infrastructure en Terraform, déploiement par GitHub Actions avec Workload Identity Federation.

## Étapes

1. Inventaire des données
2. Socle Terraform
3. CI de base
4. Ingestion
5. dbt silver et gold
6. Contrôles et alertes
7. Déploiement continu
8. Tableau de bord et documentation
