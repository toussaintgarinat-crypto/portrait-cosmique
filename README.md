# 🔮 Portrait Cosmique

*[English version](README.en.md)*

Renseigne tes prénoms, nom, date, heure et lieu de naissance : reçois un portrait complet
qui croise **numérologie, astrologie occidentale, astrologie chinoise, astrologie védique,
tradition égyptienne, celte, amérindienne et maya (Tzolkin)**. Gratuit, instantané,
auto-hébergeable.

> Lecture symbolique — divertissement, pas un fait. Les calculs suivent les conventions et approximations documentées ; ce qu'il en
> tire (archétype, forces/faiblesse, récit) est une interprétation.

## Installation

### Prérequis

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose (inclus dans Docker Desktop).
- `git`.
- `curl` (pour la commande en une ligne ci-dessous, et pour la vérification de démarrage
  du script — déjà présent par défaut sur macOS et la plupart des distributions Linux).
- Le port **8410** libre sur ta machine (changeable dans `docker-compose.yml` si besoin,
  ex. `"8420:8410"`).
- Sous **Windows** : le script d'installation est en bash — utilise **WSL** ou **Git
  Bash** (Docker Desktop pour Windows fonctionne avec les deux). L'installation manuelle
  ci-dessous, elle, marche partout où Docker tourne (PowerShell/CMD inclus).

### En une commande

```bash
curl -fsSL https://raw.githubusercontent.com/toussaintgarinat-crypto/portrait-cosmique/main/install.sh | bash
```

Ça clone le dépôt dans `./portrait-cosmique`, construit l'image et lance le service —
rien de plus (pas de `sudo`, pas d'écriture hors de ce dossier). Relancer la même
commande plus tard **met à jour** (`git pull` + rebuild) au lieu de re-cloner. Le script
est court et lisible ; si tu préfères l'inspecter avant de l'exécuter :

```bash
curl -fsSL https://raw.githubusercontent.com/toussaintgarinat-crypto/portrait-cosmique/main/install.sh -o install.sh
less install.sh   # relis-le
bash install.sh
```

### Ou manuellement

```bash
git clone https://github.com/toussaintgarinat-crypto/portrait-cosmique.git
cd portrait-cosmique
docker compose up -d --build
```

Dans les deux cas, vérifie que ça tourne :

```bash
curl http://localhost:8410/sante
# {"statut":"ok","service":"portrait-cosmique","version":"0.1.0","lecture_approfondie_configuree":false}
```

Puis ouvre **http://localhost:8410** dans ton navigateur : remplis le formulaire (au
minimum une date de naissance), clique sur « Calculer mon portrait ».

Aucune clé, aucun compte requis, aucune donnée conservée : chaque calcul est fait à la
volée, rien n'est écrit sur disque (pas de base de données).

**Arrêter / mettre à jour** :

```bash
docker compose down                    # arrêter
git pull && docker compose up -d --build   # mettre à jour puis relancer
```

**Sans Docker** (dev local) : `pip install -r requirements.txt` puis
`uvicorn main:app --reload --port 8410` depuis la racine du dépôt (le fichier `main.py`
détecte tout seul le sous-dossier `engine/` en local).

## Ce que tu obtiens

- **Stats de personnalité** (Charisme, Combativité, Sagesse, Créativité, Discrétion,
  Stabilité, Émotivité, Énergie) agrégées depuis toutes les traditions calculées.
- **Archétype**, **forces dominantes**, **point à travailler** + **pierre d'équilibrage**
  (gemmologie compensatoire choisie en fonction de ta faiblesse).
- **Empreinte multi-traditions** : Soleil, Lune, Ascendant, astrologie chinoise, Nakshatra
  védique, divinité égyptienne, arbre celte, totem amérindien, glyphe maya, chemin de vie,
  expression du nom — chaque valeur expliquée en mots-clés.
- **Récit symbolique** qui tisse tout ça en une lecture cohérente.
- **Français ou anglais** — même moteur, mêmes données, langue au choix (bouton FR/EN).

## Extensions holistiques

La Matrice dispose de son propre onglet. BaZi, Arbre de Vie, Tzolkin maya, lecture védique, calendrier des 13 arbres et numérologie du nom sont réunis dans **Traditions natales**, avec les mêmes icônes d’explication que les autres traditions. Le formulaire distingue les prénoms du **nom de famille à la naissance** (ex. Dupont-Martin).

Le fuseau est calculé automatiquement depuis les coordonnées du lieu, la date et l’heure de naissance (`tzfpy` + règles historiques IANA `tzdata`). Lors d’une heure répétée au passage à l’heure d’hiver, le formulaire demande la première ou seconde occurrence ; une heure inexistante est signalée. Sans heure, les modules calendaires restent utilisables.

- **Matrice de la destinée** : cinq points A–E calculés à partir de la date, arcanes de Marseille, octogramme interactif au clavier et au toucher. Exemple du 05/09/1990 : **5, 9, 19, 6, 12**. La réduction additionne les chiffres au-delà de 22 ; ce n'est pas un modulo. Les axes amour et finances restent des repères symboliques sans scores.
- **BaZi** : quatre piliers, maître du jour, présence des cinq éléments et Yin/Yang. Nécessite heure civile et décalage UTC historique. Année à Li Chun, mois solaires, jour à minuit ; calcul approché près des frontières, sans correction en temps solaire vrai ni pondération saisonnière des forces.
- **Arbre de Vie** : dix sephiroth avec correspondance personnelle explicitement moderne (alphabet latin cyclique et date), sans prétendre à une gématrie hébraïque universelle. Aucun résultat de nom n'est produit si aucune lettre n'est exploitable.
- **Tzolkin** : glyphe, tonalité et numéro de cycle 1–260, corrélation GMT traditionnelle ; distinct du Dreamspell.
- **Calendrier des treize arbres** : convention moderne en périodes fixes de 28 jours, distincte de l'ancien module des 21 arbres utilisé par la synthèse. Les deux conventions sont identifiées à l'écran.
- **Védique** : Nakshatra, pada, longitude sidérale et ayanamsa de Lahiri approchés. La précision est explicitée, sans présenter ce moteur comme une éphéméride exacte.

Le formulaire distingue le nom affiché du **nom de naissance** utilisé pour l'expression, l'âme et la personnalité. La polarité facultative ne modifie aucun calcul. Avec **heure inconnue**, la carte est masquée et aucune Lune n'est attribuée arbitrairement à midi ; les calculs indépendants de l'heure restent disponibles.

Le Portrait conserve les traditions et la synthèse ; la Carte astro contient les détails occidentaux. Les dix aspects disposent d'aides, avec explication des majeurs/mineurs, des orbes et de l'exactitude. La roue suit le flux du document sur mobile.

Le poster propose un **SVG autonome** et un **PNG 3 000 × 3 000 px à 300 DPI** (25,4 cm de côté), y compris pour la matrice. La matrice et les nouvelles lectures sont incluses dans l'export HTML et l'impression.

Les conventions et références sont détaillées dans [docs/holistique-conventions.md](docs/holistique-conventions.md). Le moteur IA reçoit les mêmes résultats structurés que l'interface ; les approximations et données absentes y sont conservées.

## Coût réel : zéro

Tout ce qui précède est calculé par un moteur **100% Python** (numérologie, mécanique
céleste, calendriers), sans base de données, sans réseau, sans clé API, sans LLM. Zéro
coût, zéro dépendance externe pour la fonctionnalité principale.

## Activer la lecture approfondie (bonus IA optionnel)

Par défaut, le récit est déjà rédigé (déterministe, voir ci-dessus) — la lecture
approfondie est une **réécriture littéraire par une IA** du même contenu, purement
optionnelle. Deux façons de l'activer, au choix :

### Option A — une clé pour toute l'instance (pratique en famille/perso)

1. Crée un compte gratuit sur [openrouter.ai](https://openrouter.ai) et génère une clé API
   (Settings → Keys). C'est gratuit tant que tu utilises un modèle marqué **`:free`**.
2. Choisis un modèle gratuit sur [openrouter.ai/models](https://openrouter.ai/models)
   (filtre « Free ») — par défaut ce dépôt propose `google/gemma-3-27b-it:free`, mais
   n'importe quel modèle `:free` avec function-calling non requis fonctionne.
3. Copie `.env.example` en `.env` :
   ```bash
   cp .env.example .env
   ```
4. Édite `.env` :
   ```bash
   OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   OPENROUTER_MODEL=google/gemma-3-27b-it:free
   ```
5. Redémarre :
   ```bash
   docker compose up -d --build
   ```
6. Vérifie : `curl http://localhost:8410/sante` doit répondre
   `"lecture_approfondie_configuree":true`. Le bouton « ✨ Approfondir avec l'IA » (sous
   le portrait, section « Approfondir avec l'IA ») fonctionne alors pour **tous les
   visiteurs** de cette instance, sans qu'ils aient rien à saisir.

⚠️ **Si cette instance est exposée publiquement** (pas juste sur ton réseau local),
n'importe quel visiteur consomme cette clé — même à $0, tu restes soumis aux limites de
débit (rate limit) du modèle gratuit choisi, et un visiteur mal intentionné peut les
épuiser pour tout le monde. Réserve l'option A à un usage privé/familial ; pour un usage
public, préfère l'option B ci-dessous (ou les deux à la fois : la clé BYOK d'un visiteur,
si fournie, a toujours priorité sur la clé par défaut de l'instance).

### Option B — chaque visiteur fournit sa propre clé (BYOK, adapté au public)

Rien à configurer côté serveur. Chaque visiteur :
1. Ouvre « Options avancées » dans le formulaire.
2. Renseigne son propre endpoint (n'importe quel service compatible OpenAI-chat) :
   - **Base URL** (ex. `https://openrouter.ai/api/v1`, ou l'endpoint d'un autre
     fournisseur, ou un modèle local type Ollama/LM Studio) ;
   - **Clé API** ;
   - **Modèle** (ex. `openai/gpt-4o-mini`, `anthropic/claude-3-5-haiku`…).
3. Calcule son portrait, puis clique « ✨ Approfondir avec l'IA » : l'appel part vers SA
   clé, zéro coût pour l'hébergeur de l'instance.

### Dans tous les cas

- Sans rien configurer (ni A ni B), le bouton tente quand même l'appel, échoue proprement
  et **retombe sur le récit déterministe** (`"source":"repli"` côté API) — jamais
  d'erreur affichée, jamais de blocage de l'expérience.
- La langue de la réécriture suit la langue choisie dans l'interface (FR/EN).

## Export

- **Télécharger en HTML** : fichier autonome, généré côté navigateur, à garder ou partager.
- **Imprimer / Enregistrer en PDF** : ouvre le dialogue d'impression du navigateur avec une
  mise en page dédiée (formulaire et boutons masqués).

## Origine

Extrait du moteur holistique du projet [Workplace](https://github.com/toussaintgarinat-crypto) —
`engine/` (`traditions.py`, `synthese.py`, `significations.py`) est une copie **verbatim**,
synchronisée depuis la source. `main.py`, `llm.py` et `static/` sont propres à ce produit.

## Licence

Apache-2.0 — voir [LICENSE](LICENSE) et [NOTICE](NOTICE).
