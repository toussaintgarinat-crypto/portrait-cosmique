# Dashboard de stats ludiques « Guerre Cosmique » — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Afficher des statistiques de vente agrégées/anonymisées croisées avec les
caractéristiques astro des sujets des posters — 5 widgets (Guerre des Éléments, Podium
Zodiaque, Match des Opposés, Achat vs Cadeau, Nombres Maîtres) — via une API publique
dans yop-boutique, une page `/stats`, et un widget dégradable avec backlink dans
portrait-cosmique.

**Architecture:** Les données d'achat vivent dans la DB de yop-boutique (Tasks 1-7,
repo `~/Desktop/yop-boutique`). Deux nouvelles colonnes sur `lignes_commande`
(`est_cadeau` au checkout, `caracteristiques` au fulfillment) alimentent une fonction
d'agrégation pure `calculerStats`, exposée par `GET /api/stats` (cache 5 min, CORS)
et rendue par la page `/stats`. Le widget (Task 8, repo `~/Desktop/portrait-cosmique`)
fetch cette API avec dégradation silencieuse et backlink boutique.

**Tech Stack:** Next.js 16 App Router + TypeScript strict, Vitest, Drizzle ORM +
postgres.js, `unstable_cache` (next/cache), FastAPI TestClient (pytest) pour le widget.

**Spec :** `docs/superpowers/specs/2026-08-28-dashboard-stats-design.md` (repo
portrait-cosmique). Document fondateur : `docs/strategie/2026-08-28-strategie-contenu-catalogue.md`.

## Global Constraints

- **Deux repos** : Tasks 1-7 dans `~/Desktop/yop-boutique` (commits là-bas), Task 8
  dans `~/Desktop/portrait-cosmique` (commits là-bas). Ne jamais mélanger.
- Postgres de test : container `yop-boutique-postgres-test` sur le port 5434
  (`postgresql://test:test@localhost:5434/yop_test`). S'il est arrêté :
  `docker run -d --name yop-boutique-postgres-test -p 5434:5432 -e POSTGRES_USER=test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=yop_test postgres:16-alpine`.
- Tout test touchant la DB exige **les deux** variables :
  `export DATABASE_URL_TEST="postgresql://test:test@localhost:5434/yop_test" DATABASE_URL="$DATABASE_URL_TEST"`
  (le singleton `@/lib/db/client` est fail-fast, `drizzle.config.ts` lit
  `DATABASE_URL_TEST` en priorité pour les migrations).
- Aucun mock d'ORM : vrai Postgres. Tests DB via le pattern existant
  `const database = dbTest(); const testOuSkip = database ? it : it.skip;` +
  `afterAll(() => fermerDb(database))` (voir n'importe quel `*.test.ts` DB existant).
- `vitest.config.ts` a `fileParallelism: false` — ne pas le retirer (races TRUNCATE).
- Nommage français cohérent avec l'existant (fonctions, messages d'erreur, statuts).
- Avant chaque commit : `npx tsc --noEmit` et `npm run lint` verts dans yop-boutique.
  Le build complet (`npm run build`, exige `DATABASE_URL`) est vérifié à la fin des
  Tasks 6 et 7.
- Migrations : `npx drizzle-kit generate` puis `npx drizzle-kit migrate` (jamais de SQL
  écrit à la main dans `drizzle/`).
- Écart assumé vs la spec (implémentation) : les agrégats sont calculés par **un seul
  SELECT (lignes enrichies des commandes payées) + agrégation en JS**, pas par des
  `GROUP BY` SQL séparés — même garantie « pas de table d'agrégats », code plus simple
  et directement testable ; basculer vers des `GROUP BY` si le volume le justifie un jour.

---

### Task 1: Migration — colonnes `est_cadeau` + `caracteristiques`

**Repo :** yop-boutique

**Files:**
- Modify: `src/lib/db/schema.ts` (table `lignesCommande`)
- Create: `drizzle/0002_*.sql` (généré par drizzle-kit)
- Test: `src/lib/db/commandes.test.ts` (ajout d'un test)

**Interfaces:**
- Consumes: schéma existant (`lignesCommande`), helpers existants (`creerCommande`, `ligneParId`).
- Produces: colonnes DB `lignes_commande.est_cadeau` (boolean, NOT NULL, défaut false)
  et `lignes_commande.caracteristiques` (jsonb, NULL). Les tâches suivantes écrivent
  ces colonnes via Drizzle : `estCadeau` et `caracteristiques` sur le type
  `$inferSelect`/`$inferInsert` de `lignesCommande`.

- [ ] **Step 1: Écrire le test échouant (valeur par défaut des nouvelles colonnes)**

Ajouter à la fin du `describe("state machine commandes")` dans
`src/lib/db/commandes.test.ts` :

```ts
  testOuSkip("les nouvelles colonnes ont leurs valeurs par défaut à la création", async () => {
    const { ligneIds } = await creerCommande(database!, {
      email: "colonnes@example.com", stripeCheckoutSessionId: "cs_colonnes_defaut", lignes: [LIGNE_EXEMPLE],
    });
    const ligne = await ligneParId(database!, ligneIds[0]);
    expect(ligne?.estCadeau).toBe(false);
    expect(ligne?.caracteristiques).toBeNull();
  });
```

- [ ] **Step 2: Vérifier que le test échoue**

Run: `DATABASE_URL_TEST="postgresql://test:test@localhost:5434/yop_test" DATABASE_URL="$DATABASE_URL_TEST" npx vitest src/lib/db/commandes.test.ts`
Expected: FAIL — `ligne.estCadeau` est `undefined` (colonne absente du schéma Drizzle).

- [ ] **Step 3: Ajouter les colonnes au schéma et générer la migration**

Dans `src/lib/db/schema.ts`, dans la table `lignesCommande`, ajouter après
`raisonEchec` :

```ts
  /** Ligne achetée comme cadeau (case optionnelle au checkout) — alimente les stats
   * publiques « Achat pour soi vs Cadeau offert ». */
  estCadeau: boolean("est_cadeau").notNull().default(false),
  /** Caractéristiques astro du sujet de la ligne, extraites de la réponse /portrait au
   * fulfillment — alimente les agrégats publics. NULL tant que le fulfillment n'a pas tourné. */
  caracteristiques: jsonb("caracteristiques"),
```

(Ajouter `boolean` à l'import drizzle existant en tête de fichier.)

Puis :

```bash
npx drizzle-kit generate   # crée drizzle/0002_*.sql
npx drizzle-kit migrate
```

Expected: le SQL généré contient
`ALTER TABLE "lignes_commande" ADD COLUMN "est_cadeau" boolean DEFAULT false NOT NULL;`
et `ADD COLUMN "caracteristiques" jsonb;`, puis `migrations applied successfully!`.

- [ ] **Step 4: Vérifier que le test passe**

Run: `DATABASE_URL_TEST="postgresql://test:test@localhost:5434/yop_test" DATABASE_URL="$DATABASE_URL_TEST" npx vitest src/lib/db/commandes.test.ts`
Expected: PASS (tous les tests du fichier).

- [ ] **Step 5: Commit**

```bash
git add src/lib/db/schema.ts drizzle/ src/lib/db/commandes.test.ts
git commit -m "feat: colonnes est_cadeau + caracteristiques sur lignes_commande (migration 0002)"
```

---

### Task 2: Checkout — champ `estCadeau` par ligne

**Repo :** yop-boutique

**Files:**
- Modify: `src/app/api/checkout/route.ts`
- Modify: `src/lib/db/commandes.ts` (`LigneACreer` + `creerCommande`)
- Test: `src/app/api/checkout/route.test.ts`

**Interfaces:**
- Consumes: colonnes de la Task 1 ; route checkout existante (validation
  `quantite` dans une boucle par ligne).
- Produces: `LigneACreer.estCadeau?: boolean` ; le corps de requête
  `POST /api/checkout` accepte `estCadeau?: boolean` par ligne (défaut `false`,
  non-booléen → 400 avant tout appel Stripe).

- [ ] **Step 1: Écrire les tests échouants**

Dans `src/app/api/checkout/route.test.ts`, ajouter à la fin du
`describe("POST /api/checkout")` (avant son accolade fermante) :

```ts
  testOuSkip("persiste estCadeau par ligne (défaut false, true explicite)", async () => {
    const { POST } = await import("./route");
    const req = new Request("http://localhost/api/checkout", {
      method: "POST",
      body: JSON.stringify({
        email: "cadeau@example.com",
        lignes: [
          {
            sku: "poster-traditions-carre",
            quantite: 1,
            estCadeau: true,
            payloadPersonnalisation: {
              identite: { prenoms: "Ada", nom: "Lovelace", date_naissance: "1990-01-15" },
              fondTransparent: false,
            },
          },
          {
            sku: "poster-traditions-carre",
            quantite: 2,
            payloadPersonnalisation: {
              identite: { prenoms: "Grace", nom: "Hopper", date_naissance: "1985-06-01" },
              fondTransparent: false,
            },
          },
        ],
      }),
    });
    const res = await POST(req);
    expect(res.status).toBe(200);

    const lignes = await database!.select().from(lignesCommande);
    expect(lignes).toHaveLength(2);
    expect(lignes.find(l => l.quantite === 1)?.estCadeau).toBe(true);
    expect(lignes.find(l => l.quantite === 2)?.estCadeau).toBe(false);
  });

  testOuSkip("renvoie 400 si estCadeau n'est pas un booléen, sans créer de commande", async () => {
    const { POST } = await import("./route");
    const req = new Request("http://localhost/api/checkout", {
      method: "POST",
      body: JSON.stringify({
        email: "cadeau@example.com",
        lignes: [{
          sku: "poster-traditions-carre",
          quantite: 1,
          estCadeau: "oui",
          payloadPersonnalisation: {
            identite: { prenoms: "Ada", nom: "Lovelace", date_naissance: "1990-01-15" },
            fondTransparent: false,
          },
        }],
      }),
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
    expect((await res.json()).erreur).toMatch(/estCadeau/);
    const commandesEnBase = await database!.select().from(commandes);
    expect(commandesEnBase).toHaveLength(0);
  });
```

- [ ] **Step 2: Vérifier que les tests échouent**

Run: `DATABASE_URL_TEST="postgresql://test:test@localhost:5434/yop_test" DATABASE_URL="$DATABASE_URL_TEST" npx vitest src/app/api/checkout/route.test.ts`
Expected: FAIL — le premier test lit `estCadeau: undefined` (non persisté), le second
reçoit 200 (pas de validation).

- [ ] **Step 3: Implémenter**

Dans `src/lib/db/commandes.ts`, interface `LigneACreer` — ajouter :

```ts
  /** Vrai si la ligne est achetée comme cadeau (case optionnelle au checkout). */
  estCadeau?: boolean;
```

Dans `creerCommande`, l'objet `.values({...})` de l'insert de ligne — ajouter après
`statutLigne: "en_attente",` :

```ts
        estCadeau: ligne.estCadeau ?? false,
```

Dans `src/app/api/checkout/route.ts` :

1. Interface `LigneRequete` — ajouter :

```ts
  estCadeau?: boolean;
```

2. Dans la boucle de validation existante (celle qui valide `quantite`), ajouter après
   le contrôle `quantite` :

```ts
    if (ligne.estCadeau !== undefined && typeof ligne.estCadeau !== "boolean") {
      return NextResponse.json({ erreur: `Ligne ${index + 1} : estCadeau doit être un booléen.` }, { status: 400 });
    }
```

3. Dans l'appel `creerCommande(db, {...})`, le `.map` des lignes — ajouter
   `estCadeau: requete.estCadeau ?? false,` à l'objet de chaque ligne.

- [ ] **Step 4: Vérifier que les tests passent**

Run: `DATABASE_URL_TEST="postgresql://test:test@localhost:5434/yop_test" DATABASE_URL="$DATABASE_URL_TEST" npx vitest src/app/api/checkout/route.test.ts`
Expected: PASS (tous).

- [ ] **Step 5: Commit**

```bash
git add src/app/api/checkout/route.ts src/lib/db/commandes.ts src/app/api/checkout/route.test.ts
git commit -m "feat: champ estCadeau optionnel par ligne au checkout, validé avant Stripe"
```

---

### Task 3: Fulfillment — persister `caracteristiques` depuis la réponse /portrait

**Repo :** yop-boutique

**Files:**
- Modify: `src/lib/db/commandes.ts` (nouvelle fonction `marquerCaracteristiques` + type)
- Modify: `src/lib/traiter-ligne-commande.ts`
- Test: `src/lib/traiter-ligne-commande.test.ts` (mock étoffé + 3 tests)

**Interfaces:**
- Consumes: colonne `caracteristiques` (Task 1) ; `recupererPortrait` dont la réponse
  contient `traditions` avec `signe_solaire: { nom, element }`,
  `signe_chinois: { animal }`, `chemin_de_vie: number`.
- Produces (consommé par Tasks 4-5) :

```ts
export interface CaracteristiquesLigne {
  signeSolaire: string | null;
  element: string | null;      // "Feu" | "Terre" | "Air" | "Eau" | null
  animalChinois: string | null;
  cheminDeVie: number | null;
}
export async function marquerCaracteristiques(
  db: Db, ligneId: string, caracteristiques: CaracteristiquesLigne,
): Promise<void>;
```

- [ ] **Step 1: Étoffer le mock du portrait dans le fichier de test existant**

Dans `src/lib/traiter-ligne-commande.test.ts`, remplacer le mock
`vi.mock("./portrait-cosmique-client", ...)` par :

```ts
vi.mock("./portrait-cosmique-client", () => ({
  recupererPortrait: vi.fn().mockResolvedValue({
    traditions: {
      signe_solaire: { symbole: "♑", nom: "Capricorne", element: "Terre" },
      signe_chinois: { animal: "Cheval", emoji: "🐴", element: "Feu", polarite: "Yang" },
      chemin_de_vie: 7,
    },
  }),
}));
```

- [ ] **Step 2: Écrire les tests échouants**

Ajouter à la fin du `describe("traiterLigneCommande")` :

```ts
  testOuSkip("persiste les caractéristiques extraites du portrait", async () => {
    const { ligneIds } = await creerCommande(database!, {
      email: "carac@example.com",
      stripeCheckoutSessionId: "cs_carac",
      lignes: [{
        produitGelatoSku: "poster-traditions-carre",
        variante: "carré 30×30 cm",
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
    expect(ligne?.caracteristiques).toEqual({
      signeSolaire: "Capricorne",
      element: "Terre",
      animalChinois: "Cheval",
      cheminDeVie: 7,
    });
  });

  testOuSkip("persiste les caractéristiques même si Gelato échoue ensuite (ligne payée comptable)", async () => {
    const { ligneIds } = await creerCommande(database!, {
      email: "carac-echec@example.com",
      stripeCheckoutSessionId: "cs_carac_echec",
      lignes: [{
        produitGelatoSku: "poster-traditions-carre",
        variante: "carré 30×30 cm",
        quantite: 1,
        prixUnitaireCentimes: 2490,
        payloadPersonnalisation: {
          identite: { prenoms: "Ada", nom: "Lovelace", date_naissance: "1990-01-15" },
          fondTransparent: false,
        },
      }],
    });

    const { creerCommandeGelato } = await import("./gelato");
    vi.mocked(creerCommandeGelato).mockRejectedValueOnce(new Error("Gelato a répondu 503"));

    await expect(traiterLigneCommande(database!, ligneIds[0], ADRESSE)).rejects.toThrow(/503/);

    const ligne = await ligneParId(database!, ligneIds[0]);
    expect(ligne?.statutLigne).toBe("echec_gelato");
    expect(ligne?.caracteristiques).toEqual({
      signeSolaire: "Capricorne", element: "Terre", animalChinois: "Cheval", cheminDeVie: 7,
    });
  });

  testOuSkip("idempotent : rejouer une ligne réécrit les mêmes caractéristiques", async () => {
    const { ligneIds } = await creerCommande(database!, {
      email: "carac-rejeu@example.com",
      stripeCheckoutSessionId: "cs_carac_rejeu",
      lignes: [{
        produitGelatoSku: "poster-traditions-carre",
        variante: "carré 30×30 cm",
        quantite: 1,
        prixUnitaireCentimes: 2490,
        payloadPersonnalisation: {
          identite: { prenoms: "Ada", nom: "Lovelace", date_naissance: "1990-01-15" },
          fondTransparent: false,
        },
      }],
    });

    await traiterLigneCommande(database!, ligneIds[0], ADRESSE);
    const apresPremier = await ligneParId(database!, ligneIds[0]);
    await traiterLigneCommande(database!, ligneIds[0], ADRESSE);
    const apresRejeu = await ligneParId(database!, ligneIds[0]);

    expect(apresRejeu?.caracteristiques).toEqual(apresPremier?.caracteristiques);
  });
```

- [ ] **Step 3: Vérifier que les tests échouent**

Run: `DATABASE_URL_TEST="postgresql://test:test@localhost:5434/yop_test" DATABASE_URL="$DATABASE_URL_TEST" npx vitest src/lib/traiter-ligne-commande.test.ts`
Expected: FAIL — `ligne.caracteristiques` est `null` (jamais écrit).

- [ ] **Step 4: Implémenter**

Dans `src/lib/db/commandes.ts`, ajouter (après `marquerEchecGelato`) :

```ts
/** Caractéristiques astro du sujet d'une ligne, pour les agrégats publics (stats).
 * Champs nullables : la réponse /portrait est normalement complète, mais on ne fait
 * jamais planter le fulfillment sur une clé manquante. */
export interface CaracteristiquesLigne {
  signeSolaire: string | null;
  element: string | null;
  animalChinois: string | null;
  cheminDeVie: number | null;
}

/** Persiste les caractéristiques extraites de la réponse /portrait. Idempotent :
 * réécrire les mêmes valeurs est sans effet. */
export async function marquerCaracteristiques(
  db: Db, ligneId: string, caracteristiques: CaracteristiquesLigne,
): Promise<void> {
  await db.update(lignesCommande)
    .set({ caracteristiques })
    .where(eq(lignesCommande.id, ligneId));
}
```

Dans `src/lib/traiter-ligne-commande.ts` :

1. Ajouter `marquerCaracteristiques` à l'import depuis `./db/commandes`.
2. Juste après l'appel `recupererPortrait({...})` (et AVANT `renderPosterTraditions`),
   ajouter :

```ts
    // Caractéristiques pour les stats publiques — persistées AVANT l'appel Gelato :
    // même si Gelato échoue ensuite, la ligne (payée) reste comptable dans les agrégats.
    const trad = traditions as Record<string, unknown>;
    const solaire = trad.signe_solaire as { nom?: unknown; element?: unknown } | undefined;
    const chinois = trad.signe_chinois as { animal?: unknown } | undefined;
    const chemin = trad.chemin_de_vie;
    await marquerCaracteristiques(db, ligneId, {
      signeSolaire: typeof solaire?.nom === "string" ? solaire.nom : null,
      element: typeof solaire?.element === "string" ? solaire.element : null,
      animalChinois: typeof chinois?.animal === "string" ? chinois.animal : null,
      cheminDeVie: typeof chemin === "number" ? chemin : null,
    });
```

- [ ] **Step 5: Vérifier que les tests passent**

Run: `DATABASE_URL_TEST="postgresql://test:test@localhost:5434/yop_test" DATABASE_URL="$DATABASE_URL_TEST" npx vitest src/lib/traiter-ligne-commande.test.ts`
Expected: PASS (tous).

- [ ] **Step 6: Commit**

```bash
git add src/lib/db/commandes.ts src/lib/traiter-ligne-commande.ts src/lib/traiter-ligne-commande.test.ts
git commit -m "feat: persiste les caractéristiques astro de la ligne au fulfillment (avant Gelato)"
```

---

### Task 4: `calculerStats` — squelette, garde-fou, totalCommandes, Guerre des Éléments, Podium Zodiaque

**Repo :** yop-boutique

**Files:**
- Create: `src/lib/stats.ts`
- Test: `src/lib/stats.test.ts`

**Interfaces:**
- Consumes: `CaracteristiquesLigne` (Task 3), tables `commandes`/`lignesCommande`,
  statuts `StatutCommande`.
- Produces (consommé par Tasks 5-7) :

```ts
export interface StatsSignePart { signe: string; part: number }
export interface StatsDuel { a: string; b: string; partA: number; partB: number }
export interface StatsCadeauParSigne { signe: string; partCadeau: number }
export interface StatsCadeau { pourSoi: number; cadeau: number; parSigne: StatsCadeauParSigne[] }
export interface StatsNombresMaitres { "11": number; "22": number; "33": number }
export interface StatsAgregees {
  statut: "ok" | "insuffisant";
  totalCommandes: number;
  guerreElements: { feu: number; terre: number; air: number; eau: number } | null;
  podiumZodiaque: StatsSignePart[] | null;
  duels: StatsDuel[] | null;
  cadeau: StatsCadeau | null;
  nombresMaitres: StatsNombresMaitres | null;
}
export async function calculerStats(db: Db, maintenant: Date = new Date()): Promise<StatsAgregees>;
```

(Task 4 remplit `statut`, `totalCommandes`, `guerreElements`, `podiumZodiaque` ;
`duels`, `cadeau`, `nombresMaitres` valent `null` et sont remplis en Task 5.)

- [ ] **Step 1: Écrire le fichier de test complet**

Créer `src/lib/stats.test.ts` :

```ts
import { afterAll, beforeEach, describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { dbTest, fermerDb, viderTables } from "./db/test-helpers";
import { creerCommande, marquerCaracteristiques, marquerPayee } from "./db/commandes";
import { commandes, lignesCommande } from "./db/schema";
import { calculerStats } from "./stats";

const database = dbTest();
const testOuSkip = database ? it : it.skip;

/** Date « maintenant » fixe injectée dans tous les calculs — fenêtres déterministes. */
const MAINTENANT = new Date("2026-08-15T12:00:00Z");

interface SemisLigne {
  signe: string;
  element: string;
  animal?: string;
  cheminDeVie?: number | null;
  estCadeau?: boolean;
}

let compteur = 0;

/** Sème une commande (payée par défaut) avec ses lignes enrichies. */
async function semer(lignesSpec: SemisLigne[], opts: { payee?: boolean; creeLe?: Date } = {}) {
  compteur += 1;
  const session = `cs_stats_${compteur}`;
  const { commandeId, ligneIds } = await creerCommande(database!, {
    email: `stats-${compteur}@example.com`,
    stripeCheckoutSessionId: session,
    lignes: lignesSpec.map(l => ({
      produitGelatoSku: "poster-traditions-carre",
      variante: "carré 30×30 cm",
      quantite: 1,
      prixUnitaireCentimes: 2490,
      payloadPersonnalisation: {},
      estCadeau: l.estCadeau ?? false,
    })),
  });
  if (opts.payee !== false) {
    await marquerPayee(database!, session, { stripePaymentIntentId: `pi_stats_${compteur}` });
  }
  await database!.update(commandes).set({ creeLe: opts.creeLe ?? MAINTENANT })
    .where(eq(commandes.id, commandeId));
  for (const [i, l] of lignesSpec.entries()) {
    await marquerCaracteristiques(database!, ligneIds[i], {
      signeSolaire: l.signe,
      element: l.element,
      animalChinois: l.animal ?? "Cheval",
      cheminDeVie: l.cheminDeVie ?? 7,
    });
  }
  return { commandeId, ligneIds };
}

beforeEach(async () => {
  if (database) await viderTables(database);
});

afterAll(async () => {
  if (database) await fermerDb(database);
});

describe("calculerStats — garde-fou et totalCommandes", () => {
  testOuSkip("moins de 10 commandes payées → statut insuffisant, agrégats null", async () => {
    for (let i = 0; i < 9; i++) {
      await semer([{ signe: "Bélier", element: "Feu" }]);
    }
    // Les commandes non payées ne comptent pas dans le total.
    for (let i = 0; i < 5; i++) {
      await semer([{ signe: "Lion", element: "Feu" }], { payee: false });
    }

    const stats = await calculerStats(database!, MAINTENANT);
    expect(stats.statut).toBe("insuffisant");
    expect(stats.totalCommandes).toBe(9);
    expect(stats.guerreElements).toBeNull();
    expect(stats.podiumZodiaque).toBeNull();
  });

  testOuSkip("totalCommandes compte les commandes payées même sans caracteristiques", async () => {
    for (let i = 0; i < 10; i++) {
      await semer([{ signe: "Bélier", element: "Feu" }]);
    }
    // 11ᵉ commande payée dont le fulfillment n'a pas tourné : comptée dans le total,
    // exclue des croisements astro.
    const { ligneIds } = await semer([{ signe: "Lion", element: "Feu" }], { payee: true });
    await database!.update(lignesCommande).set({ caracteristiques: null })
      .where(eq(lignesCommande.id, ligneIds[0]));

    const stats = await calculerStats(database!, MAINTENANT);
    expect(stats.statut).toBe("ok");
    expect(stats.totalCommandes).toBe(11);
    // 10 lignes enrichies seulement → la 11ᵉ ne compte pas dans les éléments.
    expect(stats.guerreElements).toEqual({ feu: 100, terre: 0, air: 0, eau: 0 });
  });
});

describe("calculerStats — Guerre des Éléments et Podium Zodiaque (mois courant)", () => {
  testOuSkip("pourcentages des éléments et top 3 des signes du mois courant", async () => {
    // 10 commandes en août 2026 : 4 Feu/Bélier, 3 Terre/Taureau, 2 Air/Gémeaux, 1 Eau/Cancer.
    for (let i = 0; i < 4; i++) await semer([{ signe: "Bélier", element: "Feu" }]);
    for (let i = 0; i < 3; i++) await semer([{ signe: "Taureau", element: "Terre" }]);
    for (let i = 0; i < 2; i++) await semer([{ signe: "Gémeaux", element: "Air" }]);
    await semer([{ signe: "Cancer", element: "Eau" }]);
    // Une commande de juillet 2026 : hors fenêtre « mois courant ».
    await semer([{ signe: "Lion", element: "Feu" }], { creeLe: new Date("2026-07-20T12:00:00Z") });

    const stats = await calculerStats(database!, MAINTENANT);
    expect(stats.statut).toBe("ok");
    expect(stats.totalCommandes).toBe(11);
    expect(stats.guerreElements).toEqual({ feu: 40, terre: 30, air: 20, eau: 10 });
    expect(stats.podiumZodiaque).toEqual([
      { signe: "Bélier", part: 40 },
      { signe: "Taureau", part: 30 },
      { signe: "Gémeaux", part: 20 },
    ]);
  });
});
```

- [ ] **Step 2: Vérifier que les tests échouent**

Run: `DATABASE_URL_TEST="postgresql://test:test@localhost:5434/yop_test" DATABASE_URL="$DATABASE_URL_TEST" npx vitest src/lib/stats.test.ts`
Expected: FAIL — `Cannot find module './stats'`.

- [ ] **Step 3: Implémenter `src/lib/stats.ts`**

```ts
import { and, eq, inArray, isNotNull, sql } from "drizzle-orm";
import type { Db } from "./db/client";
import { commandes, lignesCommande } from "./db/schema";

/** Statuts de commande considérés comme payés — seules ces commandes alimentent les
 * stats (echec_gelato inclus : la personne a payé, le fulfillment attend un retry). */
const STATUTS_PAYES = ["payee", "envoyee_gelato", "en_production", "expediee", "echec_gelato"] as const;

/** Sous ce nombre de commandes payées, les agrégats ne sont pas exposés (vie privée :
 * jamais de stats identifiables sur des micro-volumes). */
const SEUIL_COMMANDES = 10;

export interface StatsSignePart { signe: string; part: number }
export interface StatsDuel { a: string; b: string; partA: number; partB: number }
export interface StatsCadeauParSigne { signe: string; partCadeau: number }
export interface StatsCadeau { pourSoi: number; cadeau: number; parSigne: StatsCadeauParSigne[] }
export interface StatsNombresMaitres { "11": number; "22": number; "33": number }
export interface StatsAgregees {
  statut: "ok" | "insuffisant";
  totalCommandes: number;
  guerreElements: { feu: number; terre: number; air: number; eau: number } | null;
  podiumZodiaque: StatsSignePart[] | null;
  duels: StatsDuel[] | null;
  cadeau: StatsCadeau | null;
  nombresMaitres: StatsNombresMaitres | null;
}

/** Fenêtre temporelle : les commandes sont datées par `cree_le` (création du checkout,
 * à quelques minutes du paiement réel). Toutes les fenêtres sont en UTC. */
function debutMoisCourant(m: Date): Date {
  return new Date(Date.UTC(m.getUTCFullYear(), m.getUTCMonth(), 1));
}

function pourcentage(partie: number, total: number): number {
  if (total === 0) return 0;
  return Math.round((partie * 100) / total);
}

interface LigneStats {
  caracteristiques: unknown;
  estCadeau: boolean;
  creeLe: Date;
}

function versCarac(v: unknown): {
  signeSolaire: string | null; element: string | null;
  animalChinois: string | null; cheminDeVie: number | null;
} {
  if (typeof v !== "object" || v === null) {
    return { signeSolaire: null, element: null, animalChinois: null, cheminDeVie: null };
  }
  return v as {
    signeSolaire: string | null; element: string | null;
    animalChinois: string | null; cheminDeVie: number | null;
  };
}

export async function calculerStats(db: Db, maintenant: Date = new Date()): Promise<StatsAgregees> {
  const [{ total }] = await db.select({ total: sql<number>`count(*)::int` })
    .from(commandes)
    .where(inArray(commandes.statut, [...STATUTS_PAYES]));

  if (total < SEUIL_COMMANDES) {
    return {
      statut: "insuffisant",
      totalCommandes: total,
      guerreElements: null, podiumZodiaque: null,
      duels: null, cadeau: null, nombresMaitres: null,
    };
  }

  // Un seul SELECT de toutes les lignes enrichies des commandes payées (tout temps) —
  // les fenêtres (mois courant / 12 mois glissants) sont filtrées en JS.
  const lignes: LigneStats[] = await db.select({
    caracteristiques: lignesCommande.caracteristiques,
    estCadeau: lignesCommande.estCadeau,
    creeLe: commandes.creeLe,
  }).from(lignesCommande)
    .innerJoin(commandes, eq(lignesCommande.commandeId, commandes.id))
    .where(and(
      inArray(commandes.statut, [...STATUTS_PAYES]),
      isNotNull(lignesCommande.caracteristiques),
    ));

  const debutMois = debutMoisCourant(maintenant).getTime();
  const duMois = lignes
    .filter(l => l.creeLe.getTime() >= debutMois)
    .map(l => versCarac(l.caracteristiques));

  // Guerre des Éléments — mois courant.
  const compteElements = { feu: 0, terre: 0, air: 0, eau: 0 } as Record<"feu" | "terre" | "air" | "eau", number>;
  for (const c of duMois) {
    if (c.element === "Feu") compteElements.feu += 1;
    else if (c.element === "Terre") compteElements.terre += 1;
    else if (c.element === "Air") compteElements.air += 1;
    else if (c.element === "Eau") compteElements.eau += 1;
  }
  const totalMois = duMois.length;
  const guerreElements = {
    feu: pourcentage(compteElements.feu, totalMois),
    terre: pourcentage(compteElements.terre, totalMois),
    air: pourcentage(compteElements.air, totalMois),
    eau: pourcentage(compteElements.eau, totalMois),
  };

  // Podium Zodiaque — top 3 signes du mois courant (égalités départagées
  // alphabétiquement pour un résultat déterministe).
  const parSigne = new Map<string, number>();
  for (const c of duMois) {
    if (c.signeSolaire) parSigne.set(c.signeSolaire, (parSigne.get(c.signeSolaire) ?? 0) + 1);
  }
  const podiumZodiaque = [...parSigne.entries()]
    .sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0], "fr"))
    .slice(0, 3)
    .map(([signe, n]) => ({ signe, part: pourcentage(n, totalMois) }));

  return {
    statut: "ok",
    totalCommandes: total,
    guerreElements,
    podiumZodiaque,
    duels: null,          // Task 5
    cadeau: null,         // Task 5
    nombresMaitres: null, // Task 5
  };
}
```

- [ ] **Step 4: Vérifier que les tests passent**

Run: `DATABASE_URL_TEST="postgresql://test:test@localhost:5434/yop_test" DATABASE_URL="$DATABASE_URL_TEST" npx vitest src/lib/stats.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/lib/stats.ts src/lib/stats.test.ts
git commit -m "feat: calculerStats — garde-fou volume, totalCommandes, Guerre des Éléments, Podium Zodiaque"
```

---

### Task 5: `calculerStats` — duels, cadeau, Nombres Maîtres

**Repo :** yop-boutique

**Files:**
- Modify: `src/lib/stats.ts`
- Test: `src/lib/stats.test.ts` (ajouts)

**Interfaces:**
- Consumes: `StatsAgregees` (Task 4), `LigneStats` interne, `semer` du fichier de test.
- Produces: `calculerStats` complète — `duels` (≤2 oppositions les plus serrées, 12
  mois glissants), `cadeau` (`pourSoi`/`cadeau` globaux + `parSigne` top 3 avec ≥5
  lignes, 12 mois glissants), `nombresMaitres` (compteurs 11/22/33, tout temps).

- [ ] **Step 1: Écrire les tests échouants**

Ajouter à la fin de `src/lib/stats.test.ts` :

```ts
describe("calculerStats — Match des Opposés (12 mois glissants)", () => {
  testOuSkip("renvoie les 2 oppositions les plus serrées", async () => {
    // Bélier 6 vs Balance 5 (55/45) ; Lion 4 vs Verseau 4 (50/50) ; Taureau 1 vs Scorpion 3 (25/75).
    await semer([ { signe: "Bélier", element: "Feu" }, { signe: "Bélier", element: "Feu" }, { signe: "Bélier", element: "Feu" } ]);
    await semer([ { signe: "Bélier", element: "Feu" }, { signe: "Bélier", element: "Feu" }, { signe: "Bélier", element: "Feu" } ]);
    await semer([ { signe: "Balance", element: "Air" }, { signe: "Balance", element: "Air" }, { signe: "Balance", element: "Air" } ]);
    await semer([ { signe: "Balance", element: "Air" }, { signe: "Balance", element: "Air" } ]);
    await semer([ { signe: "Lion", element: "Feu" }, { signe: "Lion", element: "Feu" }, { signe: "Lion", element: "Feu" }, { signe: "Lion", element: "Feu" } ]);
    await semer([ { signe: "Verseau", element: "Air" }, { signe: "Verseau", element: "Air" }, { signe: "Verseau", element: "Air" }, { signe: "Verseau", element: "Air" } ]);
    await semer([ { signe: "Taureau", element: "Terre" } ]);
    await semer([ { signe: "Scorpion", element: "Eau" } ]);
    await semer([ { signe: "Scorpion", element: "Eau" } ]);
    await semer([ { signe: "Scorpion", element: "Eau" } ]);

    const stats = await calculerStats(database!, MAINTENANT);
    expect(stats.duels).toEqual([
      { a: "Lion", b: "Verseau", partA: 50, partB: 50 },
      { a: "Bélier", b: "Balance", partA: 55, partB: 45 },
    ]);
  });

  testOuSkip("une ligne de plus de 12 mois n'entre pas dans les duels (mais compte au total)", async () => {
    // 6 commandes Bélier + 5 commandes Balance (une ligne chacune) : seul axe du zodiaque
    // avec des données → 6/11 = 55 %.
    for (let i = 0; i < 6; i++) await semer([{ signe: "Bélier", element: "Feu" }]);
    for (let i = 0; i < 5; i++) await semer([{ signe: "Balance", element: "Air" }]);
    // Bélier il y a ~13 mois : hors fenêtre glissante — s'il comptait, Bélier
    // passerait à 7/12 = 58 % ; il doit rester à 6/11 = 55 %.
    await semer([{ signe: "Bélier", element: "Feu" }], { creeLe: new Date("2025-06-01T12:00:00Z") });

    const stats = await calculerStats(database!, MAINTENANT);
    expect(stats.totalCommandes).toBe(12);
    expect(stats.duels).toEqual([
      { a: "Bélier", b: "Balance", partA: 55, partB: 45 },
    ]);
  });
});

describe("calculerStats — Achat vs Cadeau (12 mois glissants)", () => {
  testOuSkip("parts globales et top 3 des signes (≥5 lignes chacun)", async () => {
    // 19 commandes d'une ligne chacune (le seuil compte les COMMANDES, pas les lignes) :
    // Lion 6 lignes dont 3 cadeaux → 50 % · Cancer 5 dont 4 cadeaux → 80 % ·
    // Bélier 5 dont 1 cadeau → 20 % · Taureau 3 (toutes cadeaux) → <5 lignes, exclu.
    const semis: SemisLigne[] = [
      { signe: "Lion", element: "Feu", estCadeau: true },
      { signe: "Lion", element: "Feu", estCadeau: true },
      { signe: "Lion", element: "Feu", estCadeau: true },
      { signe: "Lion", element: "Feu" },
      { signe: "Lion", element: "Feu" },
      { signe: "Lion", element: "Feu" },
      { signe: "Cancer", element: "Eau", estCadeau: true },
      { signe: "Cancer", element: "Eau", estCadeau: true },
      { signe: "Cancer", element: "Eau", estCadeau: true },
      { signe: "Cancer", element: "Eau", estCadeau: true },
      { signe: "Cancer", element: "Eau" },
      { signe: "Bélier", element: "Feu", estCadeau: true },
      { signe: "Bélier", element: "Feu" },
      { signe: "Bélier", element: "Feu" },
      { signe: "Bélier", element: "Feu" },
      { signe: "Bélier", element: "Feu" },
      { signe: "Taureau", element: "Terre", estCadeau: true },
      { signe: "Taureau", element: "Terre", estCadeau: true },
      { signe: "Taureau", element: "Terre", estCadeau: true },
    ];
    for (const l of semis) await semer([l]);

    const stats = await calculerStats(database!, MAINTENANT);
    expect(stats.cadeau).toEqual({
      pourSoi: 42,   // 8 lignes « pour soi » sur 19
      cadeau: 58,    // 11 lignes cadeau sur 19
      parSigne: [
        { signe: "Cancer", partCadeau: 80 },
        { signe: "Lion", partCadeau: 50 },
        { signe: "Bélier", partCadeau: 20 },
      ],
    });
  });
});

describe("calculerStats — Nombres Maîtres (tout temps)", () => {
  testOuSkip("compte les chemins de vie 11, 22, 33 sur tout l'historique", async () => {
    for (let i = 0; i < 8; i++) {
      await semer([{ signe: "Bélier", element: "Feu", cheminDeVie: 7 }]);
    }
    await semer([{ signe: "Taureau", element: "Terre", cheminDeVie: 11 }]);
    await semer([{ signe: "Gémeaux", element: "Air", cheminDeVie: 11 }]);
    await semer([{ signe: "Cancer", element: "Eau", cheminDeVie: 22 }]);
    // Il y a 2 ans : tout temps, ça compte.
    await semer([{ signe: "Lion", element: "Feu", cheminDeVie: 33 }], { creeLe: new Date("2024-08-15T12:00:00Z") });

    const stats = await calculerStats(database!, MAINTENANT);
    expect(stats.nombresMaitres).toEqual({ "11": 2, "22": 1, "33": 1 });
  });
});
```

- [ ] **Step 2: Vérifier que les tests échouent**

Run: `DATABASE_URL_TEST="postgresql://test:test@localhost:5434/yop_test" DATABASE_URL="$DATABASE_URL_TEST" npx vitest src/lib/stats.test.ts`
Expected: FAIL — `duels`, `cadeau`, `nombresMaitres` valent `null` (les nouveaux tests
sur ces champs échouent).

- [ ] **Step 3: Implémenter**

Dans `src/lib/stats.ts` :

1. Constante des oppositions (après `SEUIL_COMMANDES`) :

```ts
/** Les 6 oppositions canoniques du zodiaque — l'axe de chaque duel. */
const OPPOSITIONS: [string, string][] = [
  ["Bélier", "Balance"], ["Taureau", "Scorpion"], ["Gémeaux", "Sagittaire"],
  ["Cancer", "Capricorne"], ["Lion", "Verseau"], ["Vierge", "Poissons"],
];
```

2. Helper de fenêtre glissante (après `debutMoisCourant`) :

```ts
function debutGlissant(m: Date, mois: number): Date {
  return new Date(Date.UTC(m.getUTCFullYear(), m.getUTCMonth() - mois, 1));
}
```

3. Dans `calculerStats`, insérer ce calcul après le bloc Podium Zodiaque et remplacer
   les trois lignes `duels: null, cadeau: null, nombresMaitres: null` du `return`
   final par les variables calculées :

```ts
  // Match des Opposés — 12 mois glissants, les 2 oppositions au score le plus serré
  // (un 49/51 engage, un 95/5 n'informe rien).
  const debutDuels = debutGlissant(maintenant, 12).getTime();
  const glissantes = lignes
    .filter(l => l.creeLe.getTime() >= debutDuels)
    .map(l => ({ carac: versCarac(l.caracteristiques), estCadeau: l.estCadeau }));

  const duelsCalcules = OPPOSITIONS
    .map(([a, b]) => {
      const nbA = glissantes.filter(l => l.carac.signeSolaire === a).length;
      const nbB = glissantes.filter(l => l.carac.signeSolaire === b).length;
      if (nbA + nbB === 0) return null;
      const partA = pourcentage(nbA, nbA + nbB);
      return { a, b, partA, partB: 100 - partA, ecart: Math.abs(partA - 50) };
    })
    .filter((d): d is NonNullable<typeof d> => d !== null)
    .sort((x, y) => x.ecart - y.ecart || x.a.localeCompare(y.a, "fr"))
    .slice(0, 2)
    .map(({ a, b, partA, partB }) => ({ a, b, partA, partB }));

  // Achat vs Cadeau — 12 mois glissants.
  const totalGlissantes = glissantes.length;
  const nbCadeaux = glissantes.filter(l => l.estCadeau).length;
  const parSigneCadeau = new Map<string, { total: number; cadeaux: number }>();
  for (const l of glissantes) {
    const s = l.carac.signeSolaire;
    if (!s) continue;
    const e = parSigneCadeau.get(s) ?? { total: 0, cadeaux: 0 };
    e.total += 1;
    if (l.estCadeau) e.cadeaux += 1;
    parSigneCadeau.set(s, e);
  }
  const cadeau = {
    pourSoi: pourcentage(totalGlissantes - nbCadeaux, totalGlissantes),
    cadeau: pourcentage(nbCadeaux, totalGlissantes),
    parSigne: [...parSigneCadeau.entries()]
      .filter(([, e]) => e.total >= 5)
      .map(([signe, e]) => ({ signe, partCadeau: pourcentage(e.cadeaux, e.total) }))
      .sort((x, y) => y.partCadeau - x.partCadeau || x.signe.localeCompare(y.signe, "fr"))
      .slice(0, 3),
  };

  // Nombres Maîtres — compteurs tout temps.
  const chemins = lignes.map(l => versCarac(l.caracteristiques).cheminDeVie);
  const nombresMaitres = {
    "11": chemins.filter(c => c === 11).length,
    "22": chemins.filter(c => c === 22).length,
    "33": chemins.filter(c => c === 33).length,
  };
```

et le `return` final devient :

```ts
  return {
    statut: "ok",
    totalCommandes: total,
    guerreElements,
    podiumZodiaque,
    duels: duelsCalcules,
    cadeau,
    nombresMaitres,
  };
```

- [ ] **Step 4: Vérifier que les tests passent**

Run: `DATABASE_URL_TEST="postgresql://test:test@localhost:5434/yop_test" DATABASE_URL="$DATABASE_URL_TEST" npx vitest src/lib/stats.test.ts`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add src/lib/stats.ts src/lib/stats.test.ts
git commit -m "feat: duels serrés, achat vs cadeau, nombres maîtres dans calculerStats"
```

---

### Task 6: API publique `GET /api/stats` — cache 5 min + CORS

**Repo :** yop-boutique

**Files:**
- Modify: `src/lib/stats.ts` (ajout de `obtenirStats`)
- Create: `src/app/api/stats/route.ts`
- Test: `src/app/api/stats/route.test.ts`

**Interfaces:**
- Consumes: `calculerStats` (Tasks 4-5), singleton `db` de `@/lib/db/client`.
- Produces: `obtenirStats(): Promise<StatsAgregees>` (exporté depuis `@/lib/stats`,
  wrapper `unstable_cache` — consommé par la page `/stats` en Task 7) ;
  `GET /api/stats` → JSON `StatsAgregees` avec `Access-Control-Allow-Origin: *` ;
  `OPTIONS /api/stats` → 204 + CORS.

- [ ] **Step 1: Écrire le test de la route**

Créer `src/app/api/stats/route.test.ts` :

```ts
import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import { dbTest, fermerDb, viderTables } from "@/lib/db/test-helpers";
import { creerCommande, marquerCaracteristiques, marquerPayee } from "@/lib/db/commandes";

const database = dbTest();
const testOuSkip = database ? it : it.skip;

// Remplace unstable_cache par un cache mémoire clé→promesse (sémantique fidèle :
// même clé ⇒ même promesse, donc une seule exécution sous-jacente).
vi.mock("next/cache", () => {
  const cache = new Map<string, Promise<unknown>>();
  return {
    unstableCache: (fn: () => unknown, partiesCle: unknown[]) => {
      const cle = JSON.stringify(partiesCle);
      return () => {
        if (!cache.has(cle)) cache.set(cle, fn() as Promise<unknown>);
        return cache.get(cle)!;
      };
    },
    viderCacheMemoire: () => cache.clear(),
  };
});

beforeEach(async () => {
  if (database) await viderTables(database);
  const { viderCacheMemoire } = await import("next/cache") as unknown as { viderCacheMemoire: () => void };
  viderCacheMemoire();
});

afterAll(async () => {
  if (database) await fermerDb(database);
});

async function semerDixCommandes() {
  for (let i = 0; i < 10; i++) {
    const session = `cs_stats_api_${i}`;
    const { ligneIds } = await creerCommande(database!, {
      email: `stats-api-${i}@example.com`,
      stripeCheckoutSessionId: session,
      lignes: [{
        produitGelatoSku: "poster-traditions-carre",
        variante: "carré 30×30 cm",
        quantite: 1,
        prixUnitaireCentimes: 2490,
        payloadPersonnalisation: {},
      }],
    });
    await marquerPayee(database!, session, { stripePaymentIntentId: `pi_stats_api_${i}` });
    await marquerCaracteristiques(database!, ligneIds[0], {
      signeSolaire: "Bélier", element: "Feu", animalChinois: "Cheval", cheminDeVie: 7,
    });
  }
}

describe("GET /api/stats", () => {
  testOuSkip("renvoie les agrégats complets avec CORS ouvert", async () => {
    await semerDixCommandes();
    const { GET } = await import("./route");
    const res = await GET();
    expect(res.status).toBe(200);
    expect(res.headers.get("Access-Control-Allow-Origin")).toBe("*");

    const body = await res.json();
    expect(body.statut).toBe("ok");
    expect(body.totalCommandes).toBe(10);
    expect(body.guerreElements).toEqual({ feu: 100, terre: 0, air: 0, eau: 0 });
    expect(Array.isArray(body.podiumZodiaque)).toBe(true);
    expect(body.nombresMaitres).toEqual({ "11": 0, "22": 0, "33": 0 });
  });

  testOuSkip("deux appels consécutifs → une seule exécution (cache)", async () => {
    await semerDixCommandes();
    const { GET } = await import("./route");
    const premiere = await (await GET()).json();

    // Les données changent sous le cache…
    await viderTables(database!);
    const deuxieme = await (await GET()).json();

    // …mais la réponse est servie depuis le cache (inchangée).
    expect(deuxieme).toEqual(premiere);
    expect(deuxieme.totalCommandes).toBe(10);
  });

  testOuSkip("OPTIONS (preflight) → 204 avec CORS", async () => {
    const { OPTIONS } = await import("./route");
    const res = await OPTIONS();
    expect(res.status).toBe(204);
    expect(res.headers.get("Access-Control-Allow-Origin")).toBe("*");
  });

  testOuSkip("état insuffisant : agrégats null, total exposé", async () => {
    const { GET } = await import("./route");
    const res = await GET();
    const body = await res.json();
    expect(body.statut).toBe("insuffisant");
    expect(body.totalCommandes).toBe(0);
    expect(body.guerreElements).toBeNull();
  });
});
```

- [ ] **Step 2: Vérifier que les tests échouent**

Run: `DATABASE_URL_TEST="postgresql://test:test@localhost:5434/yop_test" DATABASE_URL="$DATABASE_URL_TEST" npx vitest src/app/api/stats/route.test.ts`
Expected: FAIL — `Cannot find module './route'`.

- [ ] **Step 3: Implémenter**

1. Dans `src/lib/stats.ts`, fusionner l'import type avec l'import du singleton et
   ajouter le wrapper caché (fin de fichier) :

```ts
import { db, type Db } from "./db/client";
import { unstable_cache } from "next/cache";

/** Agrégats publics, mis en cache 5 min — un seul calcul SQL au flux, quel que soit le
 * nombre de consommateurs (page /stats, API publique, widget portrait-cosmique). */
export const obtenirStats: () => Promise<StatsAgregees> = unstable_cache(
  async () => calculerStats(db),
  ["stats-guerre-cosmique"],
  { revalidate: 300 },
);
```

2. Créer `src/app/api/stats/route.ts` :

```ts
import { NextResponse } from "next/server";
import { obtenirStats } from "@/lib/stats";

/** Agrégats anonymisés — lecture publique (widget portrait-cosmique), pas d'auth :
 * jamais de données individuelles, garde-fou volume côté calcul, cache 5 min. */
export async function GET() {
  const stats = await obtenirStats();
  return NextResponse.json(stats, {
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "public, s-maxage=300, stale-while-revalidate=60",
    },
  });
}

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, OPTIONS",
    },
  });
}
```

- [ ] **Step 4: Vérifier tests + build**

Run: `DATABASE_URL_TEST="postgresql://test:test@localhost:5434/yop_test" DATABASE_URL="$DATABASE_URL_TEST" npx vitest src/app/api/stats/route.test.ts`
Expected: PASS (4 tests).

Run: `DATABASE_URL="$DATABASE_URL_TEST" npm run build && npx tsc --noEmit && npm run lint`
Expected: build vert (la route `/api/stats` apparaît dans la liste des routes), 0
erreur TS, 0 erreur lint.

- [ ] **Step 5: Commit**

```bash
git add src/lib/stats.ts src/app/api/stats/route.ts src/app/api/stats/route.test.ts
git commit -m "feat: API publique GET /api/stats (cache 5 min, CORS, agrégats anonymisés)"
```

---

### Task 7: Page `/stats` + view-model testable

**Repo :** yop-boutique

**Files:**
- Create: `src/lib/stats-vue.ts`
- Create: `src/app/stats/page.tsx`
- Test: `src/lib/stats-vue.test.ts`
- Modify: `README.md` (section Flux)

**Interfaces:**
- Consumes: `StatsAgregees` (Tasks 4-5), `obtenirStats` (Task 6).
- Produces :

```ts
export interface ModelePageStats {
  statut: "ok" | "insuffisant";
  messageInsuffisant: string | null;
  elements: { cle: "feu" | "terre" | "air" | "eau"; label: string; part: number }[];
  podium: { rang: number; signe: string; part: number }[];
  duels: { a: string; b: string; partA: number; partB: number }[];
  cadeau: { pourSoi: number; cadeau: number; parSigne: { signe: string; partCadeau: number }[] } | null;
  nombresMaitres: { nombre: string; libelle: string; total: number }[] | null;
  totalCommandes: number;
}
export function modelePageStats(stats: StatsAgregees): ModelePageStats;
```

- [ ] **Step 1: Écrire les tests du view-model**

Créer `src/lib/stats-vue.test.ts` :

```ts
import { describe, expect, it } from "vitest";
import { modelePageStats } from "./stats-vue";
import type { StatsAgregees } from "./stats";

const STATS_OK: StatsAgregees = {
  statut: "ok",
  totalCommandes: 42,
  guerreElements: { feu: 34, terre: 22, air: 28, eau: 16 },
  podiumZodiaque: [
    { signe: "Capricorne", part: 14 },
    { signe: "Lion", part: 12 },
    { signe: "Balance", part: 10 },
  ],
  duels: [
    { a: "Lion", b: "Verseau", partA: 50, partB: 50 },
    { a: "Bélier", b: "Balance", partA: 55, partB: 45 },
  ],
  cadeau: {
    pourSoi: 61, cadeau: 39,
    parSigne: [{ signe: "Lion", partCadeau: 55 }, { signe: "Cancer", partCadeau: 50 }, { signe: "Bélier", partCadeau: 20 }],
  },
  nombresMaitres: { "11": 3, "22": 1, "33": 0 },
};

const STATS_INSUFFISANT: StatsAgregees = {
  statut: "insuffisant",
  totalCommandes: 4,
  guerreElements: null, podiumZodiaque: null,
  duels: null, cadeau: null, nombresMaitres: null,
};

describe("modelePageStats", () => {
  it("état ok : éléments ordonnés, podium rangé, duels, cadeau, nombres maîtres libellés", () => {
    const vue = modelePageStats(STATS_OK);
    expect(vue.statut).toBe("ok");
    expect(vue.messageInsuffisant).toBeNull();
    expect(vue.elements).toEqual([
      { cle: "feu", label: "Feu", part: 34 },
      { cle: "terre", label: "Terre", part: 22 },
      { cle: "air", label: "Air", part: 28 },
      { cle: "eau", label: "Eau", part: 16 },
    ]);
    expect(vue.podium).toEqual([
      { rang: 1, signe: "Capricorne", part: 14 },
      { rang: 2, signe: "Lion", part: 12 },
      { rang: 3, signe: "Balance", part: 10 },
    ]);
    expect(vue.duels).toHaveLength(2);
    expect(vue.cadeau?.parSigne).toHaveLength(3);
    expect(vue.nombresMaitres).toEqual([
      { nombre: "11", libelle: "Intuition", total: 3 },
      { nombre: "22", libelle: "Bâtisseur", total: 1 },
      { nombre: "33", libelle: "Maître enseignant", total: 0 },
    ]);
    expect(vue.totalCommandes).toBe(42);
  });

  it("état insuffisant : message de teasing, widgets vides, total conservé", () => {
    const vue = modelePageStats(STATS_INSUFFISANT);
    expect(vue.statut).toBe("insuffisant");
    expect(vue.messageInsuffisant).toMatch(/étoiles/i);
    expect(vue.elements).toEqual([]);
    expect(vue.podium).toEqual([]);
    expect(vue.duels).toEqual([]);
    expect(vue.cadeau).toBeNull();
    expect(vue.nombresMaitres).toBeNull();
    expect(vue.totalCommandes).toBe(4);
  });
});
```

- [ ] **Step 2: Vérifier que les tests échouent**

Run: `npx vitest src/lib/stats-vue.test.ts`
Expected: FAIL — `Cannot find module './stats-vue'`.

- [ ] **Step 3: Implémenter `src/lib/stats-vue.ts`**

```ts
import type { StatsAgregees } from "./stats";

export interface ModelePageStats {
  statut: "ok" | "insuffisant";
  messageInsuffisant: string | null;
  elements: { cle: "feu" | "terre" | "air" | "eau"; label: string; part: number }[];
  podium: { rang: number; signe: string; part: number }[];
  duels: { a: string; b: string; partA: number; partB: number }[];
  cadeau: { pourSoi: number; cadeau: number; parSigne: { signe: string; partCadeau: number }[] } | null;
  nombresMaitres: { nombre: string; libelle: string; total: number }[] | null;
  totalCommandes: number;
}

const LIBELLES_NOMBRES_MAITRES: Record<string, string> = {
  "11": "Intuition",
  "22": "Bâtisseur",
  "33": "Maître enseignant",
};

/** Transforme les agrégats bruts en modèle de vue prêt à rendre — logique pure,
 * testée indépendamment du JSX de la page. */
export function modelePageStats(stats: StatsAgregees): ModelePageStats {
  if (stats.statut === "insuffisant") {
    return {
      statut: "insuffisant",
      messageInsuffisant: "Les étoiles alignent leurs forces… les premières statistiques arrivent bientôt.",
      elements: [], podium: [], duels: [],
      cadeau: null, nombresMaitres: null,
      totalCommandes: stats.totalCommandes,
    };
  }

  const g = stats.guerreElements!;
  return {
    statut: "ok",
    messageInsuffisant: null,
    elements: [
      { cle: "feu", label: "Feu", part: g.feu },
      { cle: "terre", label: "Terre", part: g.terre },
      { cle: "air", label: "Air", part: g.air },
      { cle: "eau", label: "Eau", part: g.eau },
    ],
    podium: (stats.podiumZodiaque ?? []).map((s, i) => ({ rang: i + 1, ...s })),
    duels: stats.duels ?? [],
    cadeau: stats.cadeau,
    nombresMaitres: Object.entries(stats.nombresMaitres ?? {}).map(([nombre, total]) => ({
      nombre,
      libelle: LIBELLES_NOMBRES_MAITRES[nombre] ?? nombre,
      total,
    })),
    totalCommandes: stats.totalCommandes,
  };
}
```

- [ ] **Step 4: Vérifier que les tests passent**

Run: `npx vitest src/lib/stats-vue.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 5: Créer la page `src/app/stats/page.tsx`**

```tsx
import { obtenirStats } from "@/lib/stats";
import { modelePageStats } from "@/lib/stats-vue";

/** Dynamique plutôt que `revalidate` : un prerender statique exécuterait la requête DB
 * au build (échec si la DB est injoignable à ce moment-là). La fraîcheur reste assurée
 * par le cache 5 min d'`obtenirStats` — un seul calcul SQL au flux. */
export const dynamic = "force-dynamic";

export const metadata = {
  title: "La Guerre Cosmique — statistiques",
  description: "Les posters les plus commandés, signe par signe : guerre des éléments, podium zodiaque, duels et nombres maîtres.",
};

export default async function PageStats() {
  const stats = await obtenirStats();
  const vue = modelePageStats(stats);

  if (vue.statut === "insuffisant") {
    return (
      <main className="mx-auto max-w-2xl px-4 py-16 text-center">
        <h1 className="text-3xl font-bold text-zinc-100">⚔️ La Guerre Cosmique</h1>
        <p className="mt-6 text-lg text-zinc-400">{vue.messageInsuffisant}</p>
        <a href="/" className="mt-8 inline-block rounded-full bg-[#b98cf7] px-6 py-3 font-medium text-[#0f1220]">
          Découvrir les posters
        </a>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <header className="text-center">
        <h1 className="text-3xl font-bold text-zinc-100">⚔️ La Guerre Cosmique</h1>
        <p className="mt-2 text-zinc-400">
          {vue.totalCommandes} posters commandés à ce jour. Ton signe est-il en tête ?
        </p>
      </header>

      <section className="mt-10 rounded-2xl bg-[#171b2e] p-6 ring-1 ring-[#2b3050]">
        <h2 className="text-lg font-semibold text-zinc-100">🔥 La Guerre des Éléments — ce mois-ci</h2>
        <div className="mt-4 flex flex-col gap-3">
          {vue.elements.map(e => (
            <div key={e.cle} className="flex items-center gap-3">
              <span className="w-14 text-sm text-zinc-300">{e.label}</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-[#0f1220]">
                <div className="h-full rounded-full bg-[#b98cf7]" style={{ width: `${e.part}%` }} />
              </div>
              <span className="w-10 text-right text-sm text-zinc-400">{e.part}%</span>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-6 rounded-2xl bg-[#171b2e] p-6 ring-1 ring-[#2b3050]">
        <h2 className="text-lg font-semibold text-zinc-100">🏆 Le Podium Zodiaque — ce mois-ci</h2>
        <ol className="mt-4 flex flex-col gap-2">
          {vue.podium.map(p => (
            <li key={p.signe} className="flex items-center justify-between rounded-lg bg-[#1e2338] px-4 py-2">
              <span className="font-medium text-zinc-100">{p.rang}. {p.signe}</span>
              <span className="text-sm text-zinc-400">{p.part}%</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="mt-6 rounded-2xl bg-[#171b2e] p-6 ring-1 ring-[#2b3050]">
        <h2 className="text-lg font-semibold text-zinc-100">⚡ Le Match des Opposés — 12 derniers mois</h2>
        <div className="mt-4 flex flex-col gap-4">
          {vue.duels.map(d => (
            <div key={`${d.a}-${d.b}`}>
              <div className="flex items-center justify-between text-sm">
                <span className="text-zinc-100">{d.a} {d.partA}%</span>
                <span className="text-zinc-500">vs</span>
                <span className="text-zinc-100">{d.partB}% {d.b}</span>
              </div>
              <div className="mt-1 flex h-2 overflow-hidden rounded-full bg-[#0f1220]">
                <div className="h-full bg-[#b98cf7]" style={{ width: `${d.partA}%` }} />
                <div className="h-full bg-[#6ee7c3]" style={{ width: `${d.partB}%` }} />
              </div>
            </div>
          ))}
        </div>
      </section>

      {vue.cadeau && (
        <section className="mt-6 rounded-2xl bg-[#171b2e] p-6 ring-1 ring-[#2b3050]">
          <h2 className="text-lg font-semibold text-zinc-100">🎁 Pour soi ou cadeau ? — 12 derniers mois</h2>
          <div className="mt-4 flex h-3 overflow-hidden rounded-full bg-[#0f1220]">
            <div className="h-full bg-[#b98cf7]" style={{ width: `${vue.cadeau.pourSoi}%` }} />
            <div className="h-full bg-[#6ee7c3]" style={{ width: `${vue.cadeau.cadeau}%` }} />
          </div>
          <p className="mt-2 text-sm text-zinc-400">
            {vue.cadeau.pourSoi}% pour soi-même · {vue.cadeau.cadeau}% cadeaux offerts
          </p>
          {vue.cadeau.parSigne.length > 0 && (
            <ul className="mt-3 flex flex-wrap gap-2">
              {vue.cadeau.parSigne.map(s => (
                <li key={s.signe} className="rounded-full bg-[#1e2338] px-3 py-1 text-sm text-zinc-300">
                  {s.signe} : {s.partCadeau}% cadeaux
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {vue.nombresMaitres && (
        <section className="mt-6 rounded-2xl bg-[#171b2e] p-6 ring-1 ring-[#2b3050]">
          <h2 className="text-lg font-semibold text-zinc-100">🔢 Les Nombres Maîtres</h2>
          <div className="mt-4 grid grid-cols-3 gap-3">
            {vue.nombresMaitres.map(n => (
              <div key={n.nombre} className="rounded-lg bg-[#1e2338] p-4 text-center">
                <div className="text-2xl font-bold text-[#b98cf7]">{n.total}</div>
                <div className="text-sm text-zinc-400">chemin {n.nombre} · {n.libelle}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      <div className="mt-10 text-center">
        <a href="/" className="inline-block rounded-full bg-[#b98cf7] px-6 py-3 font-medium text-[#0f1220]">
          Créer mon poster
        </a>
      </div>
    </main>
  );
}
```

- [ ] **Step 6: Vérifier tests complets + build + lint**

Run: `DATABASE_URL_TEST="postgresql://test:test@localhost:5434/yop_test" DATABASE_URL="$DATABASE_URL_TEST" npm test`
Expected: tous les fichiers verts.

Run: `DATABASE_URL="$DATABASE_URL_TEST" npm run build && npx tsc --noEmit && npm run lint`
Expected: build vert (`/stats` en route dynamique ƒ — aucune requête DB au build), 0
erreur TS, 0 erreur lint.

- [ ] **Step 7: Mettre à jour le README (section Flux)**

Dans `README.md`, ajouter après le diagramme de flux :

```markdown
- `GET /api/stats` expose des agrégats anonymisés (Guerre des Éléments, Podium Zodiaque,
  duels, achat vs cadeau, Nombres Maîtres) — consommés par la page `/stats` et le widget
  de portrait-cosmique. Garde-fou vie privée : rien au-dessous de 10 commandes payées.
```

- [ ] **Step 8: Commit**

```bash
git add src/lib/stats-vue.ts src/lib/stats-vue.test.ts src/app/stats/page.tsx README.md
git commit -m "feat: page /stats — widgets Guerre Cosmique rendus depuis les agrégats"
```

---

### Task 8: Widget « Guerre Cosmique » dans portrait-cosmique

**Repo :** portrait-cosmique (`~/Desktop/portrait-cosmique`)

**Files:**
- Modify: `main.py` (`accueil()` — injection des placeholders)
- Modify: `static/index.html` (section HTML + CSS + script du widget)
- Modify: `.env.example`
- Test: `engine/test_stats_widget.py` (nouveau)

**Interfaces:**
- Consumes: `GET /api/stats` de yop-boutique (Task 6) — shape `StatsAgregees` JSON :
  `{ statut, totalCommandes, guerreElements, podiumZodiaque: [{signe, part}], duels:
  [{a, b, partA, partB}], ... }`.
- Produces: `GET /` de portrait-cosmique rend le HTML avec
  `__STATS_API_URL__`/`__BOUTIQUE_URL__` substitués par les valeurs (JSON-échappées)
  des variables d'env `STATS_API_URL`/`BOUTIQUE_URL`. Env vides ⇒ placeholders
  remplacés par `""` ⇒ le widget ne s'affiche pas du tout (opt-in).

- [ ] **Step 1: Écrire le test Python échouant**

Créer `engine/test_stats_widget.py` :

```python
"""Widget Guerre Cosmique : injection de la config (STATS_API_URL / BOUTIQUE_URL)
dans la page d'accueil depuis l'environnement."""
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_ENGINE = _ROOT / "engine"
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

from fastapi.testclient import TestClient
import main

client = TestClient(main.app)


def test_widget_desactive_sans_env(monkeypatch):
    monkeypatch.delenv("STATS_API_URL", raising=False)
    monkeypatch.delenv("BOUTIQUE_URL", raising=False)
    html = client.get("/").text
    # Les placeholders sont substitués par des chaînes vides (JSON) : plus aucun
    # __PLACEHOLDER__ brut ne doit fuiter vers le navigateur.
    assert "__STATS_API_URL__" not in html
    assert "__BOUTIQUE_URL__" not in html
    assert 'const STATS_API_URL = "";' in html


def test_widget_configure_avec_env(monkeypatch):
    monkeypatch.setenv("STATS_API_URL", "https://boutique.example.com/api/stats")
    monkeypatch.setenv("BOUTIQUE_URL", "https://boutique.example.com")
    html = client.get("/").text
    assert 'const STATS_API_URL = "https://boutique.example.com/api/stats";' in html
    assert 'const BOUTIQUE_URL = "https://boutique.example.com";' in html


def test_url_maliceuse_ne_casse_pas_le_script(monkeypatch):
    # Un guillemet dans l'URL ne doit pas sortir du littéral JS (json.dumps échappe).
    monkeypatch.setenv("STATS_API_URL", 'https://x.example.com/a"b')
    monkeypatch.delenv("BOUTIQUE_URL", raising=False)
    html = client.get("/").text
    assert '__STATS_API_URL__' not in html
    assert '\\"' in html  # le guillemet est échappé, pas brut
```

- [ ] **Step 2: Vérifier que le test échoue**

Run: `python -m pytest engine/test_stats_widget.py -q` (depuis la racine de portrait-cosmique)
Expected: FAIL — les placeholders `__STATS_API_URL__` sont encore présents tels quels
(absents pour le 1er test → AssertionError sur `'const STATS_API_URL = "";'`).

- [ ] **Step 3: Injecter la config dans `main.py`**

Remplacer la fonction `accueil()` par :

```python
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def accueil():
    html = Path(__file__).parent.joinpath("static/index.html").read_text(encoding="utf-8")
    # Widget « Guerre Cosmique » (stats boutique) : opt-in via l'environnement.
    # json.dumps produit un littéral JS sûr (guillemets échappés) — l'URL vient de
    # l'opérateur de l'instance, jamais de l'utilisateur.
    import json
    return (html
            .replace("__STATS_API_URL__", json.dumps(os.getenv("STATS_API_URL", "")))
            .replace("__BOUTIQUE_URL__", json.dumps(os.getenv("BOUTIQUE_URL", ""))))
```

(`os` et `json` : `os` est déjà importé en tête de `main.py` ; déplacer
`import json` en tête de fichier avec les autres imports plutôt que dans la fonction.)

- [ ] **Step 4: Ajouter la section HTML du widget dans `static/index.html`**

Juste AVANT la ligne `<footer class="mentions" ...>` (ligne ~502), insérer :

```html
    <section id="guerre-cosmique" class="guerre-cosmique" hidden>
      <h2 class="gc-titre">⚔️ La Guerre Cosmique</h2>
      <p class="gc-sous">Les posters les plus commandés, signe par signe.</p>
      <div class="gc-grille">
        <div class="gc-bloc" id="gc-podium"></div>
        <div class="gc-bloc" id="gc-duel"></div>
      </div>
      <p class="gc-total" id="gc-total"></p>
      <a id="gc-lien" class="btn secondary" href="#" target="_blank" rel="noopener noreferrer">Voir les posters les plus achetés →</a>
    </section>
```

- [ ] **Step 5: Ajouter le CSS du widget**

Dans le bloc `<style>` existant de `static/index.html`, ajouter :

```css
    .guerre-cosmique { margin-top: 26px; padding: 18px; border-radius: 14px;
      background: #171b2e; border: 1px solid #2b3050; text-align: center; }
    .gc-titre { margin: 0 0 4px; font-size: 1.15rem; color: #eef0fb; }
    .gc-sous { margin: 0 0 14px; font-size: 0.85rem; color: #9aa1c4; }
    .gc-grille { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    @media (max-width: 640px) { .gc-grille { grid-template-columns: 1fr; } }
    .gc-bloc { padding: 10px; border-radius: 10px; background: #1e2338; }
    .gc-bloc h3 { margin: 0 0 8px; font-size: 0.8rem; color: #9aa1c4;
      text-transform: uppercase; letter-spacing: 0.5px; }
    .gc-ligne { display: flex; justify-content: space-between; font-size: 0.9rem;
      color: #eef0fb; padding: 3px 0; }
    .gc-barre { height: 8px; border-radius: 4px; background: #0f1220; overflow: hidden;
      margin: 6px 0 10px; display: flex; }
    .gc-barre span { height: 100%; }
    .gc-barre .gc-a { background: #b98cf7; }
    .gc-barre .gc-b { background: #6ee7c3; }
    .gc-total { margin: 12px 0; font-size: 0.85rem; color: #9aa1c4; }
```

- [ ] **Step 6: Ajouter le script du widget**

Juste AVANT la ligne `</body>` (dernière ligne du fichier), insérer un nouveau bloc
`<script>` **auto-contenu** (aucune dépendance au reste de la page) :

```html
<script>
(function () {
  "use strict";
  const STATS_API_URL = __STATS_API_URL__;
  const BOUTIQUE_URL = __BOUTIQUE_URL__;
  // Widget opt-in : sans config, rien n'est affiché (comportement par défaut de
  // l'installation en une commande).
  if (!STATS_API_URL || !BOUTIQUE_URL) return;

  function texte(tag, contenu) {
    const el = document.createElement(tag);
    el.textContent = contenu;   // jamais innerHTML : données externes
    return el;
  }

  const ctrl = new AbortController();
  const minuteur = setTimeout(() => ctrl.abort(), 3000);

  fetch(STATS_API_URL, { signal: ctrl.signal })
    .then(r => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
    .then(stats => {
      clearTimeout(minuteur);
      // Dégradation : statut insuffisant, réponse inattendue ou vide → rien.
      if (!stats || stats.statut !== "ok" || !Array.isArray(stats.podiumZodiaque)
          || stats.podiumZodiaque.length === 0) return;

      const podium = document.getElementById("gc-podium");
      podium.appendChild(texte("h3", "Podium du mois"));
      stats.podiumZodiaque.forEach((p, i) => {
        const ligne = texte("div", (i + 1) + ". " + p.signe + " — " + p.part + "%");
        ligne.className = "gc-ligne";
        podium.appendChild(ligne);
      });

      const duel = (stats.duels || [])[0];
      if (duel) {
        const bloc = document.getElementById("gc-duel");
        bloc.appendChild(texte("h3", "Duel le plus serré"));
        bloc.appendChild(texte("div", duel.a + " " + duel.partA + "%"));
        bloc.appendChild(texte("div", duel.b + " " + duel.partB + "%"));
      }

      document.getElementById("gc-total").textContent =
        stats.totalCommandes + " posters commandés à ce jour";

      const lien = document.getElementById("gc-lien");
      lien.href = BOUTIQUE_URL;
      document.getElementById("guerre-cosmique").hidden = false;
    })
    .catch(() => {
      // Silencieux : la section (encore hidden) n'apparaît jamais —
      // portrait-cosmique fonctionne même si la boutique est down.
      clearTimeout(minuteur);
    });
})();
</script>
```

- [ ] **Step 7: Vérifier les tests Python**

Run: `python -m pytest engine/test_stats_widget.py -q`
Expected: PASS (3 tests).

Run: `python -m pytest engine -q`
Expected: PASS (suite complète, aucune régression).

- [ ] **Step 8: Ajouter la configuration à `.env.example`**

Ajouter à la fin de `.env.example` :

```bash
# Widget « Guerre Cosmique » (optionnel, opt-in) : stats publiques de la boutique YOP.
# Vide = widget désactivé (comportement par défaut).
STATS_API_URL=
BOUTIQUE_URL=
```

- [ ] **Step 9: Vérification manuelle des trois états (navigateur)**

Lancer `python -m uvicorn main:app --port 8410` et vérifier :

1. **Sans env** : http://localhost:8410 — aucune section Guerre Cosmique visible,
   aucun message d'erreur dans la console JS.
2. **API injoignable** : `STATS_API_URL=https://invalide.example/api/stats
   BOUTIQUE_URL=https://boutique.example.com python -m uvicorn main:app --port 8410` —
   la page est normale, la section n'apparaît pas (timeout 3 s absorbé).
3. **API vivante** : avec yop-boutique local (`npm run dev`) et ≥10 commandes payées
   seedées en DB — la section apparaît avec podium, duel, compteur, et le backlink
   pointe vers `BOUTIQUE_URL`.

- [ ] **Step 10: Commit**

```bash
git add main.py static/index.html .env.example engine/test_stats_widget.py
git commit -m "feat: widget Guerre Cosmique — stats boutique opt-in, dégradation silencieuse, backlink"
```

---

## Vérification finale (après Task 8)

Dans yop-boutique :
```bash
export DATABASE_URL_TEST="postgresql://test:test@localhost:5434/yop_test" DATABASE_URL="$DATABASE_URL_TEST"
npm test                      # tous les fichiers verts
npm run build                 # /stats + /api/stats présents
npx tsc --noEmit && npm run lint
```

Dans portrait-cosmique :
```bash
python -m pytest engine -q    # inclut test_stats_widget.py
```

## Self-review du plan (vérifié à l'écriture)

- Couverture spec : enrichissement DB (Tasks 1-3), agrégats + garde-fou + fenêtres
  (Tasks 4-5), API cache/CORS (Task 6), page /stats avec état insuffisant (Task 7),
  widget opt-in + dégradation + backlink + config env (Task 8), .env.example
  portrait-cosmique (Task 8), README yop (Task 7). Le `parSigne` ≥5 lignes et les
  « 2 duels les plus serrés » sont explicitement testés (Task 5).
- Cohérence de types : `CaracteristiquesLigne` (Task 3) ↔ `versCarac` (Tasks 4-5) ;
  `StatsAgregees` définie en Task 4, consommée telle quelle en Tasks 6-7 ;
  `obtenirStats` produite en Task 6, consommée en Task 7.
- YAGNI respecté : pas de temps réel, pas de table d'agrégats, pas de i18n widget
  (français v1), pas d'historique mensuel navigable.
