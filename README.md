# 🔮 Portrait Cosmique

*[English version](README.en.md)*

Renseigne tes prénoms, nom, date, heure et lieu de naissance : reçois un portrait complet
qui croise **numérologie, astrologie occidentale, astrologie chinoise, astrologie védique,
tradition égyptienne, celte, amérindienne et maya (Tzolkin)**. Gratuit, instantané,
auto-hébergeable.

> Lecture symbolique — divertissement, pas un fait. Ce que le moteur calcule (positions
> astrales, chemins numérologiques, correspondances calendaires) est exact ; ce qu'il en
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
