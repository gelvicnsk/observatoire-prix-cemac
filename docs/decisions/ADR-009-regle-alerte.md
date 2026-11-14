# ADR-009 : alerte de prix = écart anormal à l'historique ET forte hausse sur 1 mois

Statut : accepté (étape 6). Remplace la règle « l'un ou l'autre » du cahier des charges initial.

## Contexte

Le cahier des charges prévoyait une alerte quand la hausse sur 1 mois dépasse un seuil, **ou** quand le z-score
par rapport aux 24 mois précédents dépasse 2. Les seuils devaient être fixés après observation des données.
Objectif : un nombre d'alertes lisible, de l'ordre de 5 à 20 par mois dans les grands pays.

Distribution observée (séries avec au moins 12 mois de référence, relevés suspects exclus) :

| Pays | Hausse sur 1 mois, 95e centile | 99e centile | z-score, 99e centile |
|---|---|---|---|
| Centrafrique | 27 % | 75 % | 3,8 |
| Cameroun | 29 % | 107 % | 4,5 |
| Congo | 23 % | 54 % | 3,9 |
| Tchad | 26 % | 59 % | 3,9 |

Les prix du PAM varient beaucoup d'un mois à l'autre : 5 % des séries montent de plus d'un quart en un mois.

## Calibration (36 derniers mois, alertes par mois)

| Règle, seuils | Tchad | Cameroun | Centrafrique | Congo |
|---|---|---|---|---|
| z ≥ 3 **ou** hausse ≥ 40 % (la plus stricte testée) | 63,6 | 27,9 | 8,0 | 0,7 |
| z ≥ 2 **ou** hausse ≥ 15 % | 175,8 | 80,9 | 35,0 | 2,3 |
| z ≥ 2,5 **et** hausse ≥ 25 % | 19,5 | 6,5 | 2,8 | 0,4 |
| z ≥ 3 **et** hausse ≥ 40 % | 13,3 | 3,4 | 1,7 | 0,2 |

Avec « ou », la seule condition de hausse déclenche des alertes en masse sur des produits habituellement
volatils, quel que soit le seuil.

## Décision

- Une alerte exige **les deux** conditions : un écart anormal à l'historique du même marché **et** une forte hausse.
- Deux niveaux :
  - **modérée** : z-score ≥ 2,5 et hausse ≥ 25 % ;
  - **forte** : z-score ≥ 3 et hausse ≥ 40 %.
- Un historique parfaitement stable (écart type nul) compte comme anormal dès que le prix le dépasse.
- Les seuils sont des variables de `dbt_project.yml` : ils se changent sans toucher au SQL.

## Conséquences

- Le Tchad, avec environ 900 séries par mois, reste en haut de la fourchette (19,5 alertes par mois).
- Une hausse progressive, sur plusieurs mois, peut ne déclencher aucune alerte « sur 1 mois ». La variation
  sur 12 mois est calculée et affichée, mais elle ne déclenche pas d'alerte dans cette version.
- À recalibrer si le volume de séries change fortement (nouveau pays, nouvelle source).
