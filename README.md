# TeachEazy

**L'espace numérique de travail (ENT) de l'éducation au Congo (Brazzaville) — du collège à l'université.**

TeachEazy relie sur une seule plateforme tous les acteurs de l'éducation :

| Acteur | Ce qu'il fait sur TeachEazy |
|---|---|
| **Enseignant** | Organise son travail par établissement et par classe ; publie cours, TD, devoirs, corrigés et vidéos ; fait l'appel ; note, corrige en ligne, suit ses élèves ; planifie ; analyse ses statistiques. |
| **Élève / étudiant** | Se connecte avec son **identifiant unique** ; voit automatiquement son profil, ses profs et son emploi du temps ; accède à ses cours, devoirs, notes ; rend ses devoirs ; révise et apprend. |
| **Parent** | Suit ses enfants (notes, absences, devoirs, bulletins) et reçoit des alertes SMS. |
| **Établissement** | Suit les enseignants, les élèves, les cours et le programme ; édite bulletins et attestations ; décide des passages. |
| **Inspection** | Supervise les établissements de sa zone ; contrôle la régularité des passages ; traite les alertes. |
| **Ministère** | Vue sur tout le système éducatif ; publie programmes, calendrier, coefficients et règles. |
| **Admin plateforme** | Fait fonctionner la plateforme : technique, comptes, référentiels, modération, sécurité. |

**Publics** : collège, lycée (général, technique et professionnel), université, écoles supérieures et écoles de formation. **Pas de primaire.**
Dans ce document, « élève » désigne aussi l'**étudiant** et l'apprenant ; « classe » désigne aussi le **groupe / niveau / parcours** du supérieur ; l'interface emploie le bon mot selon le cycle.

### État du projet
| Version | Contenu | État |
|---|---|---|
| **v1.0** | Enseignants, élèves, notes, cours, apprentissage, admin + socle établissement, contrôle des passages, inspection, ministère | **Construite et testée** |
| **v1.1** | Identifiant à cycles, inscription enseignant, parents, appel, emploi du temps, outils et statistiques enseignant, IA enseignant, correction en ligne, banque de sujets, outils élève (simulateur, corrigés, exercices, tuteur IA, orientation…), révisions, attestations | **À réaliser maintenant** (§18) |
| **v2 / v3** | Établissement complet et commercial, paiement, inspection et ministère étendus, interconnexions | **Projection** (§16) |

---

## Sommaire
1. [Règles de travail pour Claude](#1-règles-de-travail-pour-claude)
2. [Réalité du terrain](#2-réalité-du-terrain)
3. [Stack et architecture](#3-stack-et-architecture)
4. [Rôles et hiérarchie](#4-rôles-et-hiérarchie)
5. [Modèle de données](#5-modèle-de-données)
6. [Identifiant de l'élève](#6-identifiant-de-lélève)
7. [Espace Enseignant](#7-espace-enseignant)
8. [Notes, coefficients et moyennes](#8-notes-coefficients-et-moyennes)
9. [Espace Élève](#9-espace-élève)
10. [Espace Parents](#10-espace-parents)
11. [Établissement (socle v1.0)](#11-établissement-socle-v10)
12. [Passages, redoublements et contrôle](#12-passages-redoublements-et-contrôle)
13. [Inspection et Ministère (socle v1.0)](#13-inspection-et-ministère-socle-v10)
14. [Administration de la plateforme](#14-administration-de-la-plateforme)
15. [Notifications, sécurité et protection des données](#15-notifications-sécurité-et-protection-des-données)
16. [Projection : établissement, inspection, ministère](#16-projection--établissement-inspection-ministère)
17. [Tests obligatoires](#17-tests-obligatoires)
18. [Feuille de route](#18-feuille-de-route)
19. [Modèle économique](#19-modèle-économique)
20. [Lancer le projet](#20-lancer-le-projet)

---

## 1. Règles de travail pour Claude

Ce README est la **référence unique** du projet. La v1.0 existe déjà : **ne repars pas de zéro**, réutilise les modèles, services, composants et conventions en place, et ne casse rien de ce qui fonctionne.

### Phase 0 — Analyse ciblée (lecture seule)
Compare ce README au code et écris `ANALYSE_V1_1.md` : ce qui existe, ce qui est à adapter, ce qui manque, les écarts, les risques de régression (notes, bulletins, contrôle des passages, inspection, ministère), et tous les endroits impactés par le nouveau format d'identifiant. **Ne t'arrête pas** : enchaîne.

### Phase 1 — Plan
Écris `PLAN_V1_1.md` à partir des incréments v1.1 (§18). Pour chaque point ambigu, décide et note-le à la suite de `DECISIONS.md` (décision, raison, alternative écartée).

### Phase 2 — Réalisation testée en continu
Pour chaque incrément :
1. écris d'abord les **tests** des règles métier, puis le code ;
2. implémente : migrations, API, écrans de **chaque rôle concerné**, données de démo réalistes (établissements, classes, noms et matières congolais, parents) ;
3. lance **toute** la suite (core, unitaires, intégration, Playwright mobile et bureau) ; corrige jusqu'à ce que tout passe ; jamais d'incrément suivant avec un test rouge ;
4. démarre l'application et vérifie les parcours réels dans le navigateur, sur mobile et sur ordinateur ;
5. vérifie la non-régression de la v1.0 ;
6. commit par incrément et mise à jour de `AVANCEMENT.md`.

Une fonctionnalité n'est terminée que si elle est **testée, fonctionne dans l'application lancée, et est visible et pilotable par les rôles qui la supervisent**.

**Tu ne t'arrêtes pour me demander que pour** : données de production, vraies clés (SMS, email, stockage, IA), envoi réel de SMS, nom de domaine, déploiement. En développement, tout est simulé (`AI_PROVIDER=mock`, SMS journalisés, OTP fixe). Pour tout le reste, décide, documente et continue.

**Projection (§16)** : ne développe **pas** ces fonctionnalités maintenant, mais vérifie que le modèle de données permet de les ajouter sans réécriture, et documente-le dans `ARCHITECTURE.md`.

**Fin de la v1.1** : relance toute la suite et les parcours e2e du §17, mets à jour ce README (§20 notamment), livre `RAPPORT_V1_1.md` (livré, résultats des tests, décisions, limites, reste à faire avant production).

---

## 2. Réalité du terrain

- **Téléphones Android d'entrée de gamme, connexion lente et chère** : PWA installable, pages légères, **mode économie de données**, consultation hors ligne, taille affichée avant chaque téléchargement, upload reprenable, compression des fichiers, saisies (appel, notes) possibles **hors ligne** puis synchronisées.
- Beaucoup d'élèves utilisent **le téléphone d'un parent** : connexion rapide, déconnexion visible, session courte, écran de confirmation d'identité.
- **Système éducatif** :
  - **Collège** (6e à 3e) et **lycée** (2nde, 1ère, Terminale ; séries A, C, D… ; lycées techniques) : notes sur 20, **3 trimestres**, **D1, D2, D3** + **composition**, coefficients, passage en fin d'année, **BEPC** en 3e, **BAC** en Terminale.
  - **Université** (LMD) et **écoles supérieures / de formation** : **semestres**, UE et matières, contrôle continu + examen, rattrapage, **crédits**.
  - Niveaux, séries, filières, matières, coefficients, programmes, lettres de cycle : **configurables**, jamais figés en dur.
- Un enseignant enseigne souvent **dans plusieurs établissements**, parfois dans plusieurs villes.
- **Organisation administrative** : autorités de tutelle par ordre d'enseignement et services déconcentrés par département, **configurables** (aucun nom de ministère ni découpage codé en dur).
- **Protection des données** : loi congolaise n° 29-2019 ; données de **mineurs** ; accès limité au besoin ; journal d'accès ; rectification et suppression.
- Langue **français** ; dates JJ/MM/AAAA ; fuseau Africa/Brazzaville.

---

## 3. Stack et architecture

- Stack existante conservée (voir `ARCHITECTURE.md`) : front React PWA mobile-first (une application, des espaces par rôle), API Node.js/TypeScript, **PostgreSQL**, **Redis**, stockage S3 (local en dev), docker-compose.
- Authentification : enseignants, parents, personnel, inspecteurs, agents ministériels et admin par **email ou téléphone** + OTP ; élèves par **identifiant** (§6) + PIN optionnel.
- **Temps réel** (SSE + Redis) pour tableaux de bord, notifications et quiz en direct ; reconnexion et resynchronisation.
- **File de synchronisation hors ligne** côté front (appel, notes, brouillons) avec résolution des conflits côté serveur.
- Tâches de fond : imports, exports, bulletins, PDF, statistiques, génération IA.
- **Statistiques** sur agrégats préparés (vues matérialisées) pour rester rapides à l'échelle nationale.
- **Service IA** unique (enseignant, tuteur élève, appréciations, exercices) avec quotas, journal et fournisseur simulé en dev.
- Node 22 recommandé avant la mise en production (exigence à venir du SDK de stockage).

---

## 4. Rôles et hiérarchie

```
Ministère (une autorité par ordre d'enseignement)
   └── Inspection / direction départementale (une zone)
          └── Établissement (collège, lycée, université, école de formation)
                 ├── Personnel (chef d'établissement, censeur / directeur des études,
                 │    surveillant général, secrétariat / scolarité)
                 ├── Enseignants
                 └── Classes → Élèves ← Parents
Admin plateforme : fonctionnement technique, transversal, sans autorité pédagogique
```

| Rôle | Voit | Peut faire |
|---|---|---|
| Élève | Ses cours, devoirs, notes, emploi du temps, bulletins, parcours | Consulter, télécharger, rendre, réviser, poser des questions sur un cours |
| Parent | Les données de **ses** enfants rattachés (lecture seule) | Consulter, recevoir des alertes |
| Enseignant | Ses classes, ses élèves (dans sa matière), ses statistiques, ses documents | Publier, noter, corriger, faire l'appel, planifier, exporter |
| Personnel d'établissement | Tout son établissement | Valider enseignants et listes, emplois du temps, bulletins, attestations, passages, absences |
| Inspecteur | Établissements de **sa zone** | Superviser, alertes, dérogations, inspections |
| Agent du ministère | **Tout le système** de son ordre d'enseignement | Référentiels officiels, statistiques nationales, communications |
| Admin plateforme | Fonctionnement de la plateforme | Comptes, référentiels techniques, modération, sécurité, sauvegardes |

- Chaque rôle est **cloisonné** (classe, établissement, zone, ordre d'enseignement).
- Comptes établissement, inspection et ministère **créés et validés par l'admin** sur justificatif.
- L'admin plateforme **ne prend aucune décision pédagogique**.
- **Aucune messagerie privée** adulte ↔ élève : les échanges passent par des espaces visibles par la classe (annonces, questions sur un cours), tracés et modérés.

---

## 5. Modèle de données

### 5.1 Référentiels
- **Authority**, **Jurisdiction** (zones d'inspection).
- **School** : nom officiel, **code établissement** (2 à 5 lettres, unique national), statut, type, régime de notation, zone, ville, quartier, abonné oui/non, statut.
- **Cycle** : lettre et libellé (`C` collège, `L` lycée général, `T` lycée technique/professionnel, `U` université, `S` école supérieure/institut, `F` formation professionnelle), niveaux rattachés.
- **SchoolYear** (trimestres ou semestres), **Level / Series / Track / Subject**, **City**.
- **ValueProposal** : valeur nouvelle saisie par un utilisateur (ville, matière) en attente de validation/fusion par l'admin.
- **Coefficient** (secondaire) et **maquettes** de parcours (supérieur).
- **Curriculum** (programme officiel : chapitres, objectifs, volumes horaires), **OfficialDocument** (guides pédagogiques, répartitions officielles).
- **PromotionRule** (règles de passage).

### 5.2 Personnes et organisation
- **User**, **Teacher**, **SchoolStaff**, **Parent**.
- **Student** : clé technique interne permanente, nom, prénom(s), sexe, date et lieu de naissance, **noyau d'identifiant** (unique national), statut.
- **StudentIdentifier** : historique des identifiants complets (cycle, code établissement, noyau, contrôle, dates de validité, actif / période de transition / désactivé).
- **ParentLink** : parent ↔ élève (lien, date, ajouté par, actif) ; **ParentCode** par élève.
- **ClassGroup**, **TeachingAssignment**, **Enrollment**, **ClassHandover** (passation de classe).

### 5.3 Pédagogie et vie de classe
- **Rubric**, **Content** (COURS, TD, DEVOIR, **CORRIGÉ**), **Lesson** (séance / cahier de textes).
- **TeacherDocument** (espace « Mes documents pédagogiques ») et **DocumentFolder**.
- **SharedSubject** (banque de sujets partagée), **SubjectRating** / **SubjectReport**.
- **Submission** (devoir rendu) et **Annotation** (correction en ligne).
- **Exercise** / **ExerciseAttempt** (exercices auto-corrigés), **LiveQuiz** / **LiveQuizAnswer**.
- **CourseQuestion** / **CourseAnswer** (questions sur un cours).
- **TimetableSlot** (emploi du temps), **AgendaEvent** (devoirs planifiés, réunions, rappels).
- **Attendance** (appel : présent, absent, retard ; justification).
- **Announcement**.
- **StudentObservation** (fiche de suivi).
- **ActivityCounter** (connexions et consultations par élève, par module, par jour — compteurs agrégés).
- **LearningResource**, **OrientationSheet** (filières, métiers).
- **AiRequest** (journal et quotas IA).

### 5.4 Évaluation et parcours
- **Grade**, **ClassSubjectSetting** (coefficient, crédits), **ReportCard** (avec appréciations), **Absence** (vue issue de l'appel), **YearDecision**, **AcademicRecord**, **Derogation**, **Alert**, **Inspection**, **Certificate** (attestations avec code de vérification).
- **ChangeLog**, **AuditLog**, **UnlockRequest**, **Notification**, **Report**, **SyncOperation** (opérations hors ligne).

---

## 6. Identifiant de l'élève

### 6.1 Format : un noyau permanent + un préfixe de cycle et d'établissement
```
[CYCLE]-[CODE ÉTABLISSEMENT]-[NOYAU : 6 caractères][CONTRÔLE]
C-CEGB-7K4P9QX   collège, entré au CEG de Bacongo
L-LSB-7K4P9QM    lycée, entré au Lycée Savorgnan de Brazza
U-UMNG-7K4P9QA   université, entré à l'Université Marien Ngouabi
```

| Partie | Rôle | Change ? |
|---|---|---|
| **Cycle** (1 lettre) | Dit où en est l'élève | À chaque changement de cycle |
| **Code établissement** | Dit d'où vient l'élève : établissement d'entrée dans le cycle actuel | À chaque changement de cycle |
| **Noyau** (6 caractères aléatoires) | Identifie l'élève pour toute sa vie scolaire | **Jamais** (sauf régénération pour perte) |
| **Contrôle** (1 caractère) | Détecte les fautes de frappe | Recalculé |

- Le cycle dépend du **niveau de la classe** (dans un collège-lycée : 4e → `C`, 1ère → `L`).
- Code établissement : 2 à 5 lettres, **unique national**, proposé à partir du nom, validé par l'admin ; conflit → chiffre ajouté (`LSB2`).
- Noyau : générateur cryptographique, alphabet sans caractères ambigus (0, O, 1, I, L exclus), **unique national**, jamais séquentiel.
- Saisie tolérante : majuscules/minuscules, tirets et espaces ignorés.

### 6.2 Règles
- **La clé technique interne de l'élève ne change jamais** ; le noyau est son code d'accès permanent ; toute la logique (doublons, parcours, contrôle des passages, bulletins) s'appuie sur l'élève, pas sur le préfixe.
- **Création** à la première inscription (par un enseignant ou un établissement). Ensuite, **jamais un second élève** pour la même personne : rapprochement dans la classe (nom, prénom, tolérance aux fautes, date de naissance), recherche par identifiant à toute nouvelle inscription, détection nationale des doublons.
- **Changement d'établissement dans le même cycle** : identifiant inchangé ; l'établissement actuel s'affiche dans le profil.
- **Changement de cycle** : **seulement après autorisation du contrôle des passages** (passage décidé, BEPC pour la 2nde, BAC pour l'université), le préfixe devient la nouvelle lettre + le code du nouvel établissement ; noyau identique ; notification à l'élève et aux parents ; nouvelle carte ; l'ancien identifiant reste accepté **60 jours** (paramétrable) avec un message donnant le nouveau, puis refusé avec le même message ; historique conservé.
- **Perte ou vol** : régénération du noyau (préfixe conservé), ancien identifiant désactivé, parcours intact.
- **Sécurité** : seul le noyau protège l'accès → limitation des tentatives, blocage temporaire, **PIN à 4 chiffres** recommandé par défaut pour les établissements.
- **Ce que voit l'enseignant** : l'identifiant et en clair « Lycée — entré au Lycée Savorgnan de Brazza en 2026-2027 ». Les identifiants des cycles précédents sont visibles par l'établissement et l'inspection seulement.
- **Cartes d'accès** imprimables : nom, classe, établissement, identifiant, QR code, **code parent**.

### 6.3 Profil automatique
Dès la saisie de l'identifiant : écran de **confirmation** (« Tu es bien KOUMBA Grâce, 3e A, CEG de Bacongo ? » → Oui / Ce n'est pas moi, sans autre donnée affichée), puis affichage automatique : nom, prénom(s), cycle en clair, établissement d'entrée dans le cycle, **établissement actuel**, **ville**, **classe** et année, **enseignants par matière**, emploi du temps du jour.

---

## 7. Espace Enseignant

### 7.1 Inscription
1. Nom, prénom, **email ou téléphone** (OTP).
2. **Ville** et **matière(s)** **saisies au clavier avec suggestions** ; une valeur inconnue est acceptée tout de suite et devient une **proposition** que l'admin valide, corrige ou fusionne (« Brazaville » → « Brazzaville ») ; après fusion, tous les comptes sont mis à jour ; les statistiques utilisent les valeurs normalisées.
3. **Établissements** où il enseigne (liste officielle avec recherche, ou proposition).
4. Pour chaque établissement : ses **classes/salles** de l'année, puis **enregistrer**.
5. Si l'établissement est sur TeachEazy, il confirme le rattachement.

Accueil : **Ma journée** (cours du jour, échéances), puis établissements → classes → **Élèves, Appel, Notes, Programme, Cours, TD, Devoirs, Copies, Corrigés, Questions, Vidéos, Statistiques**. Onglets transverses : **Mes documents pédagogiques, Banque de sujets, Agenda, Emplois du temps, Statistiques globales**.

### 7.2 Listes d'élèves
- Import Excel/CSV, saisie ou copier-coller ; contrôle et aperçu ; rapprochement « un élève = un identifiant » (§6) ; **ordre alphabétique** partout ; cartes d'accès.
- Établissement sur TeachEazy : la liste officielle arrive automatiquement ; le prof signale un manquant.

### 7.3 Cours, TD, devoirs, vidéos
- **Rubriques** annuelles rattachées aux **chapitres du programme**.
- Cours et TD : **titre, objectif général, objectifs spécifiques**, puis document — obligatoires avant publication. Devoir : + consignes, date limite, formats.
- Brouillon, publier, modifier, remplacer, supprimer, dupliquer vers une autre classe, réutiliser l'année précédente ; archivage en fin d'année.
- **Cahier de textes** : séance, chapitre traité, documents utilisés, devoir donné (alimente « J'étais absent », §9.4).
- **Vidéos d'appui** : lien YouTube ou téléversement compressé ; visibilité « mes classes » ou « tous » (après modération).

### 7.4 Corrigés
- Pour chaque devoir ou composition, le prof publie un **corrigé** (document et/ou texte), **programmé automatiquement après la publication des notes** (ou à la date choisie).
- Les élèves voient le corrigé à côté de leur copie corrigée et de leur note.

### 7.5 Copies rendues et correction en ligne
- Statut par élève (à l'heure, en retard, non rendu), rappel avant la date limite, **ZIP** des copies.
- **Correction en ligne** dans le navigateur, sur téléphone ou ordinateur : surlignage, traits, symboles (✓, ✗), **commentaires** placés sur la page, **commentaire général**, **barème par question** avec total calculé.
- La note est reportée dans la **colonne choisie** (D1, D2, D3, CC…) après confirmation (soumise aux règles du §8, dont la limite de modifications).
- L'élève reçoit sa **copie annotée** en PDF ; le prof peut réutiliser ses **commentaires fréquents** (bibliothèque personnelle).
- Copies photographiées par l'élève : redressement et amélioration de lisibilité automatiques.

### 7.6 Banque de sujets partagée
- Le prof partage un sujet (devoir, composition, TD, QCM) avec **matière, niveau, série, chapitres, durée, barème, corrigé** ; visibilité : moi seul, mon établissement, ou **tous les enseignants** de TeachEazy.
- Recherche et filtres ; **réutilisation** en un clic (copie modifiable dans son espace, l'auteur est crédité) ; **note et avis** des collègues ; nombre de réutilisations.
- Signalement (erreur, contenu protégé) et modération par l'admin ; le partage public exige que le prof certifie être l'auteur ou avoir le droit de partager.
- Les sujets de composition partagés ne deviennent visibles des autres **qu'après la date de l'épreuve** (choix par défaut, pour éviter les fuites).

### 7.7 Mes documents pédagogiques
- Espace **privé** du prof, rangé par année, établissement, niveau/classe et matière : **répartition des enseignements**, **guide pédagogique** et programme officiel (documents du ministère ou de l'admin apparaissant automatiquement), **cours annuels**, **TD**, fiches de préparation, sujets et corrigés.
- Téléversement, téléchargement individuel ou **ZIP**, recherche, renommage, déplacement, duplication vers l'année suivante, bouton **« Publier aux élèves »** (titre et objectifs exigés), **« Partager dans la banque »** ; quota affiché.

### 7.8 Appel en un clic
- Liste du jour issue de l'emploi du temps ; tous **présents par défaut** ; un appui = absent ou retard ; validation en un bouton ; **hors ligne** puis synchronisation.
- Absences visibles par l'établissement (justification), les parents (SMS) et l'élève ; reprises dans le bulletin ; seuil d'alerte.

### 7.9 Emplois du temps
- **Ma semaine** regroupant tous ses établissements (couleurs par établissement), détection des **chevauchements**.
- **PDF par établissement** et **PDF global** ; export agenda (.ics).
- Créneaux issus de l'établissement, ou saisis par le prof si l'établissement n'est pas sur TeachEazy.

### 7.10 Agenda de planification
- Jour / semaine / mois, cours en fond.
- **Devoirs planifiés** (D1, D2, D3, composition, CC, examen, devoir maison) : apparaissent chez les **élèves** et **parents** avec rappel, et créent la **colonne de notes** correspondante.
- **Réunions** (conseil de classe, parents, pédagogique) et **rappels personnels**.
- Échéances de l'établissement affichées automatiquement ; conflits signalés (deux devoirs le même jour pour une classe) ; .ics.

### 7.11 Annonces et questions sur un cours
- **Annonces** du prof à ses classes (texte + pièce jointe), notification aux élèves et, si cochée, aux parents.
- **Questions sur un cours** : sous chaque cours, TD ou devoir, un fil **visible par toute la classe** ; l'élève pose une question, le prof (ou un camarade) répond ; le prof peut **épingler** une réponse, masquer une question inappropriée, fermer le fil ; option de question **anonyme vis-à-vis des camarades** (le prof voit l'auteur). Notifications au prof. Pas de messagerie privée.

### 7.12 Tableau de statistiques
Filtres : tous ses établissements, un établissement, une classe, une matière, une période.
- **Effectifs** (filles/garçons, arrivées, départs).
- **Notes** : moyennes par devoir, période et année ; min/max ; **taux de réussite** ; **répartition par tranches** ; évolution D1 → D3 → composition (ou CC → examen) ; comparaison entre classes ; élèves en difficulté et meilleurs élèves.
- **Absences**, **devoirs rendus**, **avancement du programme**, **résultats des exercices et quiz**, **activité** (§7.13).
- Graphiques lisibles sur téléphone ; **export Excel et PDF** ; mise à jour automatique ; uniquement ses classes et sa matière.

### 7.13 Activité des élèves dans son module
- **Nombre de connexions** à son module par élève (semaine, mois, période), **dernière consultation**, **qui a ouvert ou téléchargé** chaque contenu, élèves **inactifs** depuis X jours.
- Protection : compteurs et dates seulement, **uniquement sa matière**, élèves **informés**, données de l'année en cours puis agrégées, aucun classement public.

### 7.14 Fiche de suivi de l'élève
- Par élève et par matière : **observations datées** (comportement, travail, progrès), **points forts / points à améliorer**, objectifs fixés, évolution des notes et de l'assiduité sur l'année (graphique), résultats aux exercices.
- Observations **privées** par défaut ; le prof peut en partager avec l'établissement (et plus tard avec les parents).
- Sert de base aux **appréciations** du bulletin (§7.16).

### 7.15 Passation de classe
- En cas d'absence longue, de mutation ou de changement d'affectation : le prof (ou l'établissement) **transmet une classe** à un collègue en un clic : liste, notes, cours, rubriques, progression, cahier de textes, devoirs en cours, agenda.
- Le nouveau prof doit accepter ; l'ancien conserve un accès en lecture à ses propres contenus ; tout est tracé ; les élèves voient le nouveau nom dans leur profil.
- Passation temporaire (remplacement) avec date de fin et retour automatique.

### 7.16 Assistant IA de l'enseignant
À partir d'un chapitre du programme ou d'un cours publié :
- **devoir** (énoncé, barème, corrigé), **QCM**, **exercices** auto-corrigés, **fiche de révision**, **progression** ;
- **appréciations de bulletin** proposées pour chaque élève à partir des notes, de l'évolution, de l'assiduité et de la fiche de suivi (« Élève sérieux, en net progrès au troisième devoir… ») ; le prof valide, modifie ou réécrit, élève par élève ou en lot.
Règles : tout est un **brouillon** jamais publié automatiquement ; l'IA **ne note jamais** et n'écrit jamais dans les notes ; appréciations sans jugement sur la personne ni critère discriminant ; quotas réglables ; journal ; mock en dev.

### 7.17 Quiz en direct
- Le prof lance un QCM en classe ; les élèves rejoignent avec un **code court** depuis leur téléphone ; questions minutées ; résultats affichés en direct (histogramme des réponses, sans nom à l'écran) ; bilan par élève pour le prof.
- Fonctionne seulement avec du réseau ; message clair sinon ; peut aussi être lancé en **mode asynchrone** (à faire avant une date).

---

## 8. Notes, coefficients et moyennes

### 8.1 Collège et lycée (trimestriel)

| N° | Nom | Prénom(s) | D1 | D2 | D3 | Moy. devoirs | Composition | Moy. trimestrielle | Coefficient | Moy. coefficientée |
|---|---|---|---|---|---|---|---|---|---|---|

Annuel : T1, T2, T3, **moyenne annuelle**, coefficient, moyenne annuelle coefficientée.
- Moy. devoirs = (D1 + D2 + D3) / 3 (devoirs de classe ou départementaux) ; Moy. trimestrielle = (Moy. devoirs + Composition) / 2 ; Moy. annuelle = (T1 + T2 + T3) / 3 ; sur 20, arrondi à 2 décimales.
- **Coefficient** par classe et matière, prérempli depuis le référentiel officiel, modifiable si autorisé, obligatoire avant export ; Moy. coefficientée = Moyenne × Coefficient.
- ABS gérés (devoirs notés seulement ; composition ABS → moyenne non calculée) ; rang avec ex æquo ; statistiques de classe.
- Formules paramétrables par le ministère puis l'établissement.

### 8.2 Université et écoles (semestriel)

| N° | Nom | Prénom(s) | Matricule | CC1 | CC2 | … | Moy. CC | Examen | Moy. matière | Rattrapage | Moy. finale | Coefficient | Crédits | Décision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

- Moy. matière = 40 % CC + 60 % examen ; UE pondérées ; validation ≥ 10 ; compensation activable ; rattrapage remplace l'examen s'il est meilleur ; moyenne semestrielle pondérée par les crédits ; décisions (Validé, Non validé, Rattrapage, Ajourné, Défaillant) ; procès-verbaux. Tout paramétrable par établissement.

### 8.3 Règles communes
- Saisie rapide, calcul instantané, import Excel, **saisie hors ligne** avec synchronisation (une note modifiée hors ligne sur deux appareils → conflit signalé, la dernière validation explicite l'emporte après confirmation).
- **Publication** aux élèves (et parents) quand le prof le décide.
- **Limite de 3 modifications** par note, par nom d'élève et par coefficient (1ʳᵉ saisie non comptée) ; au-delà, **demande de déblocage** (établissement abonné, sinon admin) ; historique complet.
- **Clôture de période** par l'établissement : notes verrouillées, correction sur demande tracée.
- **Fichiers de notes** Excel/PDF par classe et période, et annuel (en-tête complet, coefficient, ordre alphabétique, statistiques, signature, code de vérification).

---

## 9. Espace Élève

### 9.1 Accueil
Profil automatique (§6.3), **Aujourd'hui** (cours du jour, devoirs à rendre, nouveautés), accès par **matière** (une carte par prof).

### 9.2 Cours, devoirs, notes, emploi du temps
- Cours et TD par rubrique : lecture ou téléchargement, hors ligne.
- Devoirs : consignes, compte à rebours, dépôt PDF/Word/Excel ou photo convertie, remplacement avant la date limite, **copie annotée** et **corrigé** après correction.
- Notes publiées par matière et période ; bulletins (si établissement sur TeachEazy).
- **Emploi du temps général de la classe**, toutes matières, hors ligne et **PDF**.
- **Agenda** : devoirs planifiés, compositions, échéances.

### 9.3 Simulateur de moyenne
- Pour chaque matière et période : « **Quelle note me faut-il à la composition (ou à l'examen) pour atteindre X ?** » ; l'élève choisit l'objectif (10, 12, 14…) ; calcul avec les **règles réelles** de son établissement (coefficients, ABS, régime trimestriel ou semestriel).
- Simulation de la **moyenne générale** (toutes matières, coefficients) quand les données sont disponibles.
- Messages clairs : « objectif impossible » (> 20), « déjà atteint ».
- Simulation **personnelle** : jamais enregistrée comme note ni visible des profs.

### 9.4 J'étais absent
- Pour chaque séance manquée (issue de l'appel) : chapitre traité, documents utilisés, devoir donné, annonces de la séance, à partir du **cahier de textes** ; liste « **à rattraper** » cochable par l'élève.
- Si le prof n'a pas rempli le cahier de textes : message clair et lien vers les derniers contenus publiés.

### 9.5 Exercices auto-corrigés
- Par chapitre : QCM, vrai/faux, réponses numériques, textes à trous ; **correction immédiate** avec explication ; plusieurs tentatives ; progression par chapitre (« maîtrisé / à revoir »).
- Créés par les profs, l'admin, le ministère, ou générés par l'IA puis **validés par un adulte**.
- Disponibles hors ligne une fois téléchargés (résultats synchronisés ensuite).

### 9.6 Tuteur IA
- Accessible depuis un cours ou un chapitre : **réexplique** avec d'autres mots, donne des **exemples**, propose des **exercices** et vérifie les réponses de l'élève.
- **Limité au programme** du niveau et de la série ; refuse poliment les sujets hors scolaires.
- **Ne fait pas les devoirs** : face à un énoncé de devoir publié, il guide étape par étape (questions, indices, méthode) sans donner la réponse finale ; les devoirs en cours sont reconnus pour appliquer cette règle.
- Mention claire que c'est une IA qui peut se tromper ; invitation à vérifier avec le prof.
- Protection des mineurs : pas de collecte de données personnelles dans la conversation, filtrage des contenus inadaptés, historique visible par l'élève, quotas journaliers, journal (sans lecture des conversations par les profs).

### 9.7 Questions sur un cours
Voir §7.11 : l'élève pose sa question sous le cours, voit les réponses, peut voter « utile » ; option anonyme vis-à-vis des camarades.

### 9.8 Mode économie de données
- « **Télécharger ma semaine** » : tous les cours, TD, devoirs et vidéos d'appui légères de la semaine en un seul lot, de préférence en Wi-Fi ; taille totale affichée avant.
- Réglages : images compressées, vidéos désactivées par défaut sur données mobiles, téléchargement automatique sur Wi-Fi uniquement ; compteur de données consommées par TeachEazy.
- Tout ce qui est téléchargé reste lisible hors ligne.

### 9.9 Apprentissage et révisions
- **Vidéos** (profs, catalogue YouTube sélectionné par chapitre), favoris, « continuer à regarder », propositions de liens modérées.
- **Bibliothèque** : manuels, annales, fiches, livres ; polycopiés et ouvrages pour le supérieur ; ressources libres ou autorisées uniquement.
- **Révisions BEPC / BAC** (3e et Terminale) : annales par matière, année et chapitre ; quiz par chapitre ; points faibles ; **compte à rebours** et **planning de révision**.

### 9.10 Orientation
- Pour les élèves de **3e** (choix de série / lycée technique) et de **Terminale** (filières du supérieur) :
  - fiches **filières** (séries, établissements, débouchés) et **métiers** (description, études nécessaires, matières importantes) ;
  - **questionnaire d'intérêts** simple (sans profilage psychologique) qui suggère des pistes à explorer, jamais une décision ;
  - lien vers les **concours et bourses** d'**OppCongo** (interconnexion prévue, §16.4 ; en attendant, lien externe).
- Contenus gérés par l'admin et, à terme, par le ministère.

### 9.11 Mon parcours et documents
- Parcours année par année (établissement, classe, moyenne, décision), **historique de ses identifiants**.
- Attestations mises à disposition par l'établissement (certificat de scolarité, relevés, attestation de réussite) avec QR.

---

## 10. Espace Parents

- Compte par **téléphone** (OTP) ou email ; lien (père, mère, tuteur).
- **Rattachement** : identifiant de l'élève **+ code parent** (6 caractères, imprimé sur la carte, régénérable) ; plusieurs enfants par parent ; **2 parents** par élève par défaut (paramétrable) ; l'établissement ou le prof voit et peut retirer un parent.
- Vue en **lecture seule** : profil, profs par matière, emploi du temps, notes publiées, moyennes, bulletins, absences, devoirs (à rendre, rendus, non rendus), corrigés, annonces, agenda.
- **SMS** au choix : nouvelle note, absence, bulletin, devoir non rendu, annonce importante (SMS courts, sans données superflues).
- **Consultation par SMS** depuis le numéro rattaché uniquement (simulée en dev ; USSD en projection).

---

## 11. Établissement (socle v1.0)

Déjà construit en v1.0 et conservé ; la v1.1 y ajoute ce qui est nécessaire aux nouveautés :
- **Tableau de bord** : élèves, enseignants (activité, classes sans prof), cours, **avancement du programme**, état de saisie des notes, **absences** (temps réel, justification, cumuls), calendrier.
- **Gestion** : classes, inscriptions officielles avec identifiant existant, transferts, validation des enseignants, saisie par le secrétariat, demandes de déblocage, coefficients autorisés, **emploi du temps des classes** (créneaux, salles, conflits), **annonces** (classe, niveau, établissement), **passations de classe**, **retrait de parents**.
- **Bulletins** : moyenne générale coefficientée, rang, **appréciations** (proposées par les profs, avec IA), absences, décision ; QR ; diffusion aux élèves et parents.
- **Attestations en un clic** : certificat de scolarité, relevé de notes, attestation de réussite, avec QR et page publique de vérification (authentique / non authentique, sans données sensibles).
- **Fin d'année** : conseil de classe, décisions, parcours, réinscriptions.

---

## 12. Passages, redoublements et contrôle

- Chaque année se termine par une **décision** par élève (passage, redoublement, exclusion, orientation ; admis/ajourné/crédits dans le supérieur) qui fixe le **niveau autorisé**.
- Fin de 3e → 2nde seulement avec **BEPC** et passage ; Terminale → supérieur seulement avec **BAC**.
- **Contrôle à chaque inscription**, partout dans le pays : niveau demandé comparé au niveau autorisé.
  - conforme → accepté (et, si changement de cycle, **mise à jour du préfixe d'identifiant**, §6.2) ;
  - non conforme → **bloqué** avec message explicite ; possibilité de **dérogation** motivée ;
  - **tentative répétée** → **élève bloqué** et **alerte à l'inspection** avec dossier complet.
- Inspection : accorde, refuse ou convoque ; tout est tracé et visible du ministère.
- Anti-contournement : pas de second élève (doublons détectés), modifications d'identité validées, parcours clôturé en lecture seule, préfixe modifié **uniquement** par un passage autorisé.

---

## 13. Inspection et Ministère (socle v1.0)

Déjà construits en v1.0 et conservés.
- **Inspection** (sa zone) : tableau de bord (effectifs, enseignants, programmes, notes, passages, redoublements, abandons, absences), alertes et dérogations, contrôles automatiques (anomalies de notes, retards de programme), inspections et comptes rendus, fiches établissement, exports ; accès individuel seulement justifié et journalisé.
- **Ministère** (son ordre d'enseignement) : tableau de bord national, pilotage des inspections, **publication des référentiels officiels** (programmes, guides pédagogiques et répartitions — qui apparaissent dans « Mes documents pédagogiques » des profs —, calendrier, coefficients, règles de calcul et de passage, zones, lettres de cycle), ressources officielles, contenus d'orientation et de révision, communications ciblées, annuaire statistique.

---

## 14. Administration de la plateforme

- Tableau de bord technique et d'usage ; page Exploitation (santé, métriques, sauvegardes).
- **Comptes** : validation des comptes établissement, inspection, ministère ; enseignants ; parents (fusion, retrait) ; régénération d'identifiants et de codes parents ; fusion de doublons.
- **Référentiels** : villes et matières (**propositions à valider ou fusionner**), établissements et **codes établissement**, cycles, niveaux, séries ; référentiels pédagogiques provisoires tant qu'aucune autorité n'est active.
- **Modération** : vidéos, liens, bibliothèque, **banque de sujets**, **questions sur les cours** signalées, exercices partagés.
- **IA** : quotas par rôle (enseignant, élève), journal d'usage, coûts, désactivation d'urgence.
- **SMS** : volumes, échecs, coûts.
- Sécurité, audit, sauvegardes quotidiennes testées, surveillance, annonces de maintenance ; rôles admin (super-admin, modérateur, support) ; **aucun pouvoir pédagogique**.

---

## 15. Notifications, sécurité et protection des données

### Notifications
- In-app pour tous ; SMS/email pour les adultes ; élèves : nouveaux cours, devoirs, rappels, notes, corrigés, copie annotée, réponse à sa question, changement d'identifiant ; parents : §10 ; profs : questions des élèves, copies rendues, échéances, passation reçue, déblocages ; établissement, inspection, ministère : comme en v1.0.

### Sécurité et données
- Contrôle d'accès à **chaque requête** selon le rôle et le périmètre ; parent limité à ses enfants ; prof limité à ses classes et sa matière.
- Fichiers privés, liens signés temporaires, antivirus, vérification du type réel.
- Limitation des tentatives (élèves, parents, adultes) ; OTP limité à **60 par IP** en production.
- **Journal d'audit** non modifiable : connexions, notes, noms, coefficients, clôtures, décisions, blocages, dérogations, changements d'identifiant, rattachements de parents, passations, exports, accès individuels de l'inspection et du ministère.
- **Mineurs** : pas de messagerie privée ; questions sur les cours visibles et modérées ; activité limitée à des compteurs ; tuteur IA filtré ; statistiques agrégées avec seuil minimal d'effectif ; conservation, rectification et suppression conformes à la loi n° 29-2019.

---

## 16. Projection : établissement, inspection, ministère

**À ne pas développer en v1.1.** Le modèle de données doit permettre ces ajouts sans réécriture ; Claude documente dans `ARCHITECTURE.md` comment chacun se branchera.

### 16.1 Établissement — v2 (offre commerciale)
- **Paiement des frais de scolarité** par MTN Mobile Money et Airtel Money : échéancier, reçus automatiques, suivi des impayés, relances SMS aux parents, tableau de bord financier, export comptable.
- **Abonnement** de l'établissement (par établissement ou par élève et par an), facturation, activation automatique.
- **Vie scolaire** : sanctions et retenues, convocations des parents, carnet de correspondance numérique, infirmerie (registre sans données de santé détaillées).
- **Gestion du personnel** : enseignants vacataires et permanents, heures effectuées (issues du cahier de textes et de l'appel), remplacements, absences des enseignants.
- **Emplois du temps assistés** : génération proposée à partir des contraintes (profs, salles, volumes horaires).
- **Inscriptions en ligne** des nouveaux élèves par les parents (dossier, pièces, paiement), avec contrôle des passages.
- **Communication école ↔ parents** : campagnes SMS, réunions, sondages.
- **Tableau de bord du chef d'établissement** : performance par classe et par matière, comparaison d'une année sur l'autre, prévisions d'effectifs.
- **Portail public** de l'établissement (présentation, résultats aux examens, inscriptions).

### 16.2 Inspection — v3
- **Planification des inspections** (calendrier, priorités suggérées à partir des indicateurs), **grilles d'inspection** numériques remplies sur tablette hors ligne, rapports générés.
- **Suivi des enseignants** de la zone : formation continue, inspections passées, recommandations (sans notation publique).
- **Carte de la zone** : établissements, effectifs, taux de réussite, zones en difficulté.
- **Alertes prédictives** : risque de décrochage d'un établissement (absences, retards de programme, chute des moyennes).
- **Organisation des examens** de la zone : centres, candidats, en lien avec OppCongo.
- **Formation continue** des enseignants : contenus, sessions, attestations.

### 16.3 Ministère — v3
- **Tableau de bord national avancé** : indicateurs de l'Éducation pour tous (taux de scolarisation, de passage, d'achèvement, parité filles/garçons, ratio élèves/enseignant), comparaisons régionales et historiques.
- **Gestion des carrières enseignantes** (affectations, mutations) en lien avec la passation de classe.
- **Carte scolaire** : besoins en établissements, en salles, en enseignants par zone.
- **Publication officielle des programmes** avec versionnage et période de transition.
- **Ouverture de données** anonymisées (open data) et API pour les partenaires.
- **Licence nationale** de TeachEazy pour les établissements publics.

### 16.4 Interconnexions
- **OppCongo** : résultats officiels BEPC et BAC rattachés automatiquement au parcours de l'élève (vérification des passages par la source officielle), concours et bourses affichés dans l'orientation.
- **Paiement mobile** (projet de paiement marchand) : frais de scolarité, abonnements, frais d'examens.
- **USSD** : consultation des notes et absences sans internet (via un agrégateur opérateur).

---

## 17. Tests obligatoires

### Calculs (v1.0, à conserver)
- D1 = 12, D2 = 14, D3 = 10, Compo = 9 → Moy. devoirs 12,00 ; trimestrielle 10,50 ; coefficient 4 → 42,00.
- T1 10,50, T2 12,00, T3 13,50 → annuelle 12,00.
- Supérieur : CC 12 et 8, examen 13 → 11,80 ; rattrapage 12 → 11,20 ; UE (coef 2 et 1) 11,80 et 7,00 → 10,20.
- ABS, arrondis, bornes, rang ex æquo, règles personnalisées, bulletin (moyenne générale, blocage si matière manquante, QR).

### Identifiant
- Format `C-CEGB-7K4P9QX`, contrôle, faute détectée, saisie tolérante ; 100 000 générations sans collision de noyau ni caractère ambigu.
- Code établissement unique (conflit → `LSB2`) ; cycle déduit du niveau de la classe.
- Changement d'établissement dans le cycle → identifiant inchangé ; collège → lycée autorisé → `L-<code>-<même noyau>`, ancien accepté 60 jours puis refusé ; passage refusé → aucun changement ; lycée → université après BAC → `U-…`.
- Régénération : préfixe conservé, ancien refusé, parcours intact ; tentatives limitées ; écran « Ce n'est pas moi » sans fuite de données ; profil automatique exact.

### Inscription enseignant
- Suggestions ; valeur nouvelle acceptée et proposée ; fusion admin propagée ; statistiques normalisées.

### Parents
- Rattachement impossible sans code parent ; limite par élève ; un parent ne voit que ses enfants ; retrait ; SMS aux bons événements ; consultation SMS refusée depuis un numéro non rattaché.

### Appel, emploi du temps, agenda
- Appel hors ligne puis synchronisation sans doublon ; absences dans le bulletin ; seuil d'alerte.
- Chevauchements entre établissements détectés ; PDF par établissement et global ; emploi du temps général de l'élève en PDF.
- Devoir planifié visible chez élèves et parents et colonne de notes créée ; conflit de deux devoirs le même jour signalé.

### Outils enseignant
- Statistiques exactes sur jeu connu ; filtres ; exports ; cloisonnement.
- Activité : compteurs exacts, uniquement sa matière, mention visible chez l'élève.
- Documents pédagogiques privés ; « Publier » exige titre et objectifs ; ZIP ; duplication annuelle ; quota.
- **Correction en ligne** : annotations enregistrées et rendues dans le PDF de l'élève ; barème → total exact ; report de note dans la bonne colonne avec limite de modifications.
- **Corrigés** : invisibles avant la publication des notes (ou la date choisie), visibles après.
- **Banque de sujets** : visibilités respectées ; sujet de composition invisible avant la date de l'épreuve ; réutilisation crédite l'auteur ; signalement et retrait.
- **Fiche de suivi** : observations privées par défaut ; partage avec l'établissement.
- **Passation** : tout est transmis, acceptation requise, retour automatique en fin de remplacement, élèves voient le nouveau prof.
- **Saisie des notes hors ligne** : synchronisation ; conflit entre deux appareils signalé.
- **Quiz en direct** : code de session, réponses en temps réel, aucun nom affiché à l'écran collectif, bilan exact.
- **IA enseignant** : brouillons jamais publiés automatiquement ; appréciations proposées puis validées ; aucune écriture possible dans les notes ; quotas.

### Outils élève
- **Simulateur** : D1 = 8, D2 = 9, D3 = 10 (Moy. devoirs 9,00) ; objectif 10 → composition nécessaire **11,00** ; objectif 15 → 21,00 → « objectif impossible » ; règles personnalisées et régime semestriel respectés ; aucune écriture dans les notes.
- **J'étais absent** : séance manquée → contenu du cahier de textes affiché ; cahier vide → message.
- **Exercices** : correction immédiate exacte ; progression par chapitre ; résultats hors ligne synchronisés.
- **Tuteur IA** (fournisseur simulé) : refuse de donner la réponse finale d'un devoir publié en cours, guide par indices ; refuse les sujets hors programme ; quotas.
- **Questions sur un cours** : visibles par la classe seulement ; anonymat vis-à-vis des camarades mais pas du prof ; masquage par le prof.
- **Mode économie** : « Télécharger ma semaine » récupère tous les contenus ; lisibles hors ligne ; vidéos bloquées sur données mobiles si réglé.
- **Orientation** : fiches visibles en 3e et Terminale ; questionnaire sans stockage de profil psychologique.

### Attestations
- QR valide → authentique ; document modifié ou code inventé → non authentique ; page publique sans données sensibles.

### Contrôle des passages (v1.0, à conserver avec le nouvel identifiant)
- Redoublement en 4e → 3e bloquée (même et autre établissement) ; seconde tentative → élève bloqué + alerte inspection ; dérogation accordée/refusée ; sans BEPC → 2nde refusée ; sans BAC → L1 refusée.

### Droits d'accès
- Élève, parent, prof, établissement, inspection, ministère, admin : chacun strictement dans son périmètre.

### Parcours e2e
1. Un prof s'inscrit en tapant sa ville et sa matière, ajoute ses établissements et classes, importe une liste, imprime les cartes (identifiant + code parent), planifie un D1, publie un cours (titre, objectifs) et un devoir.
2. Un élève se connecte, confirme son identité, voit son profil, ses profs et son emploi du temps, télécharge sa semaine, utilise le tuteur IA sur le cours, pose une question sous le cours, rend le devoir en photo.
3. Le prof fait l'appel hors ligne, corrige la copie en ligne avec barème, la note part dans D1, publie le corrigé ; l'élève voit sa copie annotée, sa note, le corrigé, utilise le simulateur ; un parent rattaché reçoit le SMS de la note et de l'absence.
4. Le prof génère des appréciations avec l'IA, les valide ; consulte ses statistiques et l'activité ; partage un sujet dans la banque ; un collègue le réutilise ; le prof transmet sa classe à un remplaçant.
5. L'établissement édite les bulletins et un certificat de scolarité vérifiable ; l'élève obtient son BEPC, passe en 2nde dans un autre établissement : identifiant `L-<code lycée>-<même noyau>`, parcours complet, le prof du lycée voit d'où il vient.
6. Un autre établissement tente d'inscrire un redoublant en classe supérieure → blocage, alerte inspection ; le ministère voit les statistiques mises à jour.

---

## 18. Feuille de route

### v1.0 — Construite
Socle, enseignants, élèves, notes (secondaire et supérieur), cours, devoirs, apprentissage, établissement, bulletins, fin d'année, contrôle des passages, autorités et zones, inspection, ministère, finitions (PWA, temps réel, sauvegardes, métriques).

### v1.1 — À réaliser maintenant (dans cet ordre)
1. **Identifiant à cycles** (§6) : code établissement, lettre de cycle, noyau permanent, mise à jour au changement de cycle, transition, historique, migration des données de démo, cartes (avec code parent), confirmation et profil automatique.
2. **Inscription enseignant** : ville et matières saisies avec suggestions, propositions et fusion.
3. **Espace Parents** (§10).
4. **Appel en un clic** et **saisie des notes hors ligne** (file de synchronisation commune).
5. **Emplois du temps** (classe, prof multi-établissements, élève, PDF), **agenda de planification**, **annonces**.
6. **Cahier de textes** étendu et **« J'étais absent »**.
7. **Copies, correction en ligne et corrigés**.
8. **Mes documents pédagogiques** et **banque de sujets partagée**.
9. **Tableau de statistiques**, **activité des élèves**, **fiche de suivi**, **passation de classe**.
10. **IA** : assistant enseignant (dont **appréciations**), **tuteur élève**, **exercices auto-corrigés**.
11. **Questions sur un cours** et **quiz en direct**.
12. **Simulateur de moyenne**, **mode économie de données**, **révisions BEPC/BAC**, **orientation**.
13. **Attestations** avec QR et page de vérification ; mises à jour des écrans établissement, inspection et admin liées à la v1.1.
14. **Finitions** : README (§20 et comptes de démo par rôle, parents compris), suite complète, `RAPPORT_V1_1.md`.

### v1.2 — Après les premiers retours de vrais enseignants
Ajustements d'usage, performances sur réseau faible, contenus (exercices, orientation, annales).

### v2 — Établissement commercial (§16.1)
### v3 — Inspection et ministère étendus, interconnexions (§16.2 à §16.4)

---

## 19. Modèle économique

- **Gratuit** pour les enseignants, les élèves et les parents (usage de base).
- **Établissements** (v2) : abonnement par établissement ou par élève et par an ; cibles prioritaires : écoles privées, universités privées, écoles de formation ; commission ou forfait sur le **paiement des frais de scolarité**.
- **État** (v3) : licence nationale ou par ordre d'enseignement pour l'inspection et le ministère.
- **Options** : alertes SMS parents premium, révisions BEPC/BAC premium, quotas IA étendus.

---

## 20. Lancer le projet

> Section à compléter et tenir à jour par Claude.

```bash
docker compose up -d          # Postgres 5440, Redis 6390, stockage S3 9100
# migrations et données de démo : commandes exactes à documenter ici
# API : http://localhost:4300   Front : http://localhost:5300
# tests : core, unitaires, intégration, Playwright — commandes exactes à documenter ici
```

**Après un redémarrage de l'ordinateur** : relancer `docker compose up -d` avant l'API.

**Comptes de démonstration** (OTP fixe en développement) : un compte par rôle — enseignant (multi-établissements), élève de collège, élève de lycée, étudiant, **parent**, personnel d'établissement, inspecteur, agent du ministère, admin — avec identifiants, mots de passe et identifiants élèves au nouveau format, à documenter ici.
