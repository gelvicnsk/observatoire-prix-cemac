# ADR-006 : pluviométrie CHIRPS du PAM plutôt qu'Open-Meteo

Statut : accepté (étape 4).

## Contexte

Il faut la pluie autour de chaque marché, sur toute la période des prix (depuis 2003), pour comparer
les hausses de prix aux déficits de pluie. Deux options :

| | Open-Meteo (archive) | CHIRPS agrégé par le PAM (HDX) |
|---|---|---|
| Lieu | point exact du marché | district (admin2) |
| Historique | 1940 → aujourd'hui | 1981 → aujourd'hui, par décade |
| Normale et anomalie | à calculer | déjà calculées (référence 1989-2018) |
| Pays couverts | tous | 5 sur 6 (pas le Gabon), dont la Guinée équatoriale |
| Coût d'accès | appels pondérés par la durée : ~200 marchés × 23 ans dépassent la limite gratuite de 10 000 appels/jour | 1 fichier par pays, même client que les prix |
| Référence métier | réanalyse météo générale | jeu de référence des systèmes d'alerte de sécurité alimentaire |

## Décision

CHIRPS agrégé par district, ingéré exactement comme les prix (client HDX, empreinte, Parquet, table
externe `bronze.rainfall_adm2`). Les noms de colonnes ayant varié selon les versions (`rfh_avg` ou `rfh_lta`),
l'ingestion accepte chaque variante connue et s'arrête en listant les colonnes trouvées si un champ
indispensable manque.

## Conséquences

- Chaque marché doit être rattaché à son district (code admin2) : c'est un travail de référentiel,
  traité à l'étape 5 (table de correspondance versionnée).
- La pluie est une moyenne de district, pas une mesure au marché : précision suffisante pour un signal
  mensuel, à mentionner dans le tableau de bord.
