# Bulles interactives + légende PDF — Design

Date : 2026-08-03

## Objectif

Rendre le portrait cosmique auto-explicatif :

1. **Bulles interactives** sur les titres (empreinte, stats, archétype/forces/faiblesse/pierre)
   pour expliquer ce que représente chaque concept (Soleil, Lune, Ascendant, Védique,
   Nakshatra, Maya, Celte, etc.).
2. **HTML exporté** : les bulles restent interactives (fichier autonome, hors-ligne).
3. **PDF** : une **légende groupée par thèmes** apparaît en fin de document, déroulant
   toutes les définitions (mêmes contenus que les bulles).

## Périmètre validé

- **Titres concernés** : empreinte (13 clés) + 8 stats de personnalité + archétype +
  forces + faiblesse + pierre d'équilibrage. → **Tout**.
- **Profondeur** : définition + contexte (origine, ce que ça éclaire, comment le lire),
  3-5 phrases par concept.
- **Déclencheur** : icône ℹ️ après le titre ; bulle au survol (desktop) ou clic
  (mobile/tactile/clavier via focus).
- **Source des textes** : glossaire bilingue (FR/EN) côté Python, dans
  `engine/significations.py`, renvoyé par l'API `/portrait`.
- **Légende PDF** : groupée par thèmes (Astrologie occidentale, Chinoise, Védique,
  Autres traditions, Numérologie, Stats de personnalité, Synthèse).

## Architecture

### 1. Glossaire Python (`engine/significations.py`)

Ajouter deux tables :

```python
GLOSSAIRE_FR = {
  "soleil":        "Soleil — signe zodiacal du Soleil à la naissance ...",
  "lune":          "Lune — ...",
  "ascendant":     "Ascendant — ...",
  "chinoise":      "Astrologie chinoise — ...",
  "animal_heure":  "Animal de l'heure — ...",
  "vedique":       "Védique (rashi) — ...",
  "nakshatra":     "Nakshatra — ...",
  "egypte":        "Égypte — ...",
  "celte":         "Celte — ...",
  "totem":         "Totem amérindien — ...",
  "maya":          "Maya (Tzolkin) — ...",
  "chemin_de_vie": "Chemin de vie — ...",
  "expression":    "Expression (nom) — ...",
  "archetype":     "Archétype — ...",
  "forces":        "Forces dominantes — ...",
  "faiblesse":     "Point à travailler — ...",
  "pierre":        "Pierre d'équilibrage — ...",
  "stat_charisme":   "Charisme — ...",
  "stat_combativite":"Combativité — ...",
  "stat_sagesse":    "Sagesse — ...",
  "stat_creativite": "Créativité — ...",
  "stat_discretion": "Discrétion — ...",
  "stat_stabilite":  "Stabilité — ...",
  "stat_emotivite":  "Émotivité — ...",
  "stat_energie":    "Énergie — ...",
}
GLOSSAIRE_EN = { ... }   # même clés, texte en anglais
```

Chaque entrée : 3-5 phrases (définition + contexte). Ton aligné sur le reste du moteur
(lecture symbolique de divertissement). Version EN alignée sur `SIGNES_SENS_EN`, etc.

Une fonction :

```python
def glossaire(langue: str = "fr") -> list:
    """Légende lisible, groupée par thèmes, pour la fin du document PDF.

    Retourne : [
      {"theme": "Astrologie occidentale",
       "items": [{"id":"soleil","label":"Soleil","definition":"..."},
                 {"id":"lune",...}, {"id":"ascendant",...}]},
      {"theme": "Astrologie chinoise", "items":[...]},
      {"theme": "Astrologie védique", "items":[...]},
      {"theme": "Autres traditions", "items":[...]},
      {"theme": "Numérologie", "items":[...]},
      {"theme": "Statistiques de personnalité", "items":[...]},
      {"theme": "Synthèse du portrait", "items":[...]},
    ]
    """
```

Les `label` proviennent des libellés `_CLE`/`_ROLE` existants (FR/EN déjà gérés) ;
les `definition` de `GLOSSAIRE_*`.

### 2. API (`main.py`)

`/portrait` renvoie en plus :

- `glossaire`: résultat de `significations.glossaire(body.langue)` (légende thématisée).
- Chaque entrée de `empreinte` reçoit un champ `id` stable pointant vers l'entrée du
  glossaire (`"soleil"`, `"lune"`, etc.). L'`id` est dérivé de la clé interne (mapping
  peu coûteux à ajouter dans `expliquer()`).

Aucune autre route n'est modifiée.

### 3. Front (`static/index.html`)

#### Tooltip universel

- Au rendu, après chaque titre (clé d'empreinte, label de stat, libellé de la
  sous-ligne archétype/forces/faiblesse/pierre), on injecte une icône
  `<span class="glossaire-ic" data-glossaire="<id>" role="button" tabindex="0" aria-label="Définition">ℹ️</span>`.
- Au survol (desktop) ou clic/touch/Entrée (mobile, clavier), une bulle
  `position:absolute` s'ouvre près de l'icône avec la définition correspondante.
- **Un seul gestionnaire d'événements** (délégation) posé sur `.wrap` :
  - `mouseover`/`mouseout` (avec `relatedTarget` check) sur `[data-glossaire]`
  - `click` sur `[data-glossaire]` (toggle pour mobile)
  - `keydown` Enter/Espace sur `[data-glossaire]` (accessibilité clavier)
  - fermeture au clic extérieur ou Échap.
- Les définitions sont lues dans un objet JS `GLOSSAIRE` construit à partir du
  `glossaire` reçu de l'API (aplati : `{ id: definition }`). Repli : si l'id est
  absent, pas de bulle, pas d'icône.

#### Légende PDF

- Bloc `<section class="legende" hidden>` monté à la fin de `#resultat` au moment du
  rendu, à partir de `glossaire`. Contenu : pour chaque thème, un `<h3>` + liste
  `<dl>` (`<dt>label</dt><dd>definition</dd>`).
- CSS :
  - `.legende { display: none; }` à l'écran (les bulles suffisent).
  - `@media print { .legende { display: block; } .glossaire-ic { display: none; } }`.
- Résultat : à l'impression (depuis l'app **ou** depuis l'HTML exporté), les bulles
  disparaissent et la légende thématisée apparaît en fin de PDF.

#### Export HTML

- `telechargerHTML()` sérialise :
  - le `#resultat` (qui contient déjà la légende rendue dans le DOM, marquée `hidden`
    donc absente à l'écran mais présente dans le HTML — активée par `@media print` du
    CSS embarqué),
  - le `GLOSSAIRE` (objet JS inline),
  - le script tooltip minimal (auto-contenu, pas de `fetch`, pas de réseau).
- Le fichier téléchargé est donc interactif (bulles) **et** imprimable avec légende,
  hors-ligne. Aucune dépendance externe.

### 4. Données transportées

Au calcul : `DERNIER_RESULTAT.glossaire` est stocké. Au rendu :

- Construction de `GLOSSAIRE = {}` (aplati par id) ; sert aux bulles.
- Construction du DOM de la légende (injecté dans `#resultat`).
- Sérialisation dans l'export.

## Cas aux limites

1. **API sans glossaire** (anciennes instances, mauvais réseau, repli) : `glossaire`
   absent → pas d'icône ℹ️, pas de légende. Rien ne casse.
2. **Stats** : 8 stats fixes. Mapping nom_fr/nom_en → id `stat_*` (table fixe côté
   front, basée sur l'ordre connu : Charisme=stat_charisme, etc.). Si un nom de stat
   inconnu apparaît, pas de bulle sur cette entrée (silencieux).
3. **Archétype/forces/pierre** : ids `archetype`, `forces`, `faiblesse`, `pierre`.
   L'icône est placée au début de la sous-ligne, pas sur chaque mot — une icône par
   concept accolée à son label.
4. **Empreinte** : id stable ajouté par `expliquer()` côté Python (mapping
   sobriquet→id), jamais null ; le front peut toujours piocher dans `GLOSSAIRE`.
5. **PDF depuis l'app** : `window.print()` imprime `#resultat` qui inclut la légende
   cachée ; la media query la révèle.
6. **PDF depuis l'HTML** : idem — le fichier exporté embarque son `<style>` avec la
   même media query, donc la légende est révélée à l'impression depuis le fichier
   standalone.

## Tests

- Python : `engine/test_significations.py` — étendre avec :
  - `glossaire("fr")` renvoie bien 7 thèmes, ordre attendu, ids présents.
  - `glossaire("en")` : même structure, texte anglais, clés identiques.
  - `expliquer(trad, "fr"|"en")` : chaque entrée a un `id` stable connu (`soleil`,
    `lune`, …) et présent dans le glossaire correspondant.
- Front : pas de framework de test ; vérification manuelle :
  1. Calculer un portrait → bulles présentes sur empreinte + stats + sous-ligne.
  2. Survoler une icône → bulle affiche la bonne définition (FR puis EN).
  3. Cliquer (mobile simulé via DevTools) → bulle toggle.
  4. Naviguer au clavier Tab → Entrée sur l'icône → bulle s'ouvre.
  5. Exporter HTML → ouvrir le fichier hors-ligne → bulles fonctionnent.
  6. Imprimer/PDF (depuis l'app, puis depuis l'export) → légende thématisée en fin
     de PDF, bulles invisibles.

## Non-objectif (YAGNI)

- Pas de lazy-load : le glossaire est petit, embarqué en une fois.
- Pas de mémoire des bulles déjà ouvertes.
- Pas de mode sombre/clair spécifique à la bulle (suit le thème existant).
- Pas d'animation lourde : simple fade-in CSS.