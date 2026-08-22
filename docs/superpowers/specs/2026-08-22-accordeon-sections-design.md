# Accordéon sur les titres de section

## Objectif

Réduire le scroll dans les deux onglets de résultats (« Portrait » et
« Carte astro complète ») en rendant chaque section repliable, avec un
bouton pour tout déplier/replier d'un coup. Feature 100 % frontend
(`static/index.html`), aucun changement backend.

## Contexte

Les deux onglets affichent chacun 6 sections (traditions/fondations/corps/
points/aspects/dominantes), chaque section étant introduite par un
`<h3 class="theme-section">`. Le contenu est généré en JS :

- **Onglet Portrait** (`#r-empreinte`) : `afficherResultat()` construit un
  fragment HTML plat par section via `EMPREINTE_SECTIONS.map(...)`
  (header + intro + liste d'`empreinte-item`), puis `.join("")`.
- **Onglet Carte astro complète** (`#tableaux-theme`) : `renderTableaux(tc)`
  pousse séquentiellement header/intro/contenu dans le conteneur `c` via
  `insertAdjacentHTML`/`appendChild` (cartes, tableaux, tableau d'aspects
  triable, cartes dominantes). Cette fonction est **rappelée en entier**
  quand l'utilisateur trie la colonne du tableau d'aspects (clic sur un
  `<th data-col>`, ligne ~1643).

Le pattern accordéon natif `<details>/<summary>` existe déjà dans le
fichier (`details.avance` pour « Options avancées » et « Approfondir avec
l'IA »), c'est le même mécanisme qu'on réutilise ici.

## Structure HTML

Chaque section devient :

```html
<details class="theme-section-acc" data-section="fondations" open>
  <summary class="theme-section">
    <span>Les fondations</span>
    <span class="glossaire-ic" ...>ℹ️</span>
    <span class="tsa-chevron">▶</span>
  </summary>
  <!-- section-intro + contenu existant, inchangés -->
</details>
```

- `data-section` reprend la `key` de `EMPREINTE_SECTIONS` (Portrait) ou une
  clé équivalente pour les 6 blocs de `renderTableaux` (`fondations`,
  `corps`, `points`, `maisons`, `aspects`, `dominantes`).
- Le chevron (`▶`) pivote à 90° en CSS quand `[open]`.
- Le triangle natif du `<summary>` est masqué (`list-style:none` +
  `::-webkit-details-marker { display:none }`).

## Bouton « Tout déplier / Tout replier »

Un bouton par onglet, inséré juste avant la première `<details>` de son
conteneur (`#r-empreinte`, `#tableaux-theme`) :

```html
<button type="button" class="btn ghost btn-toggle-tout"
  onclick="toggleToutesSections('r-empreinte')">Tout déplier</button>
```

- Libellé dynamique : s'il reste au moins une section fermée dans le
  conteneur → « Tout déplier » (clic = tout ouvrir) ; si tout est ouvert →
  « Tout replier » (clic = tout fermer).
- Le libellé se met à jour aussi quand l'utilisateur (re)plie une section
  individuellement (listener `toggle` délégué sur le conteneur).

Fonctions JS ajoutées (proches de `#r-empreinte`/`#tableaux-theme`
existants, pas de nouveau fichier) :

```js
function toggleToutesSections(containerId) {
  const details = document.querySelectorAll(`#${containerId} > details.theme-section-acc`);
  const tousOuverts = Array.from(details).every(d => d.open);
  details.forEach(d => d.open = !tousOuverts);
  majBoutonToggle(containerId);
}
function majBoutonToggle(containerId) {
  const t = I18N[LANGUE];
  const details = document.querySelectorAll(`#${containerId} > details.theme-section-acc`);
  const btn = document.getElementById(`btn-toggle-${containerId}`);
  if (!btn || !details.length) { if (btn) btn.style.display = "none"; return; }
  btn.style.display = "";
  const tousOuverts = Array.from(details).every(d => d.open);
  btn.textContent = tousOuverts ? t.b_replier_tout : t.b_deplier_tout;
}
```

Un listener `toggle` (capture, délégué au niveau du conteneur, posé une
fois à l'initialisation de la page — pas à chaque render) appelle
`majBoutonToggle(containerId)` à chaque ouverture/fermeture manuelle d'une
section.

Si un conteneur ne produit aucune section (ex. `#r-empreinte` vide avant
tout calcul), le bouton correspondant reste masqué (`display:none`).

## État par défaut

- **Nouveau résultat** (`afficherResultat()` appelé après un calcul, un
  changement de profil ou de langue) : seule la **première section
  effectivement rendue** est `open` (pour `#r-empreinte`, certaines
  sections comme « traditions » peuvent être absentes selon les données —
  c'est la première section non filtrée qui reçoit `open`, pas forcément
  l'index 0). Les 5 autres sont fermées.
- **Re-tri du tableau d'aspects** (`renderTableaux(tc)` rappelé depuis le
  handler de clic sur `<th data-col>`) : ce n'est pas un nouveau résultat,
  donc l'état ouvert/fermé de chaque section doit être **préservé**, pas
  réinitialisé. `renderTableaux` prend un second paramètre optionnel :

```js
function renderTableaux(tc, { reset = false } = {}) { ... }
```

  - `reset = true` : état par défaut (1ère section ouverte, reste fermé) —
    utilisé par `afficherResultat()`.
  - `reset = false` (par défaut, utilisé par le handler de tri) : avant de
    vider `c.innerHTML`, on lit l'état courant de chaque
    `details[data-section]` dans un objet `{ [key]: bool }`, puis on
    l'applique aux nouveaux `<details>` régénérés.

## CSS

```css
details.theme-section-acc { margin: 1.5rem 0 .5rem; }
details.theme-section-acc:first-child { margin-top: 0; }
details.theme-section-acc > summary.theme-section {
  font-size: 1.1rem; font-weight: 700; margin: 0 0 .5rem;
  padding-bottom: .3rem; border-bottom: 2px solid var(--accent);
  display: flex; align-items: center; gap: .4rem;
  cursor: pointer; list-style: none;
}
details.theme-section-acc > summary.theme-section::-webkit-details-marker { display: none; }
details.theme-section-acc > summary.theme-section .tsa-chevron {
  margin-left: auto; font-size: .8rem; color: var(--muted);
  transition: transform .15s;
}
details.theme-section-acc[open] > summary.theme-section .tsa-chevron { transform: rotate(90deg); }

.btn-toggle-tout { margin: 0 0 1rem; }

@media print {
  /* Un export/impression doit toujours montrer tout le contenu,
     indépendamment de l'état plié/déplié à l'écran. */
  details.theme-section-acc > *:not(summary) { display: block !important; }
  .btn-toggle-tout { display: none !important; }
}
```

`.theme-section` garde exactement le même rendu visuel qu'aujourd'hui
(taille, bordure, position de l'icône glossaire) — seul le conteneur
change (`<h3>` → `<summary>` dans un `<details>`).

## Export HTML / impression

- `telechargerHTML()` sérialise `document.getElementById("resultat").outerHTML`
  tel quel : l'état plié/déplié visible à l'écran au moment du clic est
  donc reproduit dans le fichier exporté (comportement WYSIWYG, cohérent
  avec le reste de la page). Le fichier exporté reste interactif (les
  `<details>` sont natifs, aucun JS supplémentaire requis pour les
  rouvrir).
- `window.print()` et l'impression du fichier exporté : la règle
  `@media print` ci-dessus force l'affichage de tout le contenu, quel que
  soit l'état à l'écran, pour ne jamais perdre d'information à
  l'impression/PDF.

## i18n

Nouvelles clés FR/EN (ajoutées dans les deux blocs de `I18N`, à côté de
`t_portrait`/`t_theme`) :

| clé | FR | EN |
|-----|----|----|
| `b_deplier_tout` | Tout déplier | Expand all |
| `b_replier_tout` | Tout replier | Collapse all |

## Périmètre exclus

- Pas de persistance de l'état plié/déplié entre deux visites (localStorage) :
  chaque nouveau calcul repart de l'état par défaut (1ère section ouverte).
- Les blocs `details.avance` existants (« Options avancées », « Approfondir
  avec l'IA ») ne sont pas touchés : ils gardent leur comportement actuel.
- Le tableau de légende PDF (`#r-legende`, visible seulement à
  l'impression) n'est pas concerné par l'accordéon.

## Tests

Pas de backend touché. Vérification manuelle :

1. Calculer un portrait → onglet Portrait : seule la 1ère section
   (Traditions natales) est ouverte, les 5 autres fermées.
2. Cliquer « Tout déplier » → les 6 sections s'ouvrent, le bouton devient
   « Tout replier ».
3. Refermer une section manuellement → le bouton repasse à « Tout déplier ».
4. Onglet Carte astro complète : même comportement par défaut/bouton.
5. Trier une colonne du tableau d'aspects → l'état plié/déplié des autres
   sections (ex. Fondations repliée manuellement) est conservé après le
   re-tri.
6. Changer de profil / relancer un calcul → l'état revient au défaut
   (1ère section ouverte).
7. Replier 2-3 sections puis « Télécharger en HTML » → le fichier exporté
   reflète le même état plié/déplié, et reste cliquable pour les rouvrir.
8. Replier des sections puis Ctrl+P / Imprimer → toutes les sections
   apparaissent développées dans l'aperçu d'impression.
9. Basculer FR/EN → libellés du bouton traduits.
