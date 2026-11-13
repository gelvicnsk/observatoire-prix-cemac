# ADR-004 : accès de GitHub Actions à Google Cloud sans clé, en deux pools

Statut : accepté (étape 2).

## Contexte

La CI doit lancer `terraform plan` sur chaque pull request et `terraform apply` après fusion sur `main`.
Une clé JSON de compte de service stockée dans GitHub serait permanente, copiable et difficile à révoquer.

## Décision

Workload Identity Federation : GitHub Actions présente un jeton OIDC de courte durée, échangé contre
l'identité d'un compte de service. Deux pools séparés :

| Pool | Condition sur le jeton | Compte de service | Droits |
|---|---|---|---|
| `github-plan` | dépôt `gelvicnsk/observatoire-prix-cemac` | `tf-plan` | lecture seule + verrou de l'état |
| `github-apply` | même dépôt **et** branche `refs/heads/main` | `tf-apply` | modification de l'infrastructure |

Deux pools plutôt qu'un : avec un seul pool, un jeton d'une branche de pull request porterait le même
attribut `repository` et pourrait se faire passer pour `tf-apply`. La séparation rend cela impossible.

## Conséquences

- Aucun secret à stocker dans GitHub : seulement les noms des fournisseurs et des comptes (non sensibles).
- Une pull request ne peut jamais modifier l'infrastructure, même si son code le tente.
- Le bootstrap qui crée ces pools est lancé une seule fois, en local, par le propriétaire des projets.
