# ADR-013 : un pic isolé d'un mois part en quarantaine

Statut : accepté. Complète l'ADR-012 (quarantaine) et l'ADR-009 (alertes).

## Contexte

Le prix du sel en Centrafrique passe d'environ 425 FCFA/kg en novembre 2025 à 1 360 en décembre, puis
revient à 415 en janvier 2026. Un triplement suivi d'un retour exact au niveau d'avant, en un seul mois,
ressemble à une erreur de saisie de la source (unité ou virgule) plutôt qu'à un vrai choc de prix.

Aucun contrôle existant ne l'arrêtait :

- `is_suspect` (prix hors d'un facteur 10 de la médiane du pays) laisse passer un facteur 3 ;
- la règle d'alerte (ADR-009) le signale au contraire comme une **alerte forte**, ce qui fausse le tableau
  de bord.

## Décision

Nouveau motif de quarantaine `pic_isole_suspect` dans `int_wfp__prices_checked`, testé après tous les autres.

- **Série** : pays, marché, produit, type de prix, unité de base. Prix mensuel calculé comme dans
  `fct_price_monthly` (moyenne des prix au kg ou au litre, arrondie à 4 décimales).
- **Pic isolé** : le mois testé a un voisin **immédiat** avant et après (pas de mois manquant), et
  - il vaut au moins `spike_factor` (2,5) fois chacun des deux voisins, ou au plus 1 / 2,5 fois chacun (chute) ;
  - les deux voisins sont proches : le plus grand vaut au plus `spike_neighbours_max_ratio` (1,5) fois le plus petit.
- **Lignes concernées** : toutes les lignes valides de la série pour ce mois, hors prévisions et unités sans poids.
- **Paramètres** : `spike_factor` et `spike_neighbours_max_ratio` dans `dbt_project.yml`, recopiés dans
  `quality/reconcile.py`, qui applique la même règle une seconde fois.

## Conséquences

- Le dernier mois d'une série n'a pas de voisin suivant : il ne peut pas être signalé tout de suite. Il reste
  dans les faits, et peut partir en quarantaine au run suivant, une fois le mois d'après publié. Les faits
  étant reconstruits à chaque run (ADR-012), ce retrait se fait sans intervention.
- Un vrai choc d'un seul mois de cette ampleur (pénurie brève) serait mis de côté à tort. Il n'est pas perdu :
  il reste visible dans `quarantine.qrt_wfp__prices`, avec son motif, et le test `is_empty` le signale à
  chaque run. Si la source confirme le prix, on relève le seuil ou on ajoute une exception.
- Une hausse qui dure (deux mois ou plus au nouveau niveau) n'est jamais concernée : c'est le cas que les
  alertes doivent montrer.

## Cas examinés lors de la mise en place (dev, 21 novembre 2026)

515 lignes de prix en quarantaine sur environ 243 500 (0,2 %) : Cameroun 352, Centrafrique 97, Tchad 64, Congo 2.

| Cas | Ce que montrent les données | Décision de la règle |
|---|---|---|
| Sel, Centrafrique, décembre 2025 | Environ 1 200 FCFA/kg sur tous les marchés (3 500 à Birao), contre environ 400 avant et après | En quarantaine : erreur de la source |
| Riz importé en sac de 50 kg, Cameroun, avril 2024 | 860 à 5 775 FCFA le sac sur 9 marchés, contre 24 000 à 31 000 en mars et en mai. Même mois, même schéma sur le manioc (160 kg) et l'huile de palme (20 L) | En quarantaine : erreur de saisie groupée sur une campagne de relevés |
| Riz en sac de 50 kg, Buea, avril 2024 | 16 500 FCFA, contre environ 27 500 : facteur 1,7 seulement | Gardé : sous le seuil de 2,5. Une chute ne déclenche pas d'alerte |
| Poisson sec et sel, Tchad, avril 2026 | Prix médian national du poisson sec : 2 208 en mars, 4 257 en avril, 4 682 en mai, 2 483 en juin. Sel : 781, 1 067, 636. 52 à 60 marchés, sans trou de données | Gardé : la hausse dure deux mois (poisson) ou monte par paliers (sel). Ce n'est pas un aller-retour d'un mois. Les 81 alertes d'avril sont conservées, la cause reste à confirmer dans une source extérieure |
