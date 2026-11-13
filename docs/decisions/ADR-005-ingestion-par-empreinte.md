# ADR-005 : ingestion d'historiques complets, fichiers adressés par leur empreinte

Statut : accepté (étape 4).

## Contexte

Le PAM ne publie pas un fichier par mois : il republie à chaque mise à jour l'historique complet
de chaque pays, y compris d'éventuelles corrections de mois passés. La Banque mondiale et la BCE
renvoient de même des séries complètes.

## Décision

- Chaque run télécharge l'historique complet de chaque source et calcule son empreinte sha256.
- Un fichier n'est écrit que si son empreinte est nouvelle pour cette source et cette partition.
- Le chemin de l'objet contient l'empreinte : `wfp/country=COG/ingest_date=AAAA-MM-JJ/<sha>.parquet`.
  Réécrire le même fichier produit le même objet ; une relance ne crée jamais de doublon.
- L'empreinte est enregistrée dans `meta.processed_files` **après** l'écriture : une panne entre les deux
  fait retraiter le fichier au run suivant, sans effet de bord.
- bronze = tables externes BigQuery sur ces Parquet (partitions Hive). Aucune copie, aucune mise à jour en place.

## Conséquences

- Les versions successives sont conservées : on peut retrouver ce que le PAM publiait à une date donnée.
- silver doit retenir la dernière version par pays (`max(ingested_at)`).
- Le rattrapage d'historique n'est pas un mécanisme à part : le premier run charge tout l'historique.
- Coût négligeable : quelques Mo par mise à jour.
