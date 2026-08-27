# YOP — boutique de cadeaux personnalisés astro — design

**Date :** 2026-08-27
**Projet :** YOP (nom de marque provisoire — "Your Own Project" ou "Your Own Personne", non tranché)
**Statut :** validé par l'utilisateur (brainstorming), en attente de revue finale

## Objectif

Créer un site boutique e-commerce **custom** (pas Shopify), sous la marque YOP, qui
vend des cadeaux personnalisés basés sur les signes astrologiques (posters, mugs,
textile, et autres supports du catalogue Gelato). Le visuel de chaque produit est
généré à partir des données de naissance saisies par le client, réutilisant le moteur
de calcul déjà existant dans **portrait-cosmique**. La production et l'expédition
physiques sont déléguées à **Gelato** (print-on-demand) via son API.

Ce document ne couvre que le **premier sous-projet** : le pipeline complet
personnalisation → paiement → génération du fichier print-ready → commande Gelato,
avec un catalogue large dès le lancement (posters, mugs, textile, autres). Le nom de
marque définitif reste ouvert et n'affecte pas ce design.

## Contexte : ce qui existe déjà et ne change pas

- **portrait-cosmique** (repo actuel) expose déjà publiquement `POST /theme` (et
  `/portrait`), qui renvoie `theme_complet` (carte astrologique complète) et
  `traditions` (dict brut égyptien/celte/amérindien/maya) à partir d'une fiche de
  naissance. Stateless, sans clé, sans compte — YOP l'appelle tel quel, comme le fait
  déjà `static/index.html`. **Aucun changement requis côté portrait-cosmique.**
- Le rendu visuel du poster (SVG → PNG haute résolution) existe déjà, mais
  **uniquement côté navigateur** (JS dans `static/index.html`, cf.
  `docs/superpowers/specs/2026-08-27-onglet-poster-design.md`). Ce design prévoit de
  porter cette logique dans YOP sous une forme réutilisable côté serveur (voir
  Architecture).

## Décisions structurantes (validées en brainstorming)

| Sujet | Décision |
|---|---|
| Plateforme boutique | **Custom, pas Shopify** — site YOP entièrement maison. |
| Périmètre catalogue v1 | **Large dès le départ** : posters, mugs, textile (t-shirt/hoodie), autres (cartes, coques, canvas...) via le catalogue Gelato. |
| Compte client | **Commande invité, sans compte** — infos de naissance + livraison + paiement en un seul flux, confirmation par email. |
| Repo | **Nouveau repo séparé** de portrait-cosmique — cycle de déploiement propre, appelle l'API portrait-cosmique comme un service externe public. |
| Paiement | **Stripe** (Checkout Session). |
| Pipeline de rendu | **Générateur SVG isomorphe** porté depuis l'existant, utilisé pour l'aperçu client (navigateur) et pour le fichier final print-ready (rendu serveur au moment de la commande). |
| UI | **Responsive / mobile-first** — l'achat de cadeaux se fait majoritairement depuis mobile ; l'aperçu SVG personnalisé doit rester lisible et utilisable en petit écran, pas juste redimensionné. |

## Architecture

```
┌─────────────────────┐      appel public HTTP       ┌──────────────────────────┐
│  YOP (nouveau repo)  │ ───────────────────────────► │  portrait-cosmique (API) │
│  Next.js sur Vercel  │ ◄─────────────────────────── │  existant, inchangé       │
└──────────┬───────────┘   theme_complet / traditions └──────────────────────────┘
           │
           │ SVG isomorphe (module TS partagé, préview navigateur + rendu serveur)
           │
   ┌───────┴────────┐        ┌──────────┐        ┌───────────────┐
   │  Stripe         │        │  DB       │        │  Gelato API    │
   │  Checkout       │        │  commandes│        │  (fulfillment) │
   └────────────────┘        └──────────┘        └───────────────┘
```

**Composants du nouveau repo YOP :**
- **Storefront Next.js**, responsive/mobile-first (catalogue, formulaire de
  personnalisation, aperçu live, panier, checkout) — déployé sur Vercel, domaine
  propre à la marque.
- **Module de rendu isomorphe** (fonction pure `données astro + options → SVG`) porté
  depuis `static/index.html` de portrait-cosmique. Utilisé tel quel côté navigateur
  (aperçu live pendant la personnalisation) et côté fonction serverless (génération du
  fichier final, à la résolution/bleed exacts du produit Gelato ciblé). Une seule
  source de vérité pour le rendu — évite la duplication de logique et garantit un
  résultat reproductible (réimpression, SAV).
- **API routes serverless** (Next.js route handlers) : création de session Stripe,
  webhook Stripe, webhook Gelato.
- **DB commandes** — Postgres léger (Neon/Vercel Postgres), indépendant de la DB
  comptes/abonnements de portrait-cosmique (pas de compte client ici, juste le suivi
  des commandes pour le SAV/réimpression).
- **Storage fichiers** (Vercel Blob ou S3) pour héberger temporairement les PNG
  print-ready générés, le temps que Gelato les récupère.

## Modèle de données

```
commandes
  id, email, cree_le, statut ("en_attente"|"payee"|"envoyee_gelato"|
    "en_production"|"expediee"|"echec_paiement"|"echec_gelato")
  stripe_checkout_session_id (unique), stripe_payment_intent_id
  adresse_livraison (jsonb : nom, rue, ville, cp, pays)
  total_paye, devise

lignes_commande
  id, commande_id, produit_gelato_sku, variante (taille/couleur/support),
  quantite, prix_unitaire
  payload_personnalisation (jsonb : prénoms/nom/date/heure/lieu naissance,
    type de rendu — poster ciel/traditions, densité, fond transparent, etc.)
  fichier_print_url (rempli après rendu serveur, avant envoi à Gelato)
  gelato_order_id, gelato_item_id, statut_ligne

evenements_gelato
  id, ligne_commande_id, type (ex. "item_status_updated"), payload_brut,
  recu_le
  # trace brute des webhooks Gelato, utile pour debug/SAV ; déduplication par
  # identifiant d'événement pour ne jamais retraiter deux fois le même
```

**Pourquoi une commande a plusieurs `lignes_commande`** : un panier peut contenir
plusieurs produits pour des personnes différentes (ex. un poster pour soi, un mug pour
un proche) — chaque ligne porte son propre `payload_personnalisation` et son propre
statut d'avancement Gelato, indépendamment du reste de la commande.

**Pourquoi stocker `payload_personnalisation` plutôt que juste le PNG final** :
permet de régénérer le fichier à tout moment (réimpression, changement de résolution,
bug de rendu corrigé après coup) sans redemander les infos de naissance au client.

## Flux bout-en-bout

**1. Personnalisation (côté client, aucune écriture DB)**
Client choisit un produit → remplit prénoms/nom/date/heure/lieu de naissance → le
front appelle `POST /theme` sur portrait-cosmique (public, tel quel) → le module de
rendu isomorphe affiche l'aperçu SVG live, responsive (toggle type/densité/fond
transparent selon le produit). Ajout au panier = on garde juste
`{produit_sku, variante, payload_personnalisation}` en état local (pas d'appel
serveur, pas de rendu PNG à ce stade).

**2. Checkout**
Panier validé → le front crée une **Stripe Checkout Session** via une API route YOP,
qui **avant** de rediriger vers Stripe, insère `commandes` (statut `en_attente`) + une
`ligne_commande` par article (avec son `payload_personnalisation`). Stripe reçoit le
`commande_id` en metadata.

**3. Paiement confirmé (webhook Stripe `checkout.session.completed`)**
Seul déclencheur de la suite — jamais avant paiement réel :
- passe `commandes.statut = "payee"`
- pour chaque ligne : rejoue le module de rendu **côté serveur** avec le
  `payload_personnalisation` stocké → SVG → rasterisation à la résolution/bleed du
  produit Gelato ciblé → upload storage → `fichier_print_url`
- appelle `POST /orders` Gelato avec SKU + `fichier_print_url` + adresse de livraison
  → stocke `gelato_order_id` → statut ligne `envoyee_gelato`

**4. Suivi (webhook Gelato)**
Gelato notifie les changements d'état (`en_production`, `expediee`, tracking) →
écrit dans `evenements_gelato` (déduplication par id d'événement) → met à jour
`statut_ligne` → si le statut global de toutes les lignes atteint `expediee`,
`commandes.statut = "expediee"` → email de confirmation au client.

## Gestion d'erreurs

- **Paiement Stripe échoué/abandonné** : aucune écriture au-delà de `en_attente`,
  rien n'est envoyé à Gelato — pas de nettoyage nécessaire, la ligne reste simplement
  orpheline et invisible pour l'utilisateur.
- **Rendu serveur échoue** (SVG invalide, timeout rasterisation) :
  `commandes.statut = "echec_gelato"`, la ligne concernée reste sans
  `gelato_order_id`, une alerte (log + email interne) part immédiatement — le client a
  payé, il ne doit jamais rester sans suite silencieuse. Retry manuel possible via un
  script admin qui rejoue l'étape 3 pour cette ligne précise (le
  `payload_personnalisation` étant stocké, aucune perte de données).
- **Appel Gelato échoue** (API down, SKU invalide) : même traitement — statut
  `echec_gelato`, alerte, retry manuel idempotent (vérifie `gelato_order_id` avant de
  recréer pour éviter un doublon de commande physique).
- **Webhook Stripe/Gelato dupliqué ou hors ordre** : idempotence par identifiant
  d'événement stocké (Stripe event id, Gelato event id) — un événement déjà traité est
  ignoré silencieusement.

## UI / Responsive

Site mobile-first (Next.js + approche utilitaire type Tailwind) : catalogue,
formulaire de personnalisation, aperçu SVG et checkout Stripe doivent être testés en
priorité sur mobile, l'essentiel du trafic d'achat de cadeaux personnalisés étant
attendu depuis smartphone. L'aperçu SVG doit rester lisible et manipulable en petit
écran (pas de simple redimensionnement d'un composant pensé desktop-first).

## Tests

Même discipline que portrait-cosmique : tests sur la logique métier pure, pas de
mocks lourds.

- **Module de rendu isomorphe** : tests unitaires `données astro → SVG`
  (structure/snapshot, pas pixel-perfect) — un même jeu de données produit un SVG
  déterministe, indépendamment de l'environnement (navigateur vs Node).
- **Rasterisation serveur** : test d'intégration léger — un SVG connu produit un PNG
  aux dimensions attendues pour un SKU Gelato donné (dimensions vérifiées, pas le
  contenu visuel).
- **Séquencement commande** : tests sur la state machine des statuts
  (`en_attente → payee → envoyee_gelato → expediee`), y compris les branches d'échec
  (`echec_paiement`, `echec_gelato`), contre une DB de test — pas de mock ORM.
- **Idempotence webhooks** : un même event Stripe/Gelato reçu deux fois ne crée pas de
  doublon de commande ni de double appel Gelato.
- **Retry manuel** : rejouer l'étape de rendu+envoi Gelato sur une ligne en
  `echec_gelato` la fait passer à `envoyee_gelato` sans dupliquer si un
  `gelato_order_id` existe déjà.
- Pas de test end-to-end contre les vraies API Stripe/Gelato en CI — sandbox/clés de
  test uniquement, appelées explicitement en local si besoin.

## Hors périmètre de ce sprint

- Comptes clients / historique de commandes connecté (commande invité uniquement pour
  l'instant).
- Choix final du nom de marque (YOP reste provisoire).
- Domaine et branding visuel définitifs.
- Emails transactionnels détaillés (contenu/templates) au-delà de la confirmation de
  commande et de l'alerte d'échec interne.
- Gestion des retours/remboursements physiques (au-delà du statut `echec_gelato`).
- Programme de réductions/codes promo.
