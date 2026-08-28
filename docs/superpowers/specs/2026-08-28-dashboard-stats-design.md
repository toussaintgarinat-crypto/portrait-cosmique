# Dashboard de stats ludiques « Guerre Cosmique » — design

**Date :** 2026-08-28
**Projet :** yop-boutique (implémentation principale) + widget portrait-cosmique
**Statut :** validé par l'utilisateur (brainstorming), en attente de revue finale
**Document fondateur :** `docs/strategie/2026-08-28-strategie-contenu-catalogue.md` (§ 3)

## Objectif

Afficher des statistiques de vente agrégées et anonymisées, croisées avec les
caractéristiques astrologiques et numérologiques des sujets des posters vendus, pour créer
un levier de preuve sociale, de curiosité et d'esprit de clan (« mon signe est-il en tête
ce mois-ci ? ») aux deux bouts du funnel :

- **dans la boutique** (yop-boutique) : page `/stats` + agrégats publics, au point d'achat ;
- **dans l'application** (portrait-cosmique) : widget léger avec backlink vers la boutique.

Cinq widgets, tels que définis dans le document stratégique : Guerre des Éléments, Podium
Zodiaque, Match des Opposés, Achat pour soi vs Cadeau offert, Nombres Maîtres.

## Contexte : ce qui existe déjà et ne change pas

- **yop-boutique** (repo séparé) contient le pipeline complet testé :
  checkout → Stripe → webhook → rendu print-ready → Gelato. La DB Postgres y stocke
  commandes/lignes avec `payload_personnalisation` (données de naissance brutes).
- Au moment du fulfillment, `traiterLigneCommande` appelle déjà
  `POST /portrait` sur portrait-cosmique et reçoit notamment `traditions` — dont
  `signe_solaire` (nom + élément), `signe_chinois` (animal) et `chemin_de_vie`. **Ces
  données traversent déjà le pipeline sans être persistées** : l'enrichissement ne coûte
  aucun appel réseau supplémentaire.
- **portrait-cosmique** (repo actuel) est l'app FastAPI + front statique auto-hébergeable.
  Elle n'a aucune connaissance de la boutique aujourd'hui.

## Décisions structurantes (validées en brainstorming)

| Sujet | Décision |
|---|---|
| Source de vérité des stats | **La DB commandes de yop-boutique** — seules les commandes **payées** comptent. |
| Où vivent les widgets v1 | **Les deux** : page `/stats` complète dans yop-boutique **et** widget léger dans portrait-cosmique consommant la même API (idée du backlink validée par l'utilisateur). |
| API | **Une seule API publique d'agrégats** `GET /api/stats` dans yop-boutique, anonymisée, cache 5 min, calcul SQL à la volée (pas de table d'agrégats tant que le volume ne le justifie pas). |
| Signal « cadeau » | **Case optionnelle « C'est un cadeau » par ligne de panier**, persistée **avant** Stripe (même logique anti-régénération que le reste du checkout). |
| Caractéristiques astro | **Persistées au fulfillment** depuis la réponse `/portrait` déjà appelée — pas de nouvelle dépendance réseau. |
| Vie privée | **Garde-fou volume** : moins de 10 commandes payées → réponse `insuffisant`, agrégats vides. Jamais de données individuelles, jamais de ratio identifiable. |
| Dégradation widget | portrait-cosmique est auto-hébergeable : l'URL de l'API stats est **configurable** (`STATS_API_URL`, vide = widget désactivé), fetch avec timeout court, section **masquée silencieusement** si l'API est injoignable. |

**Écart assumé vs. l'ébauche de design discutée :** `est_cadeau` vit sur
`lignes_commande` (et non sur `commandes`). Un panier peut mélanger un poster pour soi et
un mug-cadeau pour un proche ; le widget ventile par **signe du sujet de chaque ligne**,
donc le flag doit être par ligne pour être juste. L'UI panier n'existant pas encore
(plan B), aucun retravail : la case est simplement par article dans le futur formulaire.

## Architecture

```
┌────────────────────────────────────────────────────┐
│ yop-boutique (Next.js / Vercel)                    │
│                                                    │
│  DB commandes ──► lib/stats.ts (agrégats SQL)      │
│                      │                             │
│                      ├──► GET /api/stats (publique,│
│                      │        cache 5 min, CORS)   │
│                      └──► page /stats (lecture     │
│                           directe, pas de self-    │
│                           fetch HTTP)              │
└──────────────┬─────────────────────────────────────┘
               │ JSON agrégé anonymisé
               ▼
┌──────────────────────────────────────┐
│ portrait-cosmique (FastAPI, statique)│
│  widget « Guerre Cosmique »          │
│  STATS_API_URL (config, optionnelle) │
│  backlink vers la boutique           │
└──────────────────────────────────────┘
```

Deux consommateurs, une source : la page `/stats` appelle **directement** la fonction
d'agrégation (import de module), l'API route sert le même résultat au monde extérieur.
Le backlink du widget pointe vers la boutique (URL de l'API et URL de la boutique
configurables côté portrait-cosmique).

## Modèle de données (migration `0002`)

```
lignes_commande
  + est_cadeau boolean NOT NULL DEFAULT false
      # rempli à la création (checkout), par ligne de panier
  + caracteristiques jsonb NULL
      # rempli au fulfillment, depuis la réponse /portrait déjà reçue :
      # {
      #   "signe_solaire": "Capricorne",
      #   "element": "Terre",
      #   "animal_chinois": "Cheval",
      #   "chemin_de_vie": 7
      # }
```

- `est_cadeau` est connu **avant** le paiement (persistance au checkout, comme le
  payload) : le jour où l'UI panier existe, la case est par article.
- `caracteristiques` est nullable : une ligne `en_attente` n'en a pas. Une ligne en
  `echec_gelato` en a (voir Flux) — c'est voulu : **la personne a payé**, l'achat compte
  dans les stats même si le fulfillment attend un retry.
- Pas de colonne dédiée par caractéristique : le jsonb suffit largement à ce volume, et
  éventrer le schéma pour 4 colonnes lues uniquement en `GROUP BY` ne simplifie rien.

## Flux

### 1. Checkout (`POST /api/checkout`)

Le corps de requête accepte, par ligne, un champ optionnel `estCadeau: boolean`
(défaut `false`, validation type comme pour `quantite`). Persisté sur la ligne au moment
de la création de la commande, avant l'appel Stripe. Aucune metadata Stripe nécessaire :
la DB est la source de vérité des stats.

### 2. Fulfillment (`traiterLigneCommande`)

Après `recupererPortrait` (qui réussit ou fait échouer la ligne), et **avant** l'appel
Gelato : extraction du sous-ensemble utile depuis `traditions` et persistance via une
nouvelle fonction `marquerCaracteristiques(db, ligneId, {...})`. Idempotent (réécrire les
mêmes valeurs est sans effet). Un échec Gelato en aval n'efface rien : la ligne
`echec_gelato` reste comptable.

### 3. Calcul des agrégats (`src/lib/stats.ts`)

Une fonction pure `calculerStats(db, maintenant = new Date())` — la date injectée rend
les fenêtres temporelles testables. Toutes les requêtes filtrent sur les commandes payées
(`statut` ≠ `en_attente`/`echec_paiement`) et les lignes enrichies
(`caracteristiques IS NOT NULL`). Fenêtres :

| Widget | Fenêtre |
|---|---|
| Guerre des Éléments (% Feu/Terre/Air/Eau) | mois courant |
| Podium Zodiaque (Top 3 signes solaires) | mois courant |
| Match des Opposés (duels) | 12 mois glissants |
| Achat vs Cadeau (global + ventilation par signe) | 12 mois glissants || Nombres Maîtres (11, 22, 33) | tout temps |
| Compteur total de commandes | tout temps |

**Duels** : les 6 oppositions canoniques du zodiaque (Bélier/Balance, Taureau/Scorpion,
Gémeaux/Sagittaire, Cancer/Capricorne, Lion/Verseau, Vierge/Poissons). L'API renvoie les
**2 duels au score le plus serré** — un 49/51 est un moteur d'engagement, un 95/5 n'en
est pas un. Le calcul des parts est pondéré par ligne (pas par commande).
**Cadeau `parSigne`** : les 3 signes ayant la plus forte part de lignes-cadeaux (avec au
moins 5 lignes pour ce signe, sinon la ventilation n'est pas fiable).

**Garde-fou** : si le nombre total de commandes payées < 10, la fonction renvoie un état
`insuffisant` avec les agrégats à `null` — seuls le compteur total et le statut sont
exposés.

### 4. API publique `GET /api/stats`

Même payload que la page, mise en cache 5 min (`unstable_cache`), en-têtes CORS ouverts
en lecture (consommée par un front tiers : portrait-cosmique). Shape (noms français,
cohérents avec le reste du repo) :

```json
{
  "statut": "ok",
  "totalCommandes": 42,
  "guerreElements": { "feu": 34, "terre": 22, "air": 28, "eau": 16 },
  "podiumZodiaque": [{ "signe": "Capricorne", "part": 14 }, "..."],
  "duels": [{ "a": "Bélier", "b": "Balance", "partA": 48, "partB": 52 }, "..."],
  "cadeau": { "pourSoi": 61, "cadeau": 39, "parSigne": [{ "signe": "Lion", "partCadeau": 55 }] },
  "nombresMaitres": { "11": 3, "22": 1, "33": 0 }
}
```

En état `insuffisant` : `{ "statut": "insuffisant", "totalCommandes": 4, "guerreElements": null, ... }`.

### 5. Page `/stats` (yop-boutique)

Server component lisant `calculerStats` directement (aucun fetch HTTP vers soi-même),
rendu cosmique cohérent avec l'identité du poster : jauges pour les éléments, podium pour
les signes, barres face-à-face pour les duels, compteurs pour les Nombres Maîtres. En
état `insuffisant` : message de teasing (« Les étoiles alignent leurs forces… ») + CTA
catalogue — la page n'est jamais vide, elle est un argument de vente dès le premier jour.
`revalidate` aligné sur le cache de l'API.

### 6. Widget portrait-cosmique

Nouvelle section « Guerre Cosmique » dans le front statique (une fonction JS dédiée) :

- **Config** : `STATS_API_URL` (URL de l'API stats de la boutique) et `BOUTIQUE_URL`
  (destination du backlink), rendues dans le front depuis la config serveur FastAPI.
  `STATS_API_URL` vide ⇒ la section n'est pas rendue du tout (comportement par défaut
  de l'installation en une commande — le widget est opt-in).
- **Rendu** : fetch avec timeout ~3 s, affichage compact (podium + duel le plus serré +
  compteur), backlink visible « Voir les posters les plus achetés → ».
- **Dégradation** : timeout, erreur réseau, statut `insuffisant` ou réponse invalide ⇒
  section masquée silencieusement, aucun blocage, aucune erreur visible pour
  l'utilisateur de portrait-cosmique.

## Gestion d'erreurs

- **API stats injoignable depuis le widget** : dégradation gracieuse (ci-dessus) —
  portrait-cosmique doit fonctionner même si la boutique est down.
- **Volume insuffisant** : état `insuffisant`, jamais d'agrégat sur micro-volume
  (reconnaissance possible d'un individu dans un 100 % à une seule commande).
- **Ligne sans `caracteristiques`** (fulfillment pas encore joué) : exclue des
  agrégats astro, mais comptée dans `totalCommandes` — le compteur reflète l'activité
  réelle, les croisements astro attendent l'enrichissement.
- **Signature/API** : `GET /api/stats` est une lecture publique d'agrégats anonymisés —
  pas d'authentification, pas de paramètre client ; le cache absorbe tout abus de
  volume.

## Tests

Même discipline que le reste de yop-boutique : vrai Postgres de test, pas de mock d'ORM,
skip propre si `DATABASE_URL_TEST` absent.

- **Checkout** : `estCadeau` persisté par ligne, défaut `false`, rejet `400` si non
  booléen, aucune commande créée si invalide.
- **Fulfillment** : `caracteristiques` persistées après le portrait ; **persistées même
  si Gelato échoue ensuite** (ligne `echec_gelato` comptable) ; idempotent sur rejeu.
- **Agrégats** : avec des commandes seedées — pourcentages exacts des éléments, podium
  trié, duel le plus serré sélectionné, ventilation cadeau, compteurs Nombres Maîtres ;
  fenêtres temporelles via `maintenant` injecté (une commande du mois précédent n'est
  pas dans « mois courant ») ; garde-fou `< 10` renvoie `insuffisant` avec agrégats
  `null` ; lignes `en_attente` jamais comptées.
- **API route** : shape de la réponse, cache (deux appels consécutifs → une seule
  requête SQL), CORS présent.
- **Page `/stats`** : rend les widgets en état `ok`, message teasing + CTA en état
  `insuffisant`.
- **Widget portrait-cosmique** : vérification manuelle des trois états (désactivé par
  défaut, rendu OK, masquage sur timeout) — pas de harness de test JS côté front statique
  dans ce repo ; la logique de dégradation reste volontairement triviale.

## Hors périmètre de ce sprint

- Temps réel (WebSocket/SSE) — le cache 5 min suffit à l'effet « classement en direct ».
- Historique mensuel navigable (« le podium de mars »).
- Table d'agrégats précalculés (matérialisée) — à envisager si le volume dépasse ce que
  un `GROUP BY` à la volée absorbe.
- Les autres indicateurs imaginables (signes lunaires, ascendants — non calculés au
  fulfillment aujourd'hui).
- Le catalogue graphique SVG (§ 2 du document stratégique) et les nouveaux produits POD
  (T-shirts, mugs, tote-bags) : sous-projets suivants, spécifiés séparément.
- UI complète de la boutique (panier, formulaire avec case cadeau) : plan B déjà prévu —
  ce sprint rend l'API prête à la recevoir.
