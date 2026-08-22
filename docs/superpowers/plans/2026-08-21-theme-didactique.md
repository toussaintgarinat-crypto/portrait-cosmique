# Onglet « Carte astro complète » — refonte didactique : Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformer le rendu de l'onglet « Carte astro complète » en cartes didactiques (§1/§2/§3) et tableaux à intros (§4/§5/§6), avec un fil rouge pédagogique, des légendes de chiffres, et la suppression de la légende PDF en bas.

**Architecture:** Nouvelle couche `DIDACTIQUE_FR/EN` dans `engine/significations.py` (21 entrées × 2 langues : question/domaines/conclusion), exposée via `/portrait`. Frontend `index.html` : nouveau helper `cartePoint()` remplace les lignes de tableau pour §1/§2/§3 ; §4/§5/§6 gardent leur tableau mais avec intro + légende chiffres. Bandeau fil rouge en tête d'onglet. Légende bas `r-legende` supprimée.

**Tech Stack:** Python 3 stdlib (engine), FastAPI (main.py), HTML/CSS/JS vanilla (static/index.html). Tests pytest.

## Global Constraints

- Lecture de DIVERTISSEMENT, ton « à lire comme » hérité du glossaire existant (`GLOSSAIRE_FR`/`GLOSSAIRE_EN`).
- Aucun recalcul astronomique : on réutilise `theme_complet` tel quel.
- Aucun nouvel id glossaire : les clés didactiques sont des ids **déjà existants** dans `GLOSSAIRE_FR`/`GLOSSAIRE_EN`.
- i18n FR/EN obligatoire — toute chaîne affichée existe dans `I18N.fr` ET `I18N.en`.
- Pas de lib externe nouvelle. Variables CSS existantes uniquement (`--accent`, `--accent2`, `--panel2`, `--border`, `--muted`, `--text`).
- Lancer les tests : `python -m pytest engine/ -q` depuis la racine du projet.
- Lancer l'app : `python main.py` (uvicorn) puis ouvrir `http://127.0.0.1:8000`.

## File Structure

- `engine/significations.py` — ajout `DIDACTIQUE_FR`, `DIDACTIQUE_EN`, `didactique()`.
- `engine/test_significations.py` — tests de la couche didactique.
- `engine/test_api_theme.py` — test que `/portrait` renvoie `didactique`.
- `main.py` — extension de l'endpoint `/portrait` (ligne ~138) pour renvoyer `didactique`.
- `static/index.html` — refonte `renderTableaux` (ligne ~1172), ajout `chargerDidactique`, `cartePoint`, bandeau fil rouge, CSS, suppression `r-legende` (lignes ~748-758), étendre `I18N.fr`/`I18N.en`.

---

### Task 1: Couche didactique FR + fonction `didactique()` + tests FR

**Files:**
- Modify: `engine/significations.py` (insérer après la fermeture de `GLOSSAIRE_FR`, avant `GLOSSAIRE_EN` ~ligne 521)
- Test: `engine/test_significations.py` (ajouter à la fin)

**Interfaces:**
- Produces: `significations.DIDACTIQUE_FR: dict[str, dict]`, `significations.didactique(langue="fr") -> dict`
- Une entrée = `{"question": str, "domaines": list[str], "conclusion": str}`

- [ ] **Step 1: Write the failing test**

Ajouter à la fin de `engine/test_significations.py` :

```python
# ── Couche didactique (cartes pédagogiques) ───────────────────────
_DIDACTIQUE_IDS_ATTENDUS = [
    "theme_fondation_soleil", "theme_fondation_lune",
    "theme_fondation_ascendant", "theme_fondation_descendant",
    "theme_fondation_milieu_du_ciel", "theme_fondation_fond_du_ciel",
    "theme_corps_soleil", "theme_corps_lune", "theme_corps_mercure",
    "theme_corps_vénus", "theme_corps_mars", "theme_corps_jupiter",
    "theme_corps_saturne", "theme_corps_uranus", "theme_corps_neptune",
    "theme_corps_pluton",
    "theme_point_noeud_nord", "theme_point_noeud_sud",
    "theme_point_chiron", "theme_point_lilith",
    "theme_maisons", "theme_aspects", "theme_dominantes",
]


def test_didactique_fr_structure():
    d = Z.didactique("fr")
    assert set(d.keys()) == set(_DIDACTIQUE_IDS_ATTENDUS), (
        f"manquent={set(_DIDACTIQUE_IDS_ATTENDUS)-set(d.keys())}, "
        f"en_trop={set(d.keys())-set(_DIDACTIQUE_IDS_ATTENDUS)}")
    for k, e in d.items():
        assert e.get("question"), f"{k} sans question"
        assert isinstance(e.get("domaines"), list) and len(e["domaines"]) >= 3, (
            f"{k} domaines invalides")
        assert e.get("conclusion"), f"{k} sans conclusion"


def test_didactique_ids_connus_du_glossaire():
    """Toute clé didactique existe dans GLOSSAIRE_FR (garde-fou doublon)."""
    for k in Z.DIDACTIQUE_FR:
        assert Z.GLOSSAIRE_FR.get(k), f"clé didactique inconnue du glossaire FR : {k}"


def test_didactique_distinction_soleil_lune_facettes():
    """Soleil/Lune ont 2 facettes distinctes (pilier vs corps)."""
    d = Z.didactique("fr")
    assert d["theme_fondation_soleil"]["conclusion"] != d["theme_corps_soleil"]["conclusion"]
    assert d["theme_fondation_lune"]["conclusion"] != d["theme_corps_lune"]["conclusion"]
    assert d["theme_fondation_soleil"]["question"] != d["theme_corps_soleil"]["question"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest engine/test_significations.py::test_didactique_fr_structure -q`
Expected: FAIL — `AttributeError: module 'significations' has no attribute 'didactique'`.

- [ ] **Step 3: Write minimal implementation — DIDACTIQUE_FR**

Insérer ce bloc dans `engine/significations.py` **juste après la fermeture de `GLOSSAIRE_FR`** (le dictionnaire `GLOSSAIRE_FR` se termine par `}` avant `GLOSSAIRE_EN` ~ligne 521) :

```python
# ══════════════════════════════════════════════════════════════════
# Couche didactique — cartes pédagogiques de l'onglet « Carte astro
# complète ». Chaque entrée = {question, domaines[], conclusion}.
# La clé est un id glossaire EXISTANT (pas de nouvel id) ; on l'enrichit
# d'une facette didactique. Soleil & Lune ont 2 facettes distinctes
# (pilier = theme_fondation_*, corps = theme_corps_*), ce qui rend la
# double présence §1/§2 explicite plutôt qu'un doublon.
# ══════════════════════════════════════════════════════════════════
DIDACTIQUE_FR = {
    # ── §1 Fondations (facette pilier) ──
    "theme_fondation_soleil": {
        "question": "Qui suis-je ?",
        "domaines": ["identité consciente", "volonté", "affirmation de soi",
                     "ce que tu cherches à devenir", "manière de rayonner"],
        "conclusion": "Soleil = ton centre",
    },
    "theme_fondation_lune": {
        "question": "De quoi ai-je besoin intérieurement ?",
        "domaines": ["émotions", "besoins affectifs", "sécurité",
                     "réactions instinctives", "monde intérieur",
                     "habitudes émotionnelles"],
        "conclusion": "Lune = ton monde intérieur",
    },
    "theme_fondation_ascendant": {
        "question": "Comment j'entre dans le monde ?",
        "domaines": ["première impression", "comportement spontané",
                     "manière d'aborder la vie", "façon dont tu te présentes",
                     "réflexes face au monde"],
        "conclusion": "Ascendant = ta porte d'entrée",
    },
    "theme_fondation_descendant": {
        "question": "Qui est l'autre ?",
        "domaines": ["couple", "partenaires", "associations",
                     "relations importantes",
                     "qualités recherchées chez l'autre"],
        "conclusion": "Ascendant = moi, Descendant = l'autre",
    },
    "theme_fondation_milieu_du_ciel": {
        "question": "Où vais-je dans le monde ?",
        "domaines": ["vocation", "carrière", "ambition", "réputation",
                     "réussite sociale", "contribution au monde"],
        "conclusion": "MC = ce que tu cherches à accomplir",
    },
    "theme_fondation_fond_du_ciel": {
        "question": "D'où est-ce que je viens ?",
        "domaines": ["racines", "famille", "enfance", "foyer",
                     "intimité", "sentiment d'appartenance", "monde privé"],
        "conclusion": "IC = tes racines, MC = ton accomplissement",
    },
    # ── §2 10 corps (facette corps) ──
    "theme_corps_soleil": {
        "question": "Comment je rayonne au quotidien ?",
        "domaines": ["vitalité", "identité consciente", "ce que tu exprimes"],
        "conclusion": "Soleil = ton noyau",
    },
    "theme_corps_lune": {
        "question": "Comment réagis-je instinctivement ?",
        "domaines": ["instincts", "réactions", "besoins immédiats"],
        "conclusion": "Lune = tes réflexes émotionnels",
    },
    "theme_corps_mercure": {
        "question": "Comment je pense ?",
        "domaines": ["pensée", "communication", "langage",
                     "raisonnement", "apprentissage",
                     "manière de traiter l'information"],
        "conclusion": "Mercure = ton fonctionnement mental",
    },
    "theme_corps_vénus": {
        "question": "Comment j'aime ?",
        "domaines": ["amour", "attraction", "relations", "plaisir",
                     "beauté", "valeurs", "rapport au confort"],
        "conclusion": "Vénus = ce qui t'attire",
    },
    "theme_corps_mars": {
        "question": "Comment j'agis ?",
        "domaines": ["action", "désir", "volonté", "énergie",
                     "affirmation", "confrontation"],
        "conclusion": "Mars = comment tu passes de l'intention à l'acte",
    },
    "theme_corps_jupiter": {
        "question": "Comment je grandis ?",
        "domaines": ["expansion", "confiance", "opportunités",
                     "philosophie", "connaissances", "transmission",
                     "recherche de sens"],
        "conclusion": "Jupiter = ce qui te permet de grandir",
    },
    "theme_corps_saturne": {
        "question": "Où dois-je apprendre la maîtrise ?",
        "domaines": ["responsabilités", "limites", "discipline",
                     "structure", "contraintes", "maturité",
                     "construction à long terme"],
        "conclusion": "Saturne = ta zone de maîtrise à construire",
    },
    "theme_corps_uranus": {
        "question": "Où ai-je besoin de liberté ?",
        "domaines": ["innovation", "indépendance", "rupture",
                     "changement", "originalité", "révolution"],
        "conclusion": "Uranus = où tu sors du cadre",
    },
    "theme_corps_neptune": {
        "question": "Où suis-je idéaliste ?",
        "domaines": ["imagination", "intuition", "rêves",
                     "spiritualité", "idéaux", "compassion",
                     "dissolution des frontières"],
        "conclusion": "Neptune = tes idéaux (et tes illusions)",
    },
    "theme_corps_pluton": {
        "question": "Où dois-je me transformer ?",
        "domaines": ["transformation profonde", "pouvoir", "crises",
                     "destruction/reconstruction", "obsessions", "renaissance"],
        "conclusion": "Pluton = ce qui meurt et renaît en toi",
    },
    # ── §3 Points évolutifs ──
    "theme_point_noeud_nord": {
        "question": "Vers quoi évoluer ?",
        "domaines": ["direction de vie", "évolution à intégrer",
                     "axe de croissance consciente"],
        "conclusion": "Nœud Nord = ce vers quoi évoluer",
    },
    "theme_point_noeud_sud": {
        "question": "Qu'est-ce qui est familier ?",
        "domaines": ["acquis karmique", "zone de confort",
                     "ce que tu maîtrises déjà"],
        "conclusion": "Nœud Sud = ce que tu maîtrises mais dois quitter",
    },
    "theme_point_chiron": {
        "question": "Quelle blessure peut devenir une force ?",
        "domaines": ["blessure profonde", "compréhension acquise",
                     "capacité de transmission"],
        "conclusion": "Chiron = vulnérabilité → compréhension → transmission",
    },
    "theme_point_lilith": {
        "question": "Où se trouve mon côté indomptable ?",
        "domaines": ["indépendance", "désir refoulé", "refus des normes",
                     "instinct sauvage", "ce qu'on ne veut pas soumettre"],
        "conclusion": "Lilith = ta part d'ombre libre",
    },
    # ── §4/§5/§6 Intros de section ──
    "theme_maisons": {
        "question": "Où se joue cette énergie ?",
        "domaines": ["douze secteurs de l'expérience de vie",
                     "1=identité, 4=foyer, 7=relations, 10=carrière"],
        "conclusion": "La planète dit QUOI, la maison dit OÙ",
    },
    "theme_aspects": {
        "question": "Comment les parties communiquent entre elles ?",
        "domaines": ["angles entre planètes", "harmonie (trigone, sextile)",
                     "tension (carré, opposition)", "fusion (conjonction)"],
        "conclusion": "Plus l'orbe est petit, plus l'aspect est exact",
    },
    "theme_dominantes": {
        "question": "Qu'est-ce qui ressort le plus du thème ?",
        "domaines": ["famille d'élément dominante", "style d'action (mode)",
                     "planète structurante", "signe récurrent",
                     "domaine de vie le plus actif"],
        "conclusion": "Les dominantes = la synthèse qui se dégage",
    },
}
```

- [ ] **Step 4: Add `didactique()` function**

Ajouter à la fin de `engine/significations.py` (après la fonction `glossaire()` ~ligne 893) :

```python
def didactique(langue: str = "fr") -> dict:
    """Couche didactique pour l'onglet « Carte astro complète ».

    Renvoie {id: {question, domaines, conclusion}}. Les ids sont stables
    (jamais traduits) et existent tous dans GLOSSAIRE_FR/GLOSSAIRE_EN.
    langue="fr" (défaut) ou "en". Retourne {} si la langue est absente
    (l'UI retombe sur le glossaire seul)."""
    table = DIDACTIQUE_EN if (langue or "fr").lower().startswith("en") else DIDACTIQUE_FR
    return {k: {"question": v["question"], "domaines": list(v["domaines"]),
                "conclusion": v["conclusion"]} for k, v in table.items()}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest engine/test_significations.py -q -k didactique`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add engine/significations.py engine/test_significations.py
git commit -m "feat(significations): couche didactique FR (21 entrees) + didactique()"
```

---

### Task 2: Couche didactique EN + test de parité

**Files:**
- Modify: `engine/significations.py` (insérer `DIDACTIQUE_EN` juste après `DIDACTIQUE_FR`)
- Test: `engine/test_significations.py`

**Interfaces:**
- Produces: `significations.DIDACTIQUE_EN: dict` (mêmes clés que `DIDACTIQUE_FR`)
- `didactique("en")` renvoie désormais les valeurs EN.

- [ ] **Step 1: Write the failing test**

Ajouter à la fin de `engine/test_significations.py` :

```python
def test_didactique_en_memes_cles_que_fr():
    fr = Z.didactique("fr")
    en = Z.didactique("en")
    assert set(fr.keys()) == set(en.keys()), (
        f"clés divergentes : {set(fr)^set(en)}")
    for k in en:
        e = en[k]
        assert e.get("question"), f"{k} EN sans question"
        assert isinstance(e.get("domaines"), list) and len(e["domaines"]) >= 3, (
            f"{k} EN domaines invalides")
        assert e.get("conclusion"), f"{k} EN sans conclusion"


def test_didactique_en_valeurs_differentes_de_fr():
    """Les valeurs EN sont bien traduites (pas un copier-coller)."""
    fr = Z.didactique("fr")
    en = Z.didactique("en")
    diff = [k for k in fr if fr[k]["question"] == en[k]["question"]]
    assert not diff, f"entrées EN non traduites : {diff[:3]}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest engine/test_significations.py::test_didactique_en_memes_cles_que_fr -q`
Expected: FAIL — `KeyError` ou `DIDACTIQUE_EN` absent (`didactique("en")` retourne `{}`).

- [ ] **Step 3: Write minimal implementation — DIDACTIQUE_EN**

Insérer ce bloc dans `engine/significations.py` **immédiatement après la fermeture de `DIDACTIQUE_FR`** :

```python
DIDACTIQUE_EN = {
    # ── §1 Foundations (pillar facet) ──
    "theme_fondation_soleil": {
        "question": "Who am I?",
        "domaines": ["conscious identity", "will", "self-assertion",
                     "what you strive to become", "how you shine"],
        "conclusion": "Sun = your core",
    },
    "theme_fondation_lune": {
        "question": "What do I need inwardly?",
        "domaines": ["emotions", "affective needs", "security",
                     "instinctive reactions", "inner world",
                     "emotional habits"],
        "conclusion": "Moon = your inner world",
    },
    "theme_fondation_ascendant": {
        "question": "How do I enter the world?",
        "domaines": ["first impression", "spontaneous behavior",
                     "way of approaching life", "how you present yourself",
                     "reflexes toward the world"],
        "conclusion": "Ascendant = your gateway",
    },
    "theme_fondation_descendant": {
        "question": "Who is the other?",
        "domaines": ["couple", "partners", "associations",
                     "significant relationships",
                     "qualities sought in the other"],
        "conclusion": "Ascendant = self, Descendant = the other",
    },
    "theme_fondation_milieu_du_ciel": {
        "question": "Where am I going in the world?",
        "domaines": ["vocation", "career", "ambition", "reputation",
                     "social success", "contribution to the world"],
        "conclusion": "MC = what you seek to accomplish",
    },
    "theme_fondation_fond_du_ciel": {
        "question": "Where do I come from?",
        "domaines": ["roots", "family", "childhood", "home",
                     "intimacy", "sense of belonging", "private world"],
        "conclusion": "IC = your roots, MC = your accomplishment",
    },
    # ── §2 Ten bodies (body facet) ──
    "theme_corps_soleil": {
        "question": "How do I shine day to day?",
        "domaines": ["vitality", "conscious identity", "what you express"],
        "conclusion": "Sun = your nucleus",
    },
    "theme_corps_lune": {
        "question": "How do I react instinctively?",
        "domaines": ["instincts", "reactions", "immediate needs"],
        "conclusion": "Moon = your emotional reflexes",
    },
    "theme_corps_mercure": {
        "question": "How do I think?",
        "domaines": ["thought", "communication", "language",
                     "reasoning", "learning", "how you process information"],
        "conclusion": "Mercury = your mental wiring",
    },
    "theme_corps_vénus": {
        "question": "How do I love?",
        "domaines": ["love", "attraction", "relationships", "pleasure",
                     "beauty", "values", "relationship to comfort"],
        "conclusion": "Venus = what draws you",
    },
    "theme_corps_mars": {
        "question": "How do I act?",
        "domaines": ["action", "desire", "will", "energy",
                     "assertion", "confrontation"],
        "conclusion": "Mars = how you turn intent into action",
    },
    "theme_corps_jupiter": {
        "question": "How do I grow?",
        "domaines": ["expansion", "confidence", "opportunities",
                     "philosophy", "knowledge", "transmission",
                     "search for meaning"],
        "conclusion": "Jupiter = what lets you grow",
    },
    "theme_corps_saturne": {
        "question": "Where must I learn mastery?",
        "domaines": ["responsibilities", "limits", "discipline",
                     "structure", "constraints", "maturity",
                     "long-term building"],
        "conclusion": "Saturn = your mastery zone to build",
    },
    "theme_corps_uranus": {
        "question": "Where do I need freedom?",
        "domaines": ["innovation", "independence", "rupture",
                     "change", "originality", "revolution"],
        "conclusion": "Uranus = where you break the mold",
    },
    "theme_corps_neptune": {
        "question": "Where am I idealistic?",
        "domaines": ["imagination", "intuition", "dreams",
                     "spirituality", "ideals", "compassion",
                     "dissolution of boundaries"],
        "conclusion": "Neptune = your ideals (and illusions)",
    },
    "theme_corps_pluton": {
        "question": "Where must I transform?",
        "domaines": ["deep transformation", "power", "crises",
                     "destruction/reconstruction", "obsessions", "rebirth"],
        "conclusion": "Pluto = what dies and is reborn in you",
    },
    # ── §3 Evolutionary points ──
    "theme_point_noeud_nord": {
        "question": "Toward what to evolve?",
        "domaines": ["life direction", "evolution to integrate",
                     "axis of conscious growth"],
        "conclusion": "North Node = what to evolve toward",
    },
    "theme_point_noeud_sud": {
        "question": "What is familiar?",
        "domaines": ["karmic acquisition", "comfort zone",
                     "what you already master"],
        "conclusion": "South Node = what you master but must leave",
    },
    "theme_point_chiron": {
        "question": "Which wound can become a strength?",
        "domaines": ["deep wound", "acquired understanding",
                     "capacity for transmission"],
        "conclusion": "Chiron = vulnerability → understanding → transmission",
    },
    "theme_point_lilith": {
        "question": "Where is my untamed side?",
        "domaines": ["independence", "repressed desire", "refusal of norms",
                     "wild instinct", "what you won't submit"],
        "conclusion": "Lilith = your free shadow",
    },
    # ── §4/§5/§6 Section intros ──
    "theme_maisons": {
        "question": "Where does this energy play out?",
        "domaines": ["twelve sectors of life experience",
                     "1=identity, 4=home, 7=relationships, 10=career"],
        "conclusion": "The planet says WHAT, the house says WHERE",
    },
    "theme_aspects": {
        "question": "How do the parts communicate?",
        "domaines": ["angles between planets", "harmony (trine, sextile)",
                     "tension (square, opposition)", "fusion (conjunction)"],
        "conclusion": "The smaller the orb, the more exact the aspect",
    },
    "theme_dominantes": {
        "question": "What stands out most in the chart?",
        "domaines": ["dominant element family", "action style (mode)",
                     "structuring planet", "recurring sign",
                     "most active life domain"],
        "conclusion": "The dominants = the synthesis that emerges",
    },
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest engine/test_significations.py -q -k didactique`
Expected: PASS (5 tests : 3 FR + 2 EN).

- [ ] **Step 5: Commit**

```bash
git add engine/significations.py engine/test_significations.py
git commit -m "feat(significations): couche didactique EN (parite FR/EN)"
```

---

### Task 3: Exposer `didactique` via l'endpoint `/portrait`

**Files:**
- Modify: `main.py:135-138` (fonction `portrait`)
- Test: `engine/test_api_theme.py` (ajouter un test)

**Interfaces:**
- Consumes: `significations.didactique(langue)`, `significations.SIGNES_SENS`/`SIGNES_SENS_EN`
- Produces: le payload `/portrait` contient deux nouvelles clés : `didactique: dict` et `signes_sens: dict` (signe→sens, pour affichage dans les cartes).

- [ ] **Step 1: Write the failing test**

Ajouter à la fin de `engine/test_api_theme.py` :

```python
def test_portrait_endpoint_renvoie_didactique_et_signes_sens():
    r = client.post("/portrait", json=_FICHE)
    assert r.status_code == 200
    data = r.json()
    assert "didactique" in data
    did = data["didactique"]
    assert isinstance(did, dict) and did, "didactique vide"
    assert "theme_fondation_soleil" in did
    e = did["theme_fondation_soleil"]
    assert e["question"] and e["conclusion"]
    assert isinstance(e["domaines"], list) and len(e["domaines"]) >= 3
    assert "signes_sens" in data
    ss = data["signes_sens"]
    assert isinstance(ss, dict) and "Bélier" in ss and ss["Bélier"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest engine/test_api_theme.py::test_portrait_endpoint_renvoie_didactique_et_signes_sens -q`
Expected: FAIL — `KeyError: 'didactique'`.

- [ ] **Step 3: Modify `main.py` portrait endpoint**

Dans `main.py`, remplacer le bloc `return {...}` de la fonction `portrait` (lignes 135-138) pour ajouter `didactique` et `signes_sens` :

```python
    en = (body.langue or "fr").lower().startswith("en")
    return {"traditions": trad, "theme_complet": tc,
            "portrait": p,
            "empreinte": significations.expliquer(trad, body.langue, theme_complet=tc),
            "glossaire": significations.glossaire(body.langue),
            "didactique": significations.didactique(body.langue),
            "signes_sens": (significations.SIGNES_SENS_EN if en
                            else significations.SIGNES_SENS)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest engine/test_api_theme.py -q`
Expected: PASS (tous les tests du fichier, y compris le nouveau).

- [ ] **Step 5: Commit**

```bash
git add main.py engine/test_api_theme.py
git commit -m "feat(api): /portrait renvoie didactique + signes_sens"
```

---

### Task 4: Frontend — infra (chargerDidactique, fil rouge, CSS, helpers)

**Files:**
- Modify: `static/index.html` (plusieurs zones)

**Interfaces:**
- Produces: globals JS `DIDACTIQUE`, fonctions `chargerDidactique()`, `cartePoint()`, `sectionIntro()`, `legendeChiffres()` ; éléments HTML `#fil-rouge` ; classes CSS `.fil-rouge`, `.carte-point`, `.cp-*`, `.section-intro`, `.legende-chiffres` ; clés i18n `fil_rouge`, `dans_ton_theme`, `donc`, `leg_*`.

- [ ] **Step 1: Add i18n keys**

Dans `static/index.html`, dans l'objet `I18N.fr` (vers la ligne 415, après `ts_dominantes`), ajouter :

```js
    fil_rouge: "Planète = quoi · Signe = comment · Maison = où · Aspect = comment ça interagit",
    dans_ton_theme: "Dans ton thème",
    donc: "Donc",
    leg_degre: "Degré = position dans le signe (0-29.99°)",
    leg_maison_num: "Maison = secteur de vie (1-12)",
    leg_vitesse: "Vitesse = déplacement/jour (°/j)",
    leg_retro: "℞ = rétrograde (mouvement apparent inverse)",
    leg_orbe: "Orbe = écart à l'angle exact (plus petit = plus puissant)",
    leg_exact: "Exactitude = proximité au parfait (0-100%)",
    leg_score: "Score = poids selon la méthode choisie",
```

Dans l'objet `I18N.en` (vers la ligne 470, après `ts_dominantes`), ajouter les équivalents :

```js
    fil_rouge: "Planet = what · Sign = how · House = where · Aspect = how they interact",
    dans_ton_theme: "In your chart",
    donc: "So",
    leg_degre: "Degree = position in sign (0-29.99°)",
    leg_maison_num: "House = life sector (1-12)",
    leg_vitesse: "Speed = movement/day (°/d)",
    leg_retro: "℞ = retrograde (apparent reverse motion)",
    leg_orbe: "Orb = gap to exact angle (smaller = stronger)",
    leg_exact: "Exactness = closeness to perfect (0-100%)",
    leg_score: "Score = weight per chosen method",
```

- [ ] **Step 2: Add `DIDACTIQUE` global + `chargerDidactique`**

Dans `static/index.html`, juste après `let GLOSSAIRE_LABELS = {};` (ligne ~485), ajouter :

```js
let DIDACTIQUE = {};          // { id: {question, domaines, conclusion} } — aplati, alimenté par /portrait
let SIGNES_SENS = {};         // { signe: sens } — alimenté par /portrait

function chargerDidactique(d) {
  DIDACTIQUE = (d && typeof d === "object") ? d : {};
}

function chargerSignesSens(d) {
  SIGNES_SENS = (d && typeof d === "object") ? d : {};
}
```

- [ ] **Step 3: Call `chargerDidactique` and `chargerSignesSens` in `afficherResultat`**

Dans la fonction `afficherResultat` (ligne ~710), juste après `chargerGlossaire(d.glossaire);`, ajouter :

```js
  chargerDidactique(d.didactique);
  chargerSignesSens(d.signes_sens);
```

- [ ] **Step 4: Add fil rouge element in HTML**

Dans `static/index.html`, dans `<section id="onglet-theme">` (ligne ~332), ajouter juste après la balise ouvrante `<section ...>` (avant `<div class="theme-options">`) :

```html
      <div class="fil-rouge" data-t="fil_rouge">Planète = quoi · Signe = comment · Maison = où · Aspect = comment ça interagit</div>
```

- [ ] **Step 5: Add CSS classes**

Dans `static/index.html`, dans le bloc `<style>` (après `.dominante-barre .dv { ... }` ~ligne 202), ajouter :

```css
  .fil-rouge {
    background: var(--panel2); border: 1px solid var(--accent);
    border-radius: 10px; padding: .6rem .9rem; margin-bottom: 1rem;
    font-size: .82rem; color: var(--accent2); text-align: center;
  }
  .section-intro {
    background: var(--panel2); border-left: 3px solid var(--accent);
    border-radius: 0 8px 8px 0; padding: .7rem .9rem; margin: .3rem 0 1rem;
    font-size: .85rem; line-height: 1.55; color: var(--text);
  }
  .section-intro .si-q { font-weight: 600; color: var(--accent2); }
  .section-intro .si-domaines { color: var(--muted); margin: .3rem 0; }
  .section-intro .si-conclusion { font-style: italic; color: var(--accent2); }
  .legende-chiffres {
    font-size: .76rem; color: var(--muted); margin: .4rem 0 1.2rem;
    border-top: 1px dashed var(--border); padding-top: .4rem;
  }
  .cartes-grille {
    display: grid; gap: .8rem; margin: .3rem 0 1.2rem;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  }
  .carte-point {
    background: var(--panel2); border: 1px solid var(--border);
    border-radius: 10px; padding: .7rem .85rem;
  }
  .carte-point .cp-tete { display: flex; align-items: baseline; gap: .4rem; flex-wrap: wrap; }
  .carte-point .cp-sym { font-size: 1.3rem; color: var(--accent2); }
  .carte-point .cp-nom { font-weight: 700; }
  .carte-point .cp-q { color: var(--muted); font-size: .82rem; font-style: italic; }
  .carte-point .cp-domaines {
    margin: .4rem 0; padding-left: 1.1rem; font-size: .8rem; color: var(--muted);
  }
  .carte-point .cp-domaines li { margin: .1rem 0; }
  .carte-point .cp-valeur { font-size: .85rem; margin: .3rem 0; }
  .carte-point .cp-sens { color: var(--muted); font-size: .78rem; margin-top: .15rem; }
  .carte-point .cp-conclusion {
    margin-top: .4rem; font-size: .8rem; color: var(--accent2);
    border-top: 1px dashed var(--border); padding-top: .3rem;
  }
  @media print {
    .cartes-grille { grid-template-columns: 1fr; }
  }
```

- [ ] **Step 6: Add helpers `cartePoint`, `sectionIntro`, `legendeChiffres`**

Dans `static/index.html`, juste avant la fonction `renderTableaux` (ligne ~1172), ajouter :

```js
function cartePoint(symbole, nom, gid, valeur) {
  const t = I18N[LANGUE];
  const d = DIDACTIQUE[gid] || {};
  const domaines = (d.domaines || []).map(x => `<li>${x}</li>`).join("");
  const parts = [];
  if (valeur.signe) parts.push(`<strong>${valeur.signe}</strong>`);
  if (valeur.degre != null) parts.push(fmtDeg(valeur.degre));
  if (valeur.maison) parts.push(`${t.th_maison} ${valeur.maison}`);
  if (valeur.retro) parts.push("℞");
  const sens = valeur.sens_signe ? `<div class="cp-sens">${valeur.sens_signe}</div>` : "";
  const valeurHtml = parts.length
    ? `<div class="cp-valeur">${t.dans_ton_theme} : ${parts.join(" · ")}</div>${sens}` : "";
  const conclusion = d.conclusion
    ? `<div class="cp-conclusion">${t.donc} : ${d.conclusion}</div>` : "";
  return `<div class="carte-point">
    <div class="cp-tete"><span class="cp-sym">${symbole || ""}</span>
      <span class="cp-nom">${nom}</span>${icGlossaire(gid)}
      ${d.question ? `<span class="cp-q">« ${d.question} »</span>` : ""}</div>
    ${domaines ? `<ul class="cp-domaines">${domaines}</ul>` : ""}
    ${valeurHtml}${conclusion}
  </div>`;
}

function sectionIntro(gid) {
  const t = I18N[LANGUE];
  const d = DIDACTIQUE[gid] || {};
  if (!d.question && !d.conclusion) return "";
  const domaines = (d.domaines || []).join(" · ");
  return `<div class="section-intro">${icGlossaire(gid)}
    ${d.question ? `<div class="si-q">« ${d.question} »</div>` : ""}
    ${domaines ? `<div class="si-domaines">${domaines}</div>` : ""}
    ${d.conclusion ? `<div class="si-conclusion">${d.conclusion}</div>` : ""}</div>`;
}

function legendeChiffres(html) {
  const t = I18N[LANGUE];
  return `<div class="legende-chiffres">${html}</div>`;
}
```

- [ ] **Step 7: Verify no regression (smoke)**

Run: `python main.py` puis ouvrir `http://127.0.0.1:8000`, calculer un portrait, aller dans l'onglet « Carte astro complète ».
Expected: le bandeau fil rouge s'affiche en haut de l'onglet ; les tableaux sont inchangés (les helpers ne sont pas encore branchés). Aucune erreur console.

- [ ] **Step 8: Commit**

```bash
git add static/index.html
git commit -m "feat(ui): infra didactique (fil rouge, CSS, helpers cartePoint/sectionIntro)"
```

---

### Task 5: §1 Fondations en cartes didactiques

**Files:**
- Modify: `static/index.html` (bloc « 1. Fondations » de `renderTableaux`, lignes ~1181-1197)

**Interfaces:**
- Consumes: `DIDACTIQUE`, `SIGNES_SENS`, `cartePoint()`, `_FONDATIONS_ORDRE`, `_FONDATIONS_MAISON`, `tc.fondations`, `tc.dix_corps`, `tc.maisons`.

- [ ] **Step 1: Replace the fondations table by a cards grid**

Dans `static/index.html`, dans `renderTableaux`, remplacer le bloc commenté `// 1. Fondations` (lignes ~1181-1197) par :

```js
  // 1. Fondations (cartes didactiques)
  const fond = tc.fondations || {};
  const dixMap = tc.dix_corps || {};
  c.insertAdjacentHTML("beforeend", sectionH(t.ts_fondations));
  const fondCards = _FONDATIONS_ORDRE.map(o => {
    const f = fond[o.key] || {};
    let maison = _FONDATIONS_MAISON[o.key];
    if (!maison) {
      const src = o.key === "soleil" ? dixMap["Soleil"] : (o.key === "lune" ? dixMap["Lune"] : null);
      maison = src ? src.maison : null;
    }
    return cartePoint(f.symbole || "—", o.nom, o.gid, {
      signe: f.signe, degre: f.degre, maison: maison,
      retro: (o.key === "soleil" ? (dixMap["Soleil"] || {}).retrograde
              : o.key === "lune" ? (dixMap["Lune"] || {}).retrograde : false),
      sens_signe: SIGNES_SENS[f.signe] || "",
    });
  }).join("");
  c.insertAdjacentHTML("beforeend", `<div class="cartes-grille">${fondCards}</div>`);
  c.insertAdjacentHTML("beforeend", legendeChiffres(
    `${t.leg_degre} · ${t.leg_maison_num}${t.leg_retro ? " · " + t.leg_retro : ""}`));
```

- [ ] **Step 2: Verify §1 renders as cards**

Run: `python main.py`, calculer un portrait, onglet « Carte astro complète ».
Expected: §1 affiche 6 cartes (Soleil, Lune, ASC, DSC, MC, IC), chacune avec question, puces, valeur du thème (signe + degré + maison + sens), conclusion. Soleil en §1 porte la facette *pilier* (« Qui suis-je ? »).

- [ ] **Step 3: Commit**

```bash
git add static/index.html
git commit -m "feat(ui): §1 fondations en cartes didactiques"
```

---

### Task 6: §2 10 corps + §3 Points évolutifs en cartes

**Files:**
- Modify: `static/index.html` (blocs « 2. 10 corps » ~lignes 1199-1208 et « 3. Points évolutifs » ~lignes 1210-1219)

**Interfaces:**
- Consumes: `cartePoint()`, `_CORPS_GLOSS`, `_POINTS_GLOSS`, `SYMBOLES_POINTS`, `SIGNES_SENS`, `tc.dix_corps`, `tc.points_evolutifs`.

- [ ] **Step 1: Replace the « 10 corps » table by cards**

Dans `renderTableaux`, remplacer le bloc `// 2. 10 corps` (lignes ~1199-1208) par :

```js
  // 2. 10 corps (cartes didactiques, facette corps)
  const dix = Object.entries(dixMap).map(([nom, p]) => ({
    corps: nom, gid: _CORPS_GLOSS[nom], symbole: SYMBOLES_POINTS[nom] || "",
    signe: p.signe, degre: p.degre, maison: p.maison,
    retro: p.retrograde,
  }));
  c.insertAdjacentHTML("beforeend", sectionH(t.ts_corps));
  const dixCards = dix.map(r => cartePoint(r.symbole, r.corps, r.gid, {
    signe: r.signe, degre: r.degre, maison: r.maison, retro: r.retro,
    sens_signe: SIGNES_SENS[r.signe] || "",
  })).join("");
  c.insertAdjacentHTML("beforeend", `<div class="cartes-grille">${dixCards}</div>`);
  c.insertAdjacentHTML("beforeend", legendeChiffres(
    `${t.leg_degre} · ${t.leg_maison_num} · ${t.leg_vitesse} · ${t.leg_retro}`));
```

Note : `vitesse` n'est plus affichée en colonne (supprimée du rendu carte) mais reste expliquée dans la légende des chiffres pour ne pas perdre l'information. Si tu veux la conserver visuellement, ajoute-la dans `valeur` passé à `cartePoint` — mais le format didactique privilégie signe/maison/rétro. Conforme à la spec (YAGNI sur la vitesse affichée).

- [ ] **Step 2: Replace the « Points évolutifs » table by cards**

Dans `renderTableaux`, remplacer le bloc `// 3. Points évolutifs` (lignes ~1210-1219) par :

```js
  // 3. Points évolutifs (cartes didactiques)
  const pe = Object.entries(tc.points_evolutifs || {}).map(([nom, p]) => ({
    point: p.corps || nom, gid: _POINTS_GLOSS[nom],
    symbole: SYMBOLES_POINTS[p.corps || nom] || "",
    signe: p.signe, degre: p.degre, maison: p.maison, retro: p.retrograde,
  }));
  c.insertAdjacentHTML("beforeend", sectionH(t.ts_points));
  const peCards = pe.map(r => cartePoint(r.symbole, r.point, r.gid, {
    signe: r.signe, degre: r.degre, maison: r.maison, retro: r.retro,
    sens_signe: SIGNES_SENS[r.signe] || "",
  })).join("");
  c.insertAdjacentHTML("beforeend", `<div class="cartes-grille">${peCards}</div>`);
  c.insertAdjacentHTML("beforeend", legendeChiffres(
    `${t.leg_degre} · ${t.leg_maison_num}${t.leg_retro ? " · " + t.leg_retro : ""}`));
```

- [ ] **Step 3: Verify §2 and §3 render as cards**

Run: `python main.py`, recalculer, onglet « Carte astro complète ».
Expected: §2 affiche 10 cartes (Soleil→Pluton). Soleil en §2 porte la facette *corps* (« Comment je rayonne au quotidien ? »), **distincte** de sa facette pilier en §1. §3 affiche 4 cartes (Nœud Nord, Nœud Sud, Chiron, Lilith).

- [ ] **Step 4: Commit**

```bash
git add static/index.html
git commit -m "feat(ui): §2 10 corps + §3 points évolutifs en cartes didactiques"
```

---

### Task 7: §4/§5/§6 intros + légendes de chiffres + suppression légende bas

**Files:**
- Modify: `static/index.html` (blocs §4 ~1221-1227, §5 ~1229-1249, §6 ~1259-1286 ; bloc `r-legende` ~748-758)

**Interfaces:**
- Consumes: `sectionIntro()`, `legendeChiffres()`, `DIDACTIQUE` (`theme_maisons`, `theme_aspects`, `theme_dominantes`).

- [ ] **Step 1: Add intro + légende to §4 Maisons**

Dans `renderTableaux`, remplacer le bloc `// 4. Maisons` (lignes ~1221-1227) par :

```js
  // 4. Maisons (tableau + intro didactique)
  c.insertAdjacentHTML("beforeend", sectionH(t.ts_maisons, "theme_maisons"));
  c.insertAdjacentHTML("beforeend", sectionIntro("theme_maisons"));
  const mais = (tc.maisons || []).map(m => ({ n: m.maison, cuspe: m.cuspe, signe: m.signe, symbole: m.symbole }));
  c.insertAdjacentHTML("beforeend", tableHTML(t.t_maisons,
    [t.th_n, t.th_cuspe, t.th_signe, t.th_symbole],
    mais.map(r => `<tr><td class="num">${r.n}</td><td class="num">${fmtDeg(r.cuspe)}</td><td>${r.signe}</td><td>${r.symbole || ""}</td></tr>`),
    false));
  c.insertAdjacentHTML("beforeend", legendeChiffres(
    `${t.leg_maison_num} · ${t.leg_degre}`));
```

- [ ] **Step 2: Add intro + légende to §5 Aspects**

Dans `renderTableaux`, repérer le bloc `// 5. Aspects` (lignes ~1229-1257). **Conserver** la logique de filtre/tri intacte. Ajouter l'intro après la ligne `c.insertAdjacentHTML("beforeend", sectionH(t.ts_aspects, "theme_aspects"));` :

```js
  c.insertAdjacentHTML("beforeend", sectionIntro("theme_aspects"));
```

Et juste **avant** `c.appendChild(aspContainer);` (qui clôt le bloc aspects), ajouter la légende des chiffres :

```js
  c.insertAdjacentHTML("beforeend", legendeChiffres(
    `${t.leg_orbe} · ${t.leg_exact}`));
```

(Si l'ordre visuel préfère la légende avant le tableau, l'insérer avant `aspContainer.innerHTML = ...`. Les deux sont acceptables ; on la met avant `aspContainer` pour la lisibilité.)

- [ ] **Step 3: Add intro + légende to §6 Dominantes**

Dans `renderTableaux`, repérer le bloc `// 6. Dominantes` (lignes ~1259-1286). Après la ligne `c.insertAdjacentHTML("beforeend", sectionH(t.ts_dominantes));`, ajouter :

```js
  c.insertAdjacentHTML("beforeend", sectionIntro("theme_dominantes"));
```

Et juste **avant** `c.appendChild(domCont);`, ajouter :

```js
  c.insertAdjacentHTML("beforeend", legendeChiffres(t.leg_score));
```

- [ ] **Step 4: Remove the bottom PDF legend (`r-legende`)**

Dans `static/index.html`, dans la fonction `afficherResultat`, **supprimer** le bloc qui crée/remplit `r-legende` (lignes ~747-758) :

```js
  // Légende PDF (cachée à l'écran, révélée à l'impression)
  let leg = document.getElementById("r-legende");
  if (!leg) {
    leg = document.createElement("section");
    leg.id = "r-legende";
    leg.className = "legende";
    document.getElementById("resultat").appendChild(leg);
  }
  leg.innerHTML = (d.glossaire || []).map(g => `
    <h3>${g.theme}</h3>
    <dl>${(g.items || []).map(it => `<dt>${it.label}</dt><dd>${it.definition}</dd>`).join("")}</dl>
  `).join("");
```

Supprimer ce bloc entier. Les définitions sont désormais en clair dans les cartes/intros.

- [ ] **Step 5: Remove the `.legende` CSS rule (if orphan)**

Rechercher une règle `.legende { ... }` dans le `<style>` de `static/index.html`. Si elle existe et n'est plus référencée nulle part, la supprimer. (Optionnel — laisser une règle morte ne casse rien ; on la supprime pour propreté.)

- [ ] **Step 6: Full verification**

Run: `python main.py`, calculer un portrait, onglet « Carte astro complète » + test impression (Cmd+P / aperçu PDF).

Checklist d'acceptation :
1. Les 6 sections sont visuellement séparées, chacune avec son enseignement.
2. §1/§2/§3 = cartes didactiques (question → domaines → valeur thème → conclusion).
3. Soleil/Lune distincts en §1 (pilier) vs §2 (corps).
4. §4/§5/§6 ont une intro didactique + une légende des chiffres.
5. Bandeau fil rouge affiché en tête d'onglet.
6. La légende PDF en bas est **absente** (plus de `#r-legende`).
7. `SIGNES_SENS` alimente le sens du signe dans chaque carte.
8. Tests backend verts.

Run: `python -m pytest engine/ -q`
Expected: PASS (tous les tests).

- [ ] **Step 7: Commit**

```bash
git add static/index.html
git commit -m "feat(ui): intros §4/§5/§6 + legendes chiffres + suppression legende bas"
```

---

## Self-Review (post-écriture)

**Spéc coverage :** chaque exigence de la spec est couverte —
- P1 (sections didactiques) → Tasks 4-7.
- P2 (doublon légende bas) → Task 7 Step 4.
- P3 (Soleil/Lune distinction) → Task 1 (facettes distinctes) + Task 5/6 (rendu distinct).
- P4 (légendes chiffres) → Tasks 5/6/7 (`legendeChiffres`).
- P5 (fil rouge) → Task 4 Step 4.
- Critères d'acceptation 1-8 → Task 7 Step 6.

**Placeholder scan :** aucun TBD/TODO. Tout le code (FR 21 entrées, EN 21 entrées, helpers, rendu) est complet.

**Type consistency :** `cartePoint(symbole, nom, gid, valeur)` cohérent entre Task 4 (définition) et Tasks 5/6 (appels). `sectionIntro(gid)` et `legendeChiffres(html)` cohérents. `DIDACTIQUE`/`SIGNES_SENS` chargés dans Task 4, consommés Tasks 5-7.

## Execution Handoff

Plan complet, sauvegardé dans `docs/superpowers/plans/2026-08-21-theme-didactique.md`. Deux options d'exécution :

1. **Subagent-Driven (recommandé)** — je dispatche un subagent frais par tâche, revue entre tâches, itération rapide.
2. **Inline Execution** — exécution des tâches dans cette session via executing-plans, avec points de contrôle.

Quelle approche ?
