# Comptes, DB & abonnements — préparation Free/Paid

**Sous-projet 3/5** du découpage global (cache → Portrait/intros → **auth+DB** → transits → Stripe).

## Objectif

Préparer la structure backend (comptes, profils natals persistés, statut d'abonnement)
nécessaire pour distinguer plus tard **Profil Natal** (gratuit, lead magnet, création
illimitée) de **Ciel du Jour & Transits** (payant, suivi quotidien). Ce sprint ne câble
ni le moteur de transits ni Stripe — il pose uniquement les fondations pour pouvoir les
brancher ensuite sans refonte du schéma.

## Contexte et contrainte produit

Le repo est public (Apache-2.0, GitHub), documenté et vendu comme **self-hostable, sans
compte, sans base de données** : le README promet explicitement « aucune clé, aucun
compte requis, aucune donnée conservée ». `main.py` est aujourd'hui 100 % stateless.

Ce sprint doit ajouter comptes/DB/abonnements **sans rompre cette promesse** pour qui ne
configure rien de plus.

## Principe directeur : DB optionnelle par variable d'environnement

Un seul repo, un seul `Dockerfile`, un seul `main.py`. La présence de `DATABASE_URL`
active ou non le mode compte :

- **`DATABASE_URL` absent** (défaut, self-hébergement tel quel) : comportement
  strictement identique à aujourd'hui. `/portrait`, `/theme`, `/lecture-approfondie`
  inchangés. Les routes `/auth/*`, `/profils/*`, `/moi` renvoient une erreur propre
  (404, pas un crash au démarrage). Aucune table n'est créée, aucune connexion DB
  n'est tentée.
- **`DATABASE_URL` présent** (instance officielle hébergée, ou self-hoster qui active
  volontairement les comptes) : les routes compte s'activent, `compteur_portraits`
  s'incrémente sur chaque `/portrait`.

`engine/` (le moteur de calcul pur) ne change pas : il reste appelé de la même façon,
que les données viennent du formulaire à la volée ou d'un `profils_natals` persisté.

## Stack technique

- **PostgreSQL** — standard pour comptes + abonnements + futurs webhooks Stripe
  (transactions fiables). Fonctionne en conteneur `docker-compose` (self-hébergé) et en
  hébergé/serverless (Neon, Supabase, Railway…) pour l'instance officielle.
- **SQLAlchemy + Alembic** pour l'accès DB et les migrations (standard FastAPI).
- Aucune nouvelle dépendance réseau obligatoire : l'envoi d'email est optionnel avec
  repli honnête (voir plus bas), suivant le pattern déjà en place pour
  `lecture_approfondie` (bonus IA optionnel, repli sur le récit déterministe si absent).

## Modèle de données

```
comptes
  id, email (unique), cree_le
  # pas de mot de passe : authentification par lien magique uniquement

liens_magiques
  id, compte_id, token (unique, aléatoire, ~32 octets), expire_le, utilise_le
  # court-vécu (15 min), usage unique (utilise_le posé au premier clic)

sessions
  id, compte_id, token (cookie httpOnly signé), expire_le
  # ~30 jours ; SameSite=Lax

profils_natals
  id, compte_id, label, prenoms, nom, date_naissance, heure_naissance,
  ville, latitude, longitude, utc_offset, systeme_numerologie,
  suivi_actif (bool, défaut false), cree_le
  # création illimitée et gratuite par compte (y compris pour tester) ;
  # suivi_actif = suivi quotidien payant (Ciel du Jour/Transits) activé sur ce profil

abonnements
  id, compte_id (unique), statut ("inactif"|"actif"|"essai"|"annule"),
  stripe_customer_id, stripe_subscription_id, plan,
  debut_le, fin_le, maj_le
  # rempli manuellement (script CLI, voir plus bas) pour ce sprint ; un futur
  # webhook Stripe écrira ces mêmes colonnes sans changer le schéma

compteur_portraits
  id (ligne unique, id=1), total (bigint), maj_le
  # incrémenté à chaque appel /portrait (anonyme ou non) quand DATABASE_URL est
  # configuré ; métrique publique affichable sur le site ("N portraits calculés")
```

### Règle des 4 suivis actifs

Vérifiée en Python (pas en contrainte SQL), avant de poser `suivi_actif=true` sur un
profil :

1. L'abonnement du compte (`abonnements.statut`) est `actif`.
2. Moins de 4 profils du compte ont déjà `suivi_actif=true`.

Sinon : `402 Payment Required` avec un message explicite. La création de profils natals
elle-même n'est jamais limitée — seul le nombre de suivis actifs simultanés l'est.

## Flux d'authentification (lien magique)

1. `POST /auth/demande-lien {email}` — crée le compte s'il n'existe pas, génère un
   token dans `liens_magiques`, envoie un email avec le lien de vérification. Répond
   toujours `200 OK` générique, que l'email existe déjà ou non (anti-énumération).
2. `GET /auth/verifier?token=...` — si le token est valide, non expiré, non utilisé :
   le marque utilisé, crée une `session`, pose le cookie, redirige vers l'app connectée.
   Sinon : page d'erreur claire (« lien expiré, redemande-en un »).
3. **Envoi d'email** : si un service d'email est configuré (`EMAIL_SMTP_URL` ou
   équivalent) → envoi réel. Sinon, **repli honnête** : le lien est écrit dans les logs
   serveur avec un avertissement (« email non configuré — lien affiché en clair pour le
   dev/self-hoster »), au lieu de planter ou de bloquer silencieusement.
4. `POST /auth/deconnexion` — invalide la session courante.

## Endpoints

```
POST /auth/demande-lien          {email} → 200 générique
GET  /auth/verifier?token=...    → pose le cookie de session, redirige
POST /auth/deconnexion           → invalide la session
GET  /moi                        → compte courant + statut abonnement (401 si déconnecté)

GET    /profils                  → liste des profils_natals du compte
POST   /profils                  → crée un profil natal (illimité)
PATCH  /profils/{id}             → modifie (y compris suivi_actif, avec la règle des 4)
DELETE /profils/{id}             → supprime

POST   /profils/import-local     → importe un tableau de profils venus du localStorage

GET  /stats                      → {"portraits_calcules": N} — public, sans auth
```

## Prêt pour Stripe, sans Stripe

Aucun SDK Stripe n'est câblé ce sprint. Pour pouvoir tester la logique d'abonnement
quand même : un script CLI `scripts/toggle_abonnement.py --email x@y.com --statut actif`
qui écrit directement les colonnes de `abonnements` — exactement celles qu'un futur
webhook Stripe (`checkout.session.completed`, `customer.subscription.deleted`, etc.)
écrirait à sa place. Aucune route HTTP publique pour ça ; usage dev/admin en ligne de
commande uniquement.

## Import des profils localStorage

À la première connexion réussie (après clic sur le lien magique), le front vérifie
l'existence de profils dans `portrait-cosmique-profils` (localStorage, cf. sous-projet
1/5). S'il y en a : propose « Importer mes N profils enregistrés sur cet appareil ? ».
Sur confirmation : `POST /profils/import-local` avec le tableau tel quel (mêmes champs
que la structure localStorage existante) → un `profils_natals` par entrée,
`suivi_actif=false` par défaut. Import simple, sans déduplication — l'utilisateur peut
supprimer un doublon ensuite. Le localStorage n'est pas vidé après import (au cas où
l'utilisateur navigue déconnecté par la suite).

## Cas aux limites

1. **`DATABASE_URL` absent** : `/auth/*`, `/profils/*`, `/moi` renvoient 404 propre
   (pas un crash, pas de tentative de connexion DB). `/portrait` etc. inchangés.
2. **Lien magique expiré ou déjà utilisé** : `GET /auth/verifier` renvoie une erreur
   claire, jamais une session invalide silencieuse.
3. **Email non configuré** : lien loggé côté serveur au lieu d'être envoyé (repli
   honnête, jamais un plantage).
4. **5ᵉ tentative de suivi actif sans abonnement/quota disponible** : `402` explicite,
   la création/modification du profil (hors `suivi_actif`) reste possible.
5. **Import localStorage avec 0 profil local** : le front ne propose simplement pas
   l'import (pas d'endpoint appelé).

## Hors périmètre de ce sprint

- Le moteur de transits (calcul ciel du jour × natal) — sous-projet suivant (4/5).
- L'intégration Stripe réelle (Checkout, webhooks) — sous-projet après (5/5).
- Tout changement au comportement stateless existant (`/portrait`, `/theme`,
  `/lecture-approfondie` ne changent pas de contrat).
- Emails transactionnels autres que le lien magique.
- Réinitialisation de mot de passe (pas de mot de passe dans ce modèle).

## Tests

Tests Python (pytest, comme le reste du repo) sur la logique métier pure :

- Validité / expiration / usage unique des liens magiques.
- Règle des 4 suivis actifs (accepté sous la limite, `402` au-dessus, indépendant du
  nombre total de profils créés).
- Comportement du feature-flag : `DATABASE_URL` absent → routes compte en 404 propre,
  démarrage de l'app sans erreur, `/portrait` inchangé.
- Import localStorage : tableau vide, tableau avec doublons, champs manquants
  (repli sur les valeurs par défaut du profil).

Les tests touchant réellement la DB tournent contre une Postgres de test (service
dédié dans `docker-compose.yml`, pas de mock d'ORM).
