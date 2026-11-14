# Tableau de bord Looker Studio

Le tableau de bord lit trois tables de `gold`, en **prod** (`obs-cemac-prod-11259`), en lecture seule.
Chaque table est déjà jointe et nommée en français : aucune fusion de sources n'est nécessaire dans
Looker Studio. Les fusions y sont lentes et se cassent facilement.

| Source Looker Studio | Table BigQuery | Sert à |
|---|---|---|
| Prix | `gold.mart_price_dashboard` | courbes de prix, carte et liste des alertes |
| Pluie et prix | `gold.mart_rain_vs_price` | pluie du district comparée à l'indice de prix du marché |
| Fraîcheur | `gold.mart_data_freshness` | dernier relevé par pays, pays en retard |

## 1. Créer les sources

Dans Looker Studio : **Créer → Source de données → BigQuery → Mes projets → `obs-cemac-prod-11259` → `gold`**,
puis choisir la table. On répète pour les trois tables. Pour chaque source :

- **Identifiants** : « Identifiants du propriétaire ». Les lecteurs du rapport n'ont pas besoin d'accès à
  BigQuery, et les requêtes sont facturées au projet prod, dans l'offre gratuite vu les volumes.
- **Fraîcheur des données** : 12 heures. Les données ne changent qu'une fois par mois.
- **Champ `market_location`** : type **Géo → Latitude, longitude**. C'est lui qui place les marchés sur la carte.
- **Champ `price_month` / `month`** : type **Date → Année et mois**.

## 2. Pages

### Vue d'ensemble
- Fiches de score (Prix) : nombre d'alertes du dernier mois (filtre `alert_level` non nul) ; nombre de marchés
  (`COUNT_DISTINCT(market_key)`).
- Carte à bulles (Prix, filtre `alert_level` non nul) : lieu = `market_location`, taille = nombre de lignes,
  couleur = `alert_level`.
- Tableau (Fraîcheur) : pays, `data_status`, `last_price_month`, `months_since_last_price`, avec mise en
  forme conditionnelle sur `is_stale`.

### Alertes
- Tableau (Prix, filtre `alert_level` non nul) : mois, pays, marché, produit, type de prix, prix XAF par unité,
  `change_1m_pct`, `z_score`, `alert_level`, trié par mois décroissant.
- Contrôles : pays, groupe de produits, période.

### Prix
- Série temporelle (Prix) : `price_xaf_per_unit` par `price_month`, une ligne par `commodity_name_fr`.
- Contrôles : marché, produit, type de prix (Retail par défaut). Le détail et le gros ne doivent jamais apparaître
  sur la même courbe (README, section 7).

### Pluie et prix
- Graphique combiné (Pluie et prix), pour un marché : barres = `rainfall_3m_pct_of_normal`,
  ligne = `price_index_median`, par mois. 100 sur les deux axes = la normale.
- Contrôle : marché. Les marchés sans pluie rattachée (4 en Centrafrique, Libreville) affichent seulement
  l'indice de prix (ADR-007).

## 3. Partage

**Partager → Gérer l'accès → Toute personne disposant du lien : lecteur.** Le rapport n'expose que des
agrégats calculés à partir de données publiques.

Le compte `sa-dashboard` (lecture de `gold`) est prêt pour une connexion par compte de service. Pour l'utiliser
à la place des identifiants du propriétaire, il faut autoriser l'agent de service de Looker Studio à agir pour ce compte
(rôle `roles/iam.serviceAccountTokenCreator`). Ce n'est pas fait dans cette version.
