# Cache navigateur multi-profils — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permettre la sauvegarde de plusieurs profils nataux dans `localStorage` pour pré-remplir le formulaire à chaque visite, avec un sélecteur déroulant et des actions de gestion (renommer, supprimer, nouveau, enregistrer sous).

**Architecture:** Feature 100 % frontend dans `static/index.html`. Une clé `localStorage` (`portrait-cosmique-profils`) stocke un objet `{profils: [...], profil_actif: "id"}`. Des helpers JS purs gèrent load/save/list/create/delete. L'UI ajoute une barre de gestion au-dessus du formulaire. L'auto-save se branche sur le submit existant.

**Tech Stack:** Vanilla JS, `localStorage`, HTML/CSS existant (variables CSS `--panel2`, `--border`, `--accent`). Aucune dépendance. Pas de framework de test — vérification manuelle via serveur local.

## Global Constraints

- Fichier unique : `static/index.html` (monolithe HTML+CSS+JS existant).
- Clé localStorage : `portrait-cosmique-profils` (ne pas confondre avec `portrait-cosmique-llm` existant).
- IDs de profil : `"p" + Date.now()` (court, unique local).
- i18n : toutes les chaînes utilisateur dans `I18N.fr` et `I18N.en`.
- La config LLM (`portrait-cosmique-llm`) reste inchangée, globale, pas par-profil.
- L'export HTML n'embarque pas la logique de cache (snapshot autonome).
- Styles cohérents avec l'existant : `var(--panel2)`, `var(--border)`, `var(--accent)`, `.btn.ghost`, `.sous`.

---

## File Structure

Tout est dans `static/index.html` (monolithe existant). Les modifications se répartissent dans 4 zones du fichier :

1. **CSS** (balise `<style>`, ~ligne 7) : ajout d'une règle `.profils-barre` pour la barre de gestion.
2. **HTML formulaire** (~ligne 259) : insertion de la barre de gestion au-dessus du champ Prénoms.
3. **i18n** (~ligne 403, objet `I18N`) : ajout de 9 clés FR + 9 clés EN.
4. **JS logique** (~ligne 580, après `LLM_STORAGE_KEY`) : helpers + UI wiring + auto-save.

Pas de nouveau fichier. Pas de test automatisé (pas de framework de test frontend dans le projet).

---

### Task 1: Clés i18n FR/EN

**Files:**
- Modify: `static/index.html` — objet `I18N` (~ligne 403)

**Interfaces:**
- Produces: 9 nouvelles clés dans `I18N.fr` et `I18N.en`, consommées par les tâches 3 et 4.

- [ ] **Step 1: Ajouter les clés FR**

Dans `I18N.fr`, après la ligne `mentions: "Lecture symbolique — divertissement, pas un fait. Aucune donnée n'est conservée par ce service.",` (ligne ~431), ajouter :

```javascript
    l_profil: "Profil",
    b_renommer: "✏️ Renommer",
    b_supprimer: "🗑️ Supprimer",
    b_nouveau: "＋ Nouveau",
    b_sous: "💾 Enregistrer sous…",
    p_label_defaut: "Profil {n}",
    p_confirm_suppr: "Supprimer ce profil ?",
    p_prompt_label: "Nom du profil",
    p_prompt_renommer: "Nouveau nom",
```

- [ ] **Step 2: Ajouter les clés EN**

Dans `I18N.en`, après la ligne `mentions: "Symbolic reading — entertainment, not fact. No data is kept by this service.",` (ligne ~495), ajouter :

```javascript
    l_profil: "Profile",
    b_renommer: "✏️ Rename",
    b_supprimer: "🗑️ Delete",
    b_nouveau: "＋ New",
    b_sous: "💾 Save as…",
    p_label_defaut: "Profile {n}",
    p_confirm_suppr: "Delete this profile?",
    p_prompt_label: "Profile name",
    p_prompt_renommer: "New name",
```

- [ ] **Step 3: Vérifier que la page se charge sans erreur**

Run: `python3 -m http.server 8000 --directory static` puis ouvrir `http://localhost:8000` dans un navigateur.
Expected: page se charge normalement, aucun changement visible (les clés ne sont pas encore utilisées).

- [ ] **Step 4: Commit**

```bash
git add static/index.html
git commit -m "feat(i18n): clés FR/EN pour cache multi-profils"
```

---

### Task 2: CSS de la barre de gestion

**Files:**
- Modify: `static/index.html` — balise `<style>` (~ligne 245, avant `</style>`)

**Interfaces:**
- Produces: classe `.profils-barre` et enfants, consommés par Task 3.

- [ ] **Step 1: Ajouter les règles CSS**

Avant la ligne `</style>` (ligne ~245), ajouter :

```css
  .profils-barre {
    display: flex; gap: .4rem; align-items: center; flex-wrap: wrap;
    padding: .6rem .8rem; margin-bottom: 12px;
    background: var(--panel2); border: 1px solid var(--border); border-radius: 10px;
  }
  .profils-barre label { margin: 0; font-size: .82rem; color: var(--muted); }
  .profils-barre select {
    flex: 1; min-width: 120px; padding: 6px 10px; font-size: .9rem;
    background: var(--panel); border: 1px solid var(--border); color: var(--text);
    border-radius: 8px; cursor: pointer;
  }
  .profils-barre .btn.ghost { margin: 0; padding: 6px 10px; font-size: .82rem; }
```

- [ ] **Step 2: Vérifier visuellement (pas encore injecté en HTML)**

Run: `python3 -m http.server 8000 --directory static` → page se charge sans erreur CSS (règles inutilisées, silencieuses).

- [ ] **Step 3: Commit**

```bash
git add static/index.html
git commit -m "style: barre de gestion multi-profils"
```

---

### Task 3: HTML de la barre de gestion + helpers localStorage

**Files:**
- Modify: `static/index.html` — formulaire (~ligne 259, après `<form id="form-fiche">`) et JS (~ligne 580, après `const LLM_STORAGE_KEY = ...`)

**Interfaces:**
- Consumes: clés i18n de Task 1, CSS de Task 2.
- Produces: `PROFILS_STORAGE_KEY`, `chargerProfils()`, `sauvegarderProfils()`, `profilActif()`, `creerProfil()`, `supprimerProfil()`, `renommmerProfil()`, `dupliquerProfil()` — consommés par Task 4.

- [ ] **Step 1: Insérer la barre HTML dans le formulaire**

Dans le `<form id="form-fiche">`, juste après la ligne d'ouverture `<form id="form-fiche">` (ligne ~259) et avant la `<div class="row">` des prénoms, ajouter :

```html
      <div class="profils-barre" id="profils-barre">
        <label data-t="l_profil">Profil</label>
        <select id="select-profil"></select>
        <button type="button" class="btn ghost" onclick="actionRenommer()" data-t="b_renommer">✏️ Renommer</button>
        <button type="button" class="btn ghost" onclick="actionSupprimer()" data-t="b_supprimer">🗑️ Supprimer</button>
        <button type="button" class="btn ghost" onclick="actionNouveau()" data-t="b_nouveau">＋ Nouveau</button>
        <button type="button" class="btn ghost" onclick="actionSous()" data-t="b_sous">💾 Enregistrer sous…</button>
      </div>
```

- [ ] **Step 2: Ajouter la constante + helpers JS**

Après la ligne `const LLM_STORAGE_KEY = "portrait-cosmique-llm";` (ligne ~580), ajouter :

```javascript
const PROFILS_STORAGE_KEY = "portrait-cosmique-profils";

// ── Helpers localStorage multi-profils ───────────────────────────
function chargerProfils() {
  const raw = localStorage.getItem(PROFILS_STORAGE_KEY);
  if (!raw) return { profils: [], profil_actif: null };
  try {
    const d = JSON.parse(raw);
    if (!Array.isArray(d.profils)) d.profils = [];
    return d;
  } catch (e) { return { profils: [], profil_actif: null }; }
}

function sauvegarderProfils(data) {
  localStorage.setItem(PROFILS_STORAGE_KEY, JSON.stringify(data));
}

function profilActif() {
  const d = chargerProfils();
  if (!d.profil_actif) return null;
  return d.profils.find(p => p.id === d.profil_actif) || null;
}

function lireChampsForm() {
  return {
    prenoms: document.getElementById("prenoms").value,
    nom: document.getElementById("nom").value,
    date_naissance: document.getElementById("date_naissance").value,
    heure_naissance: document.getElementById("heure_naissance").value,
    ville: document.getElementById("ville").value,
    latitude: document.getElementById("latitude").value || null,
    longitude: document.getElementById("longitude").value || null,
    utc_offset: document.getElementById("utc_offset").value || null,
    systeme_numerologie: document.getElementById("systeme_numerologie").value,
  };
}

function ecrireChampsForm(p) {
  if (!p) return;
  document.getElementById("prenoms").value = p.prenoms || "";
  document.getElementById("nom").value = p.nom || "";
  document.getElementById("date_naissance").value = p.date_naissance || "";
  document.getElementById("heure_naissance").value = p.heure_naissance || "";
  document.getElementById("ville").value = p.ville || "";
  document.getElementById("latitude").value = p.latitude || "";
  document.getElementById("longitude").value = p.longitude || "";
  document.getElementById("utc_offset").value = p.utc_offset || "";
  document.getElementById("systeme_numerologie").value = p.systeme_numerologie || "classique";
  document.getElementById("coords-info").textContent = p.ville ? p.ville : "";
}

function prochainLabelDefaut() {
  const d = chargerProfils();
  const labels = new Set(d.profils.map(p => p.label));
  let n = 1;
  while (labels.has(I18N[LANGUE].p_label_defaut.replace("{n}", n))) n++;
  return I18N[LANGUE].p_label_defaut.replace("{n}", n);
}

function creerProfil(label, champs) {
  const d = chargerProfils();
  const id = "p" + Date.now();
  const profil = { id, label, ...champs };
  d.profils.push(profil);
  d.profil_actif = id;
  sauvegarderProfils(d);
  return profil;
}

function supprimerProfil(id) {
  const d = chargerProfils();
  d.profils = d.profils.filter(p => p.id !== id);
  if (d.profil_actif === id) {
    d.profil_actif = d.profils.length ? d.profils[0].id : null;
  }
  sauvegarderProfils(d);
}

function renommerProfil(id, nouveauLabel) {
  const d = chargerProfils();
  const p = d.profils.find(x => x.id === id);
  if (p) { p.label = nouveauLabel; sauvegarderProfils(d); }
}

function dupliquerProfil(label, champs) {
  return creerProfil(label, champs);
}

function mettreAJourProfilActif(champs) {
  const d = chargerProfils();
  if (!d.profil_actif) {
    const label = prochainLabelDefaut();
    const p = creerProfil(label, champs);
    return p;
  }
  const p = d.profils.find(x => x.id === d.profil_actif);
  if (p) { Object.assign(p, champs); sauvegarderProfils(d); return p; }
  return null;
}
```

- [ ] **Step 3: Vérifier que la page se charge**

Run: `python3 -m http.server 8000 --directory static` → ouvrir la page.
Expected: barre de gestion visible au-dessus du champ Prénoms (select vide, 4 boutons). Console sans erreur.

- [ ] **Step 4: Commit**

```bash
git add static/index.html
git commit -m "feat: helpers localStorage + UI barre multi-profils"
```

---

### Task 4: Peupler le select + chargement page + actions

**Files:**
- Modify: `static/index.html` — JS (~ligne 710, après `chargerConfigLLM();`)

**Interfaces:**
- Consumes: helpers de Task 3, clés i18n de Task 1.
- Produces: `rafraichirSelectProfil()`, `chargerProfilActif()`, `actionRenommer()`, `actionSupprimer()`, `actionNouveau()`, `actionSous()`, wiring du select.

- [ ] **Step 1: Ajouter le peuplement du select + chargement page**

Après la ligne `chargerConfigLLM();` (ligne ~711), ajouter :

```javascript
// ── Multi-profils : peuplement select + chargement initial ───────
function rafraichirSelectProfil() {
  const d = chargerProfils();
  const sel = document.getElementById("select-profil");
  sel.innerHTML = "";
  for (const p of d.profils) {
    const o = document.createElement("option");
    o.value = p.id;
    o.textContent = p.label;
    if (p.id === d.profil_actif) o.selected = true;
    sel.appendChild(o);
  }
  const oNouveau = document.createElement("option");
  oNouveau.value = "__nouveau__";
  oNouveau.textContent = I18N[LANGUE].b_nouveau;
  sel.appendChild(oNouveau);
}

function chargerProfilActif() {
  const d = chargerProfils();
  if (!d.profils.length) { rafraichirSelectProfil(); return; }
  let p = d.profils.find(x => x.id === d.profil_actif);
  if (!p) { p = d.profils[0]; d.profil_actif = p.id; sauvegarderProfils(d); }
  ecrireChampsForm(p);
  rafraichirSelectProfil();
}

document.getElementById("select-profil").addEventListener("change", (e) => {
  if (e.target.value === "__nouveau__") {
    document.getElementById("prenoms").value = "";
    document.getElementById("nom").value = "";
    document.getElementById("date_naissance").value = "";
    document.getElementById("heure_naissance").value = "";
    document.getElementById("ville").value = "";
    document.getElementById("latitude").value = "";
    document.getElementById("longitude").value = "";
    document.getElementById("utc_offset").value = "";
    document.getElementById("coords-info").textContent = "";
    const d = chargerProfils();
    d.profil_actif = null;
    sauvegarderProfils(d);
    return;
  }
  const d = chargerProfils();
  const p = d.profils.find(x => x.id === e.target.value);
  if (p) { d.profil_actif = p.id; sauvegarderProfils(d); ecrireChampsForm(p); }
});

chargerProfilActif();
```

- [ ] **Step 2: Ajouter les 4 actions boutons**

À la suite du bloc ajouté en Step 1, ajouter :

```javascript
function actionRenommer() {
  const d = chargerProfils();
  if (!d.profil_actif) return;
  const p = d.profils.find(x => x.id === d.profil_actif);
  if (!p) return;
  const nouveau = prompt(I18N[LANGUE].p_prompt_renommer, p.label);
  if (nouveau && nouveau.trim()) {
    renommerProfil(p.id, nouveau.trim());
    rafraichirSelectProfil();
  }
}

function actionSupprimer() {
  const d = chargerProfils();
  if (!d.profil_actif) return;
  if (!confirm(I18N[LANGUE].p_confirm_suppr)) return;
  supprimerProfil(d.profil_actif);
  chargerProfilActif();
}

function actionNouveau() {
  document.getElementById("select-profil").value = "__nouveau__";
  document.getElementById("select-profil").dispatchEvent(new Event("change"));
}

function actionSous() {
  const label = prompt(I18N[LANGUE].p_prompt_label, "");
  if (!label || !label.trim()) return;
  const champs = lireChampsForm();
  dupliquerProfil(label.trim(), champs);
  rafraichirSelectProfil();
}
```

- [ ] **Step 3: Vérification manuelle — création automatique**

Run: `python3 -m http.server 8000 --directory static` → ouvrir `http://localhost:8000`.

1. Saisir « Jean », « Dupont », « 1990-01-15 », « 14:30 », « Toulouse » → cliquer 📍 Localiser → cliquer « Calculer mon portrait ».
2. Ouvrir la console JS → `localStorage.getItem("portrait-cosmique-profils")` → vérifier qu'un profil « Profil 1 » existe avec `profil_actif` renseigné.
3. Recharger la page → champs pré-remplis, select affiche « Profil 1 ».

Expected: profil créé automatiquement au premier calcul, restauré au rechargement.

- [ ] **Step 4: Vérification manuelle — Nouveau + Enregistrer sous + Renommer + Supprimer**

Dans la même session :

4. Cliquer « ＋ Nouveau » → champs vidés, select sur « ＋ Nouveau profil ».
5. Saisir « Marie », « Curie », « 1867-11-07 » → Calculer → un nouveau profil « Profil 2 » est créé (auto-save).
6. Sélectionner « Profil 1 » dans le select → champs de Jean restaurés.
7. Cliquer « ✏️ Renommer » → saisir « Moi » → le select affiche « Moi ».
8. Cliquer « 💾 Enregistrer sous… » → saisir « Test copie » → un 3e profil apparaît, select bascule dessus, champs = copie de « Moi ».
9. Cliquer « 🗑️ Supprimer » → confirmer → profil « Test copie » supprimé, select bascule sur le prochain profil.

Expected: toutes les actions fonctionnent, le localStorage reste cohérent après chaque action.

- [ ] **Step 5: Vérification i18n**

10. Cliquer « EN » → les 4 boutons affichent leurs labels anglais (« ✏️ Rename », « 🗑️ Delete », « ＋ New », « 💾 Save as… »), le select affiche « ＋ New profile » comme dernière option.

Expected: traduction complète de la barre.

- [ ] **Step 6: Commit**

```bash
git add static/index.html
git commit -m "feat: peuplement select + actions multi-profils"
```

---

### Task 5: Auto-save au Calculer + mise à jour setLangue

**Files:**
- Modify: `static/index.html` — fonction `calculerPortrait()` (~ligne 825) et `setLangue()` (~ligne 713)

**Interfaces:**
- Consumes: `mettreAJourProfilActif()` et `rafraichirSelectProfil()` de Task 3/4.

- [ ] **Step 1: Brancher l'auto-save dans calculerPortrait()**

Dans la fonction `calculerPortrait()`, juste après la ligne `const body = { ... };` (avant le `try {`) ajouter un appel à la mise à jour du profil actif. Concrètement, repérer la ligne `try {` qui précède le `fetch("/portrait"...)` et insérer juste avant :

```javascript
  // Auto-save : mettre à jour le profil actif avec les champs courants
  mettreAJourProfilActif(lireChampsForm());
  rafraichirSelectProfil();
```

- [ ] **Step 2: Rafraîchir le select au changement de langue**

Dans la fonction `setLangue(l)`, à la fin de la fonction (après le bloc `if (DERNIER_RESULTAT) calculerPortrait();`), ajouter :

```javascript
  rafraichirSelectProfil();
```

- [ ] **Step 3: Vérification auto-save**

Run: `python3 -m http.server 8000 --directory static` → ouvrir la page.

1. Sélectionner un profil existant → modifier le champ « Prénoms » (ex. « Jean » → « Jean-Paul ») → Calculer.
2. Recharger la page → le profil affiche « Jean-Paul » (écrasement silencieux validé).

Expected: le profil actif est mis à jour à chaque calcul, sans message ni friction.

- [ ] **Step 4: Vérification setLangue + select**

3. Recharger la page → cliquer « EN » → le select re-render avec les labels traduits (« ＋ New profile »), le profil actif reste sélectionné correctement.

Expected: pas de perte de sélection au switch de langue.

- [ ] **Step 5: Commit**

```bash
git add static/index.html
git commit -m "feat: auto-save profil au calcul + refresh select i18n"
```

---

## Self-Review

**Spec coverage :**
- Structure de données `portrait-cosmique-profils` → Task 3 (`PROFILS_STORAGE_KEY`).
- UI barre de gestion (select + 4 boutons) → Task 2 (CSS) + Task 3 (HTML).
- `__nouveau__` dans select → Task 4 Step 1.
- Renommer/Supprimer/Nouveau/Enregistrer sous → Task 4 Step 2.
- Auto-save au Calculer → Task 5 Step 1.
- Création auto « Profil 1 » si `profil_actif === null` → `mettreAJourProfilActif` + `prochainLabelDefaut` (Task 3).
- Chargement page pré-remplit → `chargerProfilActif()` (Task 4 Step 1).
- i18n 9 clés → Task 1.
- Export HTML non concerné → respecté (aucune modif à `telechargerHTML()`).
- Config LLM non concernée → respecté (aucune modif à `LLM_STORAGE_KEY`).
- Vérifications manuelles (8 scénarios du spec) → réparties dans Tasks 4-5.

**Placeholder scan :** aucun TBD/TODO. Tous les pas contiennent du code complet.

**Type consistency :** `chargerProfils()` retourne `{profils, profil_actif}` partout. `mettreAJourProfilActif(champs)` appelé avec `lireChampsForm()` dans Task 5 — cohérent avec la signature définie Task 3. `rafraichirSelectProfil()` nom identique en Task 4 et Task 5.
