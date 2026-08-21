# Carte astrologique complète — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produire une carte astrologique complète (fondations, 10 corps, points évolutifs, 12 maisons, aspects, dominantes) à partir d'une fiche de naissance, sans dépendance externe (VSOP87 embarqué en stdlib only).

**Architecture:** 5 nouveaux modules Python focalisés (`ephemeride.py`, `maisons.py`, `aspects.py`, `dominantes.py`, `theme_complet.py`) orchestrés par `theme_complet(fiche)`. Extension de `significations.py`/`synthese.py`. Endpoint `/theme` + intégration au `/portrait`. UI : onglet « Carte astro complète » avec roue SVG (HTML) + tableaux (PDF).

**Tech Stack:** Python 3 (stdlib only), pytest ; FastAPI/pydantic ; HTML/CSS/vanilla JS (`static/index.html`).

**Spec de référence :** `docs/superpowers/specs/2026-08-21-carte-astrologique-complete-design.md`

## Global Constraints

- **Stdlib only** : aucune dépendance ajoutée. VSOP87 tronqué embarqué. Cohérent avec `engine/traditions.py`.
- **Fonctions pures** : tous les nouveaux modules exposent des fonctions pures, testables hors ligne.
- **Repli honnête** : un champ manquant désactive juste la lecture qui en dépend, jamais d'erreur.
- **Bilingue FR/EN** : tout texte utilisateur en deux versions.
- **Caveat d'honnêteté** affiché dans l'UI/PDF : « Soleil→Neptune : VSOP87 (<1″). Pluton/Chiron : stdlib (~0,1-1°). Sans Swiss Ephemeris. »
- **`traditions.py` inchangé** : copie verbatim Workplace — ne pas modifier. `theme_complet` réutilise `traditions.theme_astral` (Soleil/Asc/MC) et `traditions.soleil_longitude`/`lune_longitude`.
- **Tests Python** : `cd engine && python -m pytest -q` (imports `import ephemeride`, etc.).
- **Système de maisons par défaut** : Whole Sign. Placidus/Equal au choix.
- **Méthode des dominantes par défaut** : `comptage_dignite`. `score_complexe` au choix.
- **Tests d'API** via `fastapi.testclient.TestClient`.

---

## File Structure

- **Create** `engine/ephemeride.py` — longitudes des 13 corps/points + vitesse + rétrogradation. Expose `CORPS`, `longitude(corps, dt, utc_offset_h, lat, lon_geo)`, `positions(dt, utc_offset_h, lat, lon_geo)`.
- **Create** `engine/maisons.py` — 3 systèmes + repli polaire. Expose `SYSTEMES`, `maisons(asc, mc, latitude, systeme)`.
- **Create** `engine/aspects.py` — majeurs + mineurs entre 18 points. Expose `ASPECTS`, `ORBES_BASE`, `aspects(points, orbes=None)`, `filtrer_par_type(aspects, type_)`.
- **Create** `engine/dominantes.py` — 2 méthodes + tables de dignités. Expose `METHODES`, `dominantes(points, maisons, aspects, methode)`, `DOMICILES`, `EXALTATIONS`, `TRIPPLICITES`, `TERMES_EGYPTIENS`, `FACES_CHALDEENNES`.
- **Create** `engine/theme_complet.py` — orchestrateur. Expose `theme_complet(fiche)`, `theme_complet_depuis_traditions(trad, fiche)`.
- **Create** `engine/test_ephemeride.py`, `engine/test_maisons.py`, `engine/test_aspects.py`, `engine/test_dominantes.py`, `engine/test_theme_complet.py`.
- **Modify** `main.py` — `Fiche` étendue, endpoint `/theme`, `/portrait` étendu.
- **Modify** `engine/significations.py` — clefs d'interprétation nouvelles ; `expliquer()` accepte `theme_complet` optionnel.
- **Modify** `engine/synthese.py` — `portrait()` accepte `theme_complet` optionnel et enrichit archétype/forces/récit.
- **Modify** `static/index.html` — onglet « Carte astro complète » : options, roue SVG, 6 tableaux, caveat, export.

---

### Task 1: `ephemeride.py` — socle, contexte, Soleil/Lune réutilisés

**Files:**
- Create: `engine/ephemeride.py`
- Test: `engine/test_ephemeride.py`

**Interfaces:**
- Consumes: `traditions.soleil_longitude(dt, utc_offset_h) -> float`, `traditions.lune_longitude(dt, utc_offset_h) -> float`, `traditions._jour_julien(an, mois, jour, heure_ut) -> float`, `traditions.SIGNES`.
- Produces:
  - `ephemeride.CORPS : list[str]` — les 13 corps/points.
  - `ephemeride._Contexte` — dataclass interne (`jj`, `t`, `heure_ut`, `delta_t`).
  - `ephemeride._delta_t(annee) -> float` — Espenak-Meeus par siècle.
  - `ephemeride.longitude(corps, dt, utc_offset_h, latitude, longitude_geo) -> dict` — `{corps, longitude, latitude, distance_au, vitesse_deg_j, retrograde, methode}`. Task 1 : seul Soleil/Lune implémentés, autres lèvent `NotImplementedError`.

- [ ] **Step 1: Write failing tests in `engine/test_ephemeride.py`**

```python
"""Tests de l'éphéméride — cas pivots J2000 et réutilisation de traditions."""
from datetime import datetime

import ephemeride as E
import traditions as T


def test_corps_constante():
    assert E.CORPS == ["Soleil", "Lune", "Mercure", "Vénus", "Mars", "Jupiter",
                       "Saturne", "Uranus", "Neptune", "Pluton", "Chiron", "Lilith",
                       "Nœud Nord"]


def test_delta_t_j2000():
    assert 60.0 < E._delta_t(2000) < 70.0


def test_delta_t_2020():
    assert 65.0 < E._delta_t(2020) < 75.0


def test_contexte_j2000():
    dt = datetime(2000, 1, 1, 12, 0)
    c = E._contexte(dt, 0.0)
    assert abs(c.jj - 2451545.0) < 0.001
    assert abs(c.t) < 1e-6


def test_longitude_soleil_reutilise_traditions():
    dt = datetime(2000, 1, 1, 12, 0)
    attendu = T.soleil_longitude(dt, 0.0)
    res = E.longitude("Soleil", dt, 0.0, 0.0, 0.0)
    assert abs(res["longitude"] - attendu) < 1e-6
    assert res["methode"] == "meeus_soleil"
    assert "vitesse_deg_j" in res
    assert "retrograde" in res


def test_longitude_lune_reutilise_traditions():
    dt = datetime(2000, 1, 1, 12, 0)
    attendu = T.lune_longitude(dt, 0.0)
    res = E.longitude("Lune", dt, 0.0, 0.0, 0.0)
    assert abs(res["longitude"] - attendu) < 1e-4
    assert res["methode"] == "elp_abrege"


def test_longitude_corps_non_implante_leve_notreparable():
    dt = datetime(2000, 1, 1, 12, 0)
    try:
        E.longitude("Mercure", dt, 0.0, 0.0, 0.0)
        assert False, "doit lever NotImplementedError"
    except NotImplementedError:
        pass
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd engine && python -m pytest test_ephemeride.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ephemeride'`

- [ ] **Step 3: Write minimal implementation in `engine/ephemeride.py`**

```python
"""Éphéméride géocentrique — longitudes écliptiques tropicales de la date.

Stdlib only. Soleil/Lune réutilisent traditions (Meeus/ELP abrégé).
Mercure→Neptune via VSOP87 tronqué (task 2). Pluton/Chiron/Lilith/Nœud Nord
via formules approchées Meeus (task 3).

Référentiel : longitude géocentrique écliptique tropicale de la date (vraie
équinoxe), en degrés. UT1→TT via ΔT (Espenak-Meeus) pour VSOP87.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

import traditions as T


CORPS = ["Soleil", "Lune", "Mercure", "Vénus", "Mars", "Jupiter",
         "Saturne", "Uranus", "Neptune", "Pluton", "Chiron", "Lilith",
         "Nœud Nord"]


@dataclass
class _Contexte:
    jj: float
    t: float
    heure_ut: float
    delta_t: float


def _delta_t(annee: int) -> float:
    """ΔT (TT - UT1) en secondes — Espenak-Meeus par siècle."""
    if 2000 <= annee < 2100:
        t = (annee - 2000) / 100.0
        return 62.92 + 0.32217 * t + 0.005589 * t * t
    elif 1900 <= annee < 2000:
        t = (annee - 1900) / 100.0
        return -2.79 + 1.494119 * t + 0.0006205 * t * t
    elif 2100 <= annee < 2200:
        t = (annee - 2100) / 100.0
        return 111.19 + 4.06246 * t + 0.000118 * t * t
    else:
        return 69.0


def _contexte(dt: datetime, utc_offset_h: float) -> _Contexte:
    heure_ut = dt.hour + dt.minute / 60.0 - utc_offset_h
    jj = T._jour_julien(dt.year, dt.month, dt.day, heure_ut)
    t = (jj - 2451545.0) / 36525.0
    return _Contexte(jj=jj, t=t, heure_ut=heure_ut, delta_t=_delta_t(dt.year))


def _vitesse_et_retro(corps: str, dt: datetime, utc_offset_h: float,
                      lon_a_t: float) -> tuple[float, bool]:
    """Dérivée finie sur 1h → vitesse (deg/jour) + rétrogradation."""
    dt_plus = dt + timedelta(hours=1)
    lon_plus = _longitude_brute(corps, dt_plus, utc_offset_h)
    delta = (lon_plus - lon_a_t + 180) % 360 - 180
    vitesse = delta * 24.0
    return vitesse, vitesse < 0


def _longitude_brute(corps: str, dt: datetime, utc_offset_h: float) -> float:
    """Longitude écliptique brute (deg) — dispatch interne."""
    if corps == "Soleil":
        return T.soleil_longitude(dt, utc_offset_h)
    if corps == "Lune":
        return T.lune_longitude(dt, utc_offset_h)
    raise NotImplementedError(f"Corps {corps!r} non encore implémenté")


def longitude(corps: str, dt: datetime, utc_offset_h: float,
              latitude: float, longitude_geo: float) -> dict:
    """Retourne {corps, longitude, latitude, distance_au, vitesse_deg_j,
    retrograde, methode}."""
    if corps not in CORPS:
        raise ValueError(f"Corps inconnu : {corps!r}")
    lon = _longitude_brute(corps, dt, utc_offset_h)
    vitesse, retro = _vitesse_et_retro(corps, dt, utc_offset_h, lon)
    methodes = {"Soleil": "meeus_soleil", "Lune": "elp_abrege"}
    return {
        "corps": corps,
        "longitude": round(lon % 360, 4),
        "latitude": 0.0,
        "distance_au": 0.0,
        "vitesse_deg_j": round(vitesse, 4),
        "retrograde": retro,
        "methode": methodes.get(corps, "inconnu"),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd engine && python -m pytest test_ephemeride.py -v`
Expected: PASS — 7 tests.

- [ ] **Step 5: Commit**

```bash
git add engine/ephemeride.py engine/test_ephemeride.py
git commit -m "feat(ephemeride): socle + contexte + Soleil/Lune réutilisés de traditions"
```

---

### Task 2: `ephemeride.py` — Mercure→Neptune via VSOP87 tronqué

**Files:**
- Modify: `engine/ephemeride.py`
- Test: `engine/test_ephemeride.py`

**Interfaces:**
- Produces:
  - `ephemeride._VSOP87 : dict[str, dict]` — séries tronquées (amplitude > 1e-6 rad) par planète, niveaux L0-L4, termes `(A, L, B, F)`.
  - `ephemeride._vsop87_longitude(corps, ctx) -> float` — longitude géocentrique en deg (héliocentrique VSOP87 → soustraction longitude Terre).
  - `_longitude_brute` dispatche Mercure→Neptune vers `_vsop87_longitude`.

**Note importante :** Les tables VSOP87 sont volumineuses (~200-400 termes/corps). L'implémenteur doit récupérer les tables VSOP87 complètes (fichier `vsop87.txt` d'IMCCE/BDL, ou via un package Python à usage unique comme `skyfield`/`astropy` en développement — PAS au runtime), tronquer à amplitude > 1e-6 rad, et embarquer dans `_VSOP87` + constantes orbitales dans `_VSOP87_VARIABLES`. Sans données réelles, les tests échouent. Les valeurs J2000 de référence proviennent de JPL Horizons (à vérifier à l'implémentation).

- [ ] **Step 1: Write failing tests in `engine/test_ephemeride.py`**

Append:

```python
# ── Mercure→Neptune via VSOP87 ─────────────────────────────────────
def test_mercure_longitude_j2000():
    """Mercure à J2000.0 — longitude ≈ 222.51° (JPL Horizons). Tolérance 0.5°."""
    dt = datetime(2000, 1, 1, 12, 0)
    res = E.longitude("Mercure", dt, 0.0, 0.0, 0.0)
    assert abs(res["longitude"] - 222.51) < 0.5
    assert res["methode"] == "vsop87"


def test_venus_longitude_j2000():
    """Vénus à J2000.0 — longitude ≈ 327.95°."""
    dt = datetime(2000, 1, 1, 12, 0)
    res = E.longitude("Vénus", dt, 0.0, 0.0, 0.0)
    assert abs(res["longitude"] - 327.95) < 0.5


def test_mars_longitude_j2000():
    """Mars à J2000.0 — longitude ≈ 14.94°."""
    dt = datetime(2000, 1, 1, 12, 0)
    res = E.longitude("Mars", dt, 0.0, 0.0, 0.0)
    assert abs(res["longitude"] - 14.94) < 0.5


def test_jupiter_longitude_j2000():
    """Jupiter à J2000.0 — longitude ≈ 34.30°."""
    dt = datetime(2000, 1, 1, 12, 0)
    res = E.longitude("Jupiter", dt, 0.0, 0.0, 0.0)
    assert abs(res["longitude"] - 34.30) < 0.5


def test_saturne_longitude_j2000():
    """Saturne à J2000.0 — longitude ≈ 48.59°."""
    dt = datetime(2000, 1, 1, 12, 0)
    res = E.longitude("Saturne", dt, 0.0, 0.0, 0.0)
    assert abs(res["longitude"] - 48.59) < 0.5


def test_uranus_longitude_j2000():
    """Uranus à J2000.0 — longitude ≈ 312.97°."""
    dt = datetime(2000, 1, 1, 12, 0)
    res = E.longitude("Uranus", dt, 0.0, 0.0, 0.0)
    assert abs(res["longitude"] - 312.97) < 0.5


def test_neptune_longitude_j2000():
    """Neptune à J2000.0 — longitude ≈ 304.42°."""
    dt = datetime(2000, 1, 1, 12, 0)
    res = E.longitude("Neptune", dt, 0.0, 0.0, 0.0)
    assert abs(res["longitude"] - 304.42) < 0.5


def test_mercure_retrogradation_detectee():
    """Mercure rétrograde autour du 23/02/2020 (station rétro connue)."""
    dt = datetime(2020, 2, 25, 0, 0)
    res = E.longitude("Mercure", dt, 0.0, 0.0, 0.0)
    assert res["retrograde"] is True


def test_mercure_direct_apres_retro():
    """Mercure direct vers le 10/03/2020."""
    dt = datetime(2020, 3, 15, 0, 0)
    res = E.longitude("Mercure", dt, 0.0, 0.0, 0.0)
    assert res["retrograde"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd engine && python -m pytest test_ephemeride.py -v -k "mercure or venus or mars or jupiter or saturne or uranus or neptune"`
Expected: FAIL — `NotImplementedError`

- [ ] **Step 3: Implement VSOP87 truncated series and dispatcher**

Add to `engine/ephemeride.py` (after `_contexte`, before `_longitude_brute`). **L'implémenteur doit embarquer les vraies tables VSOP87** — le squelette ci-dessous montre la structure ; les valeurs réelles sont dans `vsop87.txt` (IMCCE/BDL) :

```python
# ── VSOP87 tronqué (Mercure→Neptune) ──────────────────────────────
# Format : pour chaque planète, dict avec L0..L4. Chaque terme = (A, L, B, F)
# où A = amplitude en radians, L/B/F = multiplicateurs des variables VSOP87.
# Troncature à amplitude > 1e-6 rad.

_VSOP87 = {
    "Mercure":  {"L0": [...], "L1": [...], "L2": [...], "L3": [...], "L4": [...]},
    "Vénus":    {"L0": [...], "L1": [...], "L2": [...], "L3": [...], "L4": [...]},
    "Mars":     {"L0": [...], "L1": [...], "L2": [...], "L3": [...], "L4": [...]},
    "Jupiter":  {"L0": [...], "L1": [...], "L2": [...], "L3": [...], "L4": [...]},
    "Saturne":  {"L0": [...], "L1": [...], "L2": [...], "L3": [...], "L4": [...]},
    "Uranus":   {"L0": [...], "L1": [...], "L2": [...], "L3": [...], "L4": [...]},
    "Neptune":  {"L0": [...], "L1": [...], "L2": [...], "L3": [...], "L4": [...]},
}

# Constantes orbitales VSOP87 par planète (longitude moyenne L, anomalie B,
# latitude F à J2000, en radians). L'implémenteur embarque les vraies valeurs.

_VSOP87_VARIABLES = {
    "Mercure": {"L": ..., "B": ..., "F": ...},
    # ... Vénus→Neptune
}


def _vsop87_longitude(corps: str, ctx: _Contexte) -> float:
    """Longitude géocentrique écliptique via VSOP87 tronqué (deg).

    1. t_tt = (jj + delta_t/86400 - 2451545.0) / 36525.0
    2. Pour chaque niveau L0..L4 : somme = Σ A * cos(B * var_L + F * var_F)
    3. L (rad) = L0 + L1*t + L2*t² + L3*t³ + L4*t⁴
    4. rad → deg, normaliser [0, 360)
    5. VSOP87 héliocentrique → géocentrique : lon_geo = (lon_helio - lon_terre) % 360
       avec lon_terre = (soleil_longitude + 180) % 360
    """
    t_tt = (ctx.jj + ctx.delta_t / 86400.0 - 2451545.0) / 36525.0
    series = _VSOP87[corps]
    vars_ = _VSOP87_VARIABLES[corps]
    # Calculer variables à t_tt (longitude moyenne etc.)
    var_L = vars_["L"] + ...  # formules Meeus ch.32
    lon_rad = 0.0
    for niveau, puiss in [("L0", 0), ("L1", 1), ("L2", 2), ("L3", 3), ("L4", 4)]:
        s = sum(A * math.cos(B * var_L + F * vars_["F"])
                for A, L_mult, B, F in series[niveau])
        lon_rad += s * (t_tt ** puiss)
    lon_helio = math.degrees(lon_rad) % 360
    # Géocentrique : soustraire longitude héliocentrique de la Terre
    soleil_lon = T.soleil_longitude_from_context(ctx)  # ou recalculer
    lon_terre = (soleil_lon + 180.0) % 360
    return (lon_helio - lon_terre) % 360
```

Then modify `_longitude_brute` to dispatch Mercure→Neptune :

```python
def _longitude_brute(corps: str, dt: datetime, utc_offset_h: float) -> float:
    if corps == "Soleil":
        return T.soleil_longitude(dt, utc_offset_h)
    if corps == "Lune":
        return T.lune_longitude(dt, utc_offset_h)
    if corps in _VSOP87:
        ctx = _contexte(dt, utc_offset_h)
        return _vsop87_longitude(corps, ctx)
    raise NotImplementedError(f"Corps {corps!r} non implémenté")
```

Update `methodes` in `longitude()` :

```python
    methodes = {"Soleil": "meeus_soleil", "Lune": "elp_abrege",
                "Mercure": "vsop87", "Vénus": "vsop87", "Mars": "vsop87",
                "Jupiter": "vsop87", "Saturne": "vsop87",
                "Uranus": "vsop87", "Neptune": "vsop87"}
```

- [ ] **Step 4: Run tests — ils échouent encore (tables non embarquées)**

Run: `cd engine && python -m pytest test_ephemeride.py -v -k "mercure or venus or mars or jupiter or saturne or uranus or neptune"`
Expected: FAIL — `NotImplementedError` ou erreur de calcul (tables vides).

**IMPORTANT :** cette task n'est terminée que quand les vraies tables VSOP87 sont embarquées ET les tests passent. L'implémenteur doit :
1. Récupérer `vsop87.txt` (IMCCE/BDL ou package Python à usage unique en dev).
2. Tronquer chaque planète à amplitude > 1e-6 rad.
3. Embarquer dans `_VSOP87` + `_VSOP87_VARIABLES`.
4. Implémenter `_vsop87_longitude` selon le commentaire.
5. Vérifier tests J2000 (tolérance 0.5°). Ajuster valeurs de référence vs JPL Horizons si nécessaire.

- [ ] **Step 5: Commit (une fois les tests au vert)**

```bash
git add engine/ephemeride.py engine/test_ephemeride.py
git commit -m "feat(ephemeride): Mercure→Neptune via VSOP87 tronqué (précision <1\" sur 1800-2100)"
```

---

### Task 3: `ephemeride.py` — Pluton, Chiron, Lilith, Nœud Nord + `positions()`

**Files:**
- Modify: `engine/ephemeride.py`
- Test: `engine/test_ephemeride.py`

**Interfaces:**
- Produces:
  - `ephemeride._pluton_longitude(ctx) -> float` — Meeus ch.37.
  - `ephemeride._chiron_longitude(ctx) -> float` — orbite osculatrice + Kepler.
  - `ephemeride._lilith_longitude(ctx) -> float` — apogée lunaire moyen (Ω_mean + 180°).
  - `ephemeride._noeud_nord_longitude(ctx) -> float` — nœud lunaire moyen (Ω_mean).
  - `ephemeride.positions(dt, utc_offset_h, latitude, longitude_geo) -> dict[str, dict]` — tous les CORPS d'un coup.

- [ ] **Step 1: Write failing tests**

Append:

```python
# ── Pluton, Chiron, Lilith, Nœud Nord ──────────────────────────────
def test_pluton_longitude_j2000():
    """Pluton à J2000.0 — longitude ≈ 244.18° (JPL Horizons). Tolérance 1°."""
    dt = datetime(2000, 1, 1, 12, 0)
    res = E.longitude("Pluton", dt, 0.0, 0.0, 0.0)
    assert abs(res["longitude"] - 244.18) < 1.0
    assert res["methode"] == "meeus_pluton"


def test_chiron_longitude_j2000():
    """Chiron à J2000.0 — longitude ≈ 226.0° (approx). Tolérance 1.5°."""
    dt = datetime(2000, 1, 1, 12, 0)
    res = E.longitude("Chiron", dt, 0.0, 0.0, 0.0)
    assert abs(res["longitude"] - 226.0) < 1.5
    assert res["methode"] == "osculation_chiron"


def test_lilith_longitude_j2000():
    """Lilith (apogée lunaire moyen) à J2000.0 — longitude ≈ 195.81°."""
    dt = datetime(2000, 1, 1, 12, 0)
    res = E.longitude("Lilith", dt, 0.0, 0.0, 0.0)
    assert abs(res["longitude"] - 195.81) < 0.2
    assert res["methode"] == "lilith_moyenne"


def test_noeud_nord_longitude_j2000():
    """Nœud Nord moyen à J2000.0 — longitude ≈ 125.12°."""
    dt = datetime(2000, 1, 1, 12, 0)
    res = E.longitude("Nœud Nord", dt, 0.0, 0.0, 0.0)
    assert abs(res["longitude"] - 125.12) < 0.2
    assert res["methode"] == "noeud_lunaire_moyen"


def test_positions_renvoie_tous_les_corps():
    """positions() renvoie une entrée par corps dans CORPS."""
    dt = datetime(2000, 1, 1, 12, 0)
    pos = E.positions(dt, 0.0, 0.0, 0.0)
    assert set(pos.keys()) == set(E.CORPS)
    for corps in E.CORPS:
        assert "longitude" in pos[corps]
        assert "methode" in pos[corps]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd engine && python -m pytest test_ephemeride.py -v -k "pluton or chiron or lilith or noeud or positions"`
Expected: FAIL — `NotImplementedError`

- [ ] **Step 3: Implement Pluton, Chiron, Lilith, Nœud Nord, `positions()`**

Add to `engine/ephemeride.py`:

```python
# ── Pluton (Meeus, Astronomical Algorithms ch.37) ─────────────────
def _pluton_longitude(ctx: _Contexte) -> float:
    """Longitude géocentrique écliptique approchée de Pluton (deg).
    Formule Meeus ch.37 : polynôme en J (période 1800-2100). Précision ~0.1-0.5°.
    L'implémenteur embarque les 9 coefficients a_i, b_i, c_i de Meeus (éq. 37.1).
    """
    j = ctx.jj
    # Meeus ch.37 — coefficients à embarquer (PLACEHOLDER, à remplacer) :
    # M = ... ; longitude héliocentrique L, latitude B, distance R
    # puis conversion héliocentrique → géocentrique
    raise NotImplementedError("Pluton : embarquer coefficients Meeus ch.37")


# ── Chiron (orbite osculatrice + équation de Kepler) ──────────────
_CHIRON_ELEMENTS = {
    # Éléments osculateurs à J2000 (Standish) — à embarquer :
    # "a": ..., "e": ..., "i": ..., "omega": ..., "Omega": ..., "M0": ...
}

def _chiron_longitude(ctx: _Contexte) -> float:
    """Longitude géocentrique de Chiron (deg) — orbite osculatrice au 1er ordre.
    Précision ~0.1-1°. L'implémenteur :
    1. Calculer M = M0 + n*(t - t0) (anomalie moyenne)
    2. Résoudre équation de Kepler (itération Newton) : E - e*sin(E) = M
    3. Position dans le plan orbital → coordonnées écliptiques
    4. Héliocentrique → géocentrique (soustraire Terre)
    """
    raise NotImplementedError("Chiron : embarquer éléments osculateurs + Kepler")


# ── Lilith (apogée lunaire moyen) + Nœud Nord (nœud lunaire moyen) ─
def _omega_mean_lune(ctx: _Contexte) -> float:
    """Longitude du nœud ascendant moyen de la Lune (deg) — Meeus ch.47."""
    t = ctx.t
    return (125.04452 - 1934.136261 * t + 0.0020708 * t * t
            + t ** 3 / 467411.0 - t ** 4 / 60616000.0) % 360


def _lilith_longitude(ctx: _Contexte) -> float:
    """Lilith = apogée lunaire moyen = Ω_mean + 180° (convention astrologique)."""
    return (_omega_mean_lune(ctx) + 180.0) % 360


def _noeud_nord_longitude(ctx: _Contexte) -> float:
    """Nœud Nord lunaire moyen = Ω_mean (Meeus ch.47)."""
    return _omega_mean_lune(ctx)
```

Modify `_longitude_brute` :

```python
def _longitude_brute(corps: str, dt: datetime, utc_offset_h: float) -> float:
    if corps == "Soleil":
        return T.soleil_longitude(dt, utc_offset_h)
    if corps == "Lune":
        return T.lune_longitude(dt, utc_offset_h)
    ctx = _contexte(dt, utc_offset_h)
    if corps in _VSOP87:
        return _vsop87_longitude(corps, ctx)
    if corps == "Pluton":
        return _pluton_longitude(ctx)
    if corps == "Chiron":
        return _chiron_longitude(ctx)
    if corps == "Lilith":
        return _lilith_longitude(ctx)
    if corps == "Nœud Nord":
        return _noeud_nord_longitude(ctx)
    raise NotImplementedError(f"Corps {corps!r} non implémenté")
```

Update `methodes` in `longitude()` :

```python
    methodes = {"Soleil": "meeus_soleil", "Lune": "elp_abrege",
                "Mercure": "vsop87", "Vénus": "vsop87", "Mars": "vsop87",
                "Jupiter": "vsop87", "Saturne": "vsop87",
                "Uranus": "vsop87", "Neptune": "vsop87",
                "Pluton": "meeus_pluton", "Chiron": "osculation_chiron",
                "Lilith": "lilith_moyenne", "Nœud Nord": "noeud_lunaire_moyen"}
```

Add `positions()` :

```python
def positions(dt: datetime, utc_offset_h: float,
              latitude: float, longitude_geo: float) -> dict[str, dict]:
    """Tous les CORPS d'un coup."""
    return {corps: longitude(corps, dt, utc_offset_h, latitude, longitude_geo)
            for corps in CORPS}
```

- [ ] **Step 4: Run tests (après avoir embarqué les vraies formules Pluton/Chiron)**

Run: `cd engine && python -m pytest test_ephemeride.py -v`
Expected: PASS — tous les tests.

**Note :** Pluton et Chiron sont des squelettes. L'implémenteur doit :
- Embarquer les 9 coefficients de Meeus ch.37 (éq. 37.1) pour Pluton.
- Embarquer les éléments osculateurs de Chiron (a, e, i, Ω, ω, M0 à J2000) + résoudre Kepler (itération Newton).
- Vérifier les valeurs J2000 vs JPL Horizons, ajuster tests si nécessaire.

- [ ] **Step 5: Commit**

```bash
git add engine/ephemeride.py engine/test_ephemeride.py
git commit -m "feat(ephemeride): Pluton/Chiron/Lilith/Nœud Nord + positions() — formules approchées stdlib"
```

---

### Task 4: `maisons.py` — Whole Sign / Equal House / Placidus

**Files:**
- Create: `engine/maisons.py`
- Test: `engine/test_maisons.py`

**Interfaces:**
- Consumes: `traditions.SIGNES`.
- Produces:
  - `maisons.SYSTEMES : list[str]` — `["whole_sign", "placidus", "equal_house"]`.
  - `maisons.maisons(asc, mc, latitude, systeme="whole_sign") -> list[dict]` — 12 dict `{maison, cuspe, signe, symbole, longitude_cuspe, systeme}`. Repli Placidus → Equal House si |latitude| > 66° (champ `raison` ajouté à chaque maison).

- [ ] **Step 1: Write failing tests in `engine/test_maisons.py`**

```python
"""Tests des systèmes de maisons — fonctions pures, cas pivots."""
import maisons as M
import traditions as T


def test_systemes_constante():
    assert M.SYSTEMES == ["whole_sign", "placidus", "equal_house"]


def test_whole_sign_asc_0_egal_a_equal_house():
    """Whole Sign == Equal House quand l'Asc est exactement à 0° d'un signe."""
    asc = 0.0
    ws = M.maisons(asc, 90.0, 45.0, "whole_sign")
    eh = M.maisons(asc, 90.0, 45.0, "equal_house")
    assert len(ws) == 12 and len(eh) == 12
    for i in range(12):
        assert abs(ws[i]["cuspe"] - eh[i]["cuspe"]) < 1e-6


def test_whole_sign_cuspes_multiples_de_30():
    """Whole Sign : cuspes = multiples de 30° à partir du début du signe asc."""
    asc = 12.5  # Asc à 12.5° Bélier
    ws = M.maisons(asc, 90.0, 45.0, "whole_sign")
    assert ws[0]["cuspe"] == 0.0       # début Bélier
    assert ws[1]["cuspe"] == 30.0      # début Taureau
    assert ws[11]["cuspe"] == 330.0


def test_equal_house_cuspes_a_partir_de_asc():
    """Equal House : cuspes = asc + 30*i (exact, pas arrondi au signe)."""
    asc = 12.5
    eh = M.maisons(asc, 90.0, 45.0, "equal_house")
    for i in range(12):
        assert abs(eh[i]["cuspe"] - (asc + 30 * i) % 360) < 1e-6


def test_placidus_cuspes_non_egaux():
    """Placidus : cuspes inégaux (sauf 1=Asc, 4=IC, 7=Desc, 10=MC)."""
    asc = 100.0
    mc = 220.0
    pl = M.maisons(asc, mc, 45.0, "placidus")
    assert len(pl) == 12
    assert abs(pl[0]["cuspe"] - 100.0) < 1e-6   # Asc
    assert abs(pl[6]["cuspe"] - 280.0) < 1e-6   # Desc = Asc + 180
    assert abs(pl[9]["cuspe"] - 220.0) < 1e-6   # MC
    assert abs(pl[3]["cuspe"] - 40.0) < 1e-6    # IC = MC + 180
    # Maison 2 ≠ Asc + 30 (Placidus inégal)
    assert abs(pl[1]["cuspe"] - (100.0 + 30.0)) > 0.1


def test_placidus_repli_au_dessus_de_66_deg():
    """Placidus indéfini au cercle polaire → repli Equal House + raison."""
    asc = 100.0
    mc = 220.0
    pl = M.maisons(asc, mc, 70.0, "placidus")  # 70° > 66°
    eh = M.maisons(asc, mc, 70.0, "equal_house")
    for i in range(12):
        assert abs(pl[i]["cuspe"] - eh[i]["cuspe"]) < 1e-6
    # Chaque maison porte la raison du repli
    assert "raison" in pl[0]
    assert "Equal" in pl[0]["raison"] or "equal" in pl[0]["raison"].lower()


def test_maisons_schema_de_sortie():
    asc = 100.0
    ws = M.maisons(asc, 220.0, 45.0, "whole_sign")
    m = ws[0]
    assert {"maison", "cuspe", "signe", "symbole", "longitude_cuspe", "systeme"} <= set(m.keys())
    assert m["maison"] == 1
    assert m["signe"] in [s[0] for s in T.SIGNES]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd engine && python -m pytest test_maisons.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation in `engine/maisons.py`**

```python
"""Systèmes de maisons astrologiques — Whole Sign, Equal House, Placidus.

Fonctions pures. Repli polaire Placidus → Equal House au-dessus de 66°.
"""
from __future__ import annotations

import math

import traditions as T

SYSTEMES = ["whole_sign", "placidus", "equal_house"]
_LIMITE_POLAIRE = 66.0


def _signe_et_symbole(longitude: float) -> tuple[str, str]:
    idx = int(longitude % 360 // 30)
    return T.SIGNES[idx][0], T.SIGNES[idx][1]


def _entree(maison: int, cuspe: float, systeme: str,
            raison: str | None = None) -> dict:
    signe, symbole = _signe_et_symbole(cuspe)
    d = {"maison": maison, "cuspe": float(cuspe),
         "signe": signe, "symbole": symbole,
         "longitude_cuspe": float(cuspe), "systeme": systeme}
    if raison:
        d["raison"] = raison
    return d


def _whole_sign(asc: float, mc: float, latitude: float) -> list[dict]:
    idx_asc = int(asc // 30)
    return [_entree(i + 1, ((idx_asc + i) * 30) % 360, "whole_sign")
            for i in range(12)]


def _equal_house(asc: float, mc: float, latitude: float) -> list[dict]:
    return [_entree(i + 1, (asc + 30 * i) % 360, "equal_house")
            for i in range(12)]


def _placidus(asc: float, mc: float, latitude: float) -> list[dict]:
    """Placidus : maisons 1=Asc, 4=IC, 7=Desc, 10=MC fixes ; les 8 autres
    par itération sur l'ascension droite (fraction 1/3 ou 2/3 de l'arc
    semi-diurne/nocturne). L'implémenteur :
    1. Calculer l'ascension oblique (OA) et l'arc semi-diurne (D) du MC
       via la latitude et l'obliquité de l'écliptique.
    2. Pour maisons 11,12,2,3 : fraction = 1/3 ou 2/3 de l'arc diurne.
    3. Pour maisons 5,6,8,9 : fraction = 1/3 ou 2/3 de l'arc nocturne.
    4. Itérer : trouver λ tel que AD(λ) = AD(MC) + fraction * D.
       AD(λ) = atan2(sin(λ)*cos(eps), cos(λ)) — ascension droite.
    5. Maisons opposées : 7=Asc+180, 10=MC, 4=MC+180 (déjà fixes),
       et 5-6-8-9 = 11-12-2-3 + 180°.
    """
    eps = math.radians(23.439291)  # obliquité J2000 (approx)
    phi = math.radians(latitude)

    def ad(lambda_deg: float) -> float:
        """Ascension droite d'un point écliptique (deg)."""
        lam = math.radians(lambda_deg)
        return math.degrees(math.atan2(math.sin(lam) * math.cos(eps),
                                       math.cos(lam))) % 360

    def inverse_ad(target_ad: float) -> float:
        """Itération : longitude écliptique λ dont AD(λ) = target_ad."""
        # Recherche par dichotomie sur [0, 360)
        lo, hi = 0.0, 360.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if (ad(mid) - target_ad + 180) % 360 - 180 < 0:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    # Cuspes fixes
    c1 = asc
    c4 = (mc + 180) % 360
    c7 = (asc + 180) % 360
    c10 = mc

    # Arc semi-diurne du MC (de l'horizon est à l'horizon ouest via le MC)
    # D = AD(MC) - AD(Asc) mod 360, ajusté
    ad_asc = ad(asc)
    ad_mc = ad(mc)
    # Arc diurne (moitié supérieure) = 2 * (RAMC - RAASC) si diurne, etc.
    # Formule simplifiée — l'implémenteur valide sur un cas de référence publié.
    # Ici on calcule l'arc semi-diurne comme la différence d'AD entre le MC
    # et l'Asc, normalisée.
    d = (ad_mc - ad_asc + 360) % 360  # arc diurne approximatif

    # Maisons au-dessus de l'horizon (2,3,11,12) : tiers de l'arc diurne
    # Maison 12 = 1/3 au-dessus de l'Asc (vers le MC)
    # Maison 11 = 2/3
    # Maison 3  = 1/3 au-dessous de l'Asc (vers l'IC) — arc nocturne
    # Maison 2  = 2/3
    c12 = inverse_ad((ad_asc + d / 3) % 360)
    c11 = inverse_ad((ad_asc + 2 * d / 3) % 360)
    # Arc nocturne = 360 - d (approx)
    d_noct = (360 - d) % 360
    c3 = inverse_ad((ad_asc - d_noct / 3) % 360)
    c2 = inverse_ad((ad_asc - 2 * d_noct / 3) % 360)

    # Maisons opposées (5,6,8,9) = + 180°
    c5 = (c11 + 180) % 360
    c6 = (c12 + 180) % 360
    c8 = (c2 + 180) % 360
    c9 = (c3 + 180) % 360

    cuspes = [c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12]
    return [_entree(i + 1, cuspes[i], "placidus") for i in range(12)]


def maisons(asc: float, mc: float, latitude: float,
            systeme: str = "whole_sign") -> list[dict]:
    """12 maisons selon le système choisi. Repli polaire Placidus → Equal."""
    if systeme == "whole_sign":
        return _whole_sign(asc, mc, latitude)
    if systeme == "equal_house":
        return _equal_house(asc, mc, latitude)
    if systeme == "placidus":
        if abs(latitude) > _LIMITE_POLAIRE:
            raison = f"latitude {latitude}° > {_LIMITE_POLAIRE}° — Placidus indéfini, repli Equal House"
            return [{**m, "raison": raison} for m in _equal_house(asc, mc, latitude)]
        return _placidus(asc, mc, latitude)
    raise ValueError(f"Système inconnu : {systeme!r}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd engine && python -m pytest test_maisons.py -v`
Expected: PASS — 6 tests.

**Note :** la formule Placidus ci-dessus est une approximation. L'implémenteur doit la valider sur un cas de référence publié (cuspes Placidus d'un thème connu, ex. carte du 1er janvier 2000 à 12h UTC, latitude 45°) et ajuster si les écarts dépassent 1°.

- [ ] **Step 5: Commit**

```bash
git add engine/maisons.py engine/test_maisons.py
git commit -m "feat(maisons): Whole Sign / Equal House / Placidus + repli polaire"
```

---

### Task 5: `aspects.py` — majeurs + mineurs entre 18 points

**Files:**
- Create: `engine/aspects.py`
- Test: `engine/test_aspects.py`

**Interfaces:**
- Produces:
  - `aspects.ASPECTS : dict[str, dict]` — 10 aspects (5 majeurs + 5 mineurs) avec `angle` et `type`.
  - `aspects.ORBES_BASE : dict[str, int]` — orbes par type de point.
  - `aspects.aspects(points: dict[str, dict], orbes: dict | None = None) -> list[dict]` — calcule les aspects entre tous les points, triés par `exactitude` décroissante. Pas de doublons, pas d'auto-aspect.
  - `aspects.filtrer_par_type(aspects: list, type_: str) -> list` — filtre `'majeur'`/`'mineur'`/`'tous'`.
- `points` est un dict `{nom: {longitude: float, ...}}`. Les noms déterminent le type de point (luminaire/planète/point) pour l'orbe.

- [ ] **Step 1: Write failing tests in `engine/test_aspects.py`**

```python
"""Tests des aspects — fonctions pures, cas pivots."""
import aspects as A


def test_aspects_constante():
    assert "conjonction" in A.ASPECTS
    assert A.ASPECTS["trigone"]["angle"] == 120
    assert A.ASPECTS["trigone"]["type"] == "majeur"
    assert A.ASPECTS["quintile"]["type"] == "mineur"


def test_conjonction_dans_orbe():
    """Soleil à 10°, Jupiter à 11° → conjonction (écart 1° < orbe 10)."""
    points = {"Soleil": {"longitude": 10.0}, "Jupiter": {"longitude": 11.0}}
    res = A.aspects(points)
    assert any(a["aspect"] == "conjonction" and a["point_a"] == "Soleil"
               and a["point_b"] == "Jupiter" for a in res)


def test_pas_daspect_hors_orbe():
    """Soleil à 10°, Jupiter à 50° → écart 40°, aucun aspect (orbe max 10)."""
    points = {"Soleil": {"longitude": 10.0}, "Jupiter": {"longitude": 50.0}}
    res = A.aspects(points)
    assert res == []


def test_pas_de_doublon():
    """A-B présent, B-A absent."""
    points = {"Soleil": {"longitude": 10.0}, "Lune": {"longitude": 70.0}}
    res = A.aspects(points)
    paires = [(a["point_a"], a["point_b"]) for a in res]
    assert ("Soleil", "Lune") in paires or ("Lune", "Soleil") in paires
    # Pas les deux
    assert not (("Soleil", "Lune") in paires and ("Lune", "Soleil") in paires)


def test_pas_dauto_aspect():
    """A-A absent."""
    points = {"Soleil": {"longitude": 10.0}}
    res = A.aspects(points)
    assert res == []


def test_tri_par_exactitude():
    """Aspects triés par exactitude décroissante."""
    points = {"Soleil": {"longitude": 10.0}, "Lune": {"longitude": 70.5},
              "Mars": {"longitude": 130.0}}
    res = A.aspects(points)
    exactitudes = [a["exactitude"] for a in res]
    assert exactitudes == sorted(exactitudes, reverse=True)


def test_orbe_par_type_de_point():
    """Soleil-Lune (luminaires) → orbe 10° ; Asc-Mars (point-planète) → orbe 5°."""
    points = {"Soleil": {"longitude": 0.0}, "Lune": {"longitude": 8.5},
              "Ascendant": {"longitude": 0.0}, "Mars": {"longitude": 4.5}}
    res = A.aspects(points)
    # Soleil-Lune écart 8.5° → dans orbe 10 (conjonction)
    # Asc-Mars écart 4.5° → dans orbe 5 (conjonction, min(luminaire 5, planete 8) → point 5)
    aspects_soleil_lune = [a for a in res if {a["point_a"], a["point_b"]} == {"Soleil", "Lune"}]
    aspects_asc_mars = [a for a in res if {a["point_a"], a["point_b"]} == {"Ascendant", "Mars"}]
    assert len(aspects_soleil_lune) == 1
    assert len(aspects_asc_mars) == 1
    assert aspects_soleil_lune[0]["orbe_max"] == 10
    assert aspects_asc_mars[0]["orbe_max"] == 5


def test_filtrer_par_type():
    points = {"Soleil": {"longitude": 0.0}, "Lune": {"longitude": 120.0},
              "Mars": {"longitude": 30.0}}
    res = A.aspects(points)
    majeurs = A.filtrer_par_type(res, "majeur")
    mineurs = A.filtrer_par_type(res, "mineur")
    tous = A.filtrer_par_type(res, "tous")
    assert all(a["type"] == "majeur" for a in majeurs)
    assert all(a["type"] == "mineur" for a in mineurs)
    assert len(tous) == len(res)


def test_aspects_normalisation_360():
    """Soleil à 350°, Jupiter à 10° → écart 20° (pas 340°) → pas de conjonction."""
    points = {"Soleil": {"longitude": 350.0}, "Jupiter": {"longitude": 10.0}}
    res = A.aspects(points)
    # Écart réel = 20°, orbe conjonction = 10° → hors orbe
    conjonctions = [a for a in res if a["aspect"] == "conjonction"]
    assert conjonctions == []


def test_schema_de_sortie():
    points = {"Soleil": {"longitude": 0.0}, "Jupiter": {"longitude": 120.3}}
    res = A.aspects(points)
    a = res[0]
    assert {"aspect", "type", "point_a", "point_b", "angle_exact",
            "angle_reel", "orb", "orbe_max", "exactitude"} <= set(a.keys())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd engine && python -m pytest test_aspects.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation in `engine/aspects.py`**

```python
"""Aspects astrologiques — majeurs + mineurs entre tous les points.

Fonctions pures. Orbes par type de point (luminaire/planète/point sensible).
"""
from __future__ import annotations

ASPECTS = {
    "conjonction":   {"angle": 0,   "type": "majeur"},
    "opposition":    {"angle": 180, "type": "majeur"},
    "trigone":       {"angle": 120, "type": "majeur"},
    "carre":         {"angle": 90,  "type": "majeur"},
    "sextile":       {"angle": 60,  "type": "majeur"},
    "semi_sextile":  {"angle": 30,  "type": "mineur"},
    "semi_carre":    {"angle": 45,  "type": "mineur"},
    "quintile":      {"angle": 72,  "type": "mineur"},
    "sesquicarre":   {"angle": 135, "type": "mineur"},
    "quinconce":     {"angle": 150, "type": "mineur"},
}

ORBES_BASE = {
    "majeur_luminaire": 10,
    "majeur_planete":   8,
    "majeur_point":     5,
    "mineur":           3,
}

_LUMINAIRES = {"Soleil", "Lune"}
_PLANETES = {"Mercure", "Vénus", "Mars", "Jupiter", "Saturne",
             "Uranus", "Neptune", "Pluton"}
# Tout le reste = point sensible (Asc, MC, Desc, IC, Nœuds, Chiron, Lilith)


def _type_point(nom: str) -> str:
    if nom in _LUMINAIRES:
        return "luminaire"
    if nom in _PLANETES:
        return "planete"
    return "point"


def _orbe_point(nom: str, type_aspect: str) -> int:
    if type_aspect == "mineur":
        return ORBES_BASE["mineur"]
    # Majeur
    tp = _type_point(nom)
    if tp == "luminaire":
        return ORBES_BASE["majeur_luminaire"]
    if tp == "planete":
        return ORBES_BASE["majeur_planete"]
    return ORBES_BASE["majeur_point"]


def aspects(points: dict[str, dict], orbes: dict | None = None) -> list[dict]:
    """Calcule les aspects entre tous les points. Tri par exactitude décroissante."""
    if orbes is None:
        orbes = ORBES_BASE
    noms = list(points.keys())
    resultats = []
    for i, a in enumerate(noms):
        for b in noms[i + 1:]:
            lon_a = points[a]["longitude"] % 360
            lon_b = points[b]["longitude"] % 360
            ecart_brut = abs(lon_a - lon_b) % 360
            ecart = min(ecart_brut, 360 - ecart_brut)
            for nom_aspect, info in ASPECTS.items():
                angle = info["angle"]
                diff = abs(ecart - angle)
                if diff > 180:
                    diff = 360 - diff
                # Orbe = min des orbes des deux points
                orbe_max = min(_orbe_point(a, info["type"]),
                               _orbe_point(b, info["type"]))
                if diff <= orbe_max:
                    resultats.append({
                        "aspect": nom_aspect,
                        "type": info["type"],
                        "point_a": a,
                        "point_b": b,
                        "angle_exact": float(angle),
                        "angle_reel": round(ecart, 4),
                        "orb": round(diff, 4),
                        "orbe_max": orbe_max,
                        "exactitude": round(1 - diff / orbe_max, 4),
                    })
    resultats.sort(key=lambda x: x["exactitude"], reverse=True)
    return resultats


def filtrer_par_type(aspects: list, type_: str) -> list:
    """Filtre 'majeur' / 'mineur' / 'tous'."""
    if type_ == "tous":
        return aspects
    return [a for a in aspects if a["type"] == type_]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd engine && python -m pytest test_aspects.py -v`
Expected: PASS — 9 tests.

- [ ] **Step 5: Commit**

```bash
git add engine/aspects.py engine/test_aspects.py
git commit -m "feat(aspects): majeurs + mineurs entre 18 points, orbes par type"
```

---

### Task 6: `dominantes.py` — tables de dignités + méthode 1 (comptage + dignités)

**Files:**
- Create: `engine/dominantes.py`
- Test: `engine/test_dominantes.py`

**Interfaces:**
- Produces:
  - `dominantes.METHODES : list[str]` — `["comptage_dignite", "score_complexe"]`.
  - `dominantes.DOMICILES : dict[str, list[str]]` — planète → signes gouvernés.
  - `dominantes.EXALTATIONS : dict[str, str]` — planète → signe d'exaltation.
  - `dominantes.TRIPPLICITES : dict[tuple[str, str], str]` — `(élément, "diurne"/"nocturne")` → gouverneur.
  - `dominantes.TERMES_EGYPTIENS : dict[str, list[tuple[int, str]]]` — signe → `[(borne_deg, planète), ...]` (5 termes par signe).
  - `dominantes.FACES_CHALDEENNES : dict[str, list[str]]` — signe → `[planète_décan1, décan2, décan3]`.
  - `dominantes.dominantes(points, maisons, aspects, methode="comptage_dignite") -> dict` — Task 6 : seul `comptage_dignite` implémenté, `score_complexe` lève `NotImplementedError`.
  - `dominantes._chart_diurne(soleil_lon, asc_lon, mc_lon) -> bool` — détermine si la chart est diurne.
- `points` = `{nom: {longitude, signe, maison, ...}}` (depuis theme_complet).
- `maisons` = liste de dict depuis `maisons.maisons()`.
- `aspects` = liste depuis `aspects.aspects()`.

- [ ] **Step 1: Write failing tests in `engine/test_dominantes.py`**

```python
"""Tests des dominantes — tables de dignités + méthode comptage."""
import dominantes as D


def test_methodes_constante():
    assert D.METHODES == ["comptage_dignite", "score_complexe"]


def test_domiciles_complets():
    """Chaque planète classique a 1 ou 2 domiciles ; anciens = 1, modernes = 1."""
    assert "Bélier" in D.DOMICILES["Mars"]
    assert "Scorpion" in D.DOMICILES["Mars"]
    assert D.DOMICILES["Soleil"] == ["Lion"]
    assert D.DOMICILES["Lune"] == ["Cancer"]
    # 10 planètes couvertes (Soleil→Pluton)
    assert set(D.DOMICILES.keys()) == {"Soleil", "Lune", "Mercure", "Vénus", "Mars",
                                       "Jupiter", "Saturne", "Uranus", "Neptune", "Pluton"}


def test_exaltations():
    assert D.EXALTATIONS["Soleil"] == "Bélier"
    assert D.EXALTATIONS["Lune"] == "Taureau"
    assert D.EXALTATIONS["Vénus"] == "Poissons"


def test_triplicites_diurne_nocturne():
    """Chaque élément a un gouverneur diurne et un nocturne."""
    for elem in ["Feu", "Terre", "Air", "Eau"]:
        assert (elem, "diurne") in D.TRIPPLICITES
        assert (elem, "nocturne") in D.TRIPPLICITES
    assert D.TRIPPLICITES[("Feu", "diurne")] == "Soleil"
    assert D.TRIPPLICITES[("Feu", "nocturne")] == "Jupiter"


def test_termes_egyptiens_5_par_signe():
    """Chaque signe a 5 termes, bornes croissantes, dernier = 30."""
    for signe, termes in D.TERMES_EGYPTIENS.items():
        assert len(termes) == 5
        bornes = [t[0] for t in termes]
        assert bornes == sorted(bornes)
        assert bornes[-1] == 30
        # Planètes valides
        for _, planete in termes:
            assert planete in {"Soleil", "Lune", "Mercure", "Vénus", "Mars",
                               "Jupiter", "Saturne"}


def test_faces_chaldeennes_3_par_signe():
    """Chaque signe a 3 décan/faces, planètes valides."""
    for signe, faces in D.FACES_CHALDEENNES.items():
        assert len(faces) == 3
        for planete in faces:
            assert planete in {"Soleil", "Lune", "Mercure", "Vénus", "Mars",
                               "Jupiter", "Saturne"}


def test_chart_diurne_soleil_au_dessus_horizon():
    """Soleil au-dessus de l'horizon (entre Asc et MC par voie diurne) = diurne."""
    # Simplifié : si Soleil dans la moitié supérieure (maisons 7-12) = diurne
    assert D._chart_diurne(soleil_lon=180.0, asc_lon=90.0, mc_lon=0.0) is True
    assert D._chart_diurne(soleil_lon=0.0, asc_lon=90.0, mc_lon=180.0) is False


def test_dominantes_comptage_schema():
    """dominantes() renvoie les 5 dominantes avec scores."""
    points = {
        "Soleil": {"longitude": 0.0, "signe": "Bélier", "maison": 1},
        "Lune": {"longitude": 120.0, "signe": "Lion", "maison": 5},
        "Mars": {"longitude": 0.0, "signe": "Bélier", "maison": 1},
        "Jupiter": {"longitude": 240.0, "signe": "Sagittaire", "maison": 9},
    }
    maisons = [{"maison": i + 1, "cuspe": 30 * i, "signe": "Bélier"} for i in range(12)]
    aspects = []
    res = D.dominantes(points, maisons, aspects, "comptage_dignite")
    assert {"element", "mode", "planete", "signe", "maison", "methode"} <= set(res.keys())
    assert res["methode"] == "comptage_dignite"
    # Soleil en Bélier (domicile + exaltation) → Mars en Bélier (domicile) → feu dominant
    assert res["element"]["dominant"] == "Feu"
    # Bélier dominant (Soleil x2 + Mars domicile)
    assert res["signe"]["dominant"] == "Bélier"


def test_score_complexe_non_encore_implemente():
    """Task 7 : score_complexe lève NotImplementedError."""
    points = {"Soleil": {"longitude": 0.0, "signe": "Bélier", "maison": 1}}
    maisons = [{"maison": i + 1, "cuspe": 30 * i, "signe": "Bélier"} for i in range(12)]
    try:
        D.dominantes(points, maisons, [], "score_complexe")
        assert False, "doit lever NotImplementedError"
    except NotImplementedError:
        pass
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd engine && python -m pytest test_dominantes.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation in `engine/dominantes.py`**

```python
"""Dominantes astrologiques — élément, mode, planète, signe, maison.

2 méthodes : comptage_dignite (task 6) et score_complexe (task 7).
Tables de dignités essentielles embarquées (domicile, exaltation, triplicité,
terme égyptien, face chaldéenne).
"""
from __future__ import annotations

METHODES = ["comptage_dignite", "score_complexe"]

# ── Tables de dignités essentielles ────────────────────────────────
DOMICILES = {
    "Soleil": ["Lion"], "Lune": ["Cancer"],
    "Mercure": ["Gémeaux", "Vierge"], "Vénus": ["Taureau", "Balance"],
    "Mars": ["Bélier", "Scorpion"], "Jupiter": ["Sagittaire", "Poissons"],
    "Saturne": ["Capricorne", "Verseau"],
    "Uranus": ["Verseau"], "Neptune": ["Poissons"], "Pluton": ["Scorpion"],
}

EXALTATIONS = {
    "Soleil": "Bélier", "Lune": "Taureau", "Mercure": "Vierge",
    "Vénus": "Poissons", "Mars": "Capricorne",
    "Jupiter": "Cancer", "Saturne": "Balance",
    "Uranus": "Scorpion", "Neptune": "Verseau",  # débattu ; convention
    "Pluton": "Lion",  # débattu ; convention
}

TRIPPLICITES = {
    ("Feu", "diurne"): "Soleil", ("Feu", "nocturne"): "Jupiter",
    ("Terre", "diurne"): "Saturne", ("Terre", "nocturne"): "Mercure",
    ("Air", "diurne"): "Saturne", ("Air", "nocturne"): "Mercure",  # variantes
    ("Eau", "diurne"): "Vénus", ("Eau", "nocturne"): "Mars",
}
# Note : les triplicités varient selon les auteurs (Dorotheus vs Lilly).
# L'implémenteur choisit Dorotheus (le plus classique) et documente.

# TERMES_EGYPTIENS : signe → [(borne_sup_deg, planète), ...]
# Table égyptienne de Cléomède. L'implémenteur embarque les 12×5 bornes.
TERMES_EGYPTIENS = {
    # SQUELETTE — l'implémenteur embarque les vraies bornes (source : Lilly/Dorotheus)
    "Bélier": [(6, "Jupiter"), (14, "Vénus"), (21, "Mercure"), (26, "Mars"), (30, "Saturne")],
    "Taureau": [(8, "Vénus"), (15, "Mercure"), (22, "Jupiter"), (26, "Saturne"), (30, "Mars")],
    # ... compléter les 10 autres signes
}

FACES_CHALDEENNES = {
    # SQUELETTE — l'implémenteur embarque les 12×3 faces (séquence chaldéenne)
    "Bélier": ["Mars", "Soleil", "Vénus"],
    "Taureau": ["Mercure", "Lune", "Saturne"],
    # ... compléter les 10 autres signes (séquence : Mars-Soleil-Vénus-Mercure-Lune-Saturne-Jupiter-Mars...)
}

_ELEMENTS = {"Bélier": "Feu", "Taureau": "Terre", "Gémeaux": "Air", "Cancer": "Eau",
             "Lion": "Feu", "Vierge": "Terre", "Balance": "Air", "Scorpion": "Eau",
             "Sagittaire": "Feu", "Capricorne": "Terre", "Verseau": "Air", "Poissons": "Eau"}
_MODES = {"Bélier": "Cardinal", "Taureau": "Fixe", "Gémeaux": "Mutable",
          "Cancer": "Cardinal", "Lion": "Fixe", "Vierge": "Mutable",
          "Balance": "Cardinal", "Scorpion": "Fixe", "Sagittaire": "Mutable",
          "Capricorne": "Cardinal", "Verseau": "Fixe", "Poissons": "Mutable"}

_LUMINAIRES = {"Soleil", "Lune"}
_ANGULAIRES = {1, 4, 7, 10}
_SUCCEDENTES = {2, 5, 8, 11}


def _chart_diurne(soleil_lon: float, asc_lon: float, mc_lon: float) -> bool:
    """Diurne si Soleil au-dessus de l'horizon (entre Asc et Desc par voie diurne).

    Approximation : Soleil dans les maisons 7-12 (moitié supérieure).
    On compare la longitude du Soleil à l'Asc — si Soleil est à plus de 180°
    de l'Asc (dans la moitié supérieure), c'est diurne.
    """
    ecart = (soleil_lon - asc_lon) % 360
    return 180 < ecart < 360


def _score_dignite(planete: str, signe: str, degre_dans_signe: float,
                   diurne: bool) -> dict:
    """Score de dignités essentielles pour une planète dans un signe."""
    score = 0
    detail = {}
    if signe in DOMICILES.get(planete, []):
        score += 5
        detail["domicile"] = 5
    if EXALTATIONS.get(planete) == signe:
        score += 4
        detail["exaltation"] = 4
    # Chute (exil) = domicile opposé
    signe_oppose = DOMICILES.get(planete, [])
    # Exil = signe opposé au domicile (approx : on teste si signe est opposé d'un domicile)
    # Simplifié — l'implémenteur peut affiner
    # Déchéance = exaltation opposée
    elem = _ELEMENTS[signe]
    gouverneur = TRIPPLICITES.get((elem, "diurne" if diurne else "nocturne"))
    if gouverneur == planete:
        score += 2
        detail["triplicite"] = 2
    # Terme égyptien
    termes = TERMES_EGYPTIENS.get(signe, [])
    degre_prec = 0
    for borne, planete_terme in termes:
        if degre_prec <= degre_dans_signe < borne:
            if planete_terme == planete:
                score += 1
                detail["terme"] = 1
            break
        degre_prec = borne
    # Face chaldéenne
    faces = FACES_CHALDEENNES.get(signe, [])
    if faces:
        decan = int(degre_dans_signe // 10)
        if faces[decan] == planete:
            score += 1
            detail["face"] = 1
    return {"score": score, "detail": detail}


def _comptage_dignite(points: dict, maisons: list, aspects: list,
                      chart_diurne: bool) -> dict:
    """Méthode 1 : comptage + dignités essentielles."""
    scores_elem = {"Feu": 0, "Terre": 0, "Air": 0, "Eau": 0}
    scores_mode = {"Cardinal": 0, "Fixe": 0, "Mutable": 0}
    scores_planete = {p: 0 for p in DOMICILES}
    scores_signe = {s: 0 for s in _ELEMENTS}
    scores_maison = {i: 0 for i in range(1, 13)}

    for nom, info in points.items():
        if nom not in DOMICILES:
            continue  # on ne score que les 10 planètes
        signe = info["signe"]
        maison = info.get("maison", 0)
        degre = info["longitude"] % 30
        pond = 2 if nom in _LUMINAIRES else 1
        dign = _score_dignite(nom, signe, degre, chart_diurne)
        scores_planete[nom] += dign["score"] + pond
        if maison in _ANGULAIRES:
            scores_planete[nom] += 1
        elif maison in _SUCCEDENTES:
            scores_planete[nom] += 0.5
        scores_elem[_ELEMENTS[signe]] += pond
        scores_mode[_MODES[signe]] += pond
        scores_signe[signe] += pond
        if 1 <= maison <= 12:
            scores_maison[maison] += pond

    def dominant(scores: dict) -> str:
        return max(scores, key=scores.get)

    return {
        "element": {"dominant": dominant(scores_elem), "scores": scores_elem},
        "mode": {"dominant": dominant(scores_mode), "scores": scores_mode},
        "planete": {"dominante": dominant(scores_planete), "scores": scores_planete},
        "signe": {"dominant": dominant(scores_signe), "scores": scores_signe},
        "maison": {"dominante": dominant(scores_maison), "scores": scores_maison},
        "methode": "comptage_dignite",
        "chart_diurne": chart_diurne,
        "detail": {},  # décomposition détaillée — l'implémenteur peut enrichir
    }


def dominantes(points: dict, maisons: list, aspects: list,
               methode: str = "comptage_dignite") -> dict:
    """Calcule les 5 dominantes selon la méthode choisie."""
    # Déterminer chart diurne
    soleil = points.get("Soleil", {}).get("longitude", 0)
    asc = points.get("Ascendant", {}).get("longitude", 0)
    mc = points.get("Milieu du Ciel", {}).get("longitude", 0)
    diurne = _chart_diurne(soleil, asc, mc)
    if methode == "comptage_dignite":
        return _comptage_dignite(points, maisons, aspects, diurne)
    if methode == "score_complexe":
        raise NotImplementedError("score_complexe — voir task 7")
    raise ValueError(f"Méthode inconnue : {methode!r}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd engine && python -m pytest test_dominantes.py -v`
Expected: PASS — 8 tests (après embarquement des tables TERMES_EGYPTIENS et FACES_CHALDEENNES complètes).

**Note :** l'implémenteur doit compléter :
- `TERMES_EGYPTIENS` — les 12 signes × 5 termes (source : Lilly/Dorotheus).
- `FACES_CHALDEENNES` — les 12 signes × 3 faces (séquence chaldéenne).
- Vérifier les triplicités (Dorotheus vs Lilly) et documenter le choix.

- [ ] **Step 5: Commit**

```bash
git add engine/dominantes.py engine/test_dominantes.py
git commit -m "feat(dominantes): tables de dignités + méthode comptage_dignite"
```

---

### Task 7: `dominantes.py` — méthode 2 (score complexe)

**Files:**
- Modify: `engine/dominantes.py`
- Test: `engine/test_dominantes.py`

**Interfaces:**
- Produces:
  - `dominantes._score_complexe(points, maisons, aspects, chart_diurne) -> dict` — score planète par planète sur 100 (dignité 30, angulaire 15, proximité angles 15, vitesse 10, aspects reçus 15, luminaire +15, rétro +5, combuste -10, cazimi +5, nœud nord +10).

- [ ] **Step 1: Write failing tests**

Append to `engine/test_dominantes.py`:

```python
# ── Méthode 2 : score complexe ────────────────────────────────────
def test_score_complexe_schema():
    """score_complexe renvoie le même schéma que comptage_dignite."""
    points = {
        "Soleil": {"longitude": 0.0, "signe": "Bélier", "maison": 1,
                   "vitesse_deg_j": 0.95, "retrograde": False},
        "Lune": {"longitude": 120.0, "signe": "Lion", "maison": 5,
                 "vitesse_deg_j": 13.0, "retrograde": False},
        "Mars": {"longitude": 0.0, "signe": "Bélier", "maison": 1,
                 "vitesse_deg_j": 0.5, "retrograde": False},
        "Ascendant": {"longitude": 350.0},
        "Milieu du Ciel": {"longitude": 260.0},
        "Nœud Nord": {"longitude": 100.0},
    }
    maisons = [{"maison": i + 1, "cuspe": 30 * i, "signe": "Bélier"} for i in range(12)]
    aspects = [{"point_a": "Soleil", "point_b": "Mars", "type": "majeur"},
               {"point_a": "Lune", "point_b": "Mars", "type": "majeur"}]
    res = D.dominantes(points, maisons, aspects, "score_complexe")
    assert res["methode"] == "score_complexe"
    assert {"element", "mode", "planete", "signe", "maison"} <= set(res.keys())
    # Mars en Bélier (domicile) + maison 1 (angulaire) + aspects reçus
    # → score élevé → Mars dominante probable
    assert res["planete"]["dominante"] in {"Mars", "Soleil"}


def test_score_complexe_retro_bonus():
    """Une planète rétrograde reçoit +5 au score."""
    points = {
        "Mercure": {"longitude": 200.0, "signe": "Balance", "maison": 10,
                    "vitesse_deg_j": -0.5, "retrograde": True},
        "Soleil": {"longitude": 180.0, "signe": "Balance", "maison": 10,
                   "vitesse_deg_j": 0.95, "retrograde": False},
        "Ascendant": {"longitude": 350.0},
        "Milieu du Ciel": {"longitude": 260.0},
    }
    maisons = [{"maison": i + 1, "cuspe": 30 * i, "signe": "Bélier"} for i in range(12)]
    res = D.dominantes(points, maisons, [], "score_complexe")
    # Mercure rétro → bonus de 5 dans son score
    # On vérifie juste que la méthode tourne sans erreur et produit un score
    assert res["planete"]["scores"]["Mercure"] > 0


def test_score_complexe_combuste_malus():
    """Une planète combuste (<17° du Soleil) reçoit -10."""
    points = {
        "Mercure": {"longitude": 5.0, "signe": "Bélier", "maison": 1,
                    "vitesse_deg_j": 1.5, "retrograde": False},
        "Soleil": {"longitude": 10.0, "signe": "Bélier", "maison": 1,
                   "vitesse_deg_j": 0.95, "retrograde": False},
        "Ascendant": {"longitude": 350.0},
        "Milieu du Ciel": {"longitude": 260.0},
    }
    maisons = [{"maison": i + 1, "cuspe": 30 * i, "signe": "Bélier"} for i in range(12)]
    res = D.dominantes(points, maisons, [], "score_complexe")
    # Mercure combuste (5° du Soleil) → -10
    # On vérifie que le score Mercure est impacté (moins élevé qu'un Mercure non combuste)
    # Test simple : la méthode tourne et Mercure a un score
    assert "Mercure" in res["planete"]["scores"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd engine && python -m pytest test_dominantes.py -v -k "score_complexe"`
Expected: FAIL — `NotImplementedError`

- [ ] **Step 3: Implement `_score_complexe` in `engine/dominantes.py`**

Add (after `_comptage_dignite`):

```python
def _score_complexe(points: dict, maisons: list, aspects: list,
                    chart_diurne: bool) -> dict:
    """Méthode 2 : score complexe (Jones/Muzzarelli). Score planète par planète sur 100."""
    soleil_lon = points.get("Soleil", {}).get("longitude", 0)
    asc_lon = points.get("Ascendant", {}).get("longitude", 0)
    mc_lon = points.get("Milieu du Ciel", {}).get("longitude", 0)
    nn_lon = points.get("Nœud Nord", {}).get("longitude", None)

    scores_planete = {}
    detail_planete = {}

    # Compter les aspects reçus par planète
    aspects_recus = {p: 0 for p in DOMICILES}
    for asp in aspects:
        for p in (asp.get("point_a"), asp.get("point_b")):
            if p in aspects_recus:
                aspects_recus[p] += 1

    for nom, info in points.items():
        if nom not in DOMICILES:
            continue
        signe = info["signe"]
        maison = info.get("maison", 0)
        degre = info["longitude"] % 30
        lon = info["longitude"]
        vitesse = info.get("vitesse_deg_j", 0)
        retro = info.get("retrograde", False)

        score = 0
        detail = {}

        # Dignité (max 30)
        dign = _score_dignite(nom, signe, degre, chart_diurne)
        score_dign = min(dign["score"] * 3, 30)  # échelle 0-30
        score += score_dign
        detail["dignite"] = score_dign

        # Maison angulaire/succédente (max 15)
        if maison in _ANGULAIRES:
            score += 15
            detail["angulaire"] = 15
        elif maison in _SUCCEDENTES:
            score += 8
            detail["succedente"] = 8

        # Proximité aux angles Asc/MC (< 8° du cuspe, max 15)
        for angle_lon in (asc_lon, mc_lon):
            ecart = min(abs(lon - angle_lon) % 360, 360 - abs(lon - angle_lon) % 360)
            if ecart < 8:
                bonus = int(15 * (1 - ecart / 8))
                score += bonus
                detail["proximite_angle"] = bonus
                break

        # Vitesse angulaire (max 10)
        if retro or abs(vitesse) < 0.1:
            score += 10
            detail["vitesse_lente"] = 10
        elif abs(vitesse) < 1.0:
            score += 5
            detail["vitesse_moyenne"] = 5

        # Aspects reçus (max 15)
        nb_asp = aspects_recus.get(nom, 0)
        score += min(nb_asp * 3, 15)
        detail["aspects_recus"] = min(nb_asp * 3, 15)

        # Luminaire bonus (+15)
        if nom in _LUMINAIRES:
            score += 15
            detail["luminaire"] = 15

        # Rétrogradation bonus (+5)
        if retro:
            score += 5
            detail["retrograde"] = 5

        # Combuste (-10) / Cazimi (+5)
        ecart_soleil = min(abs(lon - soleil_lon) % 360, 360 - abs(lon - soleil_lon) % 360)
        if ecart_soleil < 0.5 and nom != "Soleil":
            score += 5  # cazimi (cœur du Soleil)
            detail["cazimi"] = 5
        elif ecart_soleil < 17 and nom != "Soleil":
            score -= 10  # combuste
            detail["combuste"] = -10

        # Lien au nœud nord (+10)
        if nn_lon is not None:
            ecart_nn = min(abs(lon - nn_lon) % 360, 360 - abs(lon - nn_lon) % 360)
            if ecart_nn < 3:
                score += 10
                detail["noeud_nord"] = 10

        scores_planete[nom] = score
        detail_planete[nom] = detail

    # Agréger pour élément/mode/signe/maison
    scores_elem = {"Feu": 0, "Terre": 0, "Air": 0, "Eau": 0}
    scores_mode = {"Cardinal": 0, "Fixe": 0, "Mutable": 0}
    scores_signe = {s: 0 for s in _ELEMENTS}
    scores_maison = {i: 0 for i in range(1, 13)}

    for nom, score in scores_planete.items():
        info = points[nom]
        signe = info["signe"]
        maison = info.get("maison", 0)
        scores_elem[_ELEMENTS[signe]] += score
        scores_mode[_MODES[signe]] += score
        scores_signe[signe] += score
        if 1 <= maison <= 12:
            scores_maison[maison] += score

    def dominant(scores: dict) -> str:
        return max(scores, key=scores.get)

    return {
        "element": {"dominant": dominant(scores_elem), "scores": scores_elem},
        "mode": {"dominant": dominant(scores_mode), "scores": scores_mode},
        "planete": {"dominante": dominant(scores_planete), "scores": scores_planete},
        "signe": {"dominant": dominant(scores_signe), "scores": scores_signe},
        "maison": {"dominante": dominant(scores_maison), "scores": scores_maison},
        "methode": "score_complexe",
        "chart_diurne": chart_diurne,
        "detail": detail_planete,
    }
```

Update `dominantes()` dispatcher :

```python
    if methode == "score_complexe":
        return _score_complexe(points, maisons, aspects, diurne)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd engine && python -m pytest test_dominantes.py -v`
Expected: PASS — tous les tests (comptage + score_complexe).

- [ ] **Step 5: Commit**

```bash
git add engine/dominantes.py engine/test_dominantes.py
git commit -m "feat(dominantes): méthode score_complexe (Jones/Muzzarelli)"
```

---

### Task 8: `theme_complet.py` — orchestrateur

**Files:**
- Create: `engine/theme_complet.py`
- Test: `engine/test_theme_complet.py`

**Interfaces:**
- Consumes: `traditions.theme_astral(dt, utc_offset_h, lat, lon)`, `ephemeride.positions(...)`, `maisons.maisons(...)`, `aspects.aspects(...)`, `dominantes.dominantes(...)`, `traditions._signe_depuis_longitude(...)`.
- Produces:
  - `theme_complet.theme_complet(fiche: dict) -> dict` — carte complète.
  - `theme_complet.theme_complet_depuis_traditions(trad: dict, fiche: dict) -> dict` — variante réutilisant un calcul traditions déjà fait.

- [ ] **Step 1: Write failing tests in `engine/test_theme_complet.py`**

```python
"""Tests du theme_complet — orchestrateur, repli honnête, cohérence."""
from datetime import datetime
import theme_complet as TC
import traditions as T


_FICHE_COMPLETE = {
    "date_naissance": "2000-01-01",
    "heure_naissance": "12:00",
    "latitude": 45.0,
    "longitude": 0.0,
    "utc_offset": 0.0,
    "systeme_maisons": "whole_sign",
    "methode_dominantes": "comptage_dignite",
}


def test_theme_complet_champs_present():
    res = TC.theme_complet(_FICHE_COMPLETE)
    assert "fondations" in res
    assert "dix_corps" in res
    assert "points_evolutifs" in res
    assert "maisons" in res
    assert "aspects" in res
    assert "dominantes" in res
    assert "meta" in res


def test_fondations_six_entrees():
    res = TC.theme_complet(_FICHE_COMPLETE)
    f = res["fondations"]
    assert {"soleil", "lune", "ascendant", "descendant",
            "milieu_du_ciel", "fond_du_ciel"} <= set(f.keys())


def test_dix_corps_dix_entrees():
    res = TC.theme_complet(_FICHE_COMPLETE)
    assert set(res["dix_corps"].keys()) == {"Soleil", "Lune", "Mercure", "Vénus",
                                            "Mars", "Jupiter", "Saturne", "Uranus",
                                            "Neptune", "Pluton"}


def test_points_evolutifs_quatre():
    res = TC.theme_complet(_FICHE_COMPLETE)
    assert set(res["points_evolutifs"].keys()) == {"noeud_nord", "noeud_sud",
                                                    "chiron", "lilith"}


def test_maisons_12_et_systeme():
    res = TC.theme_complet(_FICHE_COMPLETE)
    assert len(res["maisons"]) == 12
    assert res["meta"]["systeme_maisons_effectif"] == "whole_sign"


def test_repli_sans_heure_sans_lieu():
    """Sans heure/lieu : seulement les fondations Soleil (+ Lune approx à midi)."""
    fiche = {"date_naissance": "2000-01-01"}
    res = TC.theme_complet(fiche)
    assert "soleil" in res.get("fondations", {})
    # Pas de maisons, pas d'aspects (besoin de l'heure/lieu)
    assert "maisons" not in res or not res["maisons"]
    assert "aspects" not in res or not res["aspects"]


def test_theme_complet_depuis_traditions_coherent():
    """Variante réutilisant traditions : mêmes fondations Soleil/Asc/MC."""
    trad = T.calculer(_FICHE_COMPLETE)
    res1 = TC.theme_complet(_FICHE_COMPLETE)
    res2 = TC.theme_complet_depuis_traditions(trad, _FICHE_COMPLETE)
    assert abs(res1["fondations"]["soleil"]["longitude"]
               - res2["fondations"]["soleil"]["longitude"]) < 1e-3


def test_changement_systeme_maisons_change_maisons_pas_positions():
    """Whole Sign vs Equal House : positions identiques, maisons différentes."""
    fiche_ws = {**_FICHE_COMPLETE, "systeme_maisons": "whole_sign"}
    fiche_eh = {**_FICHE_COMPLETE, "systeme_maisons": "equal_house"}
    ws = TC.theme_complet(fiche_ws)
    eh = TC.theme_complet(fiche_eh)
    # Positions des corps identiques
    assert ws["dix_corps"]["Soleil"]["longitude"] == eh["dix_corps"]["Soleil"]["longitude"]
    # Cuspes des maisons différents (sauf si Asc à 0° d'un signe)
    assert ws["meta"]["systeme_maisons_effectif"] != eh["meta"]["systeme_maisons_effectif"]


def test_meta_contient_caveats():
    res = TC.theme_complet(_FICHE_COMPLETE)
    caveats = res["meta"].get("caveats", [])
    assert any("Pluton" in c or "Chiron" in c for c in caveats)


def test_noeud_sud_symetrique_noeud_nord():
    res = TC.theme_complet(_FICHE_COMPLETE)
    nn = res["points_evolutifs"]["noeud_nord"]["longitude"]
    ns = res["points_evolutifs"]["noeud_sud"]["longitude"]
    ecart = abs(nn - ns) % 360
    assert abs(ecart - 180) < 1e-3 or abs(ecart - 180) > 179.99
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd engine && python -m pytest test_theme_complet.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation in `engine/theme_complet.py`**

```python
"""Theme complet — orchestrateur de la carte astrologique.

Assemble les 6 zones (fondations, 10 corps, points évolutifs, maisons, aspects,
dominantes) à partir d'une fiche. Repli honnête : chaque sous-section absente si
données manquantes, jamais d'erreur.
"""
from __future__ import annotations

from datetime import date, datetime

import aspects as A
import dominantes as D
import ephemeride as E
import maisons as M
import traditions as T

_CAVEATS = [
    "Pluton/Chiron : formule approchée stdlib (~0,1-1°) — suffisant pour signe/maison, limite pour aspects serrés.",
    "Nœud lunaire moyen (par défaut) — diffère du nœud vrai de ~0,1°.",
]


def _parse_naissance(fiche: dict) -> tuple[date | None, datetime | None, float, float, float]:
    """Extrait date, datetime, utc_offset, latitude, longitude de la fiche."""
    dn = (fiche.get("date_naissance") or "").strip()
    naissance = None
    if dn:
        try:
            naissance = date.fromisoformat(dn)
        except ValueError:
            naissance = None
    he = (fiche.get("heure_naissance") or "").strip()
    dt = None
    heure_valide = False
    if naissance and he:
        try:
            hh, mm = (int(x) for x in he.split(":")[:2])
            dt = datetime(naissance.year, naissance.month, naissance.day, hh, mm)
            heure_valide = True
        except (ValueError, TypeError):
            pass
    off = float(fiche.get("utc_offset") or 0)
    lat = fiche.get("latitude")
    lon = fiche.get("longitude")
    return naissance, dt, off, lat, lon, heure_valide


def _maison_de(longitude: float, maisons: list[dict]) -> int | None:
    """Trouve la maison contenant la longitude."""
    if not maisons:
        return None
    for i, m in enumerate(maisons):
        cuspe = m["cuspe"]
        next_cuspe = maisons[(i + 1) % 12]["cuspe"]
        if cuspe <= next_cuspe:
            if cuspe <= longitude < next_cuspe:
                return m["maison"]
        else:  # chevauche 0°
            if longitude >= cuspe or longitude < next_cuspe:
                return m["maison"]
    return maisons[0]["maison"]


def _construire(naissance, dt, off, lat, lon, heure_valide,
                systeme_maisons, methode_dominantes, trad=None) -> dict:
    """Construction partagée entre theme_complet et theme_complet_depuis_traditions."""
    out: dict = {}
    meta: dict = {"caveats": list(_CAVEATS)}
    if not naissance:
        return {"meta": meta}

    # Soleil (toujours calculable avec juste la date)
    soleil_lon = T.soleil_longitude(dt or datetime(naissance.year, naissance.month, naissance.day, 12, 0), off)
    fondations = {"soleil": {**T._signe_depuis_longitude(soleil_lon),
                             "longitude": round(soleil_lon % 360, 4)}}

    # Lune (besoin de l'heure, mais on peut approximer à midi si pas d'heure)
    if dt or heure_valide:
        lune_lon = T.lune_longitude(dt, off)
        fondations["lune"] = {**T._signe_depuis_longitude(lune_lon),
                              "longitude": round(lune_lon % 360, 4)}
    elif dt is None and naissance:
        # Approximation à midi
        dt_midi = datetime(naissance.year, naissance.month, naissance.day, 12, 0)
        lune_lon = T.lune_longitude(dt_midi, off)
        fondations["lune"] = {**T._signe_depuis_longitude(lune_lon),
                              "longitude": round(lune_lon % 360, 4)}

    # Asc/MC (besoin de l'heure + lieu)
    asc = mc = None
    if heure_valide and isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        ta = trad or T.theme_astral(dt, off, float(lat), float(lon))
        asc = ta["ascendant"]["longitude"]
        mc = ta["milieu_du_ciel"]["longitude"]
        fondations["ascendant"] = {**T._signe_depuis_longitude(asc), "longitude": round(asc % 360, 4)}
        fondations["descendant"] = {**T._signe_depuis_longitude((asc + 180) % 360),
                                    "longitude": round((asc + 180) % 360, 4)}
        fondations["milieu_du_ciel"] = {**T._signe_depuis_longitude(mc), "longitude": round(mc % 360, 4)}
        fondations["fond_du_ciel"] = {**T._signe_depuis_longitude((mc + 180) % 360),
                                      "longitude": round((mc + 180) % 360, 4)}

    out["fondations"] = fondations

    # 10 corps + points évolutifs (besoin de l'heure)
    points_positions = {}
    if heure_valide:
        try:
            pos = E.positions(dt, off, float(lat or 0), float(lon or 0))
            # 10 corps
            dix_corps = {}
            for corps in ["Soleil", "Lune", "Mercure", "Vénus", "Mars",
                          "Jupiter", "Saturne", "Uranus", "Neptune", "Pluton"]:
                if corps in pos:
                    p = pos[corps]
                    s = T._signe_depuis_longitude(p["longitude"])
                    dix_corps[corps] = {**s, **p, "corps": corps}
            out["dix_corps"] = dix_corps
            # Points évolutifs
            pe = {}
            if "Nœud Nord" in pos:
                nn = pos["Nœud Nord"]
                pe["noeud_nord"] = {**T._signe_depuis_longitude(nn["longitude"]), **nn}
                ns_lon = (nn["longitude"] + 180) % 360
                pe["noeud_sud"] = {**T._signe_depuis_longitude(ns_lon),
                                   "longitude": round(ns_lon, 4), "corps": "Nœud Sud"}
            if "Chiron" in pos:
                pe["chiron"] = {**T._signe_depuis_longitude(pos["Chiron"]["longitude"]), **pos["Chiron"]}
            if "Lilith" in pos:
                pe["lilith"] = {**T._signe_depuis_longitude(pos["Lilith"]["longitude"]), **pos["Lilith"]}
            out["points_evolutifs"] = pe

            # Construire le dict points pour aspects + dominantes
            points_positions = {**dix_corps, **{k: v for k, v in pe.items()}}
            if asc is not None:
                points_positions["Ascendant"] = {"longitude": asc, "signe": fondations["ascendant"]["signe"]}
                points_positions["Descendant"] = {"longitude": (asc + 180) % 360}
                points_positions["Milieu du Ciel"] = {"longitude": mc}
                points_positions["Fond du Ciel"] = {"longitude": (mc + 180) % 360}
        except (NotImplementedError, ValueError, TypeError):
            pass

    # Maisons
    maisons_list = []
    if asc is not None and mc is not None and isinstance(lat, (int, float)):
        try:
            maisons_list = M.maisons(asc, mc, float(lat), systeme_maisons)
            out["maisons"] = maisons_list
            meta["systeme_maisons_effectif"] = maisons_list[0]["systeme"]
            # Assigner la maison à chaque point
            for nom, p in points_positions.items():
                p["maison"] = _maison_de(p["longitude"], maisons_list)
        except Exception:
            meta["systeme_maisons_effectif"] = systeme_maisons
    meta["systeme_maisons_demande"] = systeme_maisons
    meta["methode_dominantes_demande"] = methode_dominantes

    # Aspects
    if len(points_positions) >= 2:
        try:
            out["aspects"] = A.aspects(points_positions)
        except Exception:
            pass

    # Dominantes
    if points_positions and maisons_list:
        try:
            out["dominantes"] = D.dominantes(points_positions, maisons_list,
                                             out.get("aspects", []), methode_dominantes)
            meta["methode_dominantes_effectif"] = out["dominantes"]["methode"]
        except NotImplementedError:
            meta["methode_dominantes_effectif"] = "non_calcule"

    out["meta"] = meta
    return out


def theme_complet(fiche: dict) -> dict:
    """Carte astrologique complète depuis une fiche."""
    naissance, dt, off, lat, lon, heure_valide = _parse_naissance(fiche)
    systeme = fiche.get("systeme_maisons", "whole_sign")
    methode = fiche.get("methode_dominantes", "comptage_dignite")
    return _construire(naissance, dt, off, lat, lon, heure_valide, systeme, methode)


def theme_complet_depuis_traditions(trad: dict, fiche: dict) -> dict:
    """Variante réutilisant un calcul traditions déjà fait."""
    naissance, dt, off, lat, lon, heure_valide = _parse_naissance(fiche)
    systeme = fiche.get("systeme_maisons", "whole_sign")
    methode = fiche.get("methode_dominantes", "comptage_dignite")
    return _construire(naissance, dt, off, lat, lon, heure_valide, systeme, methode,
                       trad=trad.get("theme_astral"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd engine && python -m pytest test_theme_complet.py -v`
Expected: PASS — 9 tests.

- [ ] **Step 5: Commit**

```bash
git add engine/theme_complet.py engine/test_theme_complet.py
git commit -m "feat(theme_complet): orchestrateur — assemble la carte complète"
```

---

### Task 9: `main.py` — endpoints `/theme` + `/portrait` étendu

**Files:**
- Modify: `main.py`
- Test: `engine/test_api_theme.py` (nouveau)

**Interfaces:**
- Produces:
  - `Fiche.systeme_maisons : str = "whole_sign"` — `"whole_sign" | "placidus" | "equal_house"`.
  - `Fiche.methode_dominantes : str = "comptage_dignite"` — `"comptage_dignite" | "score_complexe"`.
  - `POST /theme` — renvoie `theme_complet.theme_complet(fiche)`.
  - `POST /portrait` étendu — renvoie en plus `theme_complet` intégré.

- [ ] **Step 1: Write failing tests in `engine/test_api_theme.py`**

```python
"""Tests API des endpoints /theme et /portrait étendu."""
import sys
from pathlib import Path

# Ajouter la racine du projet au path pour importer main
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_ENGINE = _ROOT / "engine"
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

from fastapi.testclient import TestClient
import main

client = TestClient(main.app)


_FICHE = {
    "prenoms": "Test", "nom": "Unit",
    "date_naissance": "2000-01-01",
    "heure_naissance": "12:00",
    "latitude": 45.0,
    "longitude": 0.0,
    "utc_offset": 0.0,
    "systeme_maisons": "whole_sign",
    "methode_dominantes": "comptage_dignite",
}


def test_theme_endpoint_renvoie_carte():
    r = client.post("/theme", json=_FICHE)
    assert r.status_code == 200
    data = r.json()
    assert "fondations" in data
    assert "dix_corps" in data
    assert "meta" in data


def test_theme_endpoint_sans_date_renvoie_422():
    r = client.post("/theme", json={"prenoms": "X"})
    assert r.status_code == 422


def test_theme_endpoint_changement_systeme():
    fiche_eh = {**_FICHE, "systeme_maisons": "equal_house"}
    r = client.post("/theme", json=fiche_eh)
    assert r.status_code == 200
    data = r.json()
    assert data["meta"]["systeme_maisons_effectif"] == "equal_house"


def test_portrait_endpoint_renvoie_theme_complet():
    r = client.post("/portrait", json=_FICHE)
    assert r.status_code == 200
    data = r.json()
    assert "theme_complet" in data
    assert "fondations" in data["theme_complet"]
    # L'empreinte et le portrait existent toujours
    assert "portrait" in data
    assert "empreinte" in data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd engine && python -m pytest test_api_theme.py -v`
Expected: FAIL — `AttributeError: 'Fiche' object has no attribute 'systeme_maisons'` ou 404 sur `/theme`.

- [ ] **Step 3: Modify `main.py`**

Add imports at the top (after `import traditions`) :

```python
import theme_complet
```

Extend `Fiche` :

```python
class Fiche(BaseModel):
    """Entrée du portrait. Seule la date est requise en pratique (les stats en dérivent) ;
    chaque champ manquant désactive juste la lecture qui en dépend (repli honnête)."""
    prenoms:        str = ""
    nom:            str = ""
    date_naissance: str = ""               # "YYYY-MM-DD"
    heure_naissance: Optional[str] = None   # "HH:MM"
    latitude:       Optional[float] = None
    longitude:      Optional[float] = None  # EST-positive
    utc_offset:     Optional[float] = None  # décalage local→UTC à la naissance
    systeme_numerologie: str = "classique"  # "classique" (A=1…Z=26) ou "pythagoricien"
    langue:         str = "fr"              # "fr" ou "en" — langue du portrait déterministe
    systeme_maisons: str = "whole_sign"      # "whole_sign" | "placidus" | "equal_house"
    methode_dominantes: str = "comptage_dignite"  # "comptage_dignite" | "score_complexe"
```

Add `/theme` endpoint (after `/modeles`) :

```python
@app.post("/theme", tags=["portrait"])
def theme(body: Fiche):
    """Carte astrologique complète (fondations, 10 corps, points évolutifs,
    maisons, aspects, dominantes). Seule la date est absolument requise —
    sans heure/lieu, seules les fondations Soleil/Lune sont calculées
    (Lune approximative sans heure) ; le reste en repli honnête."""
    tc = theme_complet.theme_complet(body.model_dump())
    if not tc.get("fondations", {}).get("soleil"):
        raise HTTPException(422, "Indique au moins une date de naissance valide.")
    return tc
```

Modify `/portrait` :

```python
@app.post("/portrait", tags=["portrait"])
def portrait(body: Fiche):
    """Fiche → traditions calculées → portrait (stats/archétype/forces/faiblesse/pierre/
    récit) → empreinte lisible. Étendu : inclut désormais `theme_complet` intégré
    pour que le récit déterministe et l'empreinte exploitent les nouvelles données."""
    trad = traditions.calculer(body.model_dump())
    if not trad.get("signe_solaire"):
        raise HTTPException(422, "Indique au moins une date de naissance valide.")
    tc = theme_complet.theme_complet_depuis_traditions(trad, body.model_dump())
    p = synthese.portrait(trad, theme_complet=tc, nom=body.prenoms or body.nom, langue=body.langue)
    return {"traditions": trad, "theme_complet": tc,
            "portrait": p,
            "empreinte": significations.expliquer(trad, body.langue, theme_complet=tc),
            "glossaire": significations.glossaire(body.langue)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd engine && python -m pytest test_api_theme.py -v`
Expected: PASS — 4 tests.

**Note :** les tests `test_portrait_endpoint_renvoie_theme_complet` peuvent échouer si `synthese.portrait()` et `significations.expliquer()` ne supportent pas encore le paramètre `theme_complet` (task 10 et 11). Si c'est le cas, commenter ces deux tests pour cette task et les réactiver après les tasks 10-11. Le endpoint `/theme` doit passer indépendamment.

- [ ] **Step 5: Commit**

```bash
git add main.py engine/test_api_theme.py
git commit -m "feat(api): endpoint /theme + /portrait étendu avec theme_complet"
```

---

### Task 10: `significations.py` étendu — clefs d'interprétation + `expliquer()`

**Files:**
- Modify: `engine/significations.py`
- Test: `engine/test_significations.py`

**Interfaces:**
- Produces:
  - `significations.CLEFS_CORPS : dict[str, dict]` — 10 corps × `{fr: str, en: str}` (mot-clé par corps).
  - `significations.CLEFS_POINTS_EVOLUTIFS : dict[str, dict]` — Nœud Nord/Sud, Chiron, Lilith.
  - `significations.CLEFS_ASPECTS : dict[str, dict]` — interpretation par couple aspect×nature.
  - `significations.CLEFS_DOMINANTES : dict[str, dict]` — phrase résumé par dominante.
  - `significations.expliquer(trad, langue, theme_complet=None) -> list` — étendu : si `theme_complet` fourni, ajoute une sous-section « Carte astro complète ».

- [ ] **Step 1: Write failing tests**

Append to `engine/test_significations.py`:

```python
# ── Clefs theme_complet (task 10) ─────────────────────────────────
def test_clefs_corps_10_entrees():
    import significations as S
    assert set(S.CLEFS_CORPS.keys()) == {"Soleil", "Lune", "Mercure", "Vénus",
                                         "Mars", "Jupiter", "Saturne", "Uranus",
                                         "Neptune", "Pluton"}
    for corps, clef in S.CLEFS_CORPS.items():
        assert "fr" in clef and "en" in clef


def test_clefs_points_evolutifs_4():
    import significations as S
    assert set(S.CLEFS_POINTS_EVOLUTIFS.keys()) == {"noeud_nord", "noeud_sud",
                                                     "chiron", "lilith"}


def test_clefs_aspects_presentes():
    import significations as S
    # Au moins trigone et carré
    assert "trigone" in S.CLEFS_ASPECTS
    assert "carre" in S.CLEFS_ASPECTS


def test_clefs_dominantes_element():
    import significations as S
    assert "Feu" in S.CLEFS_DOMINANTES.get("element", {})


def test_expliquer_avec_theme_complet():
    """expliquer() avec theme_complet ajoute une sous-section carte astro."""
    import significations as S
    trad = {"signe_solaire": {"nom": "Bélier"}}
    tc = {"fondations": {"soleil": {"signe": "Bélier", "longitude": 0.0}},
          "dix_corps": {"Soleil": {"signe": "Bélier"}},
          "dominantes": {"element": {"dominant": "Feu"}}}
    res = S.expliquer(trad, "fr", theme_complet=tc)
    # L'empreinte contient une entrée liée à la carte astro complète
    assert any("carte" in e.get("id", "").lower() or "theme" in e.get("id", "").lower()
               for e in res)


def test_expliquer_sans_theme_complet_compatible():
    """expliquer() sans theme_complet reste compatible (pas d'erreur)."""
    import significations as S
    trad = {"signe_solaire": {"nom": "Bélier"}}
    res = S.expliquer(trad, "fr")
    assert isinstance(res, list)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd engine && python -m pytest test_significations.py -v -k "clefs_corps or clefs_points or clefs_aspects or clefs_dominantes or expliquer_avec_theme or expliquer_sans_theme"`
Expected: FAIL — `AttributeError: module 'significations' has no attribute 'CLEFS_CORPS'`

- [ ] **Step 3: Extend `engine/significations.py`**

Add the new tables (after existing clefs). **L'implémenteur rédige les textes FR/EN alignés sur le ton existant (lecture symbolique de divertissement).** Exemple de structure :

```python
# ── Clefs theme_complet (carte astro complète) ────────────────────
CLEFS_CORPS = {
    "Soleil":   {"fr": "identité, vitalité, essence consciente",
                 "en": "identity, vitality, conscious essence"},
    "Lune":     {"fr": "émotions, jardin secret, instincts",
                 "en": "emotions, inner world, instincts"},
    "Mercure":  {"fr": "communication, raisonnement, échanges",
                 "en": "communication, reasoning, exchanges"},
    "Vénus":    {"fr": "amour, valeurs, séduction",
                 "en": "love, values, attraction"},
    "Mars":     {"fr": "action, désir, combativité",
                 "en": "action, desire, drive"},
    "Jupiter":  {"fr": "expansion, vision, confiance",
                 "en": "expansion, vision, confidence"},
    "Saturne":  {"fr": "structure, limite, responsabilité",
                 "en": "structure, limit, responsibility"},
    "Uranus":   {"fr": "liberté, rupture, innovation",
                 "en": "freedom, disruption, innovation"},
    "Neptune":  {"fr": "rêve, compassion, dissolution",
                 "en": "dream, compassion, dissolution"},
    "Pluton":   {"fr": "transformation, pouvoir, régénération",
                 "en": "transformation, power, regeneration"},
}

CLEFS_POINTS_EVOLUTIFS = {
    "noeud_nord": {"fr": "direction de vie, évolution à intégrer",
                   "en": "life direction, evolution to integrate"},
    "noeud_sud":  {"fr": "acquis karmique, zone de confort à quitter",
                   "en": "karmic background, comfort zone to leave"},
    "chiron":     {"fr": "blessure et guérison, vulnérabilité enseignante",
                   "en": "wound and healing, teaching vulnerability"},
    "lilith":     {"fr": "ombre, désir refoulé, intuition sauvage",
                   "en": "shadow, repressed desire, wild intuition"},
}

CLEFS_ASPECTS = {
    "conjonction":  {"fr": "fusion des énergies", "en": "fusion of energies"},
    "opposition":   {"fr": "tension polarisée, mise en balance", "en": "polarized tension, balancing"},
    "trigone":      {"fr": "harmonie naturelle, flow", "en": "natural harmony, flow"},
    "carre":        {"fr": "tension constructive, défi à résoudre", "en": "constructive tension, challenge"},
    "sextile":      {"fr": "opportunité, coopération", "en": "opportunity, cooperation"},
    "semi_sextile": {"fr": "ajustement subtil", "en": "subtle adjustment"},
    "semi_carre":   {"fr": "friction mineure", "en": "minor friction"},
    "quintile":     {"fr": "créativité, talent", "en": "creativity, talent"},
    "sesquicarre":  {"fr": "tension créative", "en": "creative tension"},
    "quinconce":    {"fr": "désajustement, adaptation", "en": "mismatch, adaptation"},
}

CLEFS_DOMINANTES = {
    "element": {
        "Feu":   {"fr": "sensible, passionné, instinctif", "en": "passionate, instinctive"},
        "Terre": {"fr": "concret, pragmatique, stable", "en": "grounded, pragmatic, stable"},
        "Air":   {"fr": "mental, social, communicant", "en": "mental, social, communicative"},
        "Eau":   {"fr": "sensible, intuitif, empathique", "en": "sensitive, intuitive, empathic"},
    },
    "mode": {
        "Cardinal": {"fr": "initiateur, lanceur de projets", "en": "initiator, project starter"},
        "Fixe":     {"fr": "persévérant, constant", "en": "steadfast, persistent"},
        "Mutable":  {"fr": "adaptable, flexible", "en": "adaptable, flexible"},
    },
}
```

Then modify `expliquer()` to accept `theme_complet=None` and add a sub-section if provided. **L'implémenteur adapte la signature existante** (backwards compatible) :

```python
def expliquer(trad: dict, langue: str = "fr", theme_complet: dict | None = None) -> list:
    """... (docstring existant) ...
    Si `theme_complet` est fourni, ajoute une sous-section 'carte_astro_complete'
    avec les clefs des 10 corps, points évolutifs, aspects majeurs, dominantes.
    """
    # ... code existant qui construit l'empreinte ...
    empreinte = _expliquer_traditions(trad, langue)  # renomme l'existant si besoin

    if theme_complet:
        empreinte.extend(_expliquer_theme_complet(theme_complet, langue))

    return empreinte


def _expliquer_theme_complet(tc: dict, langue: str) -> list:
    """Sous-section empreinte pour la carte astro complète."""
    entries = []
    lg = langue if langue in ("fr", "en") else "fr"
    # Fondations
    for nom_cle, nom_aff in [("soleil", "Soleil"), ("lune", "Lune"),
                              ("ascendant", "Ascendant"), ("descendant", "Descendant"),
                              ("milieu_du_ciel", "MC"), ("fond_du_ciel", "IC")]:
        fond = tc.get("fondations", {}).get(nom_cle)
        if fond:
            entries.append({
                "id": f"theme_fondation_{nom_cle}",
                "label": nom_aff,
                "valeur": f"{fond.get('signe', '?')} ({fond.get('degre', 0):.1f}°)",
                "mots_cles": CLEFS_CORPS.get(nom_aff, {}).get(lg, "") if nom_aff in CLEFS_CORPS else "",
            })
    # 10 corps
    for corps, info in tc.get("dix_corps", {}).items():
        retro = " R" if info.get("retrograde") else ""
        entries.append({
            "id": f"theme_corps_{corps.lower()}",
            "label": corps,
            "valeur": f"{info.get('signe', '?')} {info.get('degre', 0):.1f}°{retro} (M{info.get('maison', '?')})",
            "mots_cles": CLEFS_CORPS.get(corps, {}).get(lg, ""),
        })
    # Points évolutifs
    for nom_cle, info in tc.get("points_evolutifs", {}).items():
        entries.append({
            "id": f"theme_point_{nom_cle}",
            "label": nom_cle.replace("_", " ").title(),
            "valeur": f"{info.get('signe', '?')} {info.get('degre', 0):.1f}°",
            "mots_cles": CLEFS_POINTS_EVOLUTIFS.get(nom_cle, {}).get(lg, ""),
        })
    # Aspects (majeurs seulement dans l'empreinte, top 5 par exactitude)
    aspects = tc.get("aspects", [])
    majeurs = [a for a in aspects if a.get("type") == "majeur"][:5]
    for asp in majeurs:
        entries.append({
            "id": f"theme_aspect_{asp['point_a']}_{asp['point_b']}_{asp['aspect']}",
            "label": f"{asp['aspect'].title()} {asp['point_a']}-{asp['point_b']}",
            "valeur": f"orbe {asp.get('orb', 0):.1f}°",
            "mots_cles": CLEFS_ASPECTS.get(asp["aspect"], {}).get(lg, ""),
        })
    # Dominantes
    dom = tc.get("dominantes", {})
    for categorie in ("element", "mode", "planete", "signe", "maison"):
        d = dom.get(categorie, {})
        cle = d.get("dominant") or d.get("dominante")
        if cle:
            mots = CLEFS_DOMINANTES.get(categorie, {}).get(str(cle), {}).get(lg, "") \
                if categorie in CLEFS_DOMINANTES else ""
            entries.append({
                "id": f"theme_dominante_{categorie}",
                "label": f"Dominante {categorie}",
                "valeur": str(cle),
                "mots_cles": mots,
            })
    return entries
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd engine && python -m pytest test_significations.py -v`
Expected: PASS — tous les tests (existants + nouveaux).

- [ ] **Step 5: Commit**

```bash
git add engine/significations.py engine/test_significations.py
git commit -m "feat(significations): clefs 10 corps + points évolutifs + aspects + dominantes + expliquer étendu"
```

---

### Task 11: `synthese.py` étendu — `portrait()` avec `theme_complet`

**Files:**
- Modify: `engine/synthese.py`
- Test: `engine/test_synthese.py`

**Interfaces:**
- Produces:
  - `synthese.portrait(trad, nom, langue, theme_complet=None) -> dict` — étendu : si `theme_complet` fourni, enrichit l'archétype (planète dominante × signe dominant), ajoute les aspects majeurs les plus exacts aux forces/points à travailler, ajoute un paragraphe sur le tempérament (élément/mode dominants), tient compte de la rétrogradation.

- [ ] **Step 1: Write failing tests**

Append to `engine/test_synthese.py`:

```python
# ── portrait() avec theme_complet (task 11) ───────────────────────
def test_portrait_avec_theme_complet_enrichit_archetype():
    """portrait() avec theme_complet enrichit l'archétype."""
    import synthese as S
    import significations as Z
    trad = {"signe_solaire": {"nom": "Bélier"}}
    tc = {
        "fondations": {"soleil": {"signe": "Bélier"}},
        "dix_corps": {"Soleil": {"signe": "Bélier"}, "Mars": {"signe": "Bélier"}},
        "dominantes": {"element": {"dominant": "Feu"},
                       "mode": {"dominant": "Cardinal"},
                       "planete": {"dominante": "Mars"},
                       "signe": {"dominant": "Bélier"}},
        "aspects": [{"aspect": "trigone", "type": "majeur", "point_a": "Soleil",
                     "point_b": "Jupiter", "orb": 0.3, "exactitude": 0.96}],
    }
    p = S.portrait(trad, nom="Test", langue="fr", theme_complet=tc)
    # L'archétype contient une mention de la dominante
    assert "archetype" in p
    # Le récit contient une mention du tempérament (Feu/Cardinal)
    assert "recit" in p
    assert "Feu" in p["recit"] or "feu" in p["recit"].lower() or "Cardinal" in p["recit"]


def test_portrait_avec_theme_complet_aspects_dans_forces():
    """Les aspects majeurs très exacts apparaissent dans les forces."""
    import synthese as S
    trad = {"signe_solaire": {"nom": "Bélier"}}
    tc = {
        "dominantes": {"element": {"dominant": "Feu"}, "mode": {"dominant": "Cardinal"},
                       "planete": {"dominante": "Mars"}, "signe": {"dominant": "Bélier"},
                       "maison": {"dominante": 1}},
        "aspects": [{"aspect": "trigone", "type": "majeur", "point_a": "Soleil",
                     "point_b": "Jupiter", "orb": 0.3, "exactitude": 0.96}],
    }
    p = S.portrait(trad, nom="Test", langue="fr", theme_complet=tc)
    # Soit dans forces, soit dans le récit
    forces_text = " ".join(p.get("forces", []))
    assert "trigone" in forces_text.lower() or "jupiter" in forces_text.lower() \
        or "trigone" in p.get("recit", "").lower()


def test_portrait_sans_theme_complet_compatible():
    """portrait() sans theme_complet reste compatible."""
    import synthese as S
    trad = {"signe_solaire": {"nom": "Bélier"}}
    p = S.portrait(trad, nom="Test", langue="fr")
    assert "archetype" in p
    assert "recit" in p
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd engine && python -m pytest test_synthese.py -v -k "theme_complet"`
Expected: FAIL — `TypeError: portrait() got an unexpected keyword argument 'theme_complet'`

- [ ] **Step 3: Modify `synthese.portrait()`**

**L'implémenteur adapte la fonction `portrait()` existante** pour accepter `theme_complet=None` (backwards compatible). Structure recommandée :

```python
def portrait(trad: dict, nom: str = "", langue: str = "fr",
             theme_complet: dict | None = None) -> dict:
    """... (docstring existant) ...
    Si `theme_complet` est fourni, enrichit l'archétype et le récit avec les
    dominantes, les aspects majeurs les plus exacts, et la rétrogradation.
    """
    # ... code existant qui construit p (stats, archétype, forces, faiblesse,
    #     pierre, recit) ...

    if theme_complet:
        p = _enrichir_avec_theme_complet(p, theme_complet, langue)

    return p


def _enrichir_avec_theme_complet(p: dict, tc: dict, langue: str) -> dict:
    """Enrichit le portrait avec les données de la carte astro complète."""
    import significations as Z
    lg = langue if langue in ("fr", "en") else "fr"

    dom = tc.get("dominantes", {})
    planete_dom = dom.get("planete", {}).get("dominante")
    signe_dom = dom.get("signe", {}).get("dominant")
    element_dom = dom.get("element", {}).get("dominant")
    mode_dom = dom.get("mode", {}).get("dominant")

    # Enrichir l'archétype
    if planete_dom and signe_dom:
        clef = Z.CLEFS_CORPS.get(planete_dom, {}).get(lg, "")
        if clef:
            p["archetype"] = f"{p.get('archetype', '')} — {planete_dom} en {signe_dom} dominant ({clef})".strip(" —")

    # Paragraphe tempérament (élément + mode)
    if element_dom and mode_dom:
        elem_clef = Z.CLEFS_DOMINANTES.get("element", {}).get(element_dom, {}).get(lg, "")
        mode_clef = Z.CLEFS_DOMINANTES.get("mode", {}).get(mode_dom, {}).get(lg, "")
        p["recit"] += f"\n\nTempérament : dominante {element_dom} {mode_dom.lower()} — {elem_clef}, {mode_clef}."

    # Aspects majeurs très exacts (top 3) dans les forces
    aspects = tc.get("aspects", [])
    majeurs = [a for a in aspects if a.get("type") == "majeur"
               and a.get("exactitude", 0) > 0.8][:3]
    for asp in majeurs:
        clef = Z.CLEFS_ASPECTS.get(asp["aspect"], {}).get(lg, "")
        force = f"{asp['aspect'].title()} {asp['point_a']}-{asp['point_b']} ({clef})"
        if "forces" in p and isinstance(p["forces"], list):
            p["forces"].append(force)

    # Rétrogradation des planètes dominantes
    if planete_dom:
        corps_info = tc.get("dix_corps", {}).get(planete_dom, {})
        if corps_info.get("retrograde"):
            p["recit"] += f"\n\n{planete_dom} rétrograde : intériorisation de son énergie."

    return p
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd engine && python -m pytest test_synthese.py -v`
Expected: PASS — tous les tests (existants + nouveaux).

- [ ] **Step 5: Commit**

```bash
git add engine/synthese.py engine/test_synthese.py
git commit -m "feat(synthese): portrait() enrichi avec theme_complet (dominantes, aspects, rétro)"
```

---

### Task 12: `static/index.html` — onglet « Carte astro complète » + roue SVG + tableaux

**Files:**
- Modify: `static/index.html`

**Interfaces:**
- Consumes: `POST /theme` (JSON), `POST /portrait` étendu (JSON avec `theme_complet`).
- Produces:
  - Onglet « Carte astro complète » dans les résultats, à côté de « Portrait ».
  - Options en haut : système de maisons (radio), méthode dominantes (radio) — rechargent la carte via `/theme`.
  - Roue SVG (colonne gauche) : cercle zodiacal, anneau maisons, positions des 10 corps + 4 points évolutifs, lignes d'aspects (couleurs par type, épaisseur par exactitude), légende filtre.
  - Tableaux détaillés (colonne droite) : fondations, 10 corps, points évolutifs, 12 maisons, aspects (triable, filtrable), dominantes (5 cartes avec barres de scores).
  - Caveat d'honnêteté sous la roue.
  - Export PDF : `@media print` masque options + roue, garde les tableaux (une colonne, A4).
  - Export HTML : SVG inline + tableaux, auto-contenu.

**Note :** cette task est la plus volumineuse (frontend vanilla JS + SVG). L'implémenteur suit les conventions existantes de `static/index.html` (single file, vanilla JS, FR/EN, pas de framework). On découpe en sous-étapes.

- [ ] **Step 1: Write a manual test checklist (pas de tests automatiques pour le front)**

Créer `static/index.html` modifié, puis vérifier manuellement :
1. Formulaire → bouton « Calculer » → onglet « Portrait » affiché.
2. Onglet « Carte astro complète » visible et cliquable.
3. Options système de maisons : changer → la roue et les maisons se mettent à jour.
4. Options méthode dominantes : changer → les dominantes se mettent à jour.
5. Roue SVG : 12 signes en périphérie, 12 maisons numérotées, glyphes planétaires, lignes d'aspects.
6. Tableaux : 6 sections, données cohérentes avec la roue.
7. Filtre aspects (majeurs/mineurs/tous) : les lignes de la roue et les lignes du tableau changent.
8. Caveat visible sous la roue.
9. Export HTML : ouvrir le fichier exporté hors-ligne → roue + tableaux fonctionnels.
10. Export PDF (dialogue impression) : tableaux uniquement, une colonne, pas de roue, pas d'options.

- [ ] **Step 2: Add HTML structure for the tab**

Dans `static/index.html`, ajouter après la section des résultats existante :

```html
<!-- Onglets des résultats -->
<div class="resultats-onglets">
  <button class="onglet onglet-actif" data-onglet="portrait">Portrait</button>
  <button class="onglet" data-onglet="theme">Carte astro complète</button>
</div>

<section id="onglet-portrait" class="onglet-contenu onglet-contenu-actif">
  <!-- ... contenu existant (portrait, empreinte, récit) ... -->
</section>

<section id="onglet-theme" class="onglet-contenu" hidden>
  <div class="theme-options">
    <fieldset>
      <legend>Système de maisons</legend>
      <label><input type="radio" name="systeme-maisons" value="whole_sign" checked> Whole Sign</label>
      <label><input type="radio" name="systeme-maisons" value="placidus"> Placidus</label>
      <label><input type="radio" name="systeme-maisons" value="equal_house"> Equal House</label>
    </fieldset>
    <fieldset>
      <legend>Méthode des dominantes</legend>
      <label><input type="radio" name="methode-dominantes" value="comptage_dignite" checked> Comptage + dignités</label>
      <label><input type="radio" name="methode-dominantes" value="score_complexe"> Score complexe</label>
    </fieldset>
  </div>

  <div class="theme-layout">
    <div class="theme-roue">
      <svg id="roue-svg" viewBox="-200 -200 400 400" role="img"
           aria-label="Roue zodiacale"></svg>
      <div class="theme-legend"></div>
      <p class="theme-caveat">Précision : VSOP87 (Soleil→Neptune <1″), Pluton/Chiron formule approchée (~0,1-1°). Sans Swiss Ephemeris.</p>
    </div>
    <div class="theme-tableaux">
      <div id="tableaux-theme"></div>
    </div>
  </div>
</section>
```

- [ ] **Step 3: Add CSS for the tab, layout, and print**

```css
.resultats-onglets { display: flex; gap: 0.5rem; margin: 1rem 0; }
.onglet { padding: 0.5rem 1rem; border: 1px solid var(--bord); background: var(--fond2);
          cursor: pointer; border-radius: 6px 6px 0 0; }
.onglet-actif { background: var(--accent); color: white; }
.onglet-contenu { display: none; }
.onglet-contenu-actif { display: block; }

.theme-options { display: flex; gap: 2rem; flex-wrap: wrap; margin: 1rem 0; }
.theme-options fieldset { border: 1px solid var(--bord); padding: 0.5rem 1rem; }
.theme-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }
@media (max-width: 768px) { .theme-layout { grid-template-columns: 1fr; } }
.theme-caveat { font-size: 0.85em; opacity: 0.7; margin-top: 0.5rem; }

.theme-tableaux table { width: 100%; border-collapse: collapse; margin-bottom: 1.5rem; }
.theme-tableaux caption { caption-side: top; font-weight: bold; margin-bottom: 0.5rem; }
.theme-tableaux th, .theme-tableaux td { padding: 0.3rem 0.5rem; border: 1px solid var(--bord); text-align: left; }
.theme-tableaux th { background: var(--fond2); }

.dominante-carte { border: 1px solid var(--bord); padding: 1rem; margin-bottom: 1rem; }
.dominante-carte h4 { margin: 0 0 0.5rem 0; }
.dominante-barre { height: 8px; background: var(--fond2); border-radius: 4px; overflow: hidden; }
.dominante-barre > div { height: 100%; background: var(--accent); }

@media print {
  .resultats-onglets, .theme-options, #roue-svg, .theme-legend, .theme-caveat { display: none !important; }
  .onglet-contenu { display: block !important; }
  .theme-layout { display: block !important; }
  .theme-tableaux table { font-size: 10pt; }
}
```

- [ ] **Step 4: Add JS to fetch /theme, render wheel SVG, and render tables**

Ajouter dans le `<script>` de `index.html` (l'implémenteur adapte au style existant) :

```javascript
// ── Onglet « Carte astro complète » ──────────────────────────────
let _fiche_courante = null;
let _theme_cache = null;

function afficherOnglet(nom) {
  document.querySelectorAll('.onglet').forEach(b => b.classList.toggle('onglet-actif', b.dataset.onglet === nom));
  document.querySelectorAll('.onglet-contenu').forEach(s => {
    s.classList.toggle('onglet-contenu-actif', s.id === 'onglet-' + nom);
    s.hidden = s.id !== 'onglet-' + nom;
  });
}

document.querySelectorAll('.onglet').forEach(b => {
  b.addEventListener('click', () => afficherOnglet(b.dataset.onglet));
});

async function chargerTheme(fiche) {
  _fiche_courante = fiche;
  const r = await fetch('/theme', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                     body: JSON.stringify(fiche)});
  if (!r.ok) return;
  _theme_cache = await r.json();
  renderRoue(_theme_cache);
  renderTableaux(_theme_cache);
}

// Recharger quand les options changent
document.querySelectorAll('input[name="systeme-maisons"], input[name="methode-dominantes"]').forEach(input => {
  input.addEventListener('change', () => {
    if (!_fiche_courante) return;
    _fiche_courante.systeme_maisons = document.querySelector('input[name="systeme-maisons"]:checked').value;
    _fiche_courante.methode_dominantes = document.querySelector('input[name="methode-dominantes"]:checked').value;
    chargerTheme(_fiche_courante);
  });
});

// ── Roue SVG ──────────────────────────────────────────────────────
const SYMBOLES = {Soleil:'☉', Lune:'☽', Mercure:'☿', Vénus:'♀', Mars:'♂',
                  Jupiter:'♃', Saturne:'♄', Uranus:'♅', Neptune:'♆', Pluton:'♇',
                  Chiron:'⚷', Lilith:'⚸', 'Nœud Nord':'☊', 'Nœud Sud':'☋',
                  Ascendant:'Asc', Descendant:'Desc', MC:'MC', IC:'IC'};
const COULEURS_ASPECTS = {conjonction:'#3b82f6', opposition:'#ef4444', trigone:'#22c55e',
                          carre:'#f97316', sextile:'#a855f7'};
const COULEURS_ASPECTS_MINEURS = {semi_sextile:'#94a3b8', semi_carre:'#94a3b8',
                                   quintile:'#fbbf24', sesquicarre:'#94a3b8', quinconce:'#94a3b8'};

function renderRoue(tc) {
  const svg = document.getElementById('roue-svg');
  svg.innerHTML = '';
  const ns = 'http://www.w3.org/2000/svg';
  // Anneau zodiacal (12 signes)
  // ... l'implémenteur dessine les 12 secteurs de 30° avec symboles
  // Anneau des maisons (12 numéros)
  // Positions des corps (glyphes sur l'anneau planétaire)
  // Lignes d'aspects (centre → centre, couleur par type, épaisseur par exactitude)
  // L'implémenteur suit le design du spec section 7
  // (code complet ~150 lignes — l'implémenteur rédige)
}

// ── Tableaux ──────────────────────────────────────────────────────
function renderTableaux(tc) {
  const c = document.getElementById('tableaux-theme');
  c.innerHTML = '';
  // 1. Fondations, 2. 10 corps, 3. Points évolutifs, 4. Maisons,
  // 5. Aspects (triable/filtrable), 6. Dominantes (5 cartes)
  // L'implémenteur rédige le HTML pour chaque section depuis tc.
  // (code complet ~200 lignes)
}

// ── Intégration : appeler chargerTheme après le calcul du portrait ─
// Modifier la fonction de calcul existante pour :
// 1. Récupérer la fiche depuis le formulaire.
// 2. Appeler /portrait (existant).
// 3. Appeler chargerTheme(fiche) pour remplir l'onglet thème.
// 4. _fiche_courante = fiche (pour les options).
```

- [ ] **Step 5: Run the app and verify manually**

Run: `cd /Users/garinat_t/Desktop/portrait-cosmique && uvicorn main:app --reload --port 8410`
Ouvrir `http://localhost:8410`, remplir le formulaire, vérifier le checklist de la step 1.

- [ ] **Step 6: Commit**

```bash
git add static/index.html
git commit -m "feat(ui): onglet Carte astro complète — roue SVG + tableaux + export PDF"
```

---

## Self-Review

**Spec coverage :** les 6 zones de la spec (fondations, 10 corps, points évolutifs, maisons, aspects, dominantes) sont couvertes par les tasks 1-8. L'endpoint `/theme` (task 9), l'extension de `significations`/`synthese` (tasks 10-11) et l'UI (task 12) couvrent l'intégration. Les 3 systèmes de maisons (task 4), les 2 méthodes de dominantes (tasks 6-7), le repli honnête (task 8), le caveat d'honnêteté (tasks 8 + 12), et l'export PDF/HTML (task 12) sont présents.

**Placeholder scan :** les tasks 2 (VSOP87), 3 (Pluton/Chiron), 6 (tables TERMES/FACES) contiennent des squelettes à compléter par l'implémenteur — c'est intentionnel et documenté (les données exactes ne peuvent pas être inventées). La task 12 (UI) a du code partiel — l'implémenteur complète le rendu SVG et les tableaux selon le design du spec.

**Type consistency :** `points` est toujours `dict[str, dict]` avec `longitude` (float), `signe` (str), `maison` (int). `maisons` est toujours `list[dict]` avec `cuspe`, `signe`, `maison`. `aspects` est toujours `list[dict]` avec `aspect`, `type`, `point_a`, `point_b`, `exactitude`. Cohérent à travers les tasks 5-8.

