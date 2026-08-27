# Onglet « Poster » -- design

**Date :** 2026-08-27
**Projet :** portrait-cosmique
**Statut :** validé par l'utilisateur (brainstorming), en attente de revue finale

## Objectif

Ajouter un mode de rendu visuel raffiné de la carte astrale et des traditions
natales, pensé pour servir d'exemple/aperçu à un produit dérivé imprimé
(poster mural, t-shirt). L'onglet « Carte astro complète » existant reste
inchangé (dense, technique, pensé pour l'analyse) -- ce nouvel onglet est une
vue de **présentation**, pas d'analyse : composition épurée, typographie
soignée, export image haute résolution.

## Décisions structurantes (validées en brainstorming)

| Sujet | Décision |
|---|---|
| Emplacement | **3ᵉ onglet « Poster »**, à côté de Portrait et Carte astro complète. |
| Style visuel | **Palette actuelle conservée** (violet `--accent` / vert menthe `--accent2` sur fond sombre `--bg`) -- on raffine composition/proportions/typographie, pas l'identité couleur. |
| Contenu | **Deux types de poster** au choix : « Carte du ciel » (roue) et « Traditions natales » (grille). |
| Densité (Carte du ciel) | **Épuré / Complet** au choix (toggle). |
| Bloc identité | Prénom + nom + date/heure/lieu affichés en en-tête, sobre, commun aux deux types. |
| Export | **PNG haute résolution** (~3000×3000 px), avec case **fond transparent / fond plein**. |
| Nouveau fichier ? | Non -- tout reste dans `static/index.html`, cohérent avec l'architecture mono-fichier existante. |
| Nouvel endpoint serveur ? | Non -- réutilise les données déjà chargées côté client (`DERNIER_RESULTAT`), aucun appel réseau supplémentaire. |

## Sources de données (déjà disponibles côté client)

Le `POST /portrait` existant retourne déjà tout le nécessaire, stocké dans
`DERNIER_RESULTAT` (`static/index.html:1169`) :

- `DERNIER_RESULTAT.theme_complet` -- carte astrologique complète (fondations,
  dix_corps, points_evolutifs, maisons, aspects, dominantes), déjà utilisée
  par `renderRoue()`. Le poster « Carte du ciel » consomme la même structure.
- `DERNIER_RESULTAT.traditions` -- dict brut de `engine/traditions.py:calculer()`
  (voir mapping détaillé plus bas). Pas encore lu directement côté JS
  aujourd'hui (seul son texte interprété dans `empreinte` est affiché) -- le
  poster « Traditions natales » l'exploite pour la première fois tel quel.
- `DERNIER_RESULTAT._identite` -- `{prenoms, nom, date_naissance,
  heure_naissance, ville}`, déjà construit à `static/index.html:1164`.

Aucun nouvel appel serveur : si `DERNIER_RESULTAT` est absent (aucun calcul
fait), l'onglet Poster affiche un message d'invite à calculer un portrait
d'abord (cohérent avec le comportement actuel de l'onglet Carte astro quand
`_THEME_CACHE` est vide).

## Structure HTML / onglets

Ajout d'un 3ᵉ bouton dans `#r-onglets` (`data-onglet="poster"`) suivant le
pattern existant (`.onglet` / `.onglet-contenu`, bascule via le même
gestionnaire de clic générique déjà en place à `static/index.html:1394`).

```html
<section id="onglet-poster" class="onglet-contenu" hidden>
  <div class="poster-options">
    <fieldset>
      <legend>Type de poster</legend>
      <label><input type="radio" name="poster-type" value="ciel" checked> Carte du ciel</label>
      <label><input type="radio" name="poster-type" value="traditions"> Traditions natales</label>
    </fieldset>
    <fieldset id="poster-densite-fieldset"> <!-- masqué si type=traditions -->
      <legend>Densité</legend>
      <label><input type="radio" name="poster-densite" value="epure" checked> Épuré</label>
      <label><input type="radio" name="poster-densite" value="complet"> Complet</label>
    </fieldset>
    <label class="poster-transparent">
      <input type="checkbox" id="poster-fond-transparent"> Fond transparent (t-shirt)
    </label>
    <button type="button" class="btn" id="btn-export-poster">⬇️ Télécharger en PNG</button>
  </div>

  <div class="poster-cadre" id="poster-cadre">
    <svg id="poster-svg" viewBox="-260 -260 520 520" role="img" aria-label="Poster"></svg>
  </div>
</section>
```

Le bloc identité (prénom/date/lieu) fait partie du SVG lui-même (pas du HTML
autour), pour que l'export PNG le capture automatiquement sans logique
séparée.

## Poster « Carte du ciel »

Nouvelle fonction `renderPosterCiel(tc, identite, densite)`, distincte de
`renderRoue()` (qui reste inchangée, utilisée par l'onglet Carte astro
complète). Réutilise les helpers existants (`lonToXY`, `svgArc`, `elNS`,
`SYMBOLES_ZODIAQUE`, `SYMBOLES_POINTS`, `COULEURS_ASPECTS`) mais avec des
rayons et styles propres au poster :

- **Rayons agrandis** par rapport à `renderRoue` (`R_EXT`, `R_ZOD_INT` etc.
  redéfinis, ~1.3x, adaptés au viewBox `-260..260`) pour une composition qui
  respire, la roue occupant la moitié supérieure du carré et laissant la place
  au bloc identité en bas.
- **Halo radial** : un `<radialGradient>` doré/violet doux derrière le cercle
  (`<circle>` avec `fill="url(#poster-halo)"`, rayon légèrement supérieur à
  `R_EXT`) pour donner un effet « objet » plutôt que « diagramme ». Défini une
  fois dans un `<defs>` en tête du SVG.
- **Traits affinés** : `stroke-width` des anneaux et lignes réduit d'environ
  30% par rapport à `renderRoue`, tailles de police des glyphes/symboles
  augmentées en proportion des nouveaux rayons.
- **Pas de filtre interactif** : contrairement à `renderRoue`, aucune légende
  cliquable -- c'est un rendu figé pour export.

**Mode `epure`** :
- Anneau zodiacal (12 signes) + glyphes des 10 corps + 4 points évolutifs.
- Aspects **majeurs uniquement** (`a.type === "majeur"`), pas de mineurs.
- **Aucun** anneau des maisons, aucune ligne de cuspide, aucun numéro de
  maison, aucun degré affiché.

**Mode `complet`** :
- Tout ce que `renderRoue` affiche (anneau des maisons avec cuspides et
  numéros, 18 points, aspects majeurs **et** mineurs) mais redessiné aux
  rayons/styles du poster.

## Poster « Traditions natales »

Nouvelle fonction `renderPosterTraditions(traditions, identite)`. Construit
une grille de cartes SVG (`<g>` positionnés en grille, pas de wheel) --
symbole + libellé + valeur, **sans texte d'interprétation**. Seules les clés
présentes dans `traditions` (repli honnête déjà géré côté serveur) génèrent
une carte.

Mapping clé → carte (symbole affiché, libellé, valeur formatée) :

| Clé `traditions.*` | Libellé | Symbole | Valeur affichée |
|---|---|---|---|
| `signe_solaire` | Signe solaire | `.symbole` | `.nom` (+ `.element` en sous-texte) |
| `signe_lunaire` | Signe lunaire | `.symbole` | `.signe` |
| `signe_chinois` | Signe chinois | `.emoji` | `.animal` (+ `.element` `.polarite` en sous-texte) |
| `animal_heure` | Animal de l'heure | `.emoji` | `.animal` (+ `.tranche` en sous-texte) |
| `chemin_de_vie` | Chemin de vie | — | valeur brute (grand chiffre) |
| `numerologie_nom` | Numérologie du nom | — | `Expression ‹.expression› · Âme ‹.ame› · Personnalité ‹.personnalite›` |
| `egyptien` | Divinité égyptienne | — | valeur brute (str) |
| `celte` | Arbre celte | — | valeur brute (str) |
| `amerindien` | Totem amérindien | — | valeur brute (str) |
| `maya` | Tzolkin maya | — | `.glyphe` (+ `Tonalité .tonalite` en sous-texte) |
| `pierre_du_mois` | Pierre du mois | — | valeur brute (str) |
| `nakshatra` | Nakshatra védique | — | `.nakshatra` (+ `Pada .pada` en sous-texte) |
| `vedique` | Rashi védique | `.symbole` | `.rashi` |

`theme_astral` est **exclu** de la grille (c'est le thème occidental complet,
déjà couvert par le poster « Carte du ciel » -- éviter la redondance).

Layout : grille responsive dans le SVG (calcul de colonnes selon le nombre de
cartes présentes, ex. 3 colonnes si ≤ 9 cartes, 4 sinon), chaque carte = un
rectangle à bord fin (`--border`), symbole en grand accent doré/violet,
libellé en majuscules discret (`--muted`), valeur en `--text`.

## Bloc identité (commun aux deux posters)

En tête du SVG (au-dessus de la roue ou de la grille) :

```
PRÉNOM NOM              ← grand, tracking large, majuscules, --text
── (fine règle) ──
12 janvier 1990 · 14h32 · Paris   ← petit, --muted
```

Si `_identite` manque un champ (heure ou ville non renseignées), ce segment
est simplement omis de la ligne (repli honnête, cohérent avec le style du
projet).

## Export PNG

Fonction unique `exportPosterPNG()`, appelée par `#btn-export-poster` :

1. Sérialise le `<svg id="poster-svg">` courant en chaîne (`XMLSerializer`).
2. Crée une `Image` à partir d'un blob `image/svg+xml`, l'attend en
   `onload`.
3. Dessine sur un `<canvas>` à haute résolution (largeur/hauteur ~3000px,
   ratio carré identique au viewBox).
4. Si la case **fond transparent** est décochée : remplit d'abord le canvas
   avec `--bg` (et le SVG garde son halo radial). Si cochée : canvas laissé
   transparent, et le halo radial de fond est omis du SVG exporté (cloné sans
   le `<circle>` de halo) pour ne pas laisser un dégradé flouté sur fond
   transparent.
5. `canvas.toBlob("image/png")` → lien de téléchargement, nom de fichier
   `carte-du-ciel-{prenom}.png` ou `traditions-natales-{prenom}.png` (slug du
   prénom, `portrait-cosmique` en repli si prénom absent).

## CSS

Nouvelles classes `.poster-*` dans le bloc `<style>` existant :
- `.poster-options` : barre de contrôles (fieldsets + case + bouton),
  cohérente avec `.theme-options` déjà en place.
- `.poster-cadre` : conteneur carré centré, `max-width` confortable pour
  l'écran (le SVG garde son ratio, l'export haute résolution est indépendant
  de la taille d'affichage grâce au viewBox).
- Pas de règle `@media print` spécifique : cet onglet est un aperçu écran +
  export PNG, pas un support d'impression navigateur (contrairement à
  l'onglet Carte astro qui garde son flux `@media print` existant).

## i18n

Tous les nouveaux libellés (bouton onglet, options, libellés de traditions)
ajoutés aux tables `I18N.fr` / `I18N.en` existantes, même pattern que le reste
(clé `data-t`).

## Accessibilité

`#poster-svg` garde `role="img"` avec un `aria-label` résumant le contenu
(ex. « Poster carte du ciel de {prénom}, mode épuré »), régénéré à chaque
rendu.

## Hors périmètre (explicitement exclu)

- Pas d'impression navigateur dédiée pour cet onglet (le PNG couvre le besoin
  d'export).
- Pas de nouveau palette/thème alternatif (violet/menthe conservé).
- Pas de mockup t-shirt/poster (image de produit) -- seul le visuel exporté
  est produit, pas sa mise en situation.
- Pas de nouvel endpoint serveur ni de modification du moteur Python.
