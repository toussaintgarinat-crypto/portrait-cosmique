# Carte astrologique complète -- design

**Date :** 2026-08-21
**Projet :** portrait-cosmique
**Statut :** validé par l'utilisateur (brainstorming 7 sections), en attente de revue finale

## Objectif

Étendre le moteur `portrait-cosmique` pour produire une **carte astrologique
complète** à partir d'une fiche de naissance, en complément du portrait
multi-traditions existant. La carte couvre six zones :

1. Les fondations (Soleil, Lune, Ascendant, Descendant, MC, IC).
2. Les 10 corps principaux (Soleil → Pluton).
3. Les points évolutifs (Nœud Nord, Nœud Sud, Chiron, Lilith).
4. Les 12 maisons (3 systèmes au choix).
5. Les aspects majeurs **et** mineurs entre tous les points.
6. Les 5 dominantes (élément, mode, planète, signe, maison) selon 2 méthodes au
   choix.

La carte est rendue dans l'UI sous forme de **roue zodiacale SVG interactive**
(côté HTML) et de **tableaux détaillés** (côté PDF/impression).

## Décisions structurantes (validées en brainstorming)

| Sujet | Décision |
|---|---|
| Éphéméride | **VSOP87 embarqué en stdlib only** (pas de dépendance externe) -- cohérent avec le moteur existant. |
| Système de maisons | **Whole Sign par défaut** + Placidus et Equal House au choix utilisateur. |
| Aspects | **Tous (majeurs + mineurs)** entre **tous les points** (18 points). |
| Dominantes | **2 méthodes au choix** : comptage + dignités essentielles ; score complexe (Jones/Muzzarelli). |
| Intégration API | **Nouvel endpoint `/theme`** dedié **+ intégration au `/portrait` existant** (récit/empreinte exploitent les nouvelles données). |
| Rendu UI | **Tableaux pour le PDF** + **roue SVG pour le HTML**, exposés dans un onglet « Carte astro complète ». |

## Architecture & modules

Découpe par responsabilité (approche B du brainstorming). Chaque module est
testable isolément, fonctions pures (entrées → sortie, pas d'état, pas
d'horloge) -- cohérent avec `engine/traditions.py`.

```
engine/
  ephemeride.py      # VSOP87 (Mercure→Neptune), Pluton (Meeus ch.37),
                     # Chiron (série approchée), Lilith (apogée lunaire moyen),
                     # Nœuds Nord/Sud (dérivés Lune + nœud moyen),
                     # rétrogradation (d Ω/dt < 0)
  maisons.py         # Whole Sign / Placidus / Equal House
  aspects.py         # majeurs + mineurs, orbes paramétrables par type de point
  dominantes.py      # méthode 1 (comptage + dignités essentielles)
                     # méthode 2 (score complexe : longitude, vitesse, angles,
                     #            rétro, aspects)
  theme_complet.py   # orchestrateur : assemble la carte complète
  traditions.py      # inchangé (verbatim Workplace) -- theme_astral reste
                     # pour compat ascendante ; theme_complet le réutilise
  significations.py  # étendu : clefs d'interprétation pour les nouveaux
                     # corps/points/aspects/dominantes (FR + EN)
  synthese.py        # étendu : exploite les dominantes + aspects dans le
                     # récit déterministe et l'archetype
  test_ephemeride.py
  test_maisons.py
  test_aspects.py
  test_dominantes.py
  test_theme_complet.py
main.py              # +endpoint /thème, /portrait etendu
static/index.html    # onglet « Carte astro complète » + roue SVG +
                     # tableaux ; export PDF garde les tableaux
```

**Principes :**

- Toutes fonctions pures (entrées → sortie), testables hors ligne.
- `ephemeride.py` expose `longitude(corps, dt_utc) → {longitude, latitude,
  distance, vitesse, rétrograde}`. Les autres modules consomment ces longitudes
  sans savoir comment elles sont calculées (frontière nette).
- `theme_complet` est l'unique point d'entree public : `theme_complet(fiche) →
  dict`.
- Les dominantes et aspects consomment la sortie de `theme_complet` (ou de ses
  sous-fonctions) -- pas de recalcul.
- `significations.py`/`synthese.py` grandiront ; si > 800 lignes on scinde, mais
  on commence monolithique pour rester cohérent avec le style existant.

**Caveat d'honnêteté** affiché dans l'UI et le PDF : « Soleil → Neptune :
précision VSOP87 (< 1"). Pluton / Chiron : formule approchée stdlib
(~ 0,1-1°) -- suffisant pour signe/maison, limite pour aspects serrés. Sans
Swiss Ephemeris. »

## `ephemeride.py`

### Portee

Longitudes (écliptique géocentrique tropicale de la date) + vitesse +
rétrogradation pour 13 corps/points physiques et lunaires :
Soleil, Lune, Mercure, Venus, Mars, Jupiter, Saturne, Uranus, Neptune, Pluton,
Chiron, Lilith, Nœud Nord.

L'Ascendant et le MC ne sont **pas** calculés ici : ils proviennent de
`traditions.theme_astral` (déjà implantés et exacts). Le Nœud Sud est
symétrique du Nœud Nord (Nord + 180 °), déduit par l'orchestrateur.

### API

```python
CORPS = ["Soleil", "Lune", "Mercure", "Venus", "Mars", "Jupiter",
         "Saturne", "Uranus", "Neptune", "Pluton", "Chiron", "Lilith",
         "Nœud Nord"]

def longitude(corps: str, dt: datetime, utc_offset_h: float,
              latitude: float, longitude_geo: float) → dict:
    """Retourne {corps, longitude, latitude, distance_au, vitesse_°_j,
                rétrograde, méthode}.
    `latitude` et `longitude_geo` ne servent que pour Asc/MC (geres par
    traditions.theme_astral) -- ignorees ici pour les corps physiques."""

def positions(dt: datetime, utc_offset_h: float,
              latitude: float, longitude_geo: float) → dict[str, dict]:
    """Tous les CORPS d'un coup (réutilise l'heure UTC calculee une fois)."""
```

### Méthodes par corps

| Corps | Methode | Précision attendue |
|---|---|---|
| Soleil | déjà dans `traditions.soleil_longitude` (Meeus) -- **réutilise** | < 0,01 ° |
| Lune | déjà dans `traditions.lune_longitude` (ELP abrégé) -- **réutilise** | ~ 0,1° |
| Mercure → Neptune | **VSOP87** série tronquée à ~ 2000 termes/corps (fichier ~ 5000 lignes total) | < 1" sur 1800-2100, °rade au-dela |
| Pluton | formule approchée Meeus (Astronomical Algorithms ch. 37, polynome période 1800-2100) | ~ 0,1-0,5 ° |
| Chiron | orbite elliptique osculatrice (elements de Meeus/Standish a l'époque T, correction du 1er ordre) | ~ 0,1-1° |
| Lilith | apogée lunaire moyen (série simple Meeus ch. 47 -- `Ω_mean` de la Lune) | exact pour valeur moyenne |
| Nœud Nord | nœud lunaire moyen = `Ω_mean` (Meeus) ; ou vrai (série complète) -- **moyen par défaut** (usage astrologique standard) | moyen : exact ; vrai : ~ 0,1° |

### Rétrogradation

Comparaison de la longitude a `t` et `t + 1h`. `vitesse_°_j` = dérivée finie
sur 1h × 24. `rétrograde = vitesse < 0`. Cohérent pour tous les corps (meme
Pluton/Chiron).

### VSOP87 -- découpe

Le fichier `ephemeride.py` contiendra les séries VSOP87 tronquées. Pour
maitriser la taille, on embarque les termes d'amplitude > 1e-6 rad
(~ 99 % de la précision avec ~ 200-400 termes/corps). Termes L0/L1/L2/L3/L4 par
planète. Format : liste de tuples `(amplitude, longitude_noeud,
longitude_planete, longitude_perturbateur)` -- le format VSOP87 standard.

### Époque & référentiel

TT (temps terrestre) pour VSOP87 -- on convertit UT1 → TT via ΔT (formule
Espenak-Meeus, embarquée). Longitude geocentrique écliptique de la date (vraie
equinoxe) -- on ne ramenne PAS en J2000, l'astrologie tropicale veut la position
a l'instant de naissance. Nécessaire pour cohérence avec
`soleil_longitude` existant.

### Tests

Cas pivots (0 °, 90 °, 180 °, 270 °) sur J2000 + comparaison avec 5-10
dates de référence publiées (NASA JPL Horizons en source externe pour préparer
les tests, mais pas au runtime). Tolérance : 0,01 ° pour Mercure → Neptune,
1 ° pour Pluton/Chiron.

## `maisons.py`

### Portee

3 systèmes de maisons, à partir de l'Ascendant et du MC déjà calcules par
`traditions.theme_astral`.

### API

```python
SYSTEMES = ["whole_sign", "placidus", "equal_house"]

def maisons(asc: float, mc: float, latitude: float,
            système: str = "whole_sign") → list[dict]:
    """12 maisons : [{maison: 1, signe, symbole, longitude_cuspe, ...}]
    `asc`/`mc` en °rés écliptiques. `latitude` en °rés."""
```

### Par système

**Whole Sign (defaut)** -- déjà implante dans `traditions.theme_astral`. Maison
1 = signe entier de l'Ascendant, maisons 2-12 = signes suivants. Cuspe = debut
du signe (multiples de 30 °). Robuste à toute latitude. Reutilise la logique
existante.

**Equal House** -- 12 cuspes a 30 ° à partir de l'Ascendant exact. Maison 1 =
[asc, asc+30), ..., maison 12 = [asc+330, asc+360). Indépendant du MC. Robuste a
toute latitude. Trivial : `cuspe_i = (asc + 30*i) % 360`.

**Placidus** -- le standard moderne. Chaque cuspe (sauf 1=Asc, 4=IC, 7=Desc,
10=MC) est l'intersection de l'écliptique avec un diviseur spatio-temporel :
maisons 2,3,11,12 au-dessus de l'horizon découpent l'arc semi-diurne en tiers ;
maisons 5,6,8,9 sous l'horizon découpent l'arc semi-nocturne en tiers. Iteration
: pour chaque cuspe, on cherche la longitude écliptique λ telle que
l'ascension droite du point (λ, 0) atteigne une fraction (1/3 ou 2/3) de
l'arc diurne/nocturne du point γ.

### Caveat Placidus

Aux latitudes |phi| > 66° (cercle polaire), l'arc semi-diurne/nocturne peut
s'inverser -- Placidus devient indéfini. Repli automatique vers Equal House
au-dessus de 66° avec un avertissement dans le `méta` de la carte
(`"système_effectif": "equal_house"`, `"raison": "latitude > 66° -- Placidus indéfini"`).

### Schéma de sortie (tous systèmes)

```python
{"maison": 1, "cuspe": 12.5, "signe": "Bélier", "symbole": "Aries",
 "longitude_cuspe": 12.5}
```

Placidus/Egal : `cuspe` en °rés exacts (peut etre 12,5 °). Whole Sign :
`cuspe` = début de signe (0 °, 30 °...), plus on garde l'info « signe de la
maison » comme déjà fait.

### Maisons des planètes

Pas calculees dans `maisons.py` -- c'est l'orchestrateur `theme_complet` qui,
pour chaque corps, trouve la maison dont l'intervalle [cuspe_i, cuspe_{i+1})
contient la longitude du corps. Pour Whole Sign, c'est juste
`signe == signe_maison`.

### Tests

Un cas de référence Placidus publié (ex. chart d'exemple de test astrologique
avec cuspes connus), verification que Whole Sign == Equal House quand l'Asc est
a 0° d'un signe, et le repli polaire.

## `aspects.py`

### Portee

Calcul des aspects majeurs **et** mineurs entre **tous les points** de la
carte : 10 corps + Chiron + Lilith + Nœud Nord + Nœud Sud + Ascendant + MC +
Descendant + IC = 18 points.

### API

```python
ASPECTS = {
    "conjonction":     {"angle": 0,   "type": "majeur"},
    "opposition":      {"angle": 180, "type": "majeur"},
    "trigone":         {"angle": 120, "type": "majeur"},
    "carre":           {"angle": 90,  "type": "majeur"},
    "sextile":         {"angle": 60,  "type": "majeur"},
    "semi_sextile":    {"angle": 30,  "type": "mineur"},
    "semi_carre":      {"angle": 45,  "type": "mineur"},
    "quintile":        {"angle": 72,  "type": "mineur"},
    "sesquicarre":     {"angle": 135, "type": "mineur"},
    "quinconce":       {"angle": 150, "type": "mineur"},
}

ORBES_BASE = {
    "majeur_luminaire": 10,   # aspects majeurs impliquant Soleil ou Lune
    "majeur_planete":   8,    # aspects majeurs entre planetes
    "majeur_point":     5,    # aspects majeurs impliquant Asc/MC/Nuds
    "mineur":           3,    # tous les aspects mineurs
}

def aspects(points: dict[str, dict], orbes: dict | None = None) → list[dict]:
    """Retourne [{aspect, type, point_a, point_b, orb, exactitude}].
    Pas de doublon : A-B et pas B-A. Pas d'auto-aspect (A-A)."""

def filtrer_par_type(aspects: list, type_: str) → list:
    """'majeur' | 'mineur' | 'tous' -- pour l'UI."""
```

### Logique

1. On prend les 18 longitudes (°rés écliptiques).
2. Pour chaque paire (A, B) avec A < B dans l'ordre canonique, pour chaque aspect
   défini, on calcule `écart = |(|longitude_A - longitude_B| - angle)|`
   normalisé sur [0, 180].
3. Si `écart ≤ orbe` : aspect retenu. Sinon ignoré.
4. **Orbe** = min des orbes des deux points (le plus restrictif gagne).
   Soleil/Lune = luminaire. Mercure → Pluton = planète.
   Asc/MC/Desc/IC/Nuds/Chiron/Lilith = point.
5. `exactitude` = `1 - (écart / orbe)` (0 = limite, 1 = parfait). Pour le tri :
   on retourne les aspects tries par `exactitude` decroissante.

### Exemple de sortie

```python
{
    "aspect": "trigone",
    "type": "majeur",
    "point_a": "Soleil",
    "point_b": "Jupiter",
    "angle_exact": 120.0,
    "angle_reel": 118.3,
    "orb": 1.7,
    "orbe_max": 8,
    "exactitude": 0.79,
}
```

### Caveat Pluton/Chiron

On documente dans le `méta` que les aspects serrés (< 1°) impliquant Pluton
ou Chiron sont a interprèter avec prudence vu la précision réduite.

### Tests

Cas avec positions connues → vérifier que les aspects attendus sont trouvés,
qu'aucun faux positif n'apparait hors orbe, pas de doublons, tri correct.

## `dominantes.py`

### Portee

2 méthodes au choix, calculant 5 dominantes : **élément**, **mode**,
**planète**, **signe**, **maison**.

### API

```python
METHODES = ["comptage_dignite", "score_complexe"]

def dominantes(points: dict, maisons: list, aspects: list,
               méthode: str = "comptage_dignite") → dict:
    """Retourne {
        element: {dominant, scores: {Feu: x, Terre: y, ...}},
        mode: {dominant, scores: {Cardinal, Fixe, Mutable}},
        planete: {dominante, scores: {Soleil: x, ...}},
        signe: {dominant, scores: {Bélier: x, ...}},
        maison: {dominante, scores: {1: x, 2: y, ...}},
        méthode, detail
    }"""
```

### Méthode 1 -- comptage + dignités essentielles (`comptage_dignite`)

Pour chaque planète (10 corps + Nœud Nord/Chiron/Lilith exclus du score planète
pour ne pas polluer), on ajoute des points :

- **Position** : 1 point au signe, 1 point à la maison, 1 point à l'élément,
  1 point au mode.
- **Pondération luminaire** : Soleil, Lune, Asc x2 (l'Asc n'est pas une planète
  mais on le compte comme influence dominante).
- **Dignités essentielles** (table embarquée) :
  - **Domicile** : planète dans le signe qu'elle gouverne → +5 (ex. Mars en
    Bélier/Scorpion).
  - **Exaltation** : +4 (ex. Soleil en Bélier).
  - **Chute** (exil) : -3 (ex. Mars en Balance/Gémeaux).
  - **Déchéance** (exaltation opposee) : -2.
  - **Triplicité diurne/nocturne** : +2 (selon chart diurne/nocturne — déterminé
    par Soleil au-dessus/sous l'horizon, calculé depuis le MC).
  - **Terme** : +1 (table egyptienne de Cleomede, embarquée).
  - **Face** (décan) : +1 (sequence planetaire chaldeenne, embarquée).

Pour la **planète dominante** : somme de ses points de dignité + pondération
luminaire + 1 si en maison angulaire (1/4/7/10) + 0,5 si en maison succédente
(2/5/8/11).

Pour l'**élément/mode/signe/maison dominants** : on somme les contributions de
chaque planète présente.

### Méthode 2 -- score complexe (`score_complexe`, style Jones/Muzzarelli)

Score planète par planète, sur 100, somme :

| Critere | Points max |
|---|---|
| Dignite ( domicile/exaltation/triplicite/terme/face ) | 30 |
| Maison angulaire (1/4/7/10) | 15 ; succédente (2/5/8/11) | 8 |
| Proximite aux angles Asc/MC ( < 8° du cuspe ) | 15 |
| Vitesse angulaire ( lente/arret/rétro = 10 ; moyenne = 5 ; rapide = 0 ) | 10 |
| Nombre d'aspects recus ( majeurs surtout ) | 15 |
| Luminaire ( Soleil/Lune/Asc ) | +15 bonus |
| Retrogradation | +5 ( amplifie l'effet symbolique ) |
| Conjonction au Soleil ( < 17 ° = combuste ) | -10 ( brule ) ; < 8° = cazimi | +5 ( cœur ) |
| Lien au nœud nord ( conjonction < 3° ) | +10 |

Pour élément/mode/signe/maison : on agrège les scores planétaires (chaque
planète contribue au signe/maison/élément/mode où elle se trouve, pondérée par
son score). Le signe/maison/élément/mode avec le total le plus haut l'emporte.

### Chart diurne vs nocturne

(utilise par triplicite) : déterminé en comparant la longitude du Soleil a
l'Asc/Desc. Si Soleil au-dessus de l'horizon (entre Asc et Desc par la voie
diurne) = diurne, sinon nocturne. Calcule depuis l'Asc/Desc/MC.

### Tables embarquées dans le module

- `DOMICILES = {Mars: ["Bélier", "Scorpion"], ...}`
- `EXALTATIONS = {Soleil: "Bélier", ...}`
- `TRIPPLICITES = {(element, "diurne"): gouverneur, (element, "nocturne"): gouverneur}`
- `TERMES_EGYPTIENS = {signe: [(0-6, planete), (6-14, planete), ...]}` (12 × 5)
- `FACES_CHALDEENNES = {signe: [planete_decan1, planete_decan2, planete_decan3]}`

### Choix utilisateur

Parametre `méthode_dominantes` de la fiche (par defaut `comptage_dignite`).
L'UI expose un selecteur. Les deux méthodes sont calculables et comparables.

### Tests

Cas avec chart connue (ex. thème de référence publié avec dominantes
documentees) pour chaque méthode. Vérification que la chart diurne/nocturne est
correcte. Vérification des tables (pas de signe orphelin).

## `theme_complet.py` (orchestrateur) + endpoints API

### `theme_complet.py` -- unique point d'entree public

```python
def theme_complet(fiche: dict) → dict:
    """Assemble la carte astrologique complète.
    Repli honnête : chaque sous-section absente si donnees manquantes,
    jamais d'erreur. Méta décrit ce qui a ete calcule et les caveats."""

def theme_complet_depuis_traditions(trad: dict, fiche: dict) → dict:
    """Variante : réutilise un calcul traditions déjà fait (evite de
    recalculer Soleil/Asc/MC). Utilise par /portrait etendu."""
```

### Schéma de sortie

```python
{
    "fondations": {                          # Les 6 fondations
        "soleil":       {signe, symbole, °ré, longitude, maison},
        "lune":         {signe, symbole, °ré, longitude, maison},
        "ascendant":    {signe, symbole, °ré, longitude},
        "descendant":   {signe, symbole, °ré, longitude},   # asc + 180
        "milieu_du_ciel": {signe, symbole, °ré, longitude},
        "fond_du_ciel": {signe, symbole, °ré, longitude},   # mc + 180
    },
    "dix_corps": {                           # Les 10 corps principaux
        "Soleil":   {signe, symbole, °ré, longitude, latitude,
                     distance_au, vitesse, rétrograde, maison, méthode},
        "Lune":     {...},
        "Mercure":  {...}, "Venus": {...}, "Mars": {...},
        "Jupiter":  {...}, "Saturne": {...}, "Uranus": {...},
        "Neptune":  {...}, "Pluton": {...},
    },
    "points_evolutifs": {                    # Les 4 points evolutifs
        "noeud_nord": {signe, symbole, °ré, longitude, maison, méthode},
        "noeud_sud":  {signe, symbole, °ré, longitude, maison},
        "chiron":     {signe, symbole, °ré, longitude, maison, méthode},
        "lilith":     {signe, symbole, °ré, longitude, maison, méthode},
    },
    "maisons": [                             # Les 12 maisons
        {maison, cuspe, signe, symbole, longitude_cuspe, système},
        ...
    ],
    "aspects": [                             # tous les aspects (majeurs + mineurs)
        {aspect, type, point_a, point_b, angle_exact, angle_reel,
         orb, orbe_max, exactitude},
        ...
    ],
    "dominantes": {                          # les 5 dominantes
        "element":  {dominant, scores},
        "mode":     {dominant, scores},
        "planete":  {dominante, scores},
        "signe":    {dominant, scores},
        "maison":   {dominante, scores},
        "méthode":  "comptage_dignite",
        "chart_diurne": true,
        "detail":   {...}                    # decomposition du score dominant
    },
    "meta": {
        "système_maisons_demande":   "whole_sign",
        "système_maisons_effectif":  "whole_sign",
        "méthode_dominantes_demande":  "comptage_dignite",
        "méthode_dominantes_effectif": "comptage_dignite",
        "heure_utc": 14.5,
        "delta_t": 69.2,
        "caveats": [
            "Pluton/Chiron : formule approchée stdlib (~ 0,1-1°) -- suffisant pour signe/maison, limite pour aspects serrés.",
            "Nœud lunaire moyen (par defaut) -- differe du nœud vrai de ~ 0,1°.",
        ],
        "sources": ["VSOP87 tronque", "Meeus Astronomical Algorithms", ...],
    },
}
```

### Logique d'orchestration

1. Parse la fiche -- repli si champ manquant (date/heure/lieu).
2. Calcule l'heure UTC, le JD, ΔT une seule fois (variables partagees via un
   petit objet `Contexte` interne, pas d'état global).
3. Récupère Soleil/Asc/MC depuis `traditions.theme_astral` (déjà implante) --
   réutilisation, pas duplication.
4. Calcule les 13 positions manquantes via `ephemeride.positions`.
5. Construit `fondations` (Soleil, Lune, Asc, Desc=Asc+180, MC, IC=MC+180).
6. Détermine la maison de chaque point via
   `maisons.maisons(asc, mc, lat, système)`.
7. Construit `dix_corps` et `points_evolutifs` avec leur maison.
8. Calcule les aspects via `aspects.aspects(toutes_les_positions)`.
9. Calcule les dominantes via
   `dominantes.dominantes(positions, maisons, aspects, méthode)`.
10. Assemble le `méta` avec les caveats et la méthode effective.

### Endpoints API dans `main.py`

```python
class Fiche(BaseModel):                      # etendue
    # champs existants inchanges
    système_maisons: str = "whole_sign"      # "whole_sign" | "placidus" | "equal_house"
    méthode_dominantes: str = "comptage_dignite"  # "comptage_dignite" | "score_complexe"
```

```python
@app.post("/thème", tags=["portrait"])
def thème(body: Fiche) → dict:
    """Carte astrologique complète (fondations, 10 corps, points evolutifs,
    maisons, aspects, dominantes). Seule la date est absolument requise --
    sans heure/lieu, seules les fondations Soleil/Lune sont calculees
    (Lune approximative sans heure) ; le reste en repli honnête."""
    tc = theme_complet.theme_complet(body.model_dump())
    if not tc.get("fondations", {}).get("soleil"):
        raise HTTPException(422, "Indique au moins une date de naissance valide.")
    return tc
```

```python
@app.post("/portrait", tags=["portrait"])    # etendu
def portrait(body: Fiche) → dict:
    """Etendu : la reponse inclut desormais `theme_complet` intègre au
    portrait pour que le récit déterministe et l'empreinte exploitent
    les nouvelles donnees (dominantes, aspects)."""
    trad = traditions.calculer(body.model_dump())
    if not trad.get("signe_solaire"):
        raise HTTPException(422, "Indique au moins une date de naissance valide.")
    tc = theme_complet.theme_complet_depuis_traditions(trad, body.model_dump())
    p = synthese.portrait(trad, theme_complet=tc, nom=..., langue=body.langue)
    return {"traditions": trad, "theme_complet": tc,
            "portrait": p,
            "empreinte": significations.expliquer(trad, body.langue, theme_complet=tc),
            "glossaire": significations.glossaire(body.langue)}
```

### Sans heure/lieu

`/thème` renvoie juste les fondations Soleil (+ Lune approximative à midi si pas
d'heure). Le `méta` liste `"sans_heure": true`, `"sans_lieu": true` et les
sections non calculees sont absentes du JSON -- pas de nulls partout, juste
omises (coherent avec le style `traditions.calculer`).

## UI (`static/index.html`)

### Structure

Un formulaire → bouton « Calculer » → portrait + empreinte + récit + export
HTML/PDF. On ajoute un onglet « Carte astro complète » dans les résultats.

### Onglets des résultats

1. **Portrait** (existant) -- stats, archétype, récit, empreinte multi-traditions.
2. **Carte astro complète** (nouveau) -- la carte détaillée.

Le selecteur FR/EN et les boutons export s'appliquent aux deux onglets.

### Contenu de l'onglet « Carte astro complète »

**Options en haut de l'onglet** (rechargent la carte via `/thème` sans
recalculer le portrait) :
- Système de maisons : `Whole Sign` / `Placidus` / `Equal House` (boutons radio).
- Méthode des dominantes : `Comptage + dignités` / `Score complexe` (boutons
  radio).

**Layout :** deux colonnes en desktop, empilées en mobile.

**Colonne gauche -- Roue SVG :**

- Cercle zodiacal (12 signes en périphérie, symboles + ticks tous les 30 °).
- Anneau des 12 maisons (numerotees, cuspes visibles).
- Position des 10 corps + 4 points évolutifs sur l'anneau planetaire (glyphes
  astrologiques standards, avec °ré exact en tooltip).
- Lignes d'aspects dans le centre : traits pleins pour majeurs (couleur par
  type : conjonction bleu, opposition rouge, trigone vert, carre orange,
  sextile violet), traits pointillés pour mineurs. Épaisseur selon
  `exactitude`.
- Légende cliquable sous la roue pour filtrer par type d'aspect
  (majeurs/mineurs/tous).
- Le SVG est génère côté client en JS depuis le JSON de `/thème` (pas d'image
  serveur).

**Colonne droite -- Tableaux détaillés :**

1. **Les fondations** (6 lignes) : point | signe | °ré | maison.
2. **Les 10 corps** (10 lignes) : corps | symbole | signe | °ré | maison |
   vitesse | R (si rétrograde).
3. **Points évolutifs** (4 lignes) : Nœud Nord/Sud, Chiron, Lilith.
4. **Les 12 maisons** (12 lignes) : n° | cuspe | signe.
5. **Aspects** (tableau triable) : aspect | type | point A | point B | orb |
   exactitude. Filtres par type.
6. **Dominantes** (5 cartes) : élément / mode / planète / signe / maison,
   chacune avec la valeur dominante + barres de scores relatives.

### Caveat d'honnêteté

Affiche sous la roue : badge « Précision : VSOP87 (Soleil → Neptune < 1"),
Pluton/Chiron formule approchée (~ 0,1-1°). Sans Swiss Ephemeris. ».

### Export

- **HTML autonome** (existant) : inclut la roue SVG inline + les tableaux.
  L'onglet actif est memorise.
- **PDF / impression** : la feuille de style `@media print` masque les
  boutons/options et n'affiche que les **tableaux** (pas la roue, qui ne
  s'imprime pas proprement en SVG sur tous les navigateurs). Layout une
  colonne, optimisé A4. Le PDF reprend les 6 sections de tableaux + les
  dominantes.

### i18n

Tous les labels traduits FR/EN, comme déjà fait dans l'existant. Le glossaire
etendu couvre les nouveaux termes (rétrogradation, cazimi, combuste, orbe,
cuspe, dignité, triplicité, chart diurne/nocturne).

### Performances

Calcul des 16 positions + aspects + dominantes en < 200 ms côté serveur
(VSOP87 tronque est rapide). Roue SVG rendue en < 50 ms côté client.

### Accessibilité

La roue SVG a un `rôle="img"` + `aria-label` résumant la carte. Les tableaux
sont des `<table>` sémantiques avec `<caption>`.

## `significations.py` / `synthese.py` étendus + tests

### `significations.py` étendu

Ajout de clefs d'interprétation (FR + EN) pour :
- **10 corps** : mot-clé par corps (ex. Mercure → « communication, raisonnement,
  échanges ») + modulation par signe (déjà partiellement présent pour
  Soleil/Lune/Asc, à étendre aux 7 autres).
- **4 points évolutifs** : Nœud Nord (direction de vie), Nœud Sud (acquis
  karmique), Chiron (blessure/guérison), Lilith (ombre/désir refoulé).
- **Aspects** : interprétation par couple aspect × nature (ex. « carre
  Soleil-Mars → tension entre identite et action »).
- **Dominantes** : phrase résumé par dominante (ex. élément Eau dominant →
  « sensible, intuitif, empathique »).
- **Retrogradation** : mention dans la clef planète (ex. « Mercure rétrograde :
  intériorisation de la pensée »).

`expliquer()` prend désormais un `theme_complet` optionnel et enrichit
l'empreinte avec une sous-section « Carte astro complète » qui reprend les 6
zones (fondations, 10 corps, points évolutifs, maisons, aspects, dominantes) en
mots-cles.

### `synthese.py` étendu

`portrait()` prend un `theme_complet` optionnel et :
- Enrichit l'**archetype** en croisant la planète dominante avec le signe
  dominant (ex. « Mars en Bélier dominant → Le Pionnier Ardent »).
- Ajoute une mention des **aspects majeurs les plus exacts** dans les
  forces/points a travailler (ex. trigone Soleil-Jupiter a 0,3 ° → force
  « vision étendue, confiance naturelle » ; carre Saturne-Lune a 1° →
  point a travailler « rigueur émotionnelle »).
- Ajoute une mention des **dominantes** dans le récit (élément/mode dominants →
  paragraphe sur le temperament).
- Tient compte de la **rétrogradation** des planetes dominantes dans le récit.

### Tests (nouveaux fichiers)

| Fichier | Couverture |
|---|---|
| `test_ephemeride.py` | Cas pivots J2000 pour Mercure → Neptune (tolerance 0,01 °) ; Pluton/Chiron (tolerance 1°) ; rétrogradation detectee sur dates connues ; Lilith/Nœud sur dates de référence. |
| `test_maisons.py` | Whole Sign == Equal quand Asc à 0° d'un signe ; cuspes Placidus vs référence publiée ; repli > 66°. |
| `test_aspects.py` | Aspect trouvé dans orbe, aucun hors orbe, pas de doublons, tri par exactitude, orbes par type de point. |
| `test_dominantes.py` | Chart diurne/nocturne correcte ; dignités essentielles (domicile/exaltation/chute) ; table des termes/faces complète (12 × 5 et 12 × 3) ; coherence des deux méthodes sur un cas simple. |
| `test_theme_complet.py` | Carte complète d'une date de référence → tous les champs présents ; repli sans heure/lieu ; coherence `theme_complet_depuis_traditions` vs `theme_complet` ; choix du système de maisons change les maisons mais pas les positions ; `méta` contient les caveats. |

### Tests d'integration

Extension `test_traditions.py` ou nouveau fichier : endpoint `/thème` via
`TestClient` FastAPI ; `/portrait` étendu contient `theme_complet`.

### Cas de référence

Une date de naissance publique avec thème publié (ex. 1er janvier 2000 a 12h
UTC, 0° N 0° E -- les positions JPL Horizons sont connues et réutilisables
comme oracle de test, sans dépendance runtime).

### Couverture cible

> 90 % sur les nouveaux modules (engine bien isole, fonctions pures).
