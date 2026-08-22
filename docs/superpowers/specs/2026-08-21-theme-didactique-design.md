# Onglet « Carte astro complète » -- refonte didactique

**Date :** 2026-08-21
**Projet :** portrait-cosmique
**Statut :** validé en brainstorming, en attente de revue utilisateur
**Spec parente :** `2026-08-21-carte-astrologique-complete-design.md` (construit l'existant qu'on rénove)

## Objectif

Transformer le rendu de l'onglet « Carte astro complète » (actuellement des
tableaux secs + bulles ℹ️ + légende PDF dupliquée en bas) en une présentation
**didactique** : chaque point et chaque section enseignent au lecteur **ce
qu'ils sont** et **d'où ils viennent**, puis injectent les valeurs du thème
réel du sujet. Fin du doublon (Soleil/Lune en §1+§2 rendu explicite ;
légende bas supprimée).

## Problèmes corrigés

| # | Problème actuel | Cause |
|---|---|---|
| P1 | Les 6 sections sont des tableaux secs ; le lecteur ne sait pas **ce qu'est** « MC » ni d'où vient la notion. | `renderTableaux` (index.html:1172) n'affiche que des données, pas d'enseignement. |
| P2 | Les définitions du glossaire (qui expliquent quoi+d'où) sont **cachées** derrière l'icône ℹ️ **et** **redupliquées** dans la légende PDF en bas (`r-legende`, index.html:755). | Deux surfaces d'affichage pour le même contenu. |
| P3 | **Doublon de données** : Soleil & Lune apparaissent dans §1 (fondations) ET §2 (10 corps) sans distinction visible. | Même planète, deux lectures différentes (pilier vs corps) mais non signalé. |
| P4 | Les **chiffres** (degré, vitesse, orbe, exactitude, scores dominantes) sont affichés bruts, sans légende de ce qu'ils représentent. | Aucune légende de colonne numérique. |
| P5 | Pas de **fil rouge** : le lecteur ignore la grille de lecture Planète=quoi / Signe=comment / Maison=où / Aspect=interaction. | Absence d'un chapeau pédagogique. |

## Décisions structurantes (validées en brainstorming)

| Sujet | Décision |
|---|---|
| Format | **Cartes didactiques** pour §1/§2/§3 (points) ; tableaux conservés pour §4/§5/§6 mais avec **intro didactique** + **légende des chiffres**. |
| Contenu didactique | **Couche nouvelle** (question guide + liste de domaines symboliques + conclusion) **stockée backend** dans `engine/significations.py` (`DIDACTIQUE_FR`/`DIDACTIQUE_EN`), exposée via l'API `/portrait` existante. Cohérent avec l'architecture glossaire + i18n centralisé + testable. |
| Doublon Soleil/Lune | **Gardé dans les deux sections**, mais chaque occurrence affiche **sa** facette propre (pilier en §1 via `theme_fondation_*`, corps en §2 via `theme_corps_*`). Le doublon devient une **distinction explicite**, pas une répétition. |
| Légende bas | **Supprimée** (`r-legende` retiré). Les définitions sont en clair dans les cartes/intros. |
| Fil rouge | Bandeau pédagogique en tête d'onglet : « Planète = quoi · Signe = comment · Maison = où · Aspect = comment ça interagit ». |
| Périmètre | **Les 6 sections d'un coup** (pas par étape). |
| Données thème | **Réutilisées telles quelles** : `theme_complet` (`fondations`, `dix_corps`, `points_evolutifs`, `maisons`, `aspects`, `dominantes`) + `SIGNES_SENS` pour le sens du signe. Aucun recalcul astronomique. |

## Architecture

### Backend -- nouvelle couche didactique

Nouveau bloc dans `engine/significations.py`, à côté de `GLOSSAIRE_FR/EN` :

```python
DIDACTIQUE_FR = {
    # Clé stable = id glossaire existant (réutilise l'ancrage i18n).
    # 1 entité = 1 facette. Soleil a 2 entrées (pilier + corps).
    "theme_fondation_soleil": {
        "question": "Qui suis-je ?",
        "domaines": [
            "identité consciente", "volonté", "affirmation de soi",
            "ce que tu cherches à devenir", "manière de rayonner",
        ],
        "conclusion": "Soleil = ton centre",
    },
    "theme_corps_soleil": {
        "question": "Comment je rayonne au quotidien ?",
        "domaines": ["vitalité", "identité consciente", "ce que tu exprimes"],
        "conclusion": "Soleil = ton noyau",
    },
    # ... 16 autres points + intros de section ...
    "theme_maisons": {  # intro de section §4
        "question": "Où se joue cette énergie ?",
        "domaines": ["secteurs de l'expérience de vie", ...],
        "conclusion": "La planète dit QUOI, la maison dit OÙ",
    },
    "theme_aspects": { ... },      # intro §5
    "theme_dominantes": { ... },  # intro §6
}
DIDACTIQUE_EN = { ... }  # mêmes clés, valeurs traduites
```

**Règles de clé** : chaque entrée pointe vers un **id glossaire existant**
(`theme_fondation_soleil`, `theme_corps_soleil`, `theme_point_noeud_nord`,
`theme_maisons`, `theme_aspects`, `theme_dominantes`). Aucun nouvel id créé --
on surcharge les existants d'une facette didactique. Les ids `theme_corps_*`
et `theme_fondation_*` pour Soleil/Lune restent distincts (résout P3).

**Nouvelle fonction** :
```python
def didactique(langue: str = "fr") -> dict:
    """Renvoie {id: {question, domaines, conclusion}} pour la couche didactique."""
```
Renvoie `{}` (et non une erreur) si la langue est absente -- l'UI doit
retomber sur le glossaire seul si la couche manque (grâce de robustesse).

### API -- extension `/portrait`

`main.py:138` étend le payload renvoyé au front :
```python
"didactique": significations.didactique(body.langue),
```
À côté de `"glossaire"` déjà présent. Aucun breaking change : le front
actuel ignore les clés inconnues.

### Frontend -- refonte de `renderTableaux`

**Nouvel état global** :
```js
let DIDACTIQUE = {};  // { id: {question, domaines, conclusion} } aplati
function chargerDidactique(d) { DIDACTIQUE = d || {}; }
```
Chargé en début de `afficherResultat` (comme `chargerGlossaire`).

**Bandeau fil rouge** (nouvel élément en tête de `#onglet-theme`) :
```
Planète = quoi · Signe = comment · Maison = où · Aspect = comment ça interagit
```
Caché à l'écran, révélé à l'impression (comme les autres éléments pédagogiques).

**Helper de carte** (remplace les lignes de tableau pour §1/§2/§3) :
```js
function cartePoint(symbole, nom, gid, valeur /* {signe, degre, maison, retro, sens_signe} */) {
  const d = DIDACTIQUE[gid] || {};
  return `
    <div class="carte-point">
      <div class="cp-tete"><span class="cp-sym">${symbole}</span>
        <span class="cp-nom">${nom}</span>
        ${d.question ? `<span class="cp-q">« ${d.question} »</span>` : ""}
      </div>
      ${d.domaines ? `<ul class="cp-domaines">${d.domaines.map(x => `<li>${x}</li>`).join("")}</ul>` : ""}
      <div class="cp-valeur">
        Dans ton thème : <strong>${valeur.signe}</strong>
        ${valeur.degre != null ? `· ${fmtDeg(valeur.degre)}` : ""}
        ${valeur.maison ? `· Maison ${valeur.maison}` : ""}
        ${valeur.retro ? ` · ℞ rétrograde` : ""}
        ${valeur.sens_signe ? `<div class="cp-sens">${valeur.sens_signe}</div>` : ""}
      </div>
      ${d.conclusion ? `<div class="cp-conclusion">Donc : ${d.conclusion}</div>` : ""}
    </div>`;
}
```

**Rendu par section** :

- **§1 Fondations** : 6 cartes (Soleil/Lune en facette *pilier* via
  `theme_fondation_*`). Valeurs depuis `tc.fondations` + maison dérivée.
- **§2 10 corps** : 10 cartes (Soleil/Lune en facette *corps* via
  `theme_corps_*`). Valeurs depuis `tc.dix_corps` (signe, degré, maison,
  vitesse, rétro). **La vitesse et le ℞ deviennent des chiffres légendés**
  dans la légende de section (P4).
- **§3 Points évolutifs** : 4 cartes. Valeurs depuis `tc.points_evolutifs`.
- **§4 Maisons** : tableau conservé, **précédé d'une intro didactique**
  (`theme_maisons` : question/domaines/conclusion). + légende des chiffres
  « N° = numéro du secteur (1-12) · Cuspe = degré du début de maison ».
- **§5 Aspects** : tableau conservé (déjà filtrable/triable -- on y touche
  pas), **précédé d'une intro** (`theme_aspects`). + légende chiffres :
  « Orbe = écart à l'angle exact (plus petit = plus puissant) · Exactitude =
  proximité au parfait (0-100%) ».
- **§6 Dominantes** : 5 cartes conservées, **précédées d'une intro**
  (`theme_dominantes`). + légende chiffres : « Score = poids calculé selon la
  méthode choisie (comptage+dignités ou score complexe) ».

**Suppression P2** : retrait du bloc `r-legende` (index.html:748-758) et de
son injection. Les définitions glossaire restent disponibles via ℹ️ sur les
cartes (info secondaire), mais le doublon de surface disparaît.

### Styles

Nouvelles classes `.carte-point`, `.cp-tete`, `.cp-sym`, `.cp-nom`, `.cp-q`,
`.cp-domaines`, `.cp-valeur`, `.cp-sens`, `.cp-conclusion`,
`.fil-rouge`, `.section-intro`, `.legende-chiffres`. Réutilise les variables
CSS existantes (`--accent`, `--panel2`, `--border`, `--muted`). Cartes en
grille responsive (`grid-template-columns: repeat(auto-fill, minmax(260px, 1fr))`).

## Couverture du contenu didactique à produire

18 entités-point (Soleil a 2 facettes) + 3 intros de section = **21 entrées
× 2 langues = 42 jeux** {question, domaines[3-6], conclusion}.

Liste exhaustive des clés (toutes existent déjà dans `GLOSSAIRE_FR/EN`) :

- Facette pilier (§1) : `theme_fondation_soleil`, `theme_fondation_lune`,
  `theme_fondation_ascendant`, `theme_fondation_descendant`,
  `theme_fondation_milieu_du_ciel`, `theme_fondation_fond_du_ciel`
- Facette corps (§2) : `theme_corps_soleil`, `theme_corps_lune`,
  `theme_corps_mercure`, `theme_corps_vénus`, `theme_corps_mars`,
  `theme_corps_jupiter`, `theme_corps_saturne`, `theme_corps_uranus`,
  `theme_corps_neptune`, `theme_corps_pluton`
- Points évolutifs (§3) : `theme_point_noeud_nord`,
  `theme_point_noeud_sud`, `theme_point_chiron`, `theme_point_lilith`
- Intros de section : `theme_maisons`, `theme_aspects`, `theme_dominantes`

Source d'inspiration explicite (fournie par l'utilisateur en brainstorming) :
question guide par point, liste à puces des domaines symboliques,
conclusion « Donc : X = ... ». Fil rouge QUOI→COMMENT→OÙ→INTERACTION.

## Plan de test

1. **`engine/test_significations.py`** -- étendre :
   - `test_didactique_fr_structure` : 21 clés présentes, chaque entrée a
     `question`/`domaines`(>=3)/`conclusion` non vides.
   - `test_didactique_en_memes_cles` : mêmes clés FR==EN.
   - `test_didactique_ids_connus_du_glossaire` : toute clé didactique existe
     dans `GLOSSAIRE_FR`/`GLOSSAIRE_EN` (garde-fou P3).
2. **`engine/test_api_theme.py`** -- `test_portrait_renvoie_didactique` :
   le payload `/portrait` contient `didactique` non vide avec au moins
   `theme_fondation_soleil`.
3. **Frontend** -- pas de tests automatisés existants ; vérification manuelle
   au lancement (`python main.py` + navigateur) : 6 sections rendues en
   cartes/intros, fil rouge visible, légende bas absente, Soleil distinct
   §1/§2. Capture d'écran avant/après pour comparaison.

## Hors périmètre (YAGNI)

- Pas de recalcul astronomique (VSOP87, maisons, aspects) -- données réutilisées.
- Pas de nouveau endpoint -- extension de `/portrait`.
- Pas de refonte de l'onglet « Portrait » (le multi-traditions) -- sujet
  distinct, hors scope ici.
- Pas de modification de la roue SVG -- elle reste telle quelle.
- Pas d'i18n au-delà FR/EN.
- L'interprétation IA (« Approfondir ») n'est pas touchée -- elle consomme
  déjà `theme_complet` et reste compatible.

## Risques & mitigations

| Risque | Mitigation |
|---|---|
| Contenu didactique subjectif/inexact. | S'aligner sur `GLOSSAIRE_FR` existant (déjà relu) ; formulations symboliques « à lire comme » héritées du ton du projet. |
| 21 entrées × 2 langues = effort de rédaction long. | Découpé en tâches par bloc (fondations, corps, points, intros) dans le plan d'implémentation. |
| Régression d'affichage PDF/impression. | Cartes en grille `auto-fill` repliable en une colonne à l'impression. Bandeau fil-rouge, intros de section et légendes de chiffres **visibles à l'écran ET à l'impression** (pas de masquage). |
| Coupure visuelle avec l'existant. | Réutilisation des variables CSS + tons typographique existants. |

## Critères d'acceptation

1. Les 6 sections de l'onglet « Carte astro complète » sont visuellement
   séparées et chacune porte son enseignement (quoi + d'où).
2. §1/§2/§3 s'affichent en cartes didactiques (question → domaines → valeur
   du thème → conclusion).
3. Soleil/Lune apparaissent en §1 (facette pilier) ET §2 (facette corps) avec
   des contenus didactiques **distincts** -- le lecteur voit que ce n'est pas
   un doublon.
4. §4/§5/§6 gardent leur tableau mais ont une intro didactique + une légende
   des chiffres.
5. Le bandeau fil rouge est affiché en tête d'onglet.
6. La légende PDF en bas (`r-legende`) est supprimée -- fin du doublon.
7. `SIGNES_SENS` alimente le sens du signe dans chaque carte.
8. Tests backend verts ; `/portrait` renvoie `didactique`.
