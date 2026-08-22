# Accordéon sur les titres de section — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre chaque section des onglets « Portrait » et « Carte astro complète » repliable (accordéon `<details>`), avec un bouton « Tout déplier / Tout replier » par onglet, pour réduire le scroll.

**Architecture:** Feature 100 % frontend dans le fichier unique `static/index.html` (CSS + JS vanilla embarqués). Les `<h3 class="theme-section">` deviennent des `<summary class="theme-section">` dans des `<details class="theme-section-acc">`. Aucun changement backend, aucune nouvelle dépendance.

**Tech Stack:** HTML/CSS/JS vanilla (pas de framework), FastAPI (`main.py`) sert `static/index.html` tel quel, `<details>/<summary>` natif du navigateur pour l'ouverture/fermeture (pas de JS requis pour le toggle individuel).

## Global Constraints

- Un seul fichier modifié : `static/index.html`. Ne pas créer de nouveau fichier — c'est la convention existante du projet (frontend mono-fichier).
- Style de code existant : noms de variables/fonctions en français, pas de point-virgule manquant, indentation 2 espaces.
- i18n : toute nouvelle chaîne visible doit avoir une entrée FR **et** EN dans `I18N` (`static/index.html`, bloc `fr: {...}` ~ligne 441-516, bloc `en: {...}` ~ligne 517-592).
- Pas de framework de test JS dans ce repo (CI = `pytest engine` uniquement, voir `.github/workflows/ci.yml`). La vérification de ce plan se fait par navigation réelle via le serveur de dev, avec l'outil MCP Playwright (`mcp__playwright__browser_*`).
- Serveur de dev : `uvicorn main:app --reload --port 8410` depuis la racine du dépôt. URL : `http://localhost:8410`.

---

## Task 1: Accordéon sur l'onglet « Portrait » (`#r-empreinte`)

**Files:**
- Modify: `static/index.html:99-105` (CSS `.theme-section`)
- Modify: `static/index.html:1067-1079` (fonction `afficherResultat`, bloc `EMPREINTE_SECTIONS.map`)

**Interfaces:**
- Consumes: `EMPREINTE_SECTIONS` (array `{key, titleKey, gid}`, déjà défini ligne 631-638), `sectionDeEntree(e)` (déjà défini ligne 639-646), `sectionIntro(gid)` (déjà défini ligne 1525-1533), `icGlossaire(id)` (déjà défini ligne 624-628).
- Produces: markup `<details class="theme-section-acc" data-section="{key}">` dans `#r-empreinte`, réutilisé tel quel par le Task 3 (bouton toggle) et le Task 4 (règle print). La classe CSS `.theme-section-acc` et `.tsa-chevron` sont introduites ici et réutilisées par le Task 2.

- [ ] **Step 1: Démarrer le serveur de dev et calculer un premier portrait pour observer le comportement actuel**

Run: `uvicorn main:app --reload --port 8410` (laisser tourner en arrière-plan)

Avec l'outil Playwright :
- `mcp__playwright__browser_navigate` → `http://localhost:8410`
- `mcp__playwright__browser_type` sur le champ `#date_naissance` → `1990-05-15`
- `mcp__playwright__browser_click` sur le bouton `✨ Calculer mon portrait`
- `mcp__playwright__browser_snapshot`

Expected: la page affiche l'onglet « Portrait » avec 6 blocs de titres `<h3>` (ex. « Traditions natales », « Les fondations », …) suivis chacun de leur contenu, sans possibilité de les replier. C'est l'état de référence **avant** modification.

- [ ] **Step 2: Modifier le CSS `.theme-section` pour cibler un `<summary>` dans un `<details>`, ajouter le chevron**

Remplacer dans `static/index.html` (lignes 99-105) :

```css
  .theme-section {
    font-size: 1.1rem; font-weight: 700; margin: 1.5rem 0 .5rem;
    padding-bottom: .3rem; border-bottom: 2px solid var(--accent);
    display: flex; align-items: center; gap: .4rem;
  }
  .theme-section:first-child { margin-top: 0; }
  .theme-section .glossaire-ic { margin-left: .15rem; }
```

par :

```css
  details.theme-section-acc { margin: 1.5rem 0 .5rem; }
  details.theme-section-acc:first-of-type { margin-top: 0; }
  .theme-section {
    font-size: 1.1rem; font-weight: 700; margin: 0 0 .5rem;
    padding-bottom: .3rem; border-bottom: 2px solid var(--accent);
    display: flex; align-items: center; gap: .4rem;
    cursor: pointer; list-style: none;
  }
  .theme-section::-webkit-details-marker { display: none; }
  .theme-section .glossaire-ic { margin-left: .15rem; }
  .theme-section .tsa-chevron {
    margin-left: auto; font-size: .8rem; color: var(--muted);
    transition: transform .15s;
  }
  details.theme-section-acc[open] > .theme-section .tsa-chevron { transform: rotate(90deg); }
```

Note : `:first-of-type` (et non `:first-child`) est utilisé car le Task 3 va insérer un `<button>` avant le premier `<details>` — `:first-of-type` reste correct même quand le `<details>` n'est plus le premier enfant du conteneur.

- [ ] **Step 3: Réécrire le bloc `EMPREINTE_SECTIONS.map` de `afficherResultat` en accordéon**

Remplacer dans `static/index.html` (lignes 1067-1079) :

```js
  document.getElementById("r-empreinte").innerHTML = EMPREINTE_SECTIONS.map(sec => {
    const items = d.empreinte.filter(e => sectionDeEntree(e) === sec.key);
    if (!items.length) return "";
    const header = `<h3 class="theme-section"><span>${t[sec.titleKey]}</span>${sec.gid ? icGlossaire(sec.gid) : ""}</h3>`;
    const intro = sec.gid ? sectionIntro(sec.gid) : "";
    const body = items.map(e => `
      <div class="empreinte-item">
        <div class="cle">${e.cle}${e.role ? " · " + e.role : ""}${icGlossaire(e.id)}</div>
        <div class="valeur">${e.valeur}</div>
        <div class="sens">${e.sens}</div>
      </div>`).join("");
    return header + intro + body;
  }).join("");
```

par :

```js
  const sectionsEmpreinte = EMPREINTE_SECTIONS
    .map(sec => ({ sec, items: d.empreinte.filter(e => sectionDeEntree(e) === sec.key) }))
    .filter(x => x.items.length);
  document.getElementById("r-empreinte").innerHTML = sectionsEmpreinte.map(({ sec, items }, idx) => {
    const ouverte = idx === 0 ? " open" : "";
    const header = `<summary class="theme-section"><span>${t[sec.titleKey]}</span>${sec.gid ? icGlossaire(sec.gid) : ""}<span class="tsa-chevron">▶</span></summary>`;
    const intro = sec.gid ? sectionIntro(sec.gid) : "";
    const body = items.map(e => `
      <div class="empreinte-item">
        <div class="cle">${e.cle}${e.role ? " · " + e.role : ""}${icGlossaire(e.id)}</div>
        <div class="valeur">${e.valeur}</div>
        <div class="sens">${e.sens}</div>
      </div>`).join("");
    return `<details class="theme-section-acc" data-section="${sec.key}"${ouverte}>${header}${intro}${body}</details>`;
  }).join("");
```

- [ ] **Step 4: Vérifier dans le navigateur**

Avec `--reload` actif, rafraîchir la page (ou relancer le calcul) :
- `mcp__playwright__browser_navigate` → `http://localhost:8410`
- `mcp__playwright__browser_type` sur `#date_naissance` → `1990-05-15`
- `mcp__playwright__browser_click` sur `✨ Calculer mon portrait`
- `mcp__playwright__browser_evaluate` :
  ```js
  () => {
    const details = document.querySelectorAll("#r-empreinte details.theme-section-acc");
    return { total: details.length, ouvertes: Array.from(details).filter(d => d.open).map(d => d.dataset.section) };
  }
  ```

Expected: `total` = nombre de sections avec contenu (typiquement 6, ou moins si une catégorie est vide pour cette date), `ouvertes` = un seul élément (la clé de la première section, ex. `"traditions"`).

- `mcp__playwright__browser_click` sur le `<summary>` de la 2ᵉ section → vérifier avec `browser_evaluate` que son `<details>` a maintenant `open === true` sans avoir touché aux autres (comportement natif du navigateur, aucun JS requis).

- [ ] **Step 5: Commit**

```bash
git add static/index.html
git commit -m "feat: accordéon sur les sections de l'onglet Portrait"
```

---

## Task 2: Accordéon sur l'onglet « Carte astro complète » (`#tableaux-theme`)

**Files:**
- Modify: `static/index.html:1539-1677` (fonction `renderTableaux`, réécriture complète)
- Modify: `static/index.html:1140-1144` (site d'appel qui représente un *nouveau* résultat)

**Interfaces:**
- Consumes: `.theme-section-acc` / `.tsa-chevron` (CSS du Task 1), `icGlossaire`, `sectionIntro`, `cartePoint`, `tableHTML`, `legendeChiffres`, `trierAspects`, `_ASPECT_FILTRE`, `_ASPECT_TRI`, `LEGENDE_FILTRES`, `_FONDATIONS_ORDRE`, `_FONDATIONS_MAISON`, `_CORPS_GLOSS`, `_POINTS_GLOSS`, `_DOMINANTE_GLOSS`, `_ASPECT_GLOSS`, `NOMS_ASPECTS_TR`, `COULEURS_ASPECTS`, `SYMBOLES_POINTS`, `SIGNES_SENS`, `fmtDeg` (tous déjà définis ailleurs dans le fichier, inchangés par ce plan).
- Produces: nouvelle fonction `sectionDetails(c, key, titre, gid, ouverte)` retournant l'élément `<details>` DOM créé (réutilisable si besoin par du code futur). Nouvelle signature `renderTableaux(tc, { reset = false } = {})` — **tous les appels existants sauf celui du Step 3 ci-dessous continuent de fonctionner sans modification** (le paramètre `reset` est optionnel, défaut `false`).

- [ ] **Step 1: Observer l'état actuel de l'onglet Carte astro complète**

Avec Playwright (portrait déjà calculé au Task 1, réutiliser la même session ou refaire le calcul) :
- `mcp__playwright__browser_click` sur l'onglet `Carte astro complète`
- `mcp__playwright__browser_snapshot`

Expected : 6 titres `<h3 class="theme-section">` (Fondations, 10 corps, Points évolutifs, Maisons, Aspects, Dominantes), non repliables.

- [ ] **Step 2: Ajouter le helper `sectionDetails` et réécrire `renderTableaux`**

Remplacer dans `static/index.html` (lignes 1539-1677), qui commence par :

```js
function renderTableaux(tc) {
  const c = document.getElementById("tableaux-theme");
  c.innerHTML = "";
  const t = I18N[LANGUE];
  const sectionH = (titre, gid) => {
    const ic = gid ? icGlossaire(gid) : "";
    return `<h3 class="theme-section"><span>${titre}</span>${ic}</h3>`;
  };

  // 1. Fondations (cartes didactiques)
```

et finit par :

```js
  c.insertAdjacentHTML("beforeend", legendeChiffres(t.leg_score));
  c.appendChild(domCont);
}
```

par le bloc complet suivant :

```js
function sectionDetails(c, key, titre, gid, ouverte) {
  const det = document.createElement("details");
  det.className = "theme-section-acc";
  det.dataset.section = key;
  det.open = ouverte;
  const ic = gid ? icGlossaire(gid) : "";
  det.innerHTML = `<summary class="theme-section"><span>${titre}</span>${ic}<span class="tsa-chevron">▶</span></summary>`;
  c.appendChild(det);
  return det;
}

function renderTableaux(tc, { reset = false } = {}) {
  const c = document.getElementById("tableaux-theme");
  const ouvertesAvant = {};
  c.querySelectorAll(":scope > details.theme-section-acc").forEach(d => {
    ouvertesAvant[d.dataset.section] = d.open;
  });
  const estOuverte = (key, idx) => reset ? idx === 0 : (key in ouvertesAvant ? ouvertesAvant[key] : false);
  c.innerHTML = "";
  const t = I18N[LANGUE];

  // 1. Fondations (cartes didactiques)
  const fond = tc.fondations || {};
  const dixMap = tc.dix_corps || {};
  const secFondations = sectionDetails(c, "fondations", t.ts_fondations, "theme_fondations", estOuverte("fondations", 0));
  secFondations.insertAdjacentHTML("beforeend", sectionIntro("theme_fondations"));
  const fondCards = _FONDATIONS_ORDRE.map(o => {
    const f = fond[o.key] || {};
    let maison = _FONDATIONS_MAISON[o.key];
    if (!maison) {
      const src = o.key === "soleil" ? dixMap["Soleil"] : (o.key === "lune" ? dixMap["Lune"] : null);
      maison = src ? src.maison : null;
    }
    return cartePoint(f.symbole || "—", o.nom, o.gid, {
      signe: f.signe, degre: f.degre, maison: maison,
      retro: (o.key === "soleil" ? (dixMap["Soleil"] || {}).retrograde
              : o.key === "lune" ? (dixMap["Lune"] || {}).retrograde : false),
      sens_signe: SIGNES_SENS[f.signe] || "",
    });
  }).join("");
  secFondations.insertAdjacentHTML("beforeend", `<div class="cartes-grille">${fondCards}</div>`);
  secFondations.insertAdjacentHTML("beforeend", legendeChiffres(
    `${t.leg_degre} · ${t.leg_maison_num} · ${t.leg_retro}`));

  // 2. 10 corps (cartes didactiques, facette corps)
  const dix = Object.entries(dixMap).map(([nom, p]) => ({
    corps: nom, gid: _CORPS_GLOSS[nom], symbole: SYMBOLES_POINTS[nom] || "",
    signe: p.signe, degre: p.degre, maison: p.maison,
    retro: p.retrograde,
  }));
  const secCorps = sectionDetails(c, "corps", t.ts_corps, "theme_corps", estOuverte("corps", 1));
  secCorps.insertAdjacentHTML("beforeend", sectionIntro("theme_corps"));
  const dixCards = dix.map(r => cartePoint(r.symbole, r.corps, r.gid, {
    signe: r.signe, degre: r.degre, maison: r.maison, retro: r.retro,
    sens_signe: SIGNES_SENS[r.signe] || "",
  })).join("");
  secCorps.insertAdjacentHTML("beforeend", `<div class="cartes-grille">${dixCards}</div>`);
  secCorps.insertAdjacentHTML("beforeend", legendeChiffres(
    `${t.leg_degre} · ${t.leg_maison_num} · ${t.leg_vitesse} · ${t.leg_retro}`));

  // 3. Points évolutifs (cartes didactiques)
  const pe = Object.entries(tc.points_evolutifs || {}).map(([nom, p]) => ({
    point: p.corps || nom, gid: _POINTS_GLOSS[nom],
    symbole: SYMBOLES_POINTS[p.corps || nom] || "",
    signe: p.signe, degre: p.degre, maison: p.maison, retro: p.retrograde,
  }));
  const secPoints = sectionDetails(c, "points", t.ts_points, "theme_points_evolutifs", estOuverte("points", 2));
  secPoints.insertAdjacentHTML("beforeend", sectionIntro("theme_points_evolutifs"));
  const peCards = pe.map(r => cartePoint(r.symbole, r.point, r.gid, {
    signe: r.signe, degre: r.degre, maison: r.maison, retro: r.retro,
    sens_signe: SIGNES_SENS[r.signe] || "",
  })).join("");
  secPoints.insertAdjacentHTML("beforeend", `<div class="cartes-grille">${peCards}</div>`);
  secPoints.insertAdjacentHTML("beforeend", legendeChiffres(
    `${t.leg_degre} · ${t.leg_maison_num} · ${t.leg_retro}`));

  // 4. Maisons (tableau + intro didactique)
  const secMaisons = sectionDetails(c, "maisons", t.ts_maisons, "theme_maisons", estOuverte("maisons", 3));
  secMaisons.insertAdjacentHTML("beforeend", sectionIntro("theme_maisons"));
  const mais = (tc.maisons || []).map(m => ({ n: m.maison, cuspe: m.cuspe, signe: m.signe, symbole: m.symbole }));
  secMaisons.insertAdjacentHTML("beforeend", tableHTML(t.t_maisons,
    [t.th_n, t.th_cuspe, t.th_signe, t.th_symbole],
    mais.map(r => `<tr><td class="num">${r.n}${icGlossaire("maison_" + r.n)}</td><td class="num">${fmtDeg(r.cuspe)}</td><td>${r.signe}</td><td>${r.symbole || ""}</td></tr>`),
    false));
  secMaisons.insertAdjacentHTML("beforeend", legendeChiffres(
    `${t.leg_maison_num} · ${t.leg_degre}`));

  // 5. Aspects (filtrable + triable)
  const fCfg2 = LEGENDE_FILTRES.find(f => f.val === _ASPECT_FILTRE) || LEGENDE_FILTRES[0];
  let asps = (tc.aspects || []).filter(a => !fCfg2.types || a.type === fCfg2.types);
  asps = trierAspects(asps, _ASPECT_TRI);
  const secAspects = sectionDetails(c, "aspects", t.ts_aspects, "theme_aspects", estOuverte("aspects", 4));
  secAspects.insertAdjacentHTML("beforeend", sectionIntro("theme_aspects"));
  const aspContainer = document.createElement("div");
  aspContainer.className = "theme-asp";
  aspContainer.innerHTML = `<table><caption>${t.t_aspects}</caption><thead><tr>
    <th data-col="aspect">${t.th_aspect}<span class="sort-ind">↕</span></th>
    <th data-col="type">${t.th_type}<span class="sort-ind">↕</span></th>
    <th>${t.th_pointa}</th><th>${t.th_pointb}</th>
    <th class="num" data-col="orb">${t.th_orb}<span class="sort-ind">↕</span></th>
    <th class="num" data-col="exactitude">${t.th_exact}<span class="sort-ind">↕</span></th>
    </tr></thead><tbody>${asps.map(a => `<tr class="asp-row" data-type="${a.type}">
      <td>${NOMS_ASPECTS_TR[a.aspect] || a.aspect}${icGlossaire(_ASPECT_GLOSS[a.aspect])}</td>
      <td>${a.type}</td>
      <td>${a.point_a}</td><td>${a.point_b}</td>
      <td class="num">${a.orb.toFixed(2)}°</td>
      <td class="num">${(a.exactitude * 100).toFixed(0)}%</td>
    </tr>`).join("")}</tbody></table>`;
  secAspects.insertAdjacentHTML("beforeend", legendeChiffres(
    `${t.leg_orbe} · ${t.leg_exact}`));
  secAspects.appendChild(aspContainer);
  aspContainer.querySelectorAll("th[data-col]").forEach(th => {
    th.addEventListener("click", () => {
      const col = th.dataset.col;
      if (_ASPECT_TRI.col === col) _ASPECT_TRI.sens = -_ASPECT_TRI.sens;
      else { _ASPECT_TRI.col = col; _ASPECT_TRI.sens = 1; }
      renderTableaux(tc);
    });
  });

  // 6. Dominantes (5 cartes)
  const dom = tc.dominantes || {};
  const secDominantes = sectionDetails(c, "dominantes", t.ts_dominantes, "theme_dominantes", estOuverte("dominantes", 5));
  secDominantes.insertAdjacentHTML("beforeend", sectionIntro("theme_dominantes"));
  const domCont = document.createElement("div");
  domCont.className = "theme-dominantes";
  const cards = [
    { titre: t.dom_element, gid: _DOMINANTE_GLOSS.dom_element, d: dom.element, key: "dominant" },
    { titre: t.dom_mode, gid: _DOMINANTE_GLOSS.dom_mode, d: dom.mode, key: "dominant" },
    { titre: t.dom_planete, gid: _DOMINANTE_GLOSS.dom_planete, d: dom.planete, key: "dominante" },
    { titre: t.dom_signe, gid: _DOMINANTE_GLOSS.dom_signe, d: dom.signe, key: "dominant" },
    { titre: t.dom_maison, gid: _DOMINANTE_GLOSS.dom_maison, d: dom.maison, key: "dominante" },
  ];
  for (const c2 of cards) {
    if (!c2.d || !c2.d.scores) continue;
    const scores = c2.d.scores;
    const maxVal = Math.max(...Object.values(scores), 1);
    const dominant = c2.d[c2.key] || c2.d.dominant || c2.d.dominante || "—";
    const entries = Object.entries(scores).sort((a, b) => b[1] - a[1]);
    const card = document.createElement("div");
    card.className = "dominante-carte";
    card.innerHTML = `<h4>${c2.titre}${icGlossaire(c2.gid)}</h4><div class="dom-nom">${dominant}</div>` +
      entries.map(([k, v]) => {
        const pct = maxVal > 0 ? (v / maxVal * 100) : 0;
        return `<div class="dominante-barre"><div class="dl">${k}</div><div class="bar-bg"><div class="bar-fg" style="width:${pct.toFixed(1)}%"></div></div><div class="dv">${typeof v === "number" ? v : ""}</div></div>`;
      }).join("");
    domCont.appendChild(card);
  }
  secDominantes.insertAdjacentHTML("beforeend", legendeChiffres(t.leg_score));
  secDominantes.appendChild(domCont);
}
```

- [ ] **Step 3: Marquer le seul site d'appel qui représente un *nouveau* résultat**

Chercher dans `static/index.html`, à l'intérieur de `calculerPortrait()` (~ligne 1140-1144), le bloc :

```js
      _ASPECT_FILTRE = "tous";
      _ASPECT_TRI = { col: "exactitude", sens: -1 };
      renderRoue(_THEME_CACHE);
      renderTableaux(_THEME_CACHE);
```

Remplacer la dernière ligne par :

```js
      _ASPECT_FILTRE = "tous";
      _ASPECT_TRI = { col: "exactitude", sens: -1 };
      renderRoue(_THEME_CACHE);
      renderTableaux(_THEME_CACHE, { reset: true });
```

Les 3 autres appels existants (`rechargerTheme()` ~ligne 1355, le clic sur un bouton de filtre d'aspect ~ligne 1485, le clic de tri de colonne ~ligne 1643) **restent inchangés** — ils gardent l'appel à un seul argument `renderTableaux(...)`, ce qui utilise le défaut `reset = false` et donc préserve l'état plié/déplié courant. C'est le comportement voulu : ces 3 cas ajustent l'affichage d'un même thème déjà calculé, ils ne représentent pas un nouveau résultat.

- [ ] **Step 4: Vérifier l'état par défaut sur un nouveau calcul**

- `mcp__playwright__browser_navigate` → `http://localhost:8410`
- `mcp__playwright__browser_type` sur `#date_naissance` → `1990-05-15`
- `mcp__playwright__browser_click` sur `✨ Calculer mon portrait`
- `mcp__playwright__browser_click` sur l'onglet `Carte astro complète`
- `mcp__playwright__browser_evaluate` :
  ```js
  () => {
    const details = document.querySelectorAll("#tableaux-theme details.theme-section-acc");
    return { total: details.length, ouvertes: Array.from(details).filter(d => d.open).map(d => d.dataset.section) };
  }
  ```

Expected: `total === 6`, `ouvertes` = `["fondations"]`.

- [ ] **Step 5: Vérifier la préservation d'état lors d'un re-tri**

- `mcp__playwright__browser_evaluate` : fermer manuellement la section fondations et ouvrir la section aspects :
  ```js
  () => {
    document.querySelector('#tableaux-theme details[data-section="fondations"]').open = false;
    document.querySelector('#tableaux-theme details[data-section="aspects"]').open = true;
  }
  ```
- `mcp__playwright__browser_click` sur l'en-tête de colonne « Orb » du tableau d'aspects (`th[data-col="orb"]`, dans la section aspects — s'assurer qu'elle est visible/ouverte avant de cliquer)
- `mcp__playwright__browser_evaluate` (même script que Step 4)

Expected: `fondations` toujours fermée, `aspects` toujours ouverte (l'état n'a pas été réinitialisé par le re-tri).

- [ ] **Step 6: Commit**

```bash
git add static/index.html
git commit -m "feat: accordéon sur les sections de l'onglet Carte astro complète"
```

---

## Task 3: Bouton « Tout déplier / Tout replier »

**Files:**
- Modify: `static/index.html` (bloc `I18N.fr` ~ligne 494-496, bloc `I18N.en` ~ligne 570-572)
- Modify: `static/index.html:628-630` (nouveaux helpers, insérés après `icGlossaire`)
- Modify: `static/index.html` (bloc `afficherResultat` du Task 1, insertion du bouton)
- Modify: `static/index.html` (fonction `renderTableaux` du Task 2, insertion du bouton)
- Modify: `static/index.html:1340` (ajout des listeners délégués `toggle`, juste après le listener des onglets)

**Interfaces:**
- Consumes: `.theme-section-acc` (Task 1 & 2), `I18N[LANGUE]`.
- Produces: `boutonToggleTout(containerId)` (string HTML), `toggleToutesSections(containerId)` (appelée en `onclick` inline), `majBoutonToggle(containerId)` (appelée après chaque render et à chaque `toggle` individuel).

- [ ] **Step 1: Ajouter les clés i18n**

Dans le bloc `fr:` de `I18N`, remplacer (ligne ~496) :

```js
    pt_aspects: "Aspects structurels", pt_dominantes: "Les dominantes",
```

par :

```js
    pt_aspects: "Aspects structurels", pt_dominantes: "Les dominantes",
    b_deplier_tout: "Tout déplier", b_replier_tout: "Tout replier",
```

Dans le bloc `en:` de `I18N`, remplacer (ligne ~572) :

```js
    pt_aspects: "Structural aspects", pt_dominantes: "Dominants",
```

par :

```js
    pt_aspects: "Structural aspects", pt_dominantes: "Dominants",
    b_deplier_tout: "Expand all", b_replier_tout: "Collapse all",
```

- [ ] **Step 2: Ajouter le CSS du bouton**

Ajouter, juste après le bloc CSS `.theme-section` / `.tsa-chevron` modifié au Task 1 :

```css
  .btn-toggle-tout { margin: 0 0 1rem; }
```

- [ ] **Step 3: Ajouter les 3 fonctions JS**

Dans `static/index.html`, entre la fin de `icGlossaire` (ligne 628, `}`) et le commentaire `// ── Découpage theme-section de l'empreinte` (ligne 630), insérer :

```js

// ── Accordéon des sections (bouton tout déplier/replier) ──────────
function boutonToggleTout(containerId) {
  return `<button type="button" class="btn ghost btn-toggle-tout" id="btn-toggle-${containerId}"
    onclick="toggleToutesSections('${containerId}')">${I18N[LANGUE].b_deplier_tout}</button>`;
}
function toggleToutesSections(containerId) {
  const c = document.getElementById(containerId);
  if (!c) return;
  const details = c.querySelectorAll(":scope > details.theme-section-acc");
  const tousOuverts = Array.from(details).every(d => d.open);
  details.forEach(d => { d.open = !tousOuverts; });
  majBoutonToggle(containerId);
}
function majBoutonToggle(containerId) {
  const c = document.getElementById(containerId);
  const btn = document.getElementById(`btn-toggle-${containerId}`);
  if (!btn) return;
  const details = c ? c.querySelectorAll(":scope > details.theme-section-acc") : [];
  if (!details.length) { btn.style.display = "none"; return; }
  btn.style.display = "";
  const tousOuverts = Array.from(details).every(d => d.open);
  btn.textContent = tousOuverts ? I18N[LANGUE].b_replier_tout : I18N[LANGUE].b_deplier_tout;
}
```

- [ ] **Step 4: Intégrer le bouton dans l'onglet Portrait (`afficherResultat`)**

Remplacer (bloc modifié au Task 1, Step 3) :

```js
  document.getElementById("r-empreinte").innerHTML = sectionsEmpreinte.map(({ sec, items }, idx) => {
```

par :

```js
  document.getElementById("r-empreinte").innerHTML =
    (sectionsEmpreinte.length ? boutonToggleTout("r-empreinte") : "") +
    sectionsEmpreinte.map(({ sec, items }, idx) => {
```

et juste après la fermeture de cette instruction (la ligne `}).join("");` qui suit), ajouter une nouvelle ligne :

```js
  majBoutonToggle("r-empreinte");
```

- [ ] **Step 5: Intégrer le bouton dans l'onglet Carte astro complète (`renderTableaux`)**

Dans la fonction `renderTableaux` (Task 2), remplacer :

```js
  c.innerHTML = "";
  const t = I18N[LANGUE];

  // 1. Fondations (cartes didactiques)
```

par :

```js
  c.innerHTML = boutonToggleTout("tableaux-theme");
  const t = I18N[LANGUE];

  // 1. Fondations (cartes didactiques)
```

Et tout à la fin de la fonction, remplacer la dernière ligne :

```js
  secDominantes.appendChild(domCont);
}
```

par :

```js
  secDominantes.appendChild(domCont);
  majBoutonToggle("tableaux-theme");
}
```

- [ ] **Step 6: Ajouter les listeners délégués `toggle`**

L'événement `toggle` d'un `<details>` ne remonte pas (`bubbles: false`) — un listener classique sur un ancêtre ne le recevrait jamais en phase de bubbling. Il faut l'écouter en phase de capture (`true` en 3ᵉ argument).

Juste après (dans `static/index.html`) :

```js
document.querySelectorAll(".onglet").forEach(b => b.addEventListener("click", () => afficherOnglet(b.dataset.onglet)));
```

ajouter :

```js
document.getElementById("r-empreinte").addEventListener("toggle", (e) => {
  if (e.target.classList && e.target.classList.contains("theme-section-acc")) majBoutonToggle("r-empreinte");
}, true);
document.getElementById("tableaux-theme").addEventListener("toggle", (e) => {
  if (e.target.classList && e.target.classList.contains("theme-section-acc")) majBoutonToggle("tableaux-theme");
}, true);
```

- [ ] **Step 7: Vérifier le bouton sur l'onglet Portrait**

- `mcp__playwright__browser_navigate` → `http://localhost:8410`
- `mcp__playwright__browser_type` sur `#date_naissance` → `1990-05-15`
- `mcp__playwright__browser_click` sur `✨ Calculer mon portrait`
- `mcp__playwright__browser_snapshot` : vérifier la présence d'un bouton texte « Tout déplier » au-dessus de la 1ère section.
- `mcp__playwright__browser_click` sur ce bouton
- `mcp__playwright__browser_evaluate` :
  ```js
  () => {
    const details = document.querySelectorAll("#r-empreinte details.theme-section-acc");
    return { toutesOuvertes: Array.from(details).every(d => d.open), label: document.getElementById("btn-toggle-r-empreinte").textContent };
  }
  ```

Expected: `toutesOuvertes: true`, `label: "Tout replier"`.

- `mcp__playwright__browser_click` sur le même bouton (maintenant « Tout replier »)
- Ré-évaluer : `toutesOuvertes` doit être `false` pour toutes (`Array.from(details).every(d => !d.open)`), `label: "Tout déplier"`.

- `mcp__playwright__browser_click` sur le `<summary>` d'une seule section → `mcp__playwright__browser_evaluate` : le label du bouton redevient `"Tout déplier"` (une section ouverte, les autres fermées → pas "tout ouvert").

- [ ] **Step 8: Vérifier le bouton sur l'onglet Carte astro complète**

- `mcp__playwright__browser_click` sur l'onglet `Carte astro complète`
- Répéter les mêmes vérifications qu'au Step 7 en remplaçant `r-empreinte` par `tableaux-theme`.

- [ ] **Step 9: Vérifier la traduction EN**

- `mcp__playwright__browser_click` sur le bouton `EN`
- `mcp__playwright__browser_evaluate` : `document.getElementById("btn-toggle-tableaux-theme").textContent` doit valoir `"Expand all"` (ou `"Collapse all"` selon l'état courant des sections).

- [ ] **Step 10: Commit**

```bash
git add static/index.html
git commit -m "feat: bouton tout déplier/replier pour les sections en accordéon"
```

---

## Task 4: Sécurité impression / export

**Files:**
- Modify: `static/index.html:250-258` (bloc `@media print` existant pour la Carte astro complète)

**Interfaces:**
- Consumes: `.theme-section-acc`, `.btn-toggle-tout` (Tasks 1-3).
- Produces: rien de nouveau consommé par du code ultérieur — tâche terminale.

- [ ] **Step 1: Ajouter les règles d'impression**

Remplacer dans `static/index.html` (lignes 250-258) :

```css
  @media print {
    .resultats-onglets, .theme-options, #roue-svg, .theme-legend, .theme-caveat { display: none !important; }
    .onglet-contenu { display: block !important; }
    .theme-layout { display: block !important; }
    .theme-roue { display: none !important; }
    .theme-tableaux table { font-size: 9pt; }
    .theme-tableaux th { cursor: default; }
    #resultat { display: block !important; }
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
    details.theme-section-acc > *:not(summary) { display: block !important; }
    .btn-toggle-tout { display: none !important; }
  }
```

- [ ] **Step 2: Vérifier le forçage à l'impression**

- `mcp__playwright__browser_navigate` → `http://localhost:8410`
- `mcp__playwright__browser_type` sur `#date_naissance` → `1990-05-15`
- `mcp__playwright__browser_click` sur `✨ Calculer mon portrait`
- `mcp__playwright__browser_evaluate` : replier manuellement au moins une section (`document.querySelector('#r-empreinte details.theme-section-acc').open = false;` en ciblant une section actuellement ouverte, sinon `open = false` sur la 2ᵉ section)
- `mcp__playwright__browser_evaluate` avec émulation de média print (si l'outil MCP Playwright expose `emulateMedia`, l'utiliser en amont ; sinon, valider directement la règle CSS en lisant les `cssRules` du document) :
  ```js
  () => {
    const sheet = Array.from(document.styleSheets).find(s => !s.href);
    const printRule = Array.from(sheet.cssRules).find(r => r.media && r.media.mediaText === "print" && r.cssText.includes("theme-section-acc"));
    return !!printRule;
  }
  ```

Expected: `true` — la règle print ciblant `.theme-section-acc` est bien présente dans la feuille de style.

Si l'outil Playwright utilisé expose `browser_evaluate` avec accès à `window.matchMedia` mais pas d'émulation directe de `@media print`, cette vérification structurelle (présence de la règle CSS) suffit : le mécanisme `!important` sur `display: block` face à la règle UA `details:not([open]) > *:not(summary) { display: none }` est un comportement standard du moteur de rendu, pas une logique métier à re-tester.

- [ ] **Step 3: Vérifier que l'export HTML reflète l'état courant (WYSIWYG)**

- `mcp__playwright__browser_evaluate` (avant export, intercepter `URL.createObjectURL` pour capturer le contenu du blob) :
  ```js
  () => {
    window.__blobCapture = null;
    const orig = URL.createObjectURL;
    URL.createObjectURL = (blob) => { window.__blobCapture = blob; return orig(blob); };
  }
  ```
- `mcp__playwright__browser_click` sur le bouton `⬇️ Télécharger en HTML`
- `mcp__playwright__browser_evaluate` (async) :
  ```js
  async () => {
    const txt = await window.__blobCapture.text();
    const ouvertes = (txt.match(/<details class="theme-section-acc"[^>]*\sopen/g) || []).length;
    const fermees = (txt.match(/<details class="theme-section-acc"(?!.*\sopen)[^>]*>/g) || []).length;
    return { contientDetails: txt.includes('class="theme-section-acc"'), ouvertes, fermees };
  }
  ```

Expected: `contientDetails: true`, et `ouvertes + fermees` correspond au nombre de sections affichées à l'écran au moment du clic (la section repliée manuellement au Step 2 apparaît bien sans l'attribut `open` dans le HTML exporté).

- [ ] **Step 4: Commit**

```bash
git add static/index.html
git commit -m "feat: forcer l'affichage complet des sections à l'impression"
```

---

## Self-Review (couverture spec)

- Structure `<details>/<summary>` par section, CSS chevron : Task 1 (Portrait) + Task 2 (Carte astro complète). ✓
- Bouton « Tout déplier / Tout replier » par onglet, libellé dynamique, sync sur toggle individuel : Task 3. ✓
- État par défaut (1ère section ouverte) sur nouveau résultat : Task 1 Step 3 (Portrait, toujours reset car pas d'autre site d'appel) + Task 2 Step 3-4 (Carte astro, `reset: true` uniquement sur le calcul initial). ✓
- Préservation d'état lors du re-tri des aspects (et, par extension du même mécanisme, lors du changement de système de maisons / méthode des dominantes / filtre d'aspect) : Task 2 Step 3 + Step 5. ✓
- Export HTML WYSIWYG + impression forcée : Task 4. ✓
- i18n FR/EN des nouveaux boutons : Task 3 Step 1. ✓
- Aucun changement aux `details.avance` existants ni au tableau de légende PDF : non touchés par aucun task (vérifié par grep avant écriture du plan — ces sélecteurs n'apparaissent dans aucun diff proposé). ✓
