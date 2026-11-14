# ADR-007 : référentiels générés par script, puis relus dans un fichier versionné

Statut : accepté (étape 5B).

## Contexte

Trois tables de référence relient les données brutes entre elles :

| Seed | Lignes | Rôle |
|---|---|---|
| `unit_conversion` | 23 unités | ramener les prix au kg ou au litre |
| `commodity_mapping` | 103 produits | nom français, groupe, inclusion dans l'indice |
| `market_district` | 212 marchés | district COD-AB du marché, et code à utiliser pour la pluie CHIRPS |

Les écrire à la main serait long, et l'erreur passerait inaperçue. Les générer sans relecture donnerait
des traductions approximatives et des rattachements faux, sans que personne ne le voie.

## Décision

1. Un script propose chaque seed à partir des données chargées (`make seeds-reference`, `make seeds-markets`).
   Il donne à chaque ligne un statut : `auto` si toutes les règles sont satisfaites, `a_verifier` sinon.
2. La relecture humaine est écrite dans `reference/review/<seed>.csv` : la clé, les colonnes corrigées et la
   justification. `make seeds-review` l'applique, et les lignes concernées passent au statut `relu`.
3. Les coordonnées de marché absentes ou fausses sont corrigées dans `reference/market_coordinates.csv`, avec leur source,
   avant le calcul spatial.

On peut donc régénérer un seed puis rejouer la relecture : chaque décision manuelle reste traçable dans Git.

## Règles retenues à la relecture

- **Le polygone officiel prime sur le nom du PAM.** Les noms de district du PAM ont des fautes d'orthographe ou des
  accents mal encodés (« La Nya Pendm », « Barh-K h »). Quand le point tombe dans un district dont le nom
  ne diffère que par l'orthographe, on garde le polygone.
- **Repli sur la région.** Quand le code de district des contours récents n'existe pas dans CHIRPS (Bangui découpé
  en arrondissements, Borkou divisé), la pluie est prise au niveau de la région.
- **Pas de pluie pour 6 marchés** :
  - Batangafo, Bouca, Carnot et Paoua (Centrafrique) sont dans des préfectures créées en 2020. Ni leur district ni leur
    préfecture n'existent dans CHIRPS, qui suit l'ancien découpage.
  - Libreville : le Gabon n'a pas de pluie CHIRPS (ADR-006).
  - « National Average » (Tchad) est une moyenne du PAM, pas un marché : statut `exclu`, retiré des faits.
- **Produits hors panier.** Le bétail vendu sur pied, les salaires, le taux de change et les produits non
  alimentaires ont `include_in_index = false`. Les unités Head, Day et USD/LCU sont `exclu`.

## Limites connues

- Le repli sur la région suppose que le code de région des contours récents désigne la même région dans CHIRPS.
  C'est vrai quand la région n'a pas été redécoupée. Pour les préfectures centrafricaines redécoupées en 2020,
  ce n'est pas garanti.
- Une solution complète consisterait à calculer la pluie directement depuis la grille CHIRPS sur les contours
  récents. C'est hors du périmètre actuel.
