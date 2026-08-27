# Onglet « Poster » — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un 3ᵉ onglet « Poster » qui produit un rendu visuel raffiné (roue zodiacale ou grille des traditions natales) exportable en PNG haute résolution, pensé pour servir d'exemple à un produit dérivé imprimé (t-shirt, poster).

**Architecture:** Feature 100 % frontend dans le fichier unique `static/index.html` (CSS + JS vanilla embarqués). Deux nouvelles fonctions de rendu SVG (`renderPosterCiel`, `renderPosterTraditions`) réutilisent les données déjà chargées côté client (`_THEME_CACHE`, `DERNIER_RESULTAT.traditions`, `DERNIER_RESULTAT._identite`) — aucun nouvel appel réseau. Export PNG via sérialisation SVG → `<canvas>` → `toBlob`.

**Tech Stack:** HTML/CSS/JS vanilla (pas de framework), FastAPI (`main.py`) sert `static/index.html` tel quel.

**Spec de référence :** `docs/superpowers/specs/2026-08-27-onglet-poster-design.md`

## Global Constraints

- Un seul fichier modifié : `static/index.html`. Ne pas créer de nouveau fichier, ne pas ajouter de dépendance (pas de bibliothèque de canvas/SVG externe).
- Style de code existant : noms de variables/fonctions en français, indentation 2 espaces.
- i18n : toute nouvelle chaîne visible doit avoir une entrée FR **et** EN dans `I18N` (blocs `fr: {...}` / `en: {...}`).
- `data-t` doit toujours cibler un élément dont **tout** le contenu texte est traduit (le handler fait `el.textContent = ...`, ce qui écraserait un `<input>` enfant) — placer `data-t` sur un `<span>` dédié quand le libellé cohabite avec un `<input>`, jamais sur le `<label>` englobant.
- Aucun nouvel endpoint serveur, aucune modification de `main.py` ni du dossier `engine/`.
- Palette conservée : `--bg`, `--panel`, `--panel2`, `--border`, `--text`, `--muted`, `--accent`, `--accent2` existants, pas de nouvelle palette.
- Pas de framework de test JS dans ce repo (CI = `pytest engine` uniquement). La vérification de ce plan se fait par navigation réelle via le serveur de dev, avec l'outil MCP Playwright (`mcp__playwright__browser_*`).
- Serveur de dev : `uvicorn main:app --reload --port 8410` depuis la racine du dépôt. URL : `http://localhost:8410`.
- Date de naissance de test utilisée dans toutes les vérifications : `1990-05-15`, heure `14:30`, ville `Paris` (pour obtenir un `_THEME_CACHE` complet et un `traditions` riche — signe lunaire/nakshatra/védique nécessitent heure+lieu).

---

## File Structure

- **Modify** `static/index.html` uniquement :
  - CSS : nouveau bloc `/* ── Onglet « Poster » ─── */` (classes `.poster-*`), + extension des 2 blocs `@media print` et du bloc `exportExtra` déjà existants pour masquer `#onglet-poster`.
  - HTML : 3ᵉ bouton d'onglet + `<section id="onglet-poster">`.
  - i18n : nouvelles clés dans `I18N.fr` / `I18N.en`.
  - JS : `TRADITIONS_POSTER_CHAMPS` (const), `posterBlocIdentite`, `renderPosterCiel`, `renderPosterTraditions`, `renderPoster` (dispatcher, construit puis étendu sur 3 tâches), `slugPourFichier`, `exportPosterPNG` ; nouveaux appels à `renderPoster()` dans `viderTheme()`, `calculerPortrait()` et `rechargerTheme()`.

---

## Task 1: Scaffold de l'onglet (tab, HTML, CSS, i18n, dispatcher vide)

**Files:**
- Modify: `static/index.html:388-389` (boutons d'onglets)
- Modify: `static/index.html:435` (insertion de la nouvelle `<section>`)
- Modify: `static/index.html:259-268` (bloc `@media print` existant)
- Modify: `static/index.html:1275-1279` (bloc `exportExtra` de `telechargerHTML`)
- Modify: `static/index.html` (blocs `I18N.fr` / `I18N.en`)
- Modify: `static/index.html:1376-1384` (`viderTheme`)
- Modify: `static/index.html:1431-1433` (listeners d'options, juste après ceux de l'onglet Carte astro)

**Interfaces:**
- Consumes: `DERNIER_RESULTAT`, `_THEME_CACHE` (déjà déclarés globalement), `I18N`, `LANGUE`.
- Produces: `renderPoster()` — dispatcher appelé partout où `_THEME_CACHE`/`DERNIER_RESULTAT` changent ; dans cette tâche il gère seulement l'état vide/non-vide (`#poster-vide` vs `#poster-cadre`). Les Tasks 2 et 3 étendent son corps sans changer sa signature (aucun argument). Éléments DOM produits et réutilisés ensuite : `#onglet-poster`, `#poster-svg`, `#poster-cadre`, `#poster-vide`, `#poster-fond-transparent`, `#btn-export-poster`, `input[name="poster-type"]`, `input[name="poster-densite"]`, `#poster-densite-fieldset`.

- [ ] **Step 1: Démarrer le serveur de dev et observer l'état actuel (2 onglets)**

Run: `uvicorn main:app --reload --port 8410` (laisser tourner en arrière-plan)

Avec Playwright :
- `mcp__playwright__browser_navigate` → `http://localhost:8410`
- `mcp__playwright__browser_snapshot`

Expected : formulaire visible, `#resultat` caché (aucun calcul encore fait). Pas d'onglet « Poster ».

- [ ] **Step 2: Ajouter le 3ᵉ bouton d'onglet**

Remplacer dans `static/index.html` (lignes 388-389) :

```html
<button class="onglet onglet-actif" data-onglet="portrait" data-t="t_portrait">Portrait</button>
<button class="onglet" data-onglet="theme" data-t="t_theme">Carte astro complète</button>
```

par :

```html
<button class="onglet onglet-actif" data-onglet="portrait" data-t="t_portrait">Portrait</button>
<button class="onglet" data-onglet="theme" data-t="t_theme">Carte astro complète</button>
<button class="onglet" data-onglet="poster" data-t="t_poster">Poster</button>
```

- [ ] **Step 3: Ajouter la section `#onglet-poster`**

Insérer dans `static/index.html`, juste après la ligne 435 (`    </section>` qui ferme `#onglet-theme`), avant `<section id="r-legende" class="legende"></section>` :

```html

    <section id="onglet-poster" class="onglet-contenu" hidden>
      <div class="poster-options">
        <fieldset>
          <legend data-t="l_poster_type">Type de poster</legend>
          <label><input type="radio" name="poster-type" value="ciel" checked> <span data-t="o_poster_ciel">Carte du ciel</span></label>
          <label><input type="radio" name="poster-type" value="traditions"> <span data-t="o_poster_traditions">Traditions natales</span></label>
        </fieldset>
        <fieldset id="poster-densite-fieldset">
          <legend data-t="l_poster_densite">Densité</legend>
          <label><input type="radio" name="poster-densite" value="epure" checked> <span data-t="o_poster_epure">Épuré</span></label>
          <label><input type="radio" name="poster-densite" value="complet"> <span data-t="o_poster_complet">Complet</span></label>
        </fieldset>
        <label class="poster-transparent">
          <input type="checkbox" id="poster-fond-transparent">
          <span data-t="l_poster_transparent">Fond transparent (t-shirt)</span>
        </label>
        <button type="button" class="btn" id="btn-export-poster" data-t="b_export_poster">⬇️ Télécharger en PNG</button>
      </div>
      <p id="poster-vide" class="sous poster-vide" data-t="poster_vide">Calcule d'abord un portrait pour voir le poster.</p>
      <div class="poster-cadre" id="poster-cadre" style="display:none">
        <svg id="poster-svg" viewBox="-260 -260 520 520" role="img" aria-label="Poster"></svg>
      </div>
    </section>
```

- [ ] **Step 4: Ajouter le CSS du poster + masquer l'onglet à l'impression et à l'export HTML**

Ajouter, juste après le bloc CSS `.dominante-barre .dv { ... }` (ligne 214, juste avant `.fil-rouge`) :

```css

  /* ── Onglet « Poster » ────────────────────────────────────────────── */
  .poster-options { display: flex; gap: 1.5rem; flex-wrap: wrap; align-items: center; margin: 0 0 1.2rem; }
  .poster-options fieldset { border: 1px solid var(--border); border-radius: 10px; padding: .6rem 1rem; background: var(--panel2); }
  .poster-options legend { font-size: .8rem; color: var(--accent2); padding: 0 .4rem; }
  .poster-options label { display: inline-flex; align-items: center; gap: .3rem; margin: .2rem .6rem .2rem 0;
    font-size: .88rem; color: var(--text); cursor: pointer; }
  .poster-options input[type="radio"], .poster-options input[type="checkbox"] { accent-color: var(--accent); width: auto; }
  .poster-transparent { display: inline-flex; align-items: center; gap: .4rem; font-size: .88rem; color: var(--text); cursor: pointer; }
  .poster-vide { text-align: center; }
  .poster-cadre { display: flex; justify-content: center; }
  #poster-svg { width: 100%; max-width: 560px; height: auto; background: var(--bg); border-radius: 12px;
    border: 1px solid var(--border); }
  #poster-svg text { font-family: -apple-system, "Segoe UI", sans-serif; fill: var(--text); pointer-events: none; }
```

Remplacer dans `static/index.html` (lignes 259-268) :

```css
  @media print {
    .resultats-onglets, .theme-options, #roue-svg, .theme-legend, .theme-caveat { display: none !important; }
    .onglet-contenu { display: block !important; }
    .theme-layout { display: block !important; }
    .theme-roue { display: none !important; }
    .theme-tableaux table { font-size: 9pt; }
    .theme-tableaux th { cursor: default; }
    #resultat { display: block !important; }
    .btn-toggle-tout { display: none !important; }
  }
```

par :

```css
  @media print {
    .resultats-onglets, .theme-options, #roue-svg, .theme-legend, .theme-caveat { display: none !important; }
    .onglet-contenu { display: block !important; }
    .theme-layout { display: block !important; }
    .theme-roue { display: none !important; }
    .theme-tableaux table { font-size: 9pt; }
    .theme-tableaux th { cursor: default; }
    #resultat { display: block !important; }
    .btn-toggle-tout { display: none !important; }
    #onglet-poster { display: none !important; }
  }
```

- [ ] **Step 5: Masquer aussi l'onglet Poster dans le HTML auto-suffisant exporté**

Remplacer dans `static/index.html` (lignes 1275-1279) :

```js
  const exportExtra = `<style>
    .onglet-contenu { display: block !important; }
    .resultats-onglets { display: none !important; }
    .btn-toggle-tout { display: none !important; }
  </style>
```

par :

```js
  const exportExtra = `<style>
    .onglet-contenu { display: block !important; }
    .resultats-onglets { display: none !important; }
    .btn-toggle-tout { display: none !important; }
    #onglet-poster { display: none !important; }
  </style>
```

- [ ] **Step 6: Ajouter les clés i18n**

Dans le bloc `fr:` de `I18N`, remplacer (ligne ~507) :

```js
    b_deplier_tout: "Tout déplier", b_replier_tout: "Tout replier",
```

par :

```js
    b_deplier_tout: "Tout déplier", b_replier_tout: "Tout replier",
    t_poster: "Poster",
    l_poster_type: "Type de poster", o_poster_ciel: "Carte du ciel", o_poster_traditions: "Traditions natales",
    l_poster_densite: "Densité", o_poster_epure: "Épuré", o_poster_complet: "Complet",
    l_poster_transparent: "Fond transparent (t-shirt)",
    b_export_poster: "⬇️ Télécharger en PNG",
    poster_vide: "Calcule d'abord un portrait pour voir le poster.",
```

Dans le bloc `en:` de `I18N`, remplacer (ligne ~584) :

```js
    b_deplier_tout: "Expand all", b_replier_tout: "Collapse all",
```

par :

```js
    b_deplier_tout: "Expand all", b_replier_tout: "Collapse all",
    t_poster: "Poster",
    l_poster_type: "Poster type", o_poster_ciel: "Sky chart", o_poster_traditions: "Natal traditions",
    l_poster_densite: "Density", o_poster_epure: "Minimal", o_poster_complet: "Full",
    l_poster_transparent: "Transparent background (t-shirt)",
    b_export_poster: "⬇️ Download as PNG",
    poster_vide: "Calculate a portrait first to see the poster.",
```

- [ ] **Step 7: Ajouter le dispatcher `renderPoster()` et l'appeler depuis `viderTheme()`**

Remplacer dans `static/index.html` (lignes 1376-1384) :

```js
function viderTheme() {
  _THEME_CACHE = null;
  const svg = document.getElementById("roue-svg");
  if (svg) svg.innerHTML = "";
  const leg = document.getElementById("theme-legend");
  if (leg) leg.innerHTML = "";
  const tb = document.getElementById("tableaux-theme");
  if (tb) tb.innerHTML = `<p class="sous" style="margin:.4rem 0">${I18N[LANGUE].theme_vide}</p>`;
}
```

par :

```js
function viderTheme() {
  _THEME_CACHE = null;
  const svg = document.getElementById("roue-svg");
  if (svg) svg.innerHTML = "";
  const leg = document.getElementById("theme-legend");
  if (leg) leg.innerHTML = "";
  const tb = document.getElementById("tableaux-theme");
  if (tb) tb.innerHTML = `<p class="sous" style="margin:.4rem 0">${I18N[LANGUE].theme_vide}</p>`;
  renderPoster();
}

// ── Onglet « Poster » ─────────────────────────────────────────────
function renderPoster() {
  const vide = document.getElementById("poster-vide");
  const cadre = document.getElementById("poster-cadre");
  if (!DERNIER_RESULTAT || !_THEME_CACHE) {
    vide.style.display = "";
    cadre.style.display = "none";
    return;
  }
  vide.style.display = "none";
  cadre.style.display = "";
}
```

- [ ] **Step 8: Appeler `renderPoster()` après un nouveau calcul et après un rechargement de thème**

Dans `calculerPortrait()`, remplacer (bloc déjà présent) :

```js
    _THEME_CACHE = d.theme_complet || null;
    if (_THEME_CACHE) {
      _ASPECT_FILTRE = "tous";
      _ASPECT_TRI = { col: "exactitude", sens: -1 };
      renderRoue(_THEME_CACHE);
      renderTableaux(_THEME_CACHE, { reset: true });
    } else {
      viderTheme();
    }
```

par :

```js
    _THEME_CACHE = d.theme_complet || null;
    if (_THEME_CACHE) {
      _ASPECT_FILTRE = "tous";
      _ASPECT_TRI = { col: "exactitude", sens: -1 };
      renderRoue(_THEME_CACHE);
      renderTableaux(_THEME_CACHE, { reset: true });
      renderPoster();
    } else {
      viderTheme();
    }
```

Dans `rechargerTheme()`, remplacer :

```js
    _THEME_CACHE = await r.json();
    _ASPECT_FILTRE = "tous";
    renderRoue(_THEME_CACHE);
    renderTableaux(_THEME_CACHE);
```

par :

```js
    _THEME_CACHE = await r.json();
    _ASPECT_FILTRE = "tous";
    renderRoue(_THEME_CACHE);
    renderTableaux(_THEME_CACHE);
    renderPoster();
```

- [ ] **Step 9: Ajouter les listeners des options du poster**

Juste après (dans `static/index.html`) :

```js
document.querySelectorAll("input[name='systeme-maisons'], input[name='methode-dominantes']").forEach(input => {
  input.addEventListener("change", rechargerTheme);
});
```

ajouter :

```js
document.querySelectorAll("input[name='poster-type'], input[name='poster-densite']").forEach(input => {
  input.addEventListener("change", () => {
    const type = document.querySelector("input[name='poster-type']:checked").value;
    document.getElementById("poster-densite-fieldset").style.display = type === "ciel" ? "" : "none";
    renderPoster();
  });
});
```

- [ ] **Step 10: Vérifier le scaffold dans le navigateur**

- `mcp__playwright__browser_navigate` → `http://localhost:8410`
- `mcp__playwright__browser_click` sur l'onglet « Poster » → doit fonctionner même sans calcul (juste rien à cliquer avant, `#resultat` étant caché — ignorer, ce n'est visible qu'après calcul)
- `mcp__playwright__browser_type` sur `#date_naissance` → `1990-05-15`
- `mcp__playwright__browser_click` sur `✨ Calculer mon portrait`
- `mcp__playwright__browser_click` sur l'onglet `Poster`
- `mcp__playwright__browser_evaluate` :
  ```js
  () => {
    const vide = document.getElementById("poster-vide");
    const cadre = document.getElementById("poster-cadre");
    return { videVisible: vide.style.display !== "none", cadreVisible: cadre.style.display !== "none" };
  }
  ```

Expected : `videVisible: true`, `cadreVisible: false` (date seule, sans heure/lieu → pas de `_THEME_CACHE`, cohérent avec le comportement existant de l'onglet Carte astro).

- `mcp__playwright__browser_type` sur `#heure_naissance` → `14:30`
- `mcp__playwright__browser_type` sur `#ville` → `Paris`
- `mcp__playwright__browser_click` sur le bouton `📍 Localiser` (résout la ville en coordonnées, nécessaire pour `_THEME_CACHE`)
- `mcp__playwright__browser_click` sur `✨ Calculer mon portrait`
- `mcp__playwright__browser_click` sur l'onglet `Poster`
- Ré-évaluer le même script.

Expected : `videVisible: false`, `cadreVisible: true`.

- [ ] **Step 11: Vérifier la traduction EN du nouvel onglet**

- `mcp__playwright__browser_click` sur le bouton `EN`
- `mcp__playwright__browser_evaluate` : `document.querySelector('[data-onglet="poster"]').textContent` doit valoir `"Poster"` (identique FR/EN, mais vérifie que la clé `t_poster` existe bien et ne casse rien).
- `mcp__playwright__browser_evaluate` : `document.querySelector('label.poster-transparent span').textContent` doit valoir `"Transparent background (t-shirt)"`.

- [ ] **Step 12: Commit**

```bash
git add static/index.html
git commit -m "feat: scaffold de l'onglet Poster (tab, options, état vide)"
```

---

## Task 2: Poster « Carte du ciel » (roue épurée/complète + bloc identité)

**Files:**
- Modify: `static/index.html` (nouveau bloc CSS, juste après le bloc `.poster-*` du Task 1)
- Modify: `static/index.html` (nouvelles fonctions JS, insérées juste avant `renderPoster()` du Task 1)
- Modify: `static/index.html` (corps de `renderPoster()`, Task 1)

**Interfaces:**
- Consumes: `elNS(ns, tag, attrs, text)`, `lonToXY(lon, radius, ascOffset)`, `svgArc(x1,y1,r,x2,y2,sweep)`, `SYMBOLES_ZODIAQUE`, `SYMBOLES_POINTS`, `COULEURS_ASPECTS`, `normalizePE(nom)`, `normalizeFond(nom)` (tous déjà définis, inchangés). `_THEME_CACHE` (structure `theme_complet`, voir `docs/superpowers/specs/2026-08-21-carte-astrologique-complete-design.md`). `DERNIER_RESULTAT._identite` = `{prenoms, nom, date_naissance, heure_naissance, ville}` (Task 1 amont).
- Produces: `posterBlocIdentite(svg, ns, identite, yStart)` — réutilisée telle quelle par le Task 3. `renderPosterCiel(tc, identite, densite)` où `densite` vaut `"epure"` ou `"complet"`.

- [ ] **Step 1: Ajouter le CSS de la roue poster**

Ajouter, juste après le CSS du Task 1 (après la règle `#poster-svg text { ... }`) :

```css
  #poster-svg .poster-zodiac-sector { fill: var(--panel); stroke: var(--border); stroke-width: .4; }
  #poster-svg .poster-zodiac-sector.alt { fill: #1a1f38; }
  #poster-svg .poster-zodiac-sym { font-size: 15px; fill: var(--accent2); }
  #poster-svg .poster-ring { fill: none; stroke: var(--border); stroke-width: .4; }
  #poster-svg .poster-house-line { stroke: var(--border); stroke-width: .3; }
  #poster-svg .poster-angle-line { stroke: var(--accent); stroke-width: .9; }
  #poster-svg .poster-house-num { font-size: 9px; fill: var(--muted); }
  #poster-svg .poster-planet-glyph { font-size: 15px; fill: var(--text); }
  #poster-svg .poster-aspect-line { stroke-linecap: round; }
  #poster-svg .poster-nom { font-size: 20px; font-weight: 700; letter-spacing: .12em; fill: var(--text); }
  #poster-svg .poster-regle { stroke: var(--border); stroke-width: 1; }
  #poster-svg .poster-sous { font-size: 11px; fill: var(--muted); letter-spacing: .03em; }
```

- [ ] **Step 2: Ajouter `posterBlocIdentite` et `renderPosterCiel`**

Insérer dans `static/index.html`, juste avant la fonction `renderPoster()` ajoutée au Task 1 (avant le commentaire `// ── Onglet « Poster » ───...`) :

```js
function posterBlocIdentite(svg, ns, identite, yStart) {
  const nomComplet = [identite.prenoms, identite.nom].map(s => (s || "").trim()).filter(Boolean).join(" ").toUpperCase();
  let y = yStart;
  if (nomComplet) {
    svg.appendChild(elNS(ns, "text", { class: "poster-nom", x: 0, y, "text-anchor": "middle" }, nomComplet));
    y += 24;
  }
  const parts = [];
  if (identite.date_naissance) {
    const d = new Date(identite.date_naissance + "T00:00:00");
    if (!isNaN(d)) parts.push(d.toLocaleDateString(LANGUE === "fr" ? "fr-FR" : "en-US", { day: "numeric", month: "long", year: "numeric" }));
  }
  if (identite.heure_naissance) parts.push(identite.heure_naissance);
  if (identite.ville) parts.push(identite.ville);
  if (parts.length) {
    svg.appendChild(elNS(ns, "line", { class: "poster-regle", x1: -50, y1: y, x2: 50, y2: y }));
    svg.appendChild(elNS(ns, "text", { class: "poster-sous", x: 0, y: y + 20, "text-anchor": "middle" }, parts.join(" · ")));
  }
}

function renderPosterCiel(tc, identite, densite) {
  const svg = document.getElementById("poster-svg");
  svg.innerHTML = "";
  const ns = "http://www.w3.org/2000/svg";
  svg.setAttribute("aria-label", `Poster carte du ciel de ${(identite.prenoms || "").trim() || "—"}, mode ${densite}`);

  const defs = elNS(ns, "defs");
  const grad = elNS(ns, "radialGradient", { id: "poster-halo", cx: "50%", cy: "50%", r: "50%" });
  grad.appendChild(elNS(ns, "stop", { offset: "0%", "stop-color": "#3a2a6b", "stop-opacity": "0.55" }));
  grad.appendChild(elNS(ns, "stop", { offset: "100%", "stop-color": "#3a2a6b", "stop-opacity": "0" }));
  defs.appendChild(grad);
  svg.appendChild(defs);

  const complet = densite === "complet";
  const R_EXT = 205, R_ZOD_INT = 178;
  const R_MAI_INT = complet ? 150 : null;
  const R_PLANETE = complet ? 100 : 130;
  const R_ASPECT = complet ? 108 : 120;

  let ascOffset = 0;
  if (tc.fondations && tc.fondations.ascendant) ascOffset = tc.fondations.ascendant.longitude || 0;

  const g = elNS(ns, "g", { class: "poster-roue-groupe", transform: "translate(0,-30)" });
  svg.appendChild(g);
  g.appendChild(elNS(ns, "circle", { class: "poster-halo", cx: 0, cy: 0, r: R_EXT + 30, fill: "url(#poster-halo)" }));

  for (let i = 0; i < 12; i++) {
    const start = i * 30, end = (i + 1) * 30;
    const [x1, y1] = lonToXY(start, R_EXT, ascOffset);
    const [x2, y2] = lonToXY(end, R_EXT, ascOffset);
    const [xi1, yi1] = lonToXY(start, R_ZOD_INT, ascOffset);
    const [xi2, yi2] = lonToXY(end, R_ZOD_INT, ascOffset);
    const d = `M ${x1.toFixed(2)} ${y1.toFixed(2)} ${svgArc(x1, y1, R_EXT, x2, y2, 0)} L ${xi2.toFixed(2)} ${yi2.toFixed(2)} ${svgArc(xi2, yi2, R_ZOD_INT, xi1, yi1, 1)} Z`;
    g.appendChild(elNS(ns, "path", { class: "poster-zodiac-sector" + (i % 2 ? " alt" : ""), d }));
    const mid = start + 15;
    const [sx, sy] = lonToXY(mid, (R_EXT + R_ZOD_INT) / 2, ascOffset);
    g.appendChild(elNS(ns, "text", { class: "poster-zodiac-sym", x: sx.toFixed(2), y: sy.toFixed(2), "text-anchor": "middle", "dominant-baseline": "central" }, SYMBOLES_ZODIAQUE[i]));
  }

  g.appendChild(elNS(ns, "circle", { class: "poster-ring", cx: 0, cy: 0, r: R_ZOD_INT }));

  if (complet) {
    g.appendChild(elNS(ns, "circle", { class: "poster-ring", cx: 0, cy: 0, r: R_MAI_INT }));
    for (const m of (tc.maisons || [])) {
      const lon = m.longitude_cuspe != null ? m.longitude_cuspe : m.cuspe;
      const [mx1, my1] = lonToXY(lon, R_ZOD_INT, ascOffset);
      const [mx2, my2] = lonToXY(lon, R_MAI_INT, ascOffset);
      const isAngle = [1, 4, 7, 10].includes(m.maison);
      g.appendChild(elNS(ns, "line", { class: isAngle ? "poster-angle-line" : "poster-house-line", x1: mx1.toFixed(2), y1: my1.toFixed(2), x2: mx2.toFixed(2), y2: my2.toFixed(2) }));
      const [nx, ny] = lonToXY(lon + (m.maison <= 6 ? 6 : -6), (R_ZOD_INT + R_MAI_INT) / 2, ascOffset);
      g.appendChild(elNS(ns, "text", { class: "poster-house-num", x: nx.toFixed(2), y: ny.toFixed(2), "text-anchor": "middle", "dominant-baseline": "central" }, String(m.maison)));
    }
  }

  g.appendChild(elNS(ns, "circle", { class: "poster-ring", cx: 0, cy: 0, r: R_PLANETE }));

  const aspectsSrc = (tc.aspects || []).filter(a => complet || a.type === "majeur");
  const posForAspect = (nom) => {
    const p = (tc.dix_corps || {})[nom] || (tc.points_evolutifs || {})[normalizePE(nom)] || (tc.fondations || {})[normalizeFond(nom)];
    return p ? p.longitude : null;
  };
  for (const a of aspectsSrc) {
    const la = posForAspect(a.point_a), lb = posForAspect(a.point_b);
    if (la == null || lb == null) continue;
    const [ax1, ay1] = lonToXY(la, R_ASPECT, ascOffset);
    const [ax2, ay2] = lonToXY(lb, R_ASPECT, ascOffset);
    const couleur = COULEURS_ASPECTS[a.aspect] || "#94a3b8";
    const epaisseur = Math.max(0.5, 1.6 * (a.exactitude || 0));
    g.appendChild(elNS(ns, "line", { class: "poster-aspect-line", x1: ax1.toFixed(2), y1: ay1.toFixed(2), x2: ax2.toFixed(2), y2: ay2.toFixed(2), stroke: couleur, "stroke-width": epaisseur.toFixed(2), opacity: (0.3 + 0.55 * (a.exactitude || 0)).toFixed(2) }));
  }

  const planetes = [];
  for (const [nom, info] of Object.entries(tc.dix_corps || {})) planetes.push({ nom, info });
  for (const [nom, info] of Object.entries(tc.points_evolutifs || {})) planetes.push({ nom: info.corps || nom, info });
  if (complet) {
    for (const [nom, info] of Object.entries(tc.fondations || {})) {
      if (["ascendant", "descendant", "milieu_du_ciel", "fond_du_ciel"].includes(nom)) {
        planetes.push({ nom: nom === "milieu_du_ciel" ? "Milieu du Ciel" : nom === "fond_du_ciel" ? "Fond du Ciel" : nom.charAt(0).toUpperCase() + nom.slice(1), info });
      }
    }
  }
  for (const p of planetes) {
    if (p.info.longitude == null) continue;
    const [px, py] = lonToXY(p.info.longitude, R_PLANETE - 20, ascOffset);
    const glyph = SYMBOLES_POINTS[p.nom] || p.nom.slice(0, 3);
    g.appendChild(elNS(ns, "text", { class: "poster-planet-glyph", x: px.toFixed(2), y: py.toFixed(2), "text-anchor": "middle", "dominant-baseline": "central" }, glyph));
  }

  posterBlocIdentite(svg, ns, identite, 205);
}
```

Note : en mode `epure`, `planetes` ne contient **que** les 10 corps + points évolutifs (le bloc `if (complet)` qui ajoute Ascendant/Descendant/MC/IC est sauté) — conforme à la spec (« aucun numéro de maison, aucun degré » et composition la plus nette possible, sans les angles qui n'ont de sens qu'avec les maisons).

- [ ] **Step 3: Brancher le type "ciel" dans le dispatcher `renderPoster()`**

Remplacer dans `static/index.html` (corps ajouté au Task 1, Step 7) :

```js
function renderPoster() {
  const vide = document.getElementById("poster-vide");
  const cadre = document.getElementById("poster-cadre");
  if (!DERNIER_RESULTAT || !_THEME_CACHE) {
    vide.style.display = "";
    cadre.style.display = "none";
    return;
  }
  vide.style.display = "none";
  cadre.style.display = "";
}
```

par :

```js
function renderPoster() {
  const vide = document.getElementById("poster-vide");
  const cadre = document.getElementById("poster-cadre");
  if (!DERNIER_RESULTAT || !_THEME_CACHE) {
    vide.style.display = "";
    cadre.style.display = "none";
    return;
  }
  vide.style.display = "none";
  cadre.style.display = "";
  const type = document.querySelector("input[name='poster-type']:checked").value;
  const identite = DERNIER_RESULTAT._identite || {};
  if (type === "ciel") {
    const densite = document.querySelector("input[name='poster-densite']:checked").value;
    renderPosterCiel(_THEME_CACHE, identite, densite);
  }
}
```

- [ ] **Step 4: Vérifier le poster « Carte du ciel » en mode épuré**

- `mcp__playwright__browser_navigate` → `http://localhost:8410`
- `mcp__playwright__browser_type` sur `#date_naissance` → `1990-05-15`
- `mcp__playwright__browser_type` sur `#heure_naissance` → `14:30`
- `mcp__playwright__browser_type` sur `#ville` → `Paris`
- `mcp__playwright__browser_click` sur `📍 Localiser`
- `mcp__playwright__browser_click` sur `✨ Calculer mon portrait`
- `mcp__playwright__browser_click` sur l'onglet `Poster`
- `mcp__playwright__browser_evaluate` :
  ```js
  () => {
    const svg = document.getElementById("poster-svg");
    return {
      secteurs: svg.querySelectorAll(".poster-zodiac-sector").length,
      glyphes: svg.querySelectorAll(".poster-planet-glyph").length,
      maisons: svg.querySelectorAll(".poster-house-line").length,
      nom: (svg.querySelector(".poster-nom") || {}).textContent,
      ariaLabel: svg.getAttribute("aria-label"),
    };
  }
  ```

Expected : `secteurs: 12`, `glyphes: 14` (10 corps + Nœud Nord/Sud/Chiron/Lilith), `maisons: 0` (mode épuré par défaut), `nom` non vide (majuscules), `ariaLabel` contient `"epure"`.

- `mcp__playwright__browser_take_screenshot` sur `#poster-svg` pour vérification visuelle (composition équilibrée, pas de chevauchement grossier de texte).

- [ ] **Step 5: Vérifier le mode « Complet »**

- `mcp__playwright__browser_click` sur le radio `Complet` (poster-densite)
- Ré-exécuter le script d'évaluation du Step 4.

Expected : `maisons: 12`, `glyphes: 18` (14 + Ascendant/Descendant/MC/IC), `ariaLabel` contient `"complet"`.

- [ ] **Step 6: Commit**

```bash
git add static/index.html
git commit -m "feat: poster carte du ciel (épuré/complet)"
```

---

## Task 3: Poster « Traditions natales »

**Files:**
- Modify: `static/index.html` (CSS grille, après le CSS du Task 2)
- Modify: `static/index.html` (blocs `I18N.fr` / `I18N.en`)
- Modify: `static/index.html` (nouvelle const `TRADITIONS_POSTER_CHAMPS` + fonction `renderPosterTraditions`)
- Modify: `static/index.html` (corps de `renderPoster()`)

**Interfaces:**
- Consumes: `elNS`, `posterBlocIdentite` (Task 2), `DERNIER_RESULTAT.traditions` (dict brut de `engine/traditions.py:calculer()`, voir mapping ci-dessous).
- Produces: `TRADITIONS_POSTER_CHAMPS` (array de descripteurs), `renderPosterTraditions(traditions, identite)`.

- [ ] **Step 1: Ajouter le CSS de la grille**

Ajouter, juste après le CSS du Task 2 :

```css
  #poster-svg .poster-trad-rect { fill: var(--panel2); stroke: var(--border); stroke-width: 1; }
  #poster-svg .poster-trad-sym { font-size: 20px; fill: var(--accent2); }
  #poster-svg .poster-trad-label { font-size: 8px; fill: var(--muted); letter-spacing: .04em; text-transform: uppercase; }
  #poster-svg .poster-trad-valeur { font-size: 12px; font-weight: 700; fill: var(--text); }
  #poster-svg .poster-trad-sous { font-size: 8px; fill: var(--muted); }
```

- [ ] **Step 2: Ajouter les clés i18n des libellés de traditions**

Dans le bloc `fr:` de `I18N`, remplacer (le bloc ajouté au Task 1) :

```js
    poster_vide: "Calcule d'abord un portrait pour voir le poster.",
```

par :

```js
    poster_vide: "Calcule d'abord un portrait pour voir le poster.",
    pos_signe_solaire: "Signe solaire", pos_signe_lunaire: "Signe lunaire",
    pos_signe_chinois: "Signe chinois", pos_animal_heure: "Animal de l'heure",
    pos_chemin_de_vie: "Chemin de vie", pos_numerologie_nom: "Numérologie du nom",
    pos_egyptien: "Divinité égyptienne", pos_celte: "Arbre celte",
    pos_amerindien: "Totem amérindien", pos_maya: "Tzolkin maya",
    pos_pierre_du_mois: "Pierre du mois", pos_nakshatra: "Nakshatra védique",
    pos_vedique: "Rashi védique",
    pos_ame: "Âme", pos_personnalite: "Personnalité", pos_tonalite: "Tonalité", pos_pada: "Pada",
```

Dans le bloc `en:` de `I18N`, remplacer :

```js
    poster_vide: "Calculate a portrait first to see the poster.",
```

par :

```js
    poster_vide: "Calculate a portrait first to see the poster.",
    pos_signe_solaire: "Sun sign", pos_signe_lunaire: "Moon sign",
    pos_signe_chinois: "Chinese sign", pos_animal_heure: "Hour animal",
    pos_chemin_de_vie: "Life path", pos_numerologie_nom: "Name numerology",
    pos_egyptien: "Egyptian deity", pos_celte: "Celtic tree",
    pos_amerindien: "Native American totem", pos_maya: "Maya tzolkin",
    pos_pierre_du_mois: "Birthstone", pos_nakshatra: "Vedic nakshatra",
    pos_vedique: "Vedic rashi",
    pos_ame: "Soul", pos_personnalite: "Personality", pos_tonalite: "Tone", pos_pada: "Pada",
```

- [ ] **Step 3: Ajouter `TRADITIONS_POSTER_CHAMPS` et `renderPosterTraditions`**

Insérer dans `static/index.html`, juste avant `renderPoster()` (après la fonction `renderPosterCiel` du Task 2) :

```js
const TRADITIONS_POSTER_CHAMPS = [
  { cle: "signe_solaire", labelKey: "pos_signe_solaire",
    symbole: v => v.symbole, valeur: v => v.nom, sous: v => v.element || "" },
  { cle: "signe_lunaire", labelKey: "pos_signe_lunaire",
    symbole: v => v.symbole, valeur: v => v.signe, sous: () => "" },
  { cle: "signe_chinois", labelKey: "pos_signe_chinois",
    symbole: v => v.emoji, valeur: v => v.animal, sous: v => [v.element, v.polarite].filter(Boolean).join(" · ") },
  { cle: "animal_heure", labelKey: "pos_animal_heure",
    symbole: v => v.emoji, valeur: v => v.animal, sous: v => v.tranche || "" },
  { cle: "chemin_de_vie", labelKey: "pos_chemin_de_vie",
    symbole: () => "", valeur: v => String(v), sous: () => "" },
  { cle: "numerologie_nom", labelKey: "pos_numerologie_nom",
    symbole: () => "", valeur: v => String(v.expression),
    sous: v => `${I18N[LANGUE].pos_ame} ${v.ame} · ${I18N[LANGUE].pos_personnalite} ${v.personnalite}` },
  { cle: "egyptien", labelKey: "pos_egyptien", symbole: () => "", valeur: v => String(v), sous: () => "" },
  { cle: "celte", labelKey: "pos_celte", symbole: () => "", valeur: v => String(v), sous: () => "" },
  { cle: "amerindien", labelKey: "pos_amerindien", symbole: () => "", valeur: v => String(v), sous: () => "" },
  { cle: "maya", labelKey: "pos_maya",
    symbole: () => "", valeur: v => v.glyphe, sous: v => `${I18N[LANGUE].pos_tonalite} ${v.tonalite}` },
  { cle: "pierre_du_mois", labelKey: "pos_pierre_du_mois", symbole: () => "", valeur: v => String(v), sous: () => "" },
  { cle: "nakshatra", labelKey: "pos_nakshatra",
    symbole: () => "", valeur: v => v.nakshatra, sous: v => `${I18N[LANGUE].pos_pada} ${v.pada}` },
  { cle: "vedique", labelKey: "pos_vedique", symbole: v => v.symbole, valeur: v => v.rashi, sous: () => "" },
];

function renderPosterTraditions(traditions, identite) {
  const svg = document.getElementById("poster-svg");
  svg.innerHTML = "";
  const ns = "http://www.w3.org/2000/svg";
  const t = I18N[LANGUE];
  svg.setAttribute("aria-label", `Poster traditions natales de ${(identite.prenoms || "").trim() || "—"}`);

  const defs = elNS(ns, "defs");
  const grad = elNS(ns, "radialGradient", { id: "poster-halo", cx: "50%", cy: "50%", r: "50%" });
  grad.appendChild(elNS(ns, "stop", { offset: "0%", "stop-color": "#3a2a6b", "stop-opacity": "0.4" }));
  grad.appendChild(elNS(ns, "stop", { offset: "100%", "stop-color": "#3a2a6b", "stop-opacity": "0" }));
  defs.appendChild(grad);
  svg.appendChild(defs);
  svg.appendChild(elNS(ns, "circle", { class: "poster-halo", cx: 0, cy: -20, r: 250, fill: "url(#poster-halo)" }));

  const cartes = TRADITIONS_POSTER_CHAMPS
    .map(champ => ({ champ, val: (traditions || {})[champ.cle] }))
    .filter(({ val }) => val != null && val !== "");

  const cols = cartes.length > 9 ? 4 : 3;
  const cw = 470 / cols, ch = 92;
  const rows = Math.ceil(cartes.length / cols) || 1;
  const gridW = cw * cols, gridH = ch * rows;
  const startX = -gridW / 2, startY = -gridH / 2 - 30;

  cartes.forEach(({ champ, val }, idx) => {
    const col = idx % cols, row = Math.floor(idx / cols);
    const x = startX + col * cw, y = startY + row * ch;
    const card = elNS(ns, "g", { class: "poster-trad-carte", transform: `translate(${x.toFixed(1)},${y.toFixed(1)})` });
    card.appendChild(elNS(ns, "rect", { x: 4, y: 4, width: cw - 8, height: ch - 8, rx: 8, class: "poster-trad-rect" }));
    const sym = champ.symbole(val);
    if (sym) card.appendChild(elNS(ns, "text", { class: "poster-trad-sym", x: cw / 2, y: 30, "text-anchor": "middle" }, sym));
    card.appendChild(elNS(ns, "text", { class: "poster-trad-label", x: cw / 2, y: sym ? 46 : 26, "text-anchor": "middle" }, t[champ.labelKey]));
    card.appendChild(elNS(ns, "text", { class: "poster-trad-valeur", x: cw / 2, y: sym ? 64 : 46, "text-anchor": "middle" }, String(champ.valeur(val))));
    const sous = champ.sous(val);
    if (sous) card.appendChild(elNS(ns, "text", { class: "poster-trad-sous", x: cw / 2, y: sym ? 78 : 60, "text-anchor": "middle" }, sous));
    svg.appendChild(card);
  });

  posterBlocIdentite(svg, ns, identite, startY + gridH + 45);
}
```

Note : `theme_astral` (déjà couvert par le poster « Carte du ciel ») n'apparaît **pas** dans `TRADITIONS_POSTER_CHAMPS` — c'est une exclusion volontaire, pas un oubli.

- [ ] **Step 4: Brancher le type "traditions" dans le dispatcher**

Remplacer dans `static/index.html` (corps de `renderPoster()` du Task 2) :

```js
  const type = document.querySelector("input[name='poster-type']:checked").value;
  const identite = DERNIER_RESULTAT._identite || {};
  if (type === "ciel") {
    const densite = document.querySelector("input[name='poster-densite']:checked").value;
    renderPosterCiel(_THEME_CACHE, identite, densite);
  }
}
```

par :

```js
  const type = document.querySelector("input[name='poster-type']:checked").value;
  const identite = DERNIER_RESULTAT._identite || {};
  if (type === "ciel") {
    const densite = document.querySelector("input[name='poster-densite']:checked").value;
    renderPosterCiel(_THEME_CACHE, identite, densite);
  } else if (type === "traditions") {
    renderPosterTraditions(DERNIER_RESULTAT.traditions || {}, identite);
  }
}
```

- [ ] **Step 5: Vérifier le poster « Traditions natales »**

- `mcp__playwright__browser_navigate` → `http://localhost:8410`
- `mcp__playwright__browser_type` sur `#date_naissance` → `1990-05-15`
- `mcp__playwright__browser_type` sur `#heure_naissance` → `14:30`
- `mcp__playwright__browser_type` sur `#ville` → `Paris`
- `mcp__playwright__browser_click` sur `📍 Localiser`
- `mcp__playwright__browser_click` sur `✨ Calculer mon portrait`
- `mcp__playwright__browser_click` sur l'onglet `Poster`
- `mcp__playwright__browser_click` sur le radio `Traditions natales`
- `mcp__playwright__browser_evaluate` :
  ```js
  () => {
    const svg = document.getElementById("poster-svg");
    return {
      densiteFieldsetVisible: document.getElementById("poster-densite-fieldset").style.display !== "none",
      cartes: svg.querySelectorAll(".poster-trad-carte").length,
      valeurs: Array.from(svg.querySelectorAll(".poster-trad-valeur")).map(e => e.textContent),
    };
  }
  ```

Expected : `densiteFieldsetVisible: false` (masqué car type=traditions), `cartes` entre 10 et 13 selon les traditions calculables pour cette date/heure/lieu, `valeurs` contient des chaînes non vides (ex. le signe solaire du 15 mai — Taureau).

- `mcp__playwright__browser_take_screenshot` sur `#poster-svg` pour vérification visuelle de la grille.

- [ ] **Step 6: Commit**

```bash
git add static/index.html
git commit -m "feat: poster traditions natales (grille de faits bruts)"
```

---

## Task 4: Export PNG + vérification finale (print / export HTML)

**Files:**
- Modify: `static/index.html` (nouvelles fonctions `slugPourFichier`, `exportPosterPNG` + listener du bouton)

**Interfaces:**
- Consumes: `#poster-svg` (Tasks 2-3), `#poster-fond-transparent`, `#btn-export-poster`, `DERNIER_RESULTAT._identite`.
- Produces: rien de nouveau consommé par du code ultérieur — tâche terminale.

- [ ] **Step 1: Ajouter `slugPourFichier` et `exportPosterPNG`**

Insérer dans `static/index.html`, juste après la fonction `renderPoster()` :

```js
function slugPourFichier(s) {
  return (s || "").toLowerCase().normalize("NFD").replace(/\p{Diacritic}/gu, "")
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "portrait-cosmique";
}

function exportPosterPNG() {
  const svgEl = document.getElementById("poster-svg");
  if (!svgEl.childElementCount) return;
  const transparent = document.getElementById("poster-fond-transparent").checked;
  const clone = svgEl.cloneNode(true);
  if (transparent) {
    clone.querySelectorAll(".poster-halo").forEach(el => el.remove());
  }
  const taille = 3000;
  clone.setAttribute("width", String(taille));
  clone.setAttribute("height", String(taille));
  const xml = new XMLSerializer().serializeToString(clone);
  const svgBlob = new Blob([xml], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(svgBlob);
  const img = new Image();
  img.onload = () => {
    const canvas = document.createElement("canvas");
    canvas.width = taille;
    canvas.height = taille;
    const ctx = canvas.getContext("2d");
    if (!transparent) {
      ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--bg").trim() || "#0f1220";
      ctx.fillRect(0, 0, taille, taille);
    }
    ctx.drawImage(img, 0, 0, taille, taille);
    URL.revokeObjectURL(url);
    canvas.toBlob(blob => {
      const type = document.querySelector("input[name='poster-type']:checked").value;
      const prefix = type === "ciel" ? "carte-du-ciel" : "traditions-natales";
      const prenom = slugPourFichier((DERNIER_RESULTAT._identite || {}).prenoms);
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `${prefix}-${prenom}.png`;
      a.click();
    }, "image/png");
  };
  img.src = url;
}
document.getElementById("btn-export-poster").addEventListener("click", exportPosterPNG);
```

- [ ] **Step 2: Vérifier l'export PNG (fond plein)**

- `mcp__playwright__browser_navigate` → `http://localhost:8410`
- `mcp__playwright__browser_type` sur `#date_naissance` → `1990-05-15`
- `mcp__playwright__browser_type` sur `#heure_naissance` → `14:30`
- `mcp__playwright__browser_type` sur `#ville` → `Paris`
- `mcp__playwright__browser_click` sur `📍 Localiser`
- `mcp__playwright__browser_click` sur `✨ Calculer mon portrait`
- `mcp__playwright__browser_click` sur l'onglet `Poster`
- `mcp__playwright__browser_evaluate` (intercepter le blob PNG avant le clic, comme pour l'export HTML existant) :
  ```js
  () => {
    window.__pngCapture = null;
    const orig = URL.createObjectURL;
    URL.createObjectURL = (blob) => {
      if (blob.type === "image/png") window.__pngCapture = blob;
      return orig(blob);
    };
  }
  ```
- `mcp__playwright__browser_click` sur `⬇️ Télécharger en PNG`
- `mcp__playwright__browser_evaluate` (async) :
  ```js
  async () => {
    const blob = window.__pngCapture;
    if (!blob) return { ok: false };
    const bitmap = await createImageBitmap(blob);
    return { ok: true, type: blob.type, taille: blob.size, largeur: bitmap.width, hauteur: bitmap.height };
  }
  ```

Expected : `ok: true`, `type: "image/png"`, `taille` > 10000 (fichier non vide), `largeur: 3000`, `hauteur: 3000`.

- [ ] **Step 3: Vérifier l'export PNG (fond transparent) et le nom de fichier**

- `mcp__playwright__browser_click` sur la case `Fond transparent (t-shirt)`
- Répéter l'interception du Step 2, cliquer sur `⬇️ Télécharger en PNG`
- `mcp__playwright__browser_evaluate` (async) : même script d'inspection du blob — `ok: true`, dimensions identiques. La transparence elle-même (canal alpha réellement vide) n'est pas vérifiable simplement en pixels via cet outil ; on se limite à vérifier que l'export ne plante pas et produit un PNG de la bonne taille avec la case cochée.
- `mcp__playwright__browser_evaluate` : intercepter cette fois `a.download` en surchargeant `HTMLAnchorElement.prototype.click` juste avant le clic :
  ```js
  () => {
    window.__lastDownloadName = null;
    HTMLAnchorElement.prototype.click = new Proxy(HTMLAnchorElement.prototype.click, {
      apply(target, thisArg) { window.__lastDownloadName = thisArg.download; return Reflect.apply(target, thisArg, []); }
    });
  }
  ```
  puis re-cliquer sur `⬇️ Télécharger en PNG`, puis `mcp__playwright__browser_evaluate` : `() => window.__lastDownloadName`.

Expected : une chaîne du type `carte-du-ciel-<slug>.png` (le slug dérivé du prénom saisi, ou `portrait-cosmique` si aucun prénom).

- [ ] **Step 4: Vérifier que l'onglet Poster n'apparaît ni à l'impression ni dans l'export HTML**

- `mcp__playwright__browser_evaluate` :
  ```js
  () => {
    const sheet = Array.from(document.styleSheets).find(s => !s.href);
    const printRule = Array.from(sheet.cssRules).find(r => r.media && r.media.mediaText === "print" && r.cssText.includes("onglet-poster"));
    return !!printRule;
  }
  ```

Expected : `true`.

- `mcp__playwright__browser_evaluate` (intercepter le blob HTML comme dans le plan `2026-08-22-accordeon-sections.md`) :
  ```js
  () => {
    window.__htmlCapture = null;
    const orig = URL.createObjectURL;
    URL.createObjectURL = (blob) => { if (blob.type === "text/html") window.__htmlCapture = blob; return orig(blob); };
  }
  ```
- `mcp__playwright__browser_click` sur `⬇️ Télécharger en HTML`
- `mcp__playwright__browser_evaluate` (async) :
  ```js
  async () => {
    const txt = await window.__htmlCapture.text();
    return { contientRegleMasquage: txt.includes("#onglet-poster") && txt.includes("display: none !important") };
  }
  ```

Expected : `contientRegleMasquage: true`.

- [ ] **Step 5: Commit**

```bash
git add static/index.html
git commit -m "feat: export PNG haute résolution du poster"
```

---

## Self-Review (couverture spec)

- 3ᵉ onglet « Poster », données réutilisées sans nouvel appel réseau : Task 1. ✓
- Palette conservée (variables CSS existantes uniquement, aucune nouvelle palette) : Tasks 1-3. ✓
- Deux types de poster au choix (Carte du ciel / Traditions natales), sélecteur commun : Task 1 (HTML) + Task 2 + Task 3 (dispatch). ✓
- Densité Épuré/Complet pour la Carte du ciel, fieldset masqué pour Traditions : Task 1 Step 9 (visibilité) + Task 2 (rendu) + Task 3 Step 5 (vérification masquage). ✓
- Roue agrandie, traits affinés, halo radial doré/violet, pas de filtre interactif : Task 2. ✓
- Grille de traditions (mapping complet des 13 clés `traditions.calculer()`, exclusion de `theme_astral`) : Task 3. ✓
- Bloc identité commun (prénom/nom, date/heure/lieu, repli honnête si champ manquant) : `posterBlocIdentite` (Task 2), réutilisé par Task 3. ✓
- Export PNG haute résolution (3000×3000) avec toggle fond transparent/plein et nommage de fichier par type : Task 4. ✓
- Aucun nouveau fichier, aucun nouvel endpoint serveur : respecté dans les 4 tâches (uniquement `static/index.html` modifié). ✓
- i18n FR/EN de tous les nouveaux libellés : Task 1 Step 6, Task 3 Step 2. ✓
- Accessibilité (`aria-label` dynamique sur `#poster-svg`) : Task 2 Step 2, Task 3 Step 3. ✓
- Hors périmètre respecté : pas de règle `@media print` dédiée au contenu du poster (seulement masquage de l'onglet entier), pas de mockup produit, aucune modification de `engine/` ou `main.py`. ✓
