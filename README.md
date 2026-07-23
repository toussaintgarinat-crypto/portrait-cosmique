# 🔮 Portrait Cosmique

*[English version](README.en.md)*

Renseigne tes prénoms, nom, date, heure et lieu de naissance : reçois un portrait complet
qui croise **numérologie, astrologie occidentale, astrologie chinoise, astrologie védique,
tradition égyptienne, celte, amérindienne et maya (Tzolkin)**. Gratuit, instantané,
auto-hébergeable.

> Lecture symbolique — divertissement, pas un fait. Ce que le moteur calcule (positions
> astrales, chemins numérologiques, correspondances calendaires) est exact ; ce qu'il en
> tire (archétype, forces/faiblesse, récit) est une interprétation.

## Démarrage en 30 secondes

```bash
git clone <ce-dépôt> portrait-cosmique && cd portrait-cosmique
docker compose up -d --build
```

Ouvre http://localhost:8410 — remplis le formulaire, obtiens ton portrait. Aucune clé,
aucun compte, aucune donnée conservée : tout est calculé à la volée et rien n'est stocké.

## Ce que tu obtiens

- **Stats de personnalité** (Charisme, Combativité, Sagesse, Créativité, Discrétion,
  Stabilité, Émotivité, Énergie) agrégées depuis toutes les traditions calculées.
- **Archétype**, **forces dominantes**, **point à travailler** + **pierre d'équilibrage**
  (gemmologie compensatoire choisie en fonction de ta faiblesse).
- **Empreinte multi-traditions** : Soleil, Lune, Ascendant, astrologie chinoise, Nakshatra
  védique, divinité égyptienne, arbre celte, totem amérindien, glyphe maya, chemin de vie,
  expression du nom — chaque valeur expliquée en mots-clés.
- **Récit symbolique** qui tisse tout ça en une lecture cohérente.
- **Français ou anglais** — même moteur, mêmes données, langue au choix.

## Coût réel : zéro

Le portrait est calculé par un moteur **100% Python** (numérologie, mécanique céleste,
calendriers), sans base de données, sans réseau, sans clé API, sans LLM. Zéro coût,
zéro dépendance externe pour la fonctionnalité principale.

## Bonus optionnel : lecture approfondie par IA

Une réécriture littéraire du récit est disponible en option, si :
- tu renseignes une clé **OpenRouter** gratuite (`OPENROUTER_API_KEY` dans `.env`, voir
  `.env.example`) avec un modèle gratuit (`OPENROUTER_MODEL`, ex. `google/gemma-3-27b-it:free`) —
  active le bonus pour **tous les visiteurs** de ton instance ;
- ou chaque visiteur fournit **sa propre clé** depuis le formulaire (« Options avancées »)
  — n'importe quel endpoint compatible OpenAI, zéro coût porté par toi.

⚠️ **Si tu exposes cette instance publiquement** et renseignes une clé par défaut,
n'importe quel visiteur la consomme (même à $0, tu restes soumis aux limites de débit du
modèle gratuit choisi). Réserve ce réglage à un usage privé/familial, ou laisse le champ
vide pour que seuls ceux qui fournissent leur propre clé profitent du bonus.

Sans configuration, le récit déterministe (déjà riche) fait foi — repli honnête, jamais
d'erreur affichée à l'utilisateur.

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
