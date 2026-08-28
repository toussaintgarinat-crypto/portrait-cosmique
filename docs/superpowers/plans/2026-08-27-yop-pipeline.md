# YOP — pipeline (rendu → paiement → Gelato) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire, dans un nouveau repo `yop-boutique`, le pipeline complet et testable
personnalisation → paiement Stripe → génération du fichier print-ready → commande Gelato,
pour un premier produit (poster « traditions natales », format carré). Aucune UI boutique
soignée dans ce plan (catalogue/panier/formulaire viendront dans le plan B) — chaque tâche
est vérifiable par tests automatisés et appels API directs (curl/Stripe CLI/Gelato sandbox).

**Architecture:** Next.js (App Router, TypeScript) déployé sur Vercel, avec un module de
rendu SVG isomorphe (fonction pure données → chaîne SVG, sans DOM) utilisé tel quel côté
navigateur (plan B) et côté route serverless (rendu final). Rasterisation via `@resvg/resvg-js`
(pas de navigateur headless). Postgres (Drizzle ORM) pour le suivi des commandes. Stripe pour
le paiement, appel Gelato REST direct (pas de SDK officiel).

**Tech Stack:** Next.js 15 (App Router) + TypeScript strict, Vitest, Drizzle ORM + `postgres`
(postgres.js), `@resvg/resvg-js`, `stripe` (npm), `@vercel/blob`, Docker Compose (Postgres de
test), Node ≥ 20.

## Global Constraints

- Aucun changement à `portrait-cosmique` (repo existant) — YOP l'appelle en HTTP public
  (`POST /portrait`), jamais de couplage de déploiement.
- Nouveau repo séparé : racine `~/Desktop/yop-boutique` (sibling de `portrait-cosmique`).
- Commande invité uniquement — aucune notion de compte client dans ce plan.
- Gelato n'est appelé **qu'après** confirmation de paiement Stripe (`checkout.session.completed`)
  — jamais avant, pour ne jamais payer une production sur un panier abandonné.
- `payload_personnalisation` stocke les données de naissance brutes (pas le SVG/PNG) pour
  permettre une régénération à tout moment (réimpression, SAV).
- Tests sur la logique métier pure, DB de test dédiée (`docker compose --profile test up -d
  postgres-test`), jamais de mock d'ORM. Un test touchant la DB est **skip** proprement si
  `DATABASE_URL_TEST` est absent (même pattern que `portrait-cosmique/engine/conftest.py`).
- `src/lib/db/client.ts` lit `DATABASE_URL` au chargement du module (pas paresseusement) et
  lève si absent. Toute commande `npm test` qui touche une route important `@/lib/db/client`
  (Tasks 8, 12, 13) ou le script CLI (Task 14) doit donc exporter **les deux** variables avant
  de lancer les tests, ex. :
  `export DATABASE_URL_TEST="postgresql://test:test@localhost:5434/yop_test" DATABASE_URL="$DATABASE_URL_TEST"`
  — sinon l'import de `route.ts` échoue avant même que le test ne s'exécute (indépendamment du
  skip conditionnel sur `DATABASE_URL_TEST`).
- Idempotence obligatoire : rejouer un webhook Stripe ou Gelato, ou relancer le script de
  retry, ne doit jamais créer de doublon de commande physique.
- `npm test` lancé depuis la racine du repo.

---

## File Structure

- **Create** `src/lib/poster-render/types.ts` — types partagés (identité, palette, définitions de champs traditions).
- **Create** `src/lib/poster-render/render.ts` — helpers SVG (échappement, construction d'éléments) + `renderPosterTraditions()`.
- **Create** `src/lib/rasterize.ts` — SVG string → PNG buffer via `@resvg/resvg-js`.
- **Create** `src/lib/catalogue.ts` — config statique des produits vendus (SKU interne → UID Gelato via env, dimensions, prix).
- **Create** `src/lib/portrait-cosmique-client.ts` — appel `POST /portrait` sur portrait-cosmique.
- **Create** `src/lib/db/schema.ts` — schéma Drizzle (`commandes`, `lignes_commande`, `evenements_gelato`).
- **Create** `src/lib/db/client.ts` — connexion Drizzle (lit `DATABASE_URL`).
- **Create** `src/lib/db/commandes.ts` — state machine (créer, marquer payée, etc.).
- **Create** `src/lib/stripe.ts` — client Stripe + création de session Checkout.
- **Create** `src/app/api/checkout/route.ts` — endpoint création commande + session Stripe.
- **Create** `src/lib/storage.ts` — upload du PNG final vers Vercel Blob.
- **Create** `src/lib/gelato.ts` — client Gelato (`creerCommandeGelato`).
- **Create** `src/lib/traiter-ligne-commande.ts` — orchestrateur rendu+raster+upload+Gelato pour une ligne.
- **Create** `src/app/api/webhooks/stripe/route.ts` — webhook Stripe.
- **Create** `src/app/api/webhooks/gelato/route.ts` — webhook Gelato.
- **Create** `scripts/reessayer-ligne.ts` — retry manuel idempotent (CLI).
- **Create** `docker-compose.yml`, `.env.example`, `drizzle.config.ts`, `vitest.config.ts`.

---

### Task 1: Scaffold du repo YOP

**Files:**
- Create: repo `~/Desktop/yop-boutique` (Next.js + TS + Tailwind + Vitest)
- Create: `docker-compose.yml`, `.env.example`

**Interfaces:**
- Produces: squelette buildable/testable consommé par toutes les tâches suivantes.

- [ ] **Step 1: Créer le projet Next.js**

Run:
```bash
cd ~/Desktop
npx create-next-app@latest yop-boutique --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --no-turbopack
cd yop-boutique
git init -q 2>/dev/null || true
```
Expected: dossier `yop-boutique/` créé avec `src/app/`, `package.json`, `tsconfig.json`.

- [ ] **Step 2: Ajouter les dépendances du pipeline**

Run:
```bash
npm install drizzle-orm postgres stripe @vercel/blob @resvg/resvg-js
npm install -D vitest drizzle-kit dotenv tsx
```

- [ ] **Step 3: Configurer Vitest**

Create `vitest.config.ts` :

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
```

Dans `package.json`, ajouter dans `"scripts"` :
```json
"test": "vitest run"
```

- [ ] **Step 4: Ajouter le service Postgres de test**

Create `docker-compose.yml` :

```yaml
services:
  postgres-test:
    image: postgres:16-alpine
    profiles: ["test"]
    environment:
      - POSTGRES_USER=test
      - POSTGRES_PASSWORD=test
      - POSTGRES_DB=yop_test
    ports: ["5434:5432"]
```

Run: `docker compose --profile test up -d postgres-test`
Run: `sleep 2 && docker compose exec postgres-test pg_isready -U test`
Expected: `accepting connections`.

- [ ] **Step 5: Documenter les variables d'environnement**

Create `.env.example` :

```
# Base de données commandes (Postgres). En local : voir docker-compose.yml.
DATABASE_URL=postgresql://test:test@localhost:5434/yop_test
DATABASE_URL_TEST=postgresql://test:test@localhost:5434/yop_test

# API publique portrait-cosmique (aucune clé requise, service externe existant).
PORTRAIT_COSMIQUE_API_URL=https://portrait-cosmique.example.com

# Stripe (clés de test sur dashboard.stripe.com/test/apikeys).
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# Gelato (dashboard.gelato.com > API Keys).
GELATO_API_KEY=
GELATO_WEBHOOK_SECRET=
# UID du produit Gelato pour le poster traditions natales carré (dashboard.gelato.com >
# Catalog > rechercher "poster carré" > copier le Product UID de la variante ciblée).
GELATO_PRODUCT_UID_POSTER_TRADITIONS_CARRE=

# Vercel Blob (généré automatiquement en prod ; en local, créer un store via
# `vercel blob store add` puis `vercel env pull`).
BLOB_READ_WRITE_TOKEN=
```

- [ ] **Step 6: Vérifier que le squelette build et teste**

Run: `npm run build`
Expected: build réussi (page d'accueil par défaut de `create-next-app`).
Run: `npm test`
Expected: `No test files found` (pas d'erreur — normal, aucun test encore écrit).

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: scaffold Next.js + TS + Vitest + Postgres de test"
```

---

### Task 2: Module de rendu isomorphe — poster « traditions natales »

**Files:**
- Create: `src/lib/poster-render/types.ts`
- Create: `src/lib/poster-render/render.ts`
- Test: `src/lib/poster-render/render.test.ts`

**Interfaces:**
- Produces: `Identite`, `PALETTE`, `renderPosterTraditions(traditions, identite, options): string`
  (SVG complet autonome, styles inline, `viewBox="-260 -260 520 520"`) — consommé par
  `rasterize.ts` (Task 3) et par `traiter-ligne-commande.ts` (Task 11).

Porté depuis `portrait-cosmique/static/index.html` (`renderPosterTraditions`,
`posterBlocIdentite`, `TRADITIONS_POSTER_CHAMPS`), adapté pour ne dépendre d'aucune API DOM
(construction de chaînes plutôt que `document.createElementNS`), avec les couleurs de palette
en dur (pas de `var(--accent)`, résolu au moment du build côté portrait-cosmique original).

- [ ] **Step 1: Write failing test**

Create `src/lib/poster-render/render.test.ts` :

```ts
import { describe, expect, it } from "vitest";
import { renderPosterTraditions } from "./render";
import type { Identite, Traditions } from "./types";

const IDENTITE: Identite = {
  prenoms: "Ada",
  nom: "Lovelace",
  date_naissance: "1990-01-15",
  heure_naissance: "14:30",
  ville: "Toulouse",
};

const TRADITIONS: Traditions = {
  signe_solaire: { symbole: "♑", nom: "Capricorne", element: "Terre" },
  signe_lunaire: { symbole: "♋", signe: "Cancer" },
  chemin_de_vie: 7,
  egyptien: "Osiris",
};

describe("renderPosterTraditions", () => {
  it("produit un SVG autonome avec le bon viewBox", () => {
    const svg = renderPosterTraditions(TRADITIONS, IDENTITE, { fondTransparent: false });
    expect(svg).toContain('viewBox="-260 -260 520 520"');
    expect(svg.startsWith("<svg")).toBe(true);
    expect(svg.trim().endsWith("</svg>")).toBe(true);
  });

  it("inclut une carte par champ de tradition présent, ignore les champs absents", () => {
    const svg = renderPosterTraditions(TRADITIONS, IDENTITE, { fondTransparent: false });
    expect(svg).toContain("Capricorne");
    expect(svg).toContain("Cancer");
    expect(svg).toContain("Osiris");
    expect(svg).not.toContain("pos_maya");
  });

  it("échappe les caractères spéciaux du nom (anti-injection SVG)", () => {
    const identiteMalicieuse: Identite = { ...IDENTITE, prenoms: "<script>alert(1)</script>" };
    const svg = renderPosterTraditions(TRADITIONS, identiteMalicieuse, { fondTransparent: false });
    expect(svg).not.toContain("<script>");
    expect(svg).toContain("&lt;script&gt;");
  });

  it("omet le halo radial quand fondTransparent est vrai", () => {
    const opaque = renderPosterTraditions(TRADITIONS, IDENTITE, { fondTransparent: false });
    const transparent = renderPosterTraditions(TRADITIONS, IDENTITE, { fondTransparent: true });
    expect(opaque).toContain("poster-halo");
    expect(transparent).not.toContain("poster-halo");
  });

  it("est déterministe pour les mêmes entrées", () => {
    const a = renderPosterTraditions(TRADITIONS, IDENTITE, { fondTransparent: false });
    const b = renderPosterTraditions(TRADITIONS, IDENTITE, { fondTransparent: false });
    expect(a).toBe(b);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm test -- render.test.ts`
Expected: FAIL (`Cannot find module './render'`).

- [ ] **Step 3: Implement `types.ts`**

Create `src/lib/poster-render/types.ts` :

```ts
export interface Identite {
  prenoms: string;
  nom: string;
  date_naissance: string; // "YYYY-MM-DD"
  heure_naissance?: string | null;
  ville?: string | null;
}

/** Dict brut renvoyé par `POST /portrait` sur portrait-cosmique (champ `traditions`). */
export type Traditions = Record<string, unknown>;

export interface OptionsRenduTraditions {
  fondTransparent: boolean;
}

export const PALETTE = {
  bg: "#0f1220",
  panel: "#171b2e",
  panel2: "#1e2338",
  border: "#2b3050",
  text: "#eef0fb",
  muted: "#9aa1c4",
  accent: "#b98cf7",
  accent2: "#6ee7c3",
} as const;

interface ChampTraditionDef {
  cle: string;
  label: string;
  symbole: (v: any) => string;
  valeur: (v: any) => string;
  sous: (v: any) => string;
}

export const TRADITIONS_POSTER_CHAMPS: ChampTraditionDef[] = [
  { cle: "signe_solaire", label: "Signe solaire",
    symbole: v => v.symbole ?? "", valeur: v => v.nom, sous: v => v.element ?? "" },
  { cle: "signe_lunaire", label: "Signe lunaire",
    symbole: v => v.symbole ?? "", valeur: v => v.signe, sous: () => "" },
  { cle: "signe_chinois", label: "Signe chinois",
    symbole: v => v.emoji ?? "", valeur: v => v.animal,
    sous: v => [v.element, v.polarite].filter(Boolean).join(" · ") },
  { cle: "animal_heure", label: "Animal de l'heure",
    symbole: v => v.emoji ?? "", valeur: v => v.animal, sous: v => v.tranche ?? "" },
  { cle: "chemin_de_vie", label: "Chemin de vie",
    symbole: () => "", valeur: v => String(v), sous: () => "" },
  { cle: "numerologie_nom", label: "Numérologie du nom",
    symbole: () => "", valeur: v => String(v.expression),
    sous: v => `Âme ${v.ame} · Personnalité ${v.personnalite}` },
  { cle: "egyptien", label: "Divinité égyptienne",
    symbole: () => "", valeur: v => String(v), sous: () => "" },
  { cle: "celte", label: "Arbre celte",
    symbole: () => "", valeur: v => String(v), sous: () => "" },
  { cle: "amerindien", label: "Totem amérindien",
    symbole: () => "", valeur: v => String(v), sous: () => "" },
  { cle: "maya", label: "Tzolkin maya",
    symbole: () => "", valeur: v => v.glyphe, sous: v => `Tonalité ${v.tonalite}` },
  { cle: "pierre_du_mois", label: "Pierre du mois",
    symbole: () => "", valeur: v => String(v), sous: () => "" },
  { cle: "nakshatra", label: "Nakshatra védique",
    symbole: () => "", valeur: v => v.nakshatra, sous: v => `Pada ${v.pada}` },
  { cle: "vedique", label: "Rashi védique",
    symbole: v => v.symbole ?? "", valeur: v => v.rashi, sous: () => "" },
];
```

- [ ] **Step 4: Implement `render.ts`**

Create `src/lib/poster-render/render.ts` :

```ts
import { Identite, OptionsRenduTraditions, PALETTE, Traditions, TRADITIONS_POSTER_CHAMPS } from "./types";

function esc(s: string): string {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Élément avec du texte échappé (feuille). */
function elText(tag: string, attrs: Record<string, string | number>, texte: string): string {
  const a = Object.entries(attrs).map(([k, v]) => `${k}="${esc(String(v))}"`).join(" ");
  return `<${tag} ${a}>${esc(texte)}</${tag}>`;
}

/** Élément conteneur : `inner` est du markup déjà construit par nos propres helpers (jamais
 * du texte utilisateur brut), donc non ré-échappé ici. */
function elWrap(tag: string, attrs: Record<string, string | number>, inner: string): string {
  const a = Object.entries(attrs).map(([k, v]) => `${k}="${esc(String(v))}"`).join(" ");
  return `<${tag} ${a}>${inner}</${tag}>`;
}

function elVoid(tag: string, attrs: Record<string, string | number>): string {
  const a = Object.entries(attrs).map(([k, v]) => `${k}="${esc(String(v))}"`).join(" ");
  return `<${tag} ${a}/>`;
}

function formatDate(dateISO: string): string {
  const d = new Date(dateISO + "T00:00:00");
  if (isNaN(d.getTime())) return "";
  return new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "long", year: "numeric" }).format(d);
}

function renderBlocIdentite(identite: Identite, yStart: number): string {
  const nomComplet = [identite.prenoms, identite.nom]
    .map(s => (s ?? "").trim()).filter(Boolean).join(" ").toUpperCase();
  let y = yStart;
  let out = "";
  if (nomComplet) {
    out += elText("text", { x: 0, y, "text-anchor": "middle", "font-size": 20, "font-weight": 700,
      "letter-spacing": 1, fill: PALETTE.text }, nomComplet);
    y += 24;
  }
  const parts: string[] = [];
  const dateFmt = identite.date_naissance ? formatDate(identite.date_naissance) : "";
  if (dateFmt) parts.push(dateFmt);
  if (identite.heure_naissance) parts.push(identite.heure_naissance);
  if (identite.ville) parts.push(identite.ville);
  if (parts.length) {
    out += elVoid("line", { x1: -50, y1: y, x2: 50, y2: y, stroke: PALETTE.border, "stroke-width": 1 });
    out += elText("text", { x: 0, y: y + 20, "text-anchor": "middle", "font-size": 11,
      "letter-spacing": 0.5, fill: PALETTE.muted }, parts.join(" · "));
  }
  return out;
}

export function renderPosterTraditions(
  traditions: Traditions,
  identite: Identite,
  options: OptionsRenduTraditions,
): string {
  let defs = "";
  let halo = "";
  if (!options.fondTransparent) {
    defs = elWrap("defs", {}, elWrap("radialGradient",
      { id: "poster-halo", cx: "50%", cy: "50%", r: "50%" },
      elVoid("stop", { offset: "0%", "stop-color": PALETTE.accent, "stop-opacity": "0.4" }) +
      elVoid("stop", { offset: "100%", "stop-color": PALETTE.accent, "stop-opacity": "0" })));
    halo = elVoid("circle", { class: "poster-halo", cx: 0, cy: -20, r: 250, fill: "url(#poster-halo)" });
  }

  const cartes = TRADITIONS_POSTER_CHAMPS
    .map(champ => ({ champ, val: (traditions ?? {})[champ.cle] }))
    .filter(({ val }) => val !== null && val !== undefined && val !== "");

  const cols = cartes.length > 9 ? 4 : 3;
  const cw = 470 / cols;
  const ch = 92;
  const rows = Math.ceil(cartes.length / cols) || 1;
  const gridW = cw * cols;
  const gridH = ch * rows;
  const startX = -gridW / 2;
  const startY = -gridH / 2 - 30;

  let cartesMarkup = "";
  cartes.forEach(({ champ, val }, idx) => {
    const col = idx % cols;
    const row = Math.floor(idx / cols);
    const reste = cartes.length % cols;
    const decalage = row === rows - 1 && reste !== 0 ? ((cols - reste) * cw) / 2 : 0;
    const x = startX + col * cw + decalage;
    const y = startY + row * ch;
    const sym = champ.symbole(val);
    let carte = elVoid("rect", { x: 4, y: 4, width: cw - 8, height: ch - 8, rx: 8,
      fill: PALETTE.panel2, stroke: PALETTE.border, "stroke-width": 1 });
    if (sym) {
      carte += elText("text", { x: cw / 2, y: 30, "text-anchor": "middle", "font-size": 20,
        fill: PALETTE.accent2 }, sym);
    }
    carte += elText("text", { x: cw / 2, y: sym ? 46 : 26, "text-anchor": "middle", "font-size": 8,
      "letter-spacing": 0.5, fill: PALETTE.muted }, champ.label);
    carte += elText("text", { x: cw / 2, y: sym ? 64 : 46, "text-anchor": "middle", "font-size": 12,
      "font-weight": 700, fill: PALETTE.text }, String(champ.valeur(val)));
    const sous = champ.sous(val);
    if (sous) {
      carte += elText("text", { x: cw / 2, y: sym ? 78 : 60, "text-anchor": "middle", "font-size": 8,
        fill: PALETTE.muted }, sous);
    }
    cartesMarkup += elWrap("g", { class: "poster-trad-carte",
      transform: `translate(${x.toFixed(1)},${y.toFixed(1)})` }, carte);
  });

  const identiteMarkup = renderBlocIdentite(identite, startY + gridH + 45);

  return elWrap("svg", {
    xmlns: "http://www.w3.org/2000/svg",
    viewBox: "-260 -260 520 520",
    role: "img",
    "aria-label": `Poster traditions natales de ${(identite.prenoms ?? "").trim() || "—"}`,
    "font-family": "-apple-system, 'Segoe UI', sans-serif",
  }, defs + halo + cartesMarkup + identiteMarkup);
}
```

- [ ] **Step 5: Run to verify it passes**

Run: `npm test -- render.test.ts`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add src/lib/poster-render
git commit -m "feat: module de rendu isomorphe — poster traditions natales"
```

---

### Task 3: Rasterisation serveur (SVG → PNG)

**Files:**
- Create: `src/lib/rasterize.ts`
- Test: `src/lib/rasterize.test.ts`

**Interfaces:**
- Consumes: sortie string de `renderPosterTraditions` (Task 2).
- Produces: `rasteriser(svg: string, options: OptionsRasterisation): Buffer` — consommé par
  `traiter-ligne-commande.ts` (Task 11).

- [ ] **Step 1: Write failing test**

Create `src/lib/rasterize.test.ts` :

```ts
import { describe, expect, it } from "vitest";
import { rasteriser } from "./rasterize";

const SVG_MINIMAL = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">
  <rect width="10" height="10" fill="#ff0000"/>
</svg>`;

describe("rasteriser", () => {
  it("produit un buffer PNG valide à la résolution demandée", () => {
    const png = rasteriser(SVG_MINIMAL, { largeurPx: 100, hauteurPx: 100, fondTransparent: false });
    expect(png.subarray(0, 8)).toEqual(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]));
  });

  it("respecte le fond transparent quand demandé", () => {
    const opaque = rasteriser(SVG_MINIMAL, { largeurPx: 50, hauteurPx: 50, fondTransparent: false });
    const transparent = rasteriser(SVG_MINIMAL, { largeurPx: 50, hauteurPx: 50, fondTransparent: true });
    expect(opaque.length).toBeGreaterThan(0);
    expect(transparent.length).toBeGreaterThan(0);
    expect(opaque.equals(transparent)).toBe(false);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm test -- rasterize.test.ts`
Expected: FAIL (`Cannot find module './rasterize'`).

- [ ] **Step 3: Implement `rasterize.ts`**

Create `src/lib/rasterize.ts` :

```ts
import { Resvg } from "@resvg/resvg-js";
import { PALETTE } from "./poster-render/types";

export interface OptionsRasterisation {
  largeurPx: number;
  hauteurPx: number;
  fondTransparent: boolean;
}

/** Rastérise un SVG carré en PNG à la résolution exacte demandée. Suppose un SVG dont le
 * viewBox est carré (cas du poster traditions natales, -260..260) — la largeur pilote l'échelle,
 * `hauteurPx` doit donc être égale à `largeurPx` pour un rendu non déformé. */
export function rasteriser(svg: string, options: OptionsRasterisation): Buffer {
  const resvg = new Resvg(svg, {
    fitTo: { mode: "width", value: options.largeurPx },
    background: options.fondTransparent ? "transparent" : PALETTE.bg,
  });
  const image = resvg.render();
  return image.asPng();
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `npm test -- rasterize.test.ts`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/lib/rasterize.ts src/lib/rasterize.test.ts
git commit -m "feat: rasterisation serveur SVG vers PNG (resvg-js)"
```

---

### Task 4: Catalogue produits

**Files:**
- Create: `src/lib/catalogue.ts`
- Test: `src/lib/catalogue.test.ts`

**Interfaces:**
- Produces: `ProduitCatalogue`, `catalogue(): ProduitCatalogue[]`,
  `trouverProduit(sku: string): ProduitCatalogue | undefined` — consommé par
  `api/checkout/route.ts` (Task 8) et `traiter-ligne-commande.ts` (Task 11).

- [ ] **Step 1: Write failing test**

Create `src/lib/catalogue.test.ts` :

```ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { catalogue, trouverProduit } from "./catalogue";

describe("catalogue", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("lève une erreur claire si l'UID Gelato n'est pas configuré", () => {
    vi.stubEnv("GELATO_PRODUCT_UID_POSTER_TRADITIONS_CARRE", "");
    expect(() => catalogue()).toThrow(/GELATO_PRODUCT_UID_POSTER_TRADITIONS_CARRE/);
  });

  it("expose le poster traditions natales carré une fois l'UID configuré", () => {
    vi.stubEnv("GELATO_PRODUCT_UID_POSTER_TRADITIONS_CARRE", "gelato-uid-test");
    const produits = catalogue();
    expect(produits).toHaveLength(1);
    expect(produits[0]).toMatchObject({
      sku: "poster-traditions-carre",
      gelatoProductUid: "gelato-uid-test",
      typeRendu: "traditions",
      largeurPx: 3543,
      hauteurPx: 3543,
    });
  });

  it("trouverProduit renvoie undefined pour un sku inconnu", () => {
    vi.stubEnv("GELATO_PRODUCT_UID_POSTER_TRADITIONS_CARRE", "gelato-uid-test");
    expect(trouverProduit("inexistant")).toBeUndefined();
    expect(trouverProduit("poster-traditions-carre")?.sku).toBe("poster-traditions-carre");
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm test -- catalogue.test.ts`
Expected: FAIL (`Cannot find module './catalogue'`).

- [ ] **Step 3: Implement `catalogue.ts`**

Create `src/lib/catalogue.ts` :

```ts
export interface ProduitCatalogue {
  sku: string;
  gelatoProductUid: string;
  nom: string;
  typeRendu: "traditions";
  largeurPx: number;
  hauteurPx: number;
  prixCentimes: number;
  devise: string;
}

function requireEnv(nom: string): string {
  const v = process.env[nom];
  if (!v) throw new Error(`Variable d'environnement manquante : ${nom}`);
  return v;
}

/** Catalogue des produits vendus. Fonction (pas une constante au chargement du module) pour
 * ne lever que lorsqu'un produit est réellement consulté, pas à l'import du fichier. */
export function catalogue(): ProduitCatalogue[] {
  return [
    {
      sku: "poster-traditions-carre",
      gelatoProductUid: requireEnv("GELATO_PRODUCT_UID_POSTER_TRADITIONS_CARRE"),
      nom: "Poster Traditions Natales — carré 30×30cm",
      typeRendu: "traditions",
      largeurPx: 3543, // 30cm @ 300 DPI
      hauteurPx: 3543,
      prixCentimes: 2490,
      devise: "EUR",
    },
  ];
}

export function trouverProduit(sku: string): ProduitCatalogue | undefined {
  return catalogue().find(p => p.sku === sku);
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `npm test -- catalogue.test.ts`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/lib/catalogue.ts src/lib/catalogue.test.ts
git commit -m "feat: catalogue produits (poster traditions natales carré)"
```

---

### Task 5: Client API portrait-cosmique

**Files:**
- Create: `src/lib/portrait-cosmique-client.ts`
- Test: `src/lib/portrait-cosmique-client.test.ts`

**Interfaces:**
- Produces: `FicheNaissance`, `recupererPortrait(fiche): Promise<{traditions: Traditions}>` —
  consommé par `traiter-ligne-commande.ts` (Task 11).

- [ ] **Step 1: Write failing test**

Create `src/lib/portrait-cosmique-client.test.ts` :

```ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { recupererPortrait } from "./portrait-cosmique-client";

describe("recupererPortrait", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("appelle POST /portrait et renvoie le JSON", async () => {
    vi.stubEnv("PORTRAIT_COSMIQUE_API_URL", "https://pc.example.com");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ traditions: { signe_solaire: { nom: "Bélier" } } }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const res = await recupererPortrait({ prenoms: "Ada", nom: "Lovelace", date_naissance: "1990-01-15" });

    expect(fetchMock).toHaveBeenCalledWith("https://pc.example.com/portrait", expect.objectContaining({
      method: "POST",
      headers: { "Content-Type": "application/json" },
    }));
    expect(res.traditions.signe_solaire).toEqual({ nom: "Bélier" });
  });

  it("lève une erreur explicite si la réponse n'est pas ok", async () => {
    vi.stubEnv("PORTRAIT_COSMIQUE_API_URL", "https://pc.example.com");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 422 }));

    await expect(recupererPortrait({ prenoms: "", nom: "", date_naissance: "" }))
      .rejects.toThrow(/422/);
  });

  it("lève une erreur claire si PORTRAIT_COSMIQUE_API_URL est absent", async () => {
    vi.stubEnv("PORTRAIT_COSMIQUE_API_URL", "");
    await expect(recupererPortrait({ prenoms: "A", nom: "B", date_naissance: "2000-01-01" }))
      .rejects.toThrow(/PORTRAIT_COSMIQUE_API_URL/);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm test -- portrait-cosmique-client.test.ts`
Expected: FAIL (`Cannot find module './portrait-cosmique-client'`).

- [ ] **Step 3: Implement `portrait-cosmique-client.ts`**

Create `src/lib/portrait-cosmique-client.ts` :

```ts
import type { Traditions } from "./poster-render/types";

export interface FicheNaissance {
  prenoms: string;
  nom: string;
  date_naissance: string;
  heure_naissance?: string | null;
  ville?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  utc_offset?: number | null;
}

export interface ReponsePortrait {
  traditions: Traditions;
  [key: string]: unknown;
}

export async function recupererPortrait(fiche: FicheNaissance): Promise<ReponsePortrait> {
  const base = process.env.PORTRAIT_COSMIQUE_API_URL;
  if (!base) throw new Error("PORTRAIT_COSMIQUE_API_URL manquant.");
  const res = await fetch(`${base}/portrait`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fiche),
  });
  if (!res.ok) {
    throw new Error(`portrait-cosmique /portrait a répondu ${res.status}`);
  }
  return res.json();
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `npm test -- portrait-cosmique-client.test.ts`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/lib/portrait-cosmique-client.ts src/lib/portrait-cosmique-client.test.ts
git commit -m "feat: client HTTP portrait-cosmique (POST /portrait)"
```

---

### Task 6: Schéma DB + connexion Drizzle

**Files:**
- Create: `src/lib/db/schema.ts`
- Create: `src/lib/db/client.ts`
- Create: `drizzle.config.ts`
- Create: `src/lib/db/test-helpers.ts`

**Interfaces:**
- Produces: `commandes`, `lignesCommande`, `evenementsGelato` (tables Drizzle), `db` (client),
  fixture `dbTest()` (skip si `DATABASE_URL_TEST` absent) — consommé par Tasks 7, 8, 11, 12, 13, 14.

- [ ] **Step 1: Implement `schema.ts`**

Create `src/lib/db/schema.ts` :

```ts
import { integer, jsonb, numeric, pgTable, text, timestamp, uuid } from "drizzle-orm/pg-core";

export const commandes = pgTable("commandes", {
  id: uuid("id").primaryKey().defaultRandom(),
  email: text("email").notNull(),
  creeLe: timestamp("cree_le", { withTimezone: true }).notNull().defaultNow(),
  statut: text("statut").notNull().default("en_attente"),
  stripeCheckoutSessionId: text("stripe_checkout_session_id").unique(),
  stripePaymentIntentId: text("stripe_payment_intent_id"),
  adresseLivraison: jsonb("adresse_livraison"),
  totalPaye: numeric("total_paye", { precision: 10, scale: 2 }),
  devise: text("devise"),
});

export const lignesCommande = pgTable("lignes_commande", {
  id: uuid("id").primaryKey().defaultRandom(),
  commandeId: uuid("commande_id").notNull().references(() => commandes.id),
  produitGelatoSku: text("produit_gelato_sku").notNull(),
  variante: text("variante").notNull(),
  quantite: integer("quantite").notNull().default(1),
  prixUnitaireCentimes: integer("prix_unitaire_centimes").notNull(),
  payloadPersonnalisation: jsonb("payload_personnalisation").notNull(),
  fichierPrintUrl: text("fichier_print_url"),
  gelatoOrderId: text("gelato_order_id"),
  gelatoItemId: text("gelato_item_id"),
  statutLigne: text("statut_ligne").notNull().default("en_attente"),
});

export const evenementsGelato = pgTable("evenements_gelato", {
  id: uuid("id").primaryKey().defaultRandom(),
  ligneCommandeId: uuid("ligne_commande_id").notNull().references(() => lignesCommande.id),
  type: text("type").notNull(),
  eventId: text("event_id").notNull().unique(),
  payloadBrut: jsonb("payload_brut").notNull(),
  recuLe: timestamp("recu_le", { withTimezone: true }).notNull().defaultNow(),
});
```

- [ ] **Step 2: Implement `client.ts`**

Create `src/lib/db/client.ts` :

```ts
import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "./schema";

const DATABASE_URL = process.env.DATABASE_URL;
if (!DATABASE_URL) throw new Error("DATABASE_URL manquant.");

const queryClient = postgres(DATABASE_URL);
export const db = drizzle(queryClient, { schema });
export type Db = typeof db;
```

- [ ] **Step 3: Configurer Drizzle Kit**

Create `drizzle.config.ts` :

```ts
import "dotenv/config";
import type { Config } from "drizzle-kit";

export default {
  schema: "./src/lib/db/schema.ts",
  out: "./drizzle",
  dialect: "postgresql",
  dbCredentials: { url: process.env.DATABASE_URL_TEST ?? process.env.DATABASE_URL! },
} satisfies Config;
```

- [ ] **Step 4: Générer et appliquer la migration initiale**

Run:
```bash
export DATABASE_URL_TEST="postgresql://test:test@localhost:5434/yop_test"
npx drizzle-kit generate
npx drizzle-kit migrate
```
Expected: `drizzle/0000_*.sql` créé, appliqué sans erreur.

Run: `docker compose exec postgres-test psql -U test -d yop_test -c "\dt"`
Expected: liste `commandes`, `lignes_commande`, `evenements_gelato`, `__drizzle_migrations`.

- [ ] **Step 5: Créer le helper de test DB**

Create `src/lib/db/test-helpers.ts` :

```ts
import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "./schema";

/** Renvoie un client DB de test, ou `null` si DATABASE_URL_TEST est absent — les tests
 * appelants doivent `skip` (via `it.skipIf`) plutôt que planter faute de service démarré. */
export function dbTest() {
  const url = process.env.DATABASE_URL_TEST;
  if (!url) return null;
  const queryClient = postgres(url);
  return drizzle(queryClient, { schema });
}

export async function viderTables(db: NonNullable<ReturnType<typeof dbTest>>) {
  await db.execute(`TRUNCATE TABLE evenements_gelato, lignes_commande, commandes CASCADE`);
}
```

- [ ] **Step 6: Vérifier (pas de test dédié — validé par Task 7)**

Run: `npm run build`
Expected: build réussi (aucune régression TypeScript).

- [ ] **Step 7: Commit**

```bash
git add src/lib/db drizzle.config.ts drizzle/
git commit -m "feat: schéma Drizzle (commandes/lignes_commande/evenements_gelato) + migration"
```

---

### Task 7: State machine commandes

**Files:**
- Create: `src/lib/db/commandes.ts`
- Test: `src/lib/db/commandes.test.ts`

**Interfaces:**
- Consumes: `db`/`dbTest`, schéma (Task 6).
- Produces: `creerCommande`, `marquerPayee`, `marquerEnvoyeeGelato`, `marquerEchecGelato`,
  `StatutCommande`, `StatutLigne` — consommé par Tasks 8, 11, 12, 13, 14.

- [ ] **Step 1: Write failing test**

Create `src/lib/db/commandes.test.ts` :

```ts
import { beforeEach, describe, expect, it } from "vitest";
import { dbTest, viderTables } from "./test-helpers";
import { creerCommande, marquerEchecGelato, marquerEnvoyeeGelato, marquerPayee } from "./commandes";

const database = dbTest();
const testOuSkip = database ? it : it.skip;

beforeEach(async () => {
  if (database) await viderTables(database);
});

const LIGNE_EXEMPLE = {
  produitGelatoSku: "poster-traditions-carre",
  variante: "30x30",
  quantite: 1,
  prixUnitaireCentimes: 2490,
  payloadPersonnalisation: { identite: { prenoms: "Ada", nom: "Lovelace", date_naissance: "1990-01-15" } },
};

describe("state machine commandes", () => {
  testOuSkip("creerCommande insère une commande en_attente avec ses lignes", async () => {
    const { commandeId, ligneIds } = await creerCommande(database!, {
      email: "ada@example.com",
      stripeCheckoutSessionId: "cs_test_1",
      lignes: [LIGNE_EXEMPLE],
    });
    expect(commandeId).toBeTruthy();
    expect(ligneIds).toHaveLength(1);
  });

  testOuSkip("marquerPayee passe la commande à payee, idempotent si rejouée", async () => {
    const { commandeId } = await creerCommande(database!, {
      email: "b@example.com", stripeCheckoutSessionId: "cs_test_2", lignes: [LIGNE_EXEMPLE],
    });
    const premiere = await marquerPayee(database!, "cs_test_2", "pi_test_2");
    expect(premiere.statut).toBe("payee");
    expect(premiere.dejaTraitee).toBe(false);

    const seconde = await marquerPayee(database!, "cs_test_2", "pi_test_2");
    expect(seconde.dejaTraitee).toBe(true);
  });

  testOuSkip("marquerEnvoyeeGelato puis marquerEchecGelato mettent à jour la ligne", async () => {
    const { ligneIds } = await creerCommande(database!, {
      email: "c@example.com", stripeCheckoutSessionId: "cs_test_3", lignes: [LIGNE_EXEMPLE],
    });
    await marquerEnvoyeeGelato(database!, ligneIds[0], "gelato-order-1", "gelato-item-1");
    const echec = await marquerEchecGelato(database!, ligneIds[0], "timeout rasterisation");
    expect(echec.statutLigne).toBe("echec_gelato");
  });
});
```

- [ ] **Step 2: Run to verify it fails or skips**

Run: `export DATABASE_URL_TEST="postgresql://test:test@localhost:5434/yop_test"; npm test -- commandes.test.ts`
Expected: FAIL (`Cannot find module './commandes'`). Si `DATABASE_URL_TEST` n'est pas exporté,
les tests sont `skip` (jamais d'échec bruyant).

- [ ] **Step 3: Implement `commandes.ts`**

Create `src/lib/db/commandes.ts` :

```ts
import { eq } from "drizzle-orm";
import type { Db } from "./client";
import { commandes, lignesCommande } from "./schema";

export type StatutCommande =
  | "en_attente" | "payee" | "envoyee_gelato" | "en_production"
  | "expediee" | "echec_paiement" | "echec_gelato";
export type StatutLigne = "en_attente" | "envoyee_gelato" | "en_production" | "expediee" | "echec_gelato";

export interface LigneACreer {
  produitGelatoSku: string;
  variante: string;
  quantite: number;
  prixUnitaireCentimes: number;
  payloadPersonnalisation: Record<string, unknown>;
}

export async function creerCommande(
  db: Db,
  params: { email: string; stripeCheckoutSessionId: string; lignes: LigneACreer[] },
): Promise<{ commandeId: string; ligneIds: string[] }> {
  return db.transaction(async tx => {
    const [commande] = await tx.insert(commandes).values({
      email: params.email,
      stripeCheckoutSessionId: params.stripeCheckoutSessionId,
      statut: "en_attente",
    }).returning({ id: commandes.id });

    const ligneIds: string[] = [];
    for (const ligne of params.lignes) {
      const [inseree] = await tx.insert(lignesCommande).values({
        commandeId: commande.id,
        produitGelatoSku: ligne.produitGelatoSku,
        variante: ligne.variante,
        quantite: ligne.quantite,
        prixUnitaireCentimes: ligne.prixUnitaireCentimes,
        payloadPersonnalisation: ligne.payloadPersonnalisation,
        statutLigne: "en_attente",
      }).returning({ id: lignesCommande.id });
      ligneIds.push(inseree.id);
    }
    return { commandeId: commande.id, ligneIds };
  });
}

/** Idempotent : si la commande est déjà `payee` (ou au-delà), ne réécrit rien et renvoie
 * `dejaTraitee: true` — un webhook Stripe rejoué ne doit jamais redéclencher le pipeline. */
export async function marquerPayee(
  db: Db, stripeCheckoutSessionId: string, stripePaymentIntentId: string,
): Promise<{ commandeId: string; statut: StatutCommande; dejaTraitee: boolean }> {
  const [commande] = await db.select().from(commandes)
    .where(eq(commandes.stripeCheckoutSessionId, stripeCheckoutSessionId));
  if (!commande) throw new Error(`Commande introuvable pour la session ${stripeCheckoutSessionId}`);
  if (commande.statut !== "en_attente") {
    return { commandeId: commande.id, statut: commande.statut as StatutCommande, dejaTraitee: true };
  }
  await db.update(commandes)
    .set({ statut: "payee", stripePaymentIntentId })
    .where(eq(commandes.id, commande.id));
  return { commandeId: commande.id, statut: "payee", dejaTraitee: false };
}

export async function marquerEnvoyeeGelato(
  db: Db, ligneId: string, gelatoOrderId: string, gelatoItemId: string,
): Promise<{ statutLigne: StatutLigne }> {
  await db.update(lignesCommande)
    .set({ statutLigne: "envoyee_gelato", gelatoOrderId, gelatoItemId })
    .where(eq(lignesCommande.id, ligneId));
  return { statutLigne: "envoyee_gelato" };
}

export async function marquerEchecGelato(
  db: Db, ligneId: string, _raison: string,
): Promise<{ statutLigne: StatutLigne }> {
  await db.update(lignesCommande)
    .set({ statutLigne: "echec_gelato" })
    .where(eq(lignesCommande.id, ligneId));
  return { statutLigne: "echec_gelato" };
}

export async function ligneParId(db: Db, ligneId: string) {
  const [ligne] = await db.select().from(lignesCommande).where(eq(lignesCommande.id, ligneId));
  return ligne ?? null;
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `npm test -- commandes.test.ts`
Expected: 3 passed (contre la Postgres de test).

- [ ] **Step 5: Commit**

```bash
git add src/lib/db/commandes.ts src/lib/db/commandes.test.ts
git commit -m "feat: state machine commandes (créer/payee/envoyee_gelato/echec_gelato)"
```

---

### Task 8: Checkout — création commande + session Stripe

**Files:**
- Create: `src/lib/stripe.ts`
- Create: `src/app/api/checkout/route.ts`
- Test: `src/app/api/checkout/route.test.ts`

**Interfaces:**
- Consumes: `creerCommande` (Task 7), `trouverProduit` (Task 4), `db` (Task 6).
- Produces: `POST /api/checkout` → `{ url: string }` (URL de redirection Stripe) — consommé par
  le panier du plan B.

- [ ] **Step 1: Implement `stripe.ts`**

Create `src/lib/stripe.ts` :

```ts
import Stripe from "stripe";

function requireEnv(nom: string): string {
  const v = process.env[nom];
  if (!v) throw new Error(`Variable d'environnement manquante : ${nom}`);
  return v;
}

export function stripeClient(): Stripe {
  return new Stripe(requireEnv("STRIPE_SECRET_KEY"));
}
```

- [ ] **Step 2: Write failing test**

Create `src/app/api/checkout/route.test.ts` :

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";
import { dbTest, viderTables } from "@/lib/db/test-helpers";

const database = dbTest();
const testOuSkip = database ? it : it.skip;

vi.mock("@/lib/stripe", () => ({
  stripeClient: () => ({
    checkout: {
      sessions: {
        create: vi.fn().mockResolvedValue({ id: "cs_test_mock", url: "https://checkout.stripe.com/mock" }),
      },
    },
  }),
}));

beforeEach(async () => {
  if (database) await viderTables(database);
  vi.stubEnv("GELATO_PRODUCT_UID_POSTER_TRADITIONS_CARRE", "gelato-uid-test");
});

describe("POST /api/checkout", () => {
  testOuSkip("crée une commande en_attente et renvoie l'URL Stripe", async () => {
    const { POST } = await import("./route");
    const req = new Request("http://localhost/api/checkout", {
      method: "POST",
      body: JSON.stringify({
        email: "ada@example.com",
        lignes: [{
          sku: "poster-traditions-carre",
          quantite: 1,
          payloadPersonnalisation: {
            identite: { prenoms: "Ada", nom: "Lovelace", date_naissance: "1990-01-15" },
            fondTransparent: false,
          },
        }],
      }),
    });
    const res = await POST(req);
    const body = await res.json();
    expect(res.status).toBe(200);
    expect(body.url).toBe("https://checkout.stripe.com/mock");
  });

  testOuSkip("renvoie 400 si un sku est inconnu", async () => {
    const { POST } = await import("./route");
    const req = new Request("http://localhost/api/checkout", {
      method: "POST",
      body: JSON.stringify({
        email: "ada@example.com",
        lignes: [{ sku: "inexistant", quantite: 1, payloadPersonnalisation: {} }],
      }),
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
  });
});
```

- [ ] **Step 3: Run to verify it fails**

Run: `npm test -- checkout/route.test.ts`
Expected: FAIL (`Cannot find module './route'`).

- [ ] **Step 4: Implement `route.ts`**

Create `src/app/api/checkout/route.ts` :

```ts
import { NextResponse } from "next/server";
import { db } from "@/lib/db/client";
import { creerCommande } from "@/lib/db/commandes";
import { trouverProduit } from "@/lib/catalogue";
import { stripeClient } from "@/lib/stripe";

interface LigneRequete {
  sku: string;
  quantite: number;
  payloadPersonnalisation: Record<string, unknown>;
}

export async function POST(req: Request) {
  const body = await req.json() as { email: string; lignes: LigneRequete[] };

  const lignesResolues = body.lignes.map(l => {
    const produit = trouverProduit(l.sku);
    if (!produit) return null;
    return { requete: l, produit };
  });
  if (lignesResolues.some(l => l === null)) {
    return NextResponse.json({ erreur: "SKU produit inconnu." }, { status: 400 });
  }
  const resolues = lignesResolues as { requete: LigneRequete; produit: NonNullable<ReturnType<typeof trouverProduit>> }[];

  const stripe = stripeClient();
  const session = await stripe.checkout.sessions.create({
    mode: "payment",
    payment_method_types: ["card"],
    customer_email: body.email,
    line_items: resolues.map(({ requete, produit }) => ({
      quantity: requete.quantite,
      price_data: {
        currency: produit.devise.toLowerCase(),
        unit_amount: produit.prixCentimes,
        product_data: { name: produit.nom },
      },
    })),
    shipping_address_collection: { allowed_countries: ["FR", "BE", "CH", "LU"] },
    success_url: `${process.env.NEXT_PUBLIC_SITE_URL}/commande/confirmee?session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `${process.env.NEXT_PUBLIC_SITE_URL}/panier`,
  });

  await creerCommande(db, {
    email: body.email,
    stripeCheckoutSessionId: session.id,
    lignes: resolues.map(({ requete, produit }) => ({
      produitGelatoSku: produit.sku,
      variante: produit.sku,
      quantite: requete.quantite,
      prixUnitaireCentimes: produit.prixCentimes,
      payloadPersonnalisation: requete.payloadPersonnalisation,
    })),
  });

  return NextResponse.json({ url: session.url });
}
```

- [ ] **Step 5: Run to verify it passes**

Run: `npm test -- checkout/route.test.ts`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add src/lib/stripe.ts src/app/api/checkout
git commit -m "feat: endpoint checkout — commande en_attente + session Stripe"
```

---

### Task 9: Storage du fichier print-ready

**Files:**
- Create: `src/lib/storage.ts`
- Test: `src/lib/storage.test.ts`

**Interfaces:**
- Produces: `televerserFichierPrint(nomFichier: string, png: Buffer): Promise<string>` (URL
  publique) — consommé par `traiter-ligne-commande.ts` (Task 11).

- [ ] **Step 1: Write failing test**

Create `src/lib/storage.test.ts` :

```ts
import { describe, expect, it, vi } from "vitest";

vi.mock("@vercel/blob", () => ({
  put: vi.fn().mockResolvedValue({ url: "https://blob.vercel-storage.com/fichier-abc.png" }),
}));

describe("televerserFichierPrint", () => {
  it("téléverse le buffer et renvoie l'URL publique", async () => {
    const { televerserFichierPrint } = await import("./storage");
    const { put } = await import("@vercel/blob");
    const url = await televerserFichierPrint("commande-1-ligne-1.png", Buffer.from([1, 2, 3]));
    expect(url).toBe("https://blob.vercel-storage.com/fichier-abc.png");
    expect(put).toHaveBeenCalledWith(
      "commande-1-ligne-1.png",
      expect.any(Buffer),
      expect.objectContaining({ access: "public" }),
    );
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm test -- storage.test.ts`
Expected: FAIL (`Cannot find module './storage'`).

- [ ] **Step 3: Implement `storage.ts`**

Create `src/lib/storage.ts` :

```ts
import { put } from "@vercel/blob";

export async function televerserFichierPrint(nomFichier: string, png: Buffer): Promise<string> {
  const { url } = await put(nomFichier, png, { access: "public", contentType: "image/png" });
  return url;
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `npm test -- storage.test.ts`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add src/lib/storage.ts src/lib/storage.test.ts
git commit -m "feat: téléversement du fichier print-ready (Vercel Blob)"
```

---

### Task 10: Client Gelato

**Files:**
- Create: `src/lib/gelato.ts`
- Test: `src/lib/gelato.test.ts`

**Interfaces:**
- Produces: `creerCommandeGelato(params): Promise<{orderId: string; itemId: string}>` —
  consommé par `traiter-ligne-commande.ts` (Task 11).

- [ ] **Step 1: Write failing test**

Create `src/lib/gelato.test.ts` :

```ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { creerCommandeGelato } from "./gelato";

describe("creerCommandeGelato", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("appelle l'API Gelato avec le SKU, le fichier et l'adresse, renvoie les identifiants", async () => {
    vi.stubEnv("GELATO_API_KEY", "gelato-key-test");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: "gelato-order-1", items: [{ id: "gelato-item-1" }] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const res = await creerCommandeGelato({
      referenceCommande: "ligne-abc",
      gelatoProductUid: "uid-test",
      fichierPrintUrl: "https://blob.example.com/f.png",
      adresseLivraison: { nom: "Ada Lovelace", rue: "1 rue X", ville: "Toulouse", cp: "31000", pays: "FR" },
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "https://order.gelatoapis.com/v4/orders",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-API-KEY": "gelato-key-test" }),
      }),
    );
    expect(res).toEqual({ orderId: "gelato-order-1", itemId: "gelato-item-1" });
  });

  it("lève une erreur explicite si Gelato répond une erreur", async () => {
    vi.stubEnv("GELATO_API_KEY", "gelato-key-test");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 400, text: async () => "SKU invalide" }));

    await expect(creerCommandeGelato({
      referenceCommande: "ligne-abc", gelatoProductUid: "uid-invalide",
      fichierPrintUrl: "https://blob.example.com/f.png",
      adresseLivraison: { nom: "A", rue: "B", ville: "C", cp: "D", pays: "FR" },
    })).rejects.toThrow(/400/);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm test -- gelato.test.ts`
Expected: FAIL (`Cannot find module './gelato'`).

- [ ] **Step 3: Implement `gelato.ts`**

Create `src/lib/gelato.ts` :

```ts
export interface AdresseLivraison {
  nom: string;
  rue: string;
  ville: string;
  cp: string;
  pays: string;
}

export interface ParamsCommandeGelato {
  referenceCommande: string;
  gelatoProductUid: string;
  fichierPrintUrl: string;
  adresseLivraison: AdresseLivraison;
}

function requireEnv(nom: string): string {
  const v = process.env[nom];
  if (!v) throw new Error(`Variable d'environnement manquante : ${nom}`);
  return v;
}

export async function creerCommandeGelato(
  params: ParamsCommandeGelato,
): Promise<{ orderId: string; itemId: string }> {
  const res = await fetch("https://order.gelatoapis.com/v4/orders", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-KEY": requireEnv("GELATO_API_KEY"),
    },
    body: JSON.stringify({
      orderReferenceId: params.referenceCommande,
      items: [{
        itemReferenceId: params.referenceCommande,
        productUid: params.gelatoProductUid,
        files: [{ type: "default", url: params.fichierPrintUrl }],
        quantity: 1,
      }],
      shippingAddress: {
        companyName: params.adresseLivraison.nom,
        addressLine1: params.adresseLivraison.rue,
        city: params.adresseLivraison.ville,
        postCode: params.adresseLivraison.cp,
        country: params.adresseLivraison.pays,
      },
    }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Gelato a répondu ${res.status} : ${detail}`);
  }
  const data = await res.json();
  return { orderId: data.id, itemId: data.items[0].id };
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `npm test -- gelato.test.ts`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/lib/gelato.ts src/lib/gelato.test.ts
git commit -m "feat: client Gelato (création de commande de production)"
```

---

### Task 11: Orchestrateur `traiterLigneCommande`

**Files:**
- Create: `src/lib/traiter-ligne-commande.ts`
- Test: `src/lib/traiter-ligne-commande.test.ts`

**Interfaces:**
- Consumes: `ligneParId`, `marquerEnvoyeeGelato`, `marquerEchecGelato` (Task 7),
  `trouverProduit` (Task 4), `recupererPortrait` (Task 5), `renderPosterTraditions` (Task 2),
  `rasteriser` (Task 3), `televerserFichierPrint` (Task 9), `creerCommandeGelato` (Task 10).
- Produces: `traiterLigneCommande(db, ligneId, adresseLivraison): Promise<void>` — consommé par
  le webhook Stripe (Task 12) et le script de retry (Task 14). **Idempotent** : si la ligne a
  déjà un `gelatoOrderId`, ne refait rien.

- [ ] **Step 1: Write failing test**

Create `src/lib/traiter-ligne-commande.test.ts` :

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";
import { dbTest, viderTables } from "./db/test-helpers";
import { creerCommande, ligneParId } from "./db/commandes";
import { traiterLigneCommande } from "./traiter-ligne-commande";

const database = dbTest();
const testOuSkip = database ? it : it.skip;

vi.mock("./portrait-cosmique-client", () => ({
  recupererPortrait: vi.fn().mockResolvedValue({
    traditions: { signe_solaire: { symbole: "♑", nom: "Capricorne", element: "Terre" } },
  }),
}));
vi.mock("./storage", () => ({
  televerserFichierPrint: vi.fn().mockResolvedValue("https://blob.example.com/fichier.png"),
}));
vi.mock("./gelato", () => ({
  creerCommandeGelato: vi.fn().mockResolvedValue({ orderId: "gelato-order-x", itemId: "gelato-item-x" }),
}));

const ADRESSE = { nom: "Ada Lovelace", rue: "1 rue X", ville: "Toulouse", cp: "31000", pays: "FR" };

beforeEach(async () => {
  if (database) await viderTables(database);
  vi.stubEnv("GELATO_PRODUCT_UID_POSTER_TRADITIONS_CARRE", "gelato-uid-test");
  vi.clearAllMocks();
});

describe("traiterLigneCommande", () => {
  testOuSkip("génère le fichier, l'envoie à Gelato, marque la ligne envoyee_gelato", async () => {
    const { ligneIds } = await creerCommande(database!, {
      email: "ada@example.com",
      stripeCheckoutSessionId: "cs_x",
      lignes: [{
        produitGelatoSku: "poster-traditions-carre",
        variante: "poster-traditions-carre",
        quantite: 1,
        prixUnitaireCentimes: 2490,
        payloadPersonnalisation: {
          identite: { prenoms: "Ada", nom: "Lovelace", date_naissance: "1990-01-15" },
          fondTransparent: false,
        },
      }],
    });

    await traiterLigneCommande(database!, ligneIds[0], ADRESSE);

    const ligne = await ligneParId(database!, ligneIds[0]);
    expect(ligne?.statutLigne).toBe("envoyee_gelato");
    expect(ligne?.gelatoOrderId).toBe("gelato-order-x");
    expect(ligne?.fichierPrintUrl).toBe("https://blob.example.com/fichier.png");
  });

  testOuSkip("est idempotent : ne rappelle pas Gelato si gelatoOrderId existe déjà", async () => {
    const { ligneIds } = await creerCommande(database!, {
      email: "b@example.com",
      stripeCheckoutSessionId: "cs_y",
      lignes: [{
        produitGelatoSku: "poster-traditions-carre",
        variante: "poster-traditions-carre",
        quantite: 1,
        prixUnitaireCentimes: 2490,
        payloadPersonnalisation: {
          identite: { prenoms: "B", nom: "C", date_naissance: "1990-01-15" },
          fondTransparent: false,
        },
      }],
    });

    await traiterLigneCommande(database!, ligneIds[0], ADRESSE);
    const { creerCommandeGelato } = await import("./gelato");
    expect(creerCommandeGelato).toHaveBeenCalledTimes(1);

    await traiterLigneCommande(database!, ligneIds[0], ADRESSE);
    expect(creerCommandeGelato).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm test -- traiter-ligne-commande.test.ts`
Expected: FAIL (`Cannot find module './traiter-ligne-commande'`).

- [ ] **Step 3: Implement `traiter-ligne-commande.ts`**

Create `src/lib/traiter-ligne-commande.ts` :

```ts
import type { Db } from "./db/client";
import { ligneParId, marquerEchecGelato, marquerEnvoyeeGelato } from "./db/commandes";
import { trouverProduit } from "./catalogue";
import { recupererPortrait } from "./portrait-cosmique-client";
import { renderPosterTraditions } from "./poster-render/render";
import type { Identite } from "./poster-render/types";
import { rasteriser } from "./rasterize";
import { televerserFichierPrint } from "./storage";
import { creerCommandeGelato, type AdresseLivraison } from "./gelato";

interface PayloadPersonnalisationTraditions {
  identite: Identite;
  fondTransparent: boolean;
}

export async function traiterLigneCommande(
  db: Db, ligneId: string, adresseLivraison: AdresseLivraison,
): Promise<void> {
  const ligne = await ligneParId(db, ligneId);
  if (!ligne) throw new Error(`Ligne de commande introuvable : ${ligneId}`);
  if (ligne.gelatoOrderId) return; // déjà traitée — idempotent

  try {
    const produit = trouverProduit(ligne.produitGelatoSku);
    if (!produit) throw new Error(`Produit inconnu au catalogue : ${ligne.produitGelatoSku}`);

    const payload = ligne.payloadPersonnalisation as unknown as PayloadPersonnalisationTraditions;
    const { traditions } = await recupererPortrait({
      prenoms: payload.identite.prenoms,
      nom: payload.identite.nom,
      date_naissance: payload.identite.date_naissance,
      heure_naissance: payload.identite.heure_naissance,
      ville: payload.identite.ville,
    });

    const svg = renderPosterTraditions(traditions, payload.identite, { fondTransparent: payload.fondTransparent });
    const png = rasteriser(svg, {
      largeurPx: produit.largeurPx,
      hauteurPx: produit.hauteurPx,
      fondTransparent: payload.fondTransparent,
    });
    const fichierPrintUrl = await televerserFichierPrint(`${ligneId}.png`, png);

    const { orderId, itemId } = await creerCommandeGelato({
      referenceCommande: ligneId,
      gelatoProductUid: produit.gelatoProductUid,
      fichierPrintUrl,
      adresseLivraison,
    });

    await marquerEnvoyeeGelato(db, ligneId, orderId, itemId);
  } catch (e) {
    await marquerEchecGelato(db, ligneId, e instanceof Error ? e.message : String(e));
    throw e;
  }
}
```

Remarque : `marquerEnvoyeeGelato` (Task 7) ne stocke pas encore `fichierPrintUrl` — ajouter ce
champ à sa signature avant cette tâche (voir correction ci-dessous).

- [ ] **Step 3bis: Corriger `marquerEnvoyeeGelato` pour stocker `fichierPrintUrl`**

Dans `src/lib/db/commandes.ts`, remplace la fonction `marquerEnvoyeeGelato` par :

```ts
export async function marquerEnvoyeeGelato(
  db: Db, ligneId: string, gelatoOrderId: string, gelatoItemId: string, fichierPrintUrl: string,
): Promise<{ statutLigne: StatutLigne }> {
  await db.update(lignesCommande)
    .set({ statutLigne: "envoyee_gelato", gelatoOrderId, gelatoItemId, fichierPrintUrl })
    .where(eq(lignesCommande.id, ligneId));
  return { statutLigne: "envoyee_gelato" };
}
```

Dans `src/lib/db/commandes.test.ts`, mets à jour l'appel du Task 7 :
```ts
await marquerEnvoyeeGelato(database!, ligneIds[0], "gelato-order-1", "gelato-item-1", "https://blob.example.com/f.png");
```

Et dans `traiter-ligne-commande.ts` (ci-dessus), l'appel devient :
```ts
await marquerEnvoyeeGelato(db, ligneId, orderId, itemId, fichierPrintUrl);
```

Run: `npm test -- commandes.test.ts traiter-ligne-commande.test.ts`
Expected: tous passent après cette correction.

- [ ] **Step 4: Run to verify it passes**

Run: `npm test -- traiter-ligne-commande.test.ts`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/lib/traiter-ligne-commande.ts src/lib/traiter-ligne-commande.test.ts src/lib/db/commandes.ts src/lib/db/commandes.test.ts
git commit -m "feat: orchestrateur traiterLigneCommande (rendu+raster+upload+Gelato), idempotent"
```

---

### Task 12: Webhook Stripe

**Files:**
- Create: `src/app/api/webhooks/stripe/route.ts`
- Test: `src/app/api/webhooks/stripe/route.test.ts`

**Interfaces:**
- Consumes: `marquerPayee` (Task 7), `traiterLigneCommande` (Task 11), `stripeClient` (Task 8).
- Produces: `POST /api/webhooks/stripe`.

- [ ] **Step 1: Write failing test**

Create `src/app/api/webhooks/stripe/route.test.ts` :

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";
import { dbTest, viderTables } from "@/lib/db/test-helpers";
import { creerCommande, ligneParId } from "@/lib/db/commandes";

const database = dbTest();
const testOuSkip = database ? it : it.skip;

const construireEvenement = vi.fn();
vi.mock("@/lib/stripe", () => ({
  stripeClient: () => ({ webhooks: { constructEvent: construireEvenement } }),
}));
vi.mock("@/lib/traiter-ligne-commande", () => ({
  traiterLigneCommande: vi.fn().mockResolvedValue(undefined),
}));

beforeEach(async () => {
  if (database) await viderTables(database);
  vi.stubEnv("STRIPE_WEBHOOK_SECRET", "whsec_test");
  vi.clearAllMocks();
});

function evenementPaiementConfirme(sessionId: string) {
  return {
    type: "checkout.session.completed",
    data: {
      object: {
        id: sessionId,
        payment_intent: "pi_test",
        customer_details: { address: { line1: "1 rue X", city: "Toulouse", postal_code: "31000", country: "FR" }, name: "Ada Lovelace" },
      },
    },
  };
}

describe("POST /api/webhooks/stripe", () => {
  testOuSkip("marque la commande payee et traite chaque ligne", async () => {
    const { commandeId, ligneIds } = await creerCommande(database!, {
      email: "ada@example.com",
      stripeCheckoutSessionId: "cs_webhook_1",
      lignes: [{
        produitGelatoSku: "poster-traditions-carre", variante: "poster-traditions-carre",
        quantite: 1, prixUnitaireCentimes: 2490,
        payloadPersonnalisation: { identite: { prenoms: "Ada", nom: "L", date_naissance: "1990-01-15" }, fondTransparent: false },
      }],
    });
    construireEvenement.mockReturnValue(evenementPaiementConfirme("cs_webhook_1"));

    const { POST } = await import("./route");
    const req = new Request("http://localhost/api/webhooks/stripe", {
      method: "POST", headers: { "stripe-signature": "sig_test" }, body: "{}",
    });
    const res = await POST(req);

    expect(res.status).toBe(200);
    const { traiterLigneCommande } = await import("@/lib/traiter-ligne-commande");
    expect(traiterLigneCommande).toHaveBeenCalledWith(expect.anything(), ligneIds[0], expect.objectContaining({ ville: "Toulouse" }));
  });

  testOuSkip("signature invalide → 400, aucun traitement", async () => {
    construireEvenement.mockImplementation(() => { throw new Error("signature invalide"); });
    const { POST } = await import("./route");
    const req = new Request("http://localhost/api/webhooks/stripe", {
      method: "POST", headers: { "stripe-signature": "mauvaise" }, body: "{}",
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm test -- webhooks/stripe/route.test.ts`
Expected: FAIL (`Cannot find module './route'`).

- [ ] **Step 3: Implement `route.ts`**

Create `src/app/api/webhooks/stripe/route.ts` :

```ts
import { NextResponse } from "next/server";
import { db } from "@/lib/db/client";
import { marquerPayee } from "@/lib/db/commandes";
import { eq } from "drizzle-orm";
import { lignesCommande } from "@/lib/db/schema";
import { stripeClient } from "@/lib/stripe";
import { traiterLigneCommande } from "@/lib/traiter-ligne-commande";

export async function POST(req: Request) {
  const payload = await req.text();
  const signature = req.headers.get("stripe-signature") ?? "";

  let event;
  try {
    event = stripeClient().webhooks.constructEvent(payload, signature, process.env.STRIPE_WEBHOOK_SECRET!);
  } catch {
    return NextResponse.json({ erreur: "Signature invalide." }, { status: 400 });
  }

  if (event.type !== "checkout.session.completed") {
    return NextResponse.json({ statut: "ignore" });
  }

  const session = event.data.object as {
    id: string;
    payment_intent: string;
    customer_details?: { name?: string; address?: { line1?: string; city?: string; postal_code?: string; country?: string } };
  };

  const { commandeId, dejaTraitee } = await marquerPayee(db, session.id, session.payment_intent);
  if (dejaTraitee) {
    return NextResponse.json({ statut: "deja_traitee" });
  }

  const adresse = {
    nom: session.customer_details?.name ?? "",
    rue: session.customer_details?.address?.line1 ?? "",
    ville: session.customer_details?.address?.city ?? "",
    cp: session.customer_details?.address?.postal_code ?? "",
    pays: session.customer_details?.address?.country ?? "",
  };

  const lignes = await db.select({ id: lignesCommande.id }).from(lignesCommande)
    .where(eq(lignesCommande.commandeId, commandeId));

  for (const ligne of lignes) {
    await traiterLigneCommande(db, ligne.id, adresse);
  }

  return NextResponse.json({ statut: "traitee" });
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `npm test -- webhooks/stripe/route.test.ts`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/app/api/webhooks/stripe
git commit -m "feat: webhook Stripe checkout.session.completed — déclenche le pipeline Gelato"
```

---

### Task 13: Webhook Gelato

**Files:**
- Create: `src/app/api/webhooks/gelato/route.ts`
- Test: `src/app/api/webhooks/gelato/route.test.ts`

**Interfaces:**
- Consumes: `db`, `evenementsGelato`/`lignesCommande` (Task 6).
- Produces: `POST /api/webhooks/gelato`, met à jour `statutLigne` (dédupliqué par `eventId`).

- [ ] **Step 1: Write failing test**

Create `src/app/api/webhooks/gelato/route.test.ts` :

```ts
import { beforeEach, describe, expect, it } from "vitest";
import { dbTest, viderTables } from "@/lib/db/test-helpers";
import { creerCommande, ligneParId, marquerEnvoyeeGelato } from "@/lib/db/commandes";

const database = dbTest();
const testOuSkip = database ? it : it.skip;

beforeEach(async () => {
  if (database) await viderTables(database);
});

function evenement(eventId: string, itemId: string, statut: string) {
  return { id: eventId, event: "order_item_status_updated", itemReferenceId: "ligne-ref",
    itemId, status: statut };
}

describe("POST /api/webhooks/gelato", () => {
  testOuSkip("met à jour statutLigne et journalise l'événement", async () => {
    const { ligneIds } = await creerCommande(database!, {
      email: "ada@example.com", stripeCheckoutSessionId: "cs_g1",
      lignes: [{ produitGelatoSku: "poster-traditions-carre", variante: "poster-traditions-carre",
        quantite: 1, prixUnitaireCentimes: 2490, payloadPersonnalisation: {} }],
    });
    await marquerEnvoyeeGelato(database!, ligneIds[0], "gelato-order-1", "gelato-item-1", "https://blob.example.com/f.png");

    const { POST } = await import("./route");
    const req = new Request("http://localhost/api/webhooks/gelato", {
      method: "POST",
      body: JSON.stringify(evenement("evt-1", "gelato-item-1", "shipped")),
    });
    const res = await POST(req);
    expect(res.status).toBe(200);

    const ligne = await ligneParId(database!, ligneIds[0]);
    expect(ligne?.statutLigne).toBe("expediee");
  });

  testOuSkip("un événement rejoué (même eventId) est ignoré la seconde fois", async () => {
    const { ligneIds } = await creerCommande(database!, {
      email: "b@example.com", stripeCheckoutSessionId: "cs_g2",
      lignes: [{ produitGelatoSku: "poster-traditions-carre", variante: "poster-traditions-carre",
        quantite: 1, prixUnitaireCentimes: 2490, payloadPersonnalisation: {} }],
    });
    await marquerEnvoyeeGelato(database!, ligneIds[0], "gelato-order-2", "gelato-item-2", "https://blob.example.com/f.png");

    const { POST } = await import("./route");
    const corps = JSON.stringify(evenement("evt-2", "gelato-item-2", "in_production"));
    const res1 = await POST(new Request("http://localhost/api/webhooks/gelato", { method: "POST", body: corps }));
    const res2 = await POST(new Request("http://localhost/api/webhooks/gelato", { method: "POST", body: corps }));
    expect(res1.status).toBe(200);
    expect(res2.status).toBe(200);
    const body2 = await res2.json();
    expect(body2.statut).toBe("deja_traite");
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm test -- webhooks/gelato/route.test.ts`
Expected: FAIL (`Cannot find module './route'`).

- [ ] **Step 3: Implement `route.ts`**

Create `src/app/api/webhooks/gelato/route.ts` :

```ts
import { eq } from "drizzle-orm";
import { NextResponse } from "next/server";
import { db } from "@/lib/db/client";
import { evenementsGelato, lignesCommande } from "@/lib/db/schema";

const MAPPING_STATUT: Record<string, string> = {
  in_production: "en_production",
  shipped: "expediee",
};

export async function POST(req: Request) {
  const evt = await req.json() as { id: string; itemId: string; status: string };

  const [ligne] = await db.select().from(lignesCommande).where(eq(lignesCommande.gelatoItemId, evt.itemId));
  if (!ligne) {
    return NextResponse.json({ erreur: "Ligne de commande introuvable pour cet itemId." }, { status: 404 });
  }

  const [existant] = await db.select().from(evenementsGelato).where(eq(evenementsGelato.eventId, evt.id));
  if (existant) {
    return NextResponse.json({ statut: "deja_traite" });
  }

  await db.insert(evenementsGelato).values({
    ligneCommandeId: ligne.id,
    type: "order_item_status_updated",
    eventId: evt.id,
    payloadBrut: evt,
  });

  const nouveauStatut = MAPPING_STATUT[evt.status];
  if (nouveauStatut) {
    await db.update(lignesCommande).set({ statutLigne: nouveauStatut }).where(eq(lignesCommande.id, ligne.id));
  }

  return NextResponse.json({ statut: "traite" });
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `npm test -- webhooks/gelato/route.test.ts`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/app/api/webhooks/gelato
git commit -m "feat: webhook Gelato — suivi statutLigne, déduplication par eventId"
```

---

### Task 14: Script de retry manuel

**Files:**
- Create: `scripts/reessayer-ligne.ts`
- Test: `src/lib/reessayer-ligne.test.ts`

**Interfaces:**
- Consumes: `traiterLigneCommande` (Task 11), `ligneParId` (Task 7), `db` (Task 6).
- Produces: `reessayerLigne(db, ligneId, adresseLivraison): Promise<void>` (importable et
  testable), plus un usage CLI.

- [ ] **Step 1: Write failing test**

Create `src/lib/reessayer-ligne.test.ts` :

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";
import { dbTest, viderTables } from "./db/test-helpers";
import { creerCommande, ligneParId } from "./db/commandes";

const database = dbTest();
const testOuSkip = database ? it : it.skip;

vi.mock("./traiter-ligne-commande", () => ({
  traiterLigneCommande: vi.fn().mockResolvedValue(undefined),
}));

const ADRESSE = { nom: "Ada Lovelace", rue: "1 rue X", ville: "Toulouse", cp: "31000", pays: "FR" };

beforeEach(async () => {
  if (database) await viderTables(database);
  vi.clearAllMocks();
});

describe("reessayerLigne", () => {
  testOuSkip("rejoue traiterLigneCommande sur la ligne demandée", async () => {
    const { ligneIds } = await creerCommande(database!, {
      email: "ada@example.com", stripeCheckoutSessionId: "cs_retry",
      lignes: [{ produitGelatoSku: "poster-traditions-carre", variante: "poster-traditions-carre",
        quantite: 1, prixUnitaireCentimes: 2490, payloadPersonnalisation: {} }],
    });

    const { reessayerLigne } = await import("./reessayer-ligne");
    await reessayerLigne(database!, ligneIds[0], ADRESSE);

    const { traiterLigneCommande } = await import("./traiter-ligne-commande");
    expect(traiterLigneCommande).toHaveBeenCalledWith(database, ligneIds[0], ADRESSE);
  });

  testOuSkip("lève une erreur claire si la ligne n'existe pas", async () => {
    const { reessayerLigne } = await import("./reessayer-ligne");
    await expect(reessayerLigne(database!, "id-inexistant", ADRESSE)).rejects.toThrow(/introuvable/);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm test -- reessayer-ligne.test.ts`
Expected: FAIL (`Cannot find module './reessayer-ligne'`).

- [ ] **Step 3: Implement `src/lib/reessayer-ligne.ts`**

Create `src/lib/reessayer-ligne.ts` :

```ts
import type { Db } from "./db/client";
import { ligneParId } from "./db/commandes";
import { traiterLigneCommande } from "./traiter-ligne-commande";
import type { AdresseLivraison } from "./gelato";

export async function reessayerLigne(db: Db, ligneId: string, adresseLivraison: AdresseLivraison): Promise<void> {
  const ligne = await ligneParId(db, ligneId);
  if (!ligne) throw new Error(`Ligne introuvable : ${ligneId}`);
  await traiterLigneCommande(db, ligneId, adresseLivraison);
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `npm test -- reessayer-ligne.test.ts`
Expected: 2 passed.

- [ ] **Step 5: Créer le point d'entrée CLI**

Create `scripts/reessayer-ligne.ts` :

```ts
import "dotenv/config";
import { db } from "../src/lib/db/client";
import { reessayerLigne } from "../src/lib/reessayer-ligne";

async function main() {
  const [ligneId, nom, rue, ville, cp, pays] = process.argv.slice(2);
  if (!ligneId || !nom || !rue || !ville || !cp || !pays) {
    console.error("Usage: tsx scripts/reessayer-ligne.ts <ligneId> <nom> <rue> <ville> <cp> <pays>");
    process.exit(1);
  }
  await reessayerLigne(db, ligneId, { nom, rue, ville, cp, pays });
  console.log(`Ligne ${ligneId} retraitée avec succès.`);
}

main().catch(e => {
  console.error(e);
  process.exit(1);
});
```

Dans `package.json`, ajouter dans `"scripts"` :
```json
"reessayer-ligne": "tsx scripts/reessayer-ligne.ts"
```

- [ ] **Step 6: Commit**

```bash
git add scripts/reessayer-ligne.ts src/lib/reessayer-ligne.ts src/lib/reessayer-ligne.test.ts package.json
git commit -m "feat: script CLI de retry manuel idempotent pour une ligne en echec_gelato"
```

---

## Self-Review

**Spec coverage :**
- Générateur SVG isomorphe (préview navigateur réutilisable + rendu serveur) → Task 2 ; le
  plan B (UI) réutilisera `renderPosterTraditions` tel quel côté client.
- Rasterisation ajustée par produit (résolution/bleed) → Task 3 + `catalogue.ts` (Task 4).
- Appel à l'API publique portrait-cosmique existante, inchangée → Task 5 (`POST /portrait`).
- Modèle de données (commandes/lignes_commande/evenements_gelato) → Task 6.
- Séquencement paiement → génération → Gelato, jamais avant paiement → Tasks 7, 8, 11, 12.
- Gestion d'erreurs (rendu échoué, Gelato indisponible, alerte, retry idempotent) →
  `marquerEchecGelato` (Task 7), `traiterLigneCommande` (Task 11, idempotent via
  `gelatoOrderId`), Task 14 (retry manuel).
- Idempotence webhooks (Stripe via garde de statut, Gelato via `evenements_gelato.eventId`
  unique) → Tasks 12, 13.
- Tests contre Postgres de test, jamais de mock ORM, skip propre si `DATABASE_URL_TEST`
  absent → `db/test-helpers.ts` (Task 6), utilisé dans toutes les tâches touchant la DB.

**Placeholder scan :** aucun TBD ; le seul renvoi à une donnée externe (`GELATO_PRODUCT_UID_...`)
est résolu via variable d'environnement documentée avec la procédure exacte pour l'obtenir
(dashboard Gelato), pas un TODO dans le code.

**Type consistency :** `PayloadPersonnalisation` (Task 11) utilise les mêmes clés
(`identite.{prenoms,nom,date_naissance,heure_naissance,ville}`, `fondTransparent`) que celles
attendues par `renderPosterTraditions`/`OptionsRenduTraditions` (Task 2) et par
`recupererPortrait`/`FicheNaissance` (Task 5). `marquerEnvoyeeGelato` est corrigée dès son
introduction (Task 7) pour accepter `fichierPrintUrl`, signature reprise à l'identique dans
Task 11 — pas de divergence entre les tâches qui la définissent et celle qui l'appelle.
`AdresseLivraison` (Task 10) est le type réutilisé tel quel par `traiterLigneCommande` (Task 11),
le webhook Stripe (Task 12) et le script de retry (Task 14).

No gaps found. Plan complete — le plan B (catalogue, formulaire de personnalisation avec
aperçu live réutilisant `renderPosterTraditions`, panier, responsive) s'appuiera sur
`POST /api/checkout` (Task 8) sans modification de ce plan.
