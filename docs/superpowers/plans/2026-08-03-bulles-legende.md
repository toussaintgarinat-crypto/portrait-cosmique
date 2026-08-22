# Bulles interactives + légende PDF — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter des bulles interactives (ℹ️) sur les titres du portrait (empreinte, stats, archétype/forces/faiblesse/pierre) avec un glossaire bilingue côté Python ; l'export HTML reste interactif hors-ligne ; le PDF imprime une légende thématisée en fin de document.

**Architecture:** Glossaire FR/EN dans `engine/significations.py` + fonction `glossaire(langue)` renvoyant la légende groupée par thèmes. L'API `/portrait` embarque ce glossaire + un `id` stable sur chaque entrée de l'empreinte. Le front `static/index.html` monte des tooltips (délégation d'événements, survol/clic/clavier) + une `<section class="legende">` cachée à l'écran, révélée en `@media print`. L'export HTML sérialise le glossaire inline + le script tooltip (auto-contenu).

**Tech Stack:** Python (FastAPI, pydantic), pytest ; HTML/CSS/vanilla JS (single file `static/index.html`).

## Global Constraints

- Bilingue FR/EN : tout texte utilisateur existe en deux versions alignées (les ids restent identiques).
- Ton du glossaire : lecture symbolique de divertissement (aligné sur `SIGNES_SENS` etc.).
- Aucune dépendance externe ajoutée (vanilla JS, pas de lib tooltip).
- L'export HTML doit fonctionner **hors-ligne** (pas de `fetch`, glossaire sérialisé inline).
- Repli silencieux : si `glossaire` est absent d'une réponse API, pas d'icône, pas de légende — rien ne casse.
- Les tests Python se lancent depuis `engine/` : `cd engine && python -m pytest -q` (les imports sont `import significations`, `import traditions`).

---

## File Structure

- **Modify** `engine/significations.py` — ajouter `GLOSSAIRE_FR`, `GLOSSAIRE_EN`, `_GLOSSAIRE_THEMES` (ordre des thèmes + ids par thème), `_GLOSSAIRE_LABELS` (labels FR/EN par id), `_GLOSSAIRE_LABELS_EN`, et la fonction `glossaire(langue)`. Étendre `expliquer()` pour poser un champ `id` stable sur chaque entrée.
- **Modify** `main.py` — `/portrait` renvoie en plus `glossaire` (résultat de `significations.glossaire(body.langue)`).
- **Modify** `static/index.html` — CSS tooltip + légende ; JS : construction de `GLOSSAIRE`, injection des icônes ℹ️ au rendu, délégué d'événements tooltip, bloc légende, export HTML embarquant glossaire + script.
- **Modify** `engine/test_significations.py` — tests du glossaire (structure, complétude, ids stables dans `expliquer`).

---

### Task 1: Glossaire FR/EN + fonction `glossaire()` + ids sur `expliquer()`

**Files:**
- Modify: `engine/significations.py`
- Test: `engine/test_significations.py`

**Interfaces:**
- Produces:
  - `significations.GLOSSAIRE_FR`, `significations.GLOSSAIRE_EN` — `dict[str, str]` (id → définition 3-5 phrases).
  - `significations.glossaire(langue: str = "fr") -> list[dict]` — renvoie `[{"theme": str, "items": [{"id": str, "label": str, "definition": str}, ...]}, ...]`.
  - `significations.expliquer(trad, langue)` — chaque entrée gagne un champ `id` (stable, `'soleil'`, `'lune'`, …, `'stat_*'` non inclus car les stats ne viennent pas de `expliquer`).

- [ ] **Step 1: Write failing tests in `engine/test_significations.py`**

Append at end of file:

```python
# ── Glossaire (bulles + légende PDF) ───────────────────────────────
def test_glossaire_fr_structure():
    g = Z.glossaire("fr")
    assert [t["theme"] for t in g] == [
        "Astrologie occidentale", "Astrologie chinoise", "Astrologie védique",
        "Autres traditions", "Numérologie",
        "Statistiques de personnalité", "Synthèse du portrait",
    ]
    ids = {it["id"] for t in g for it in t["items"]}
    assert {"soleil", "lune", "ascendant", "chinoise", "animal_heure",
            "vedique", "nakshatra", "egypte", "celte", "totem", "maya",
            "chemin_de_vie", "expression", "archetype", "forces",
            "faiblesse", "pierre"} <= ids
    assert {"stat_charisme", "stat_combativite", "stat_sagesse",
            "stat_creativite", "stat_discretion", "stat_stabilite",
            "stat_emotivite", "stat_energie"} <= ids
    for t in g:
        for it in t["items"]:
            assert it["label"] and it["definition"], f"entrée glossaire incomplète : {it}"


def test_glossaire_en_memes_ids_memes_themes():
    """Mêmes ids, mêmes thèmes (en anglais), que en français."""
    fr = Z.glossaire("fr")
    en = Z.glossaire("en")
    fr_ids = {it["id"] for t in fr for it in t["items"]}
    en_ids = {it["id"] for t in en for it in t["items"]}
    assert fr_ids == en_ids
    assert [t["theme"] for t in en] != [t["theme"] for t in fr]  # thèmes traduits
    for t in en:
        for it in t["items"]:
            assert it["label"] and it["definition"], f"entrée EN incomplète : {it}"


def test_glossaire_completude_ids_dans_tables():
    """Chaque id du glossaire existe dans GLOSSAIRE_FR et GLOSSAIRE_EN."""
    ids_TH = set(Z._GLOSSAIRE_THEMES_IDS)  # union des ids par thème
    for i in ids_TH:
        assert Z.GLOSSAIRE_FR.get(i), f"id sans définition FR : {i}"
        assert Z.GLOSSAIRE_EN.get(i), f"id sans définition EN : {i}"


def test_expliquer_empreinte_possede_ids_stables():
    """Chaque entrée de l'empreinte porte un `id` stable connu du glossaire."""
    trad = _fiche_complete()
    emp = Z.expliquer(trad, "fr")
    ids_connus = {it["id"] for t in Z.glossaire("fr") for it in t["items"]}
    for e in emp:
        assert e.get("id") and e["id"] in ids_connus, f"entrée sans id stable : {e}"
    cles_vers_ids = {e["cle"]: e["id"] for e in emp}
    assert cles_vers_ids["Soleil"] == "soleil"
    assert cles_vers_ids["Lune"] == "lune"
    assert cles_vers_ids["Ascendant"] == "ascendant"
```

Fix typo in test name (will rename below):

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd engine && python -m pytest test_significations.py -k "glossaire or ids_stables" -v`
Expected: FAIL (import errors / `AttributeError: module 'significations' has no attribute 'glossaire'`).

Note: the test file imports `significations as Z` and `traditions as T` (already present at top of file), so no new imports needed.

- [ ] **Step 3: Add `GLOSSAIRE_FR` to `engine/significations.py`**

Insert after the `NOMBRE_SENS` block (after line 179, before the i18n comment block starting at line 182). Use exactly this content (no typos):

```python
# ══════════════════════════════════════════════════════════════════
# Glossaire — bulles interactives + légende PDF (FR). Chaque id est
# stable (jamais traduit) ; son libellé (`label`) suit la langue via
# `_GLOSSAIRE_LABELS`/`_GLOSSAIRE_LABELS_EN`. Définitions : lecture
# symbolique de divertissement, 3-5 phrases.
# ══════════════════════════════════════════════════════════════════
GLOSSAIRE_FR = {
    "soleil": (
        "Soleil — signe zodiacal où se trouvait le Soleil à ta naissance. "
        "Cœur de la personnalité, identité consciente, ce que tu rayonnes au quotidien. "
        "Tradition occidentale classique ; il marque l'ego, l'essentiel de soi. "
        "À lire comme le fil conducteur du portrait : tout le reste colorie autour."
    ),
    "lune": (
        "Lune — signe traversé par la Lune à ta naissance. Gouverne les émotions, "
        "le jardin secret, les instincts et les besoins de sécurité. Tradition "
        "occidentale ; seconde signature du thème après le Soleil. À lire comme ton "
        "visage intime, rarement montré en société."
    ),
    "ascendant": (
        "Ascendant — signe se levant à l'horizon Est au moment exact de ta naissance. "
        "Apparence, premier contact, masque social, comment on te perçoit avant de te "
        "connaître. Dépend de l'heure (à la minute près). À lire comme la vitrine "
        "que le Soleil habille derrière."
    ),
    "chinoise": (
        "Astrologie chinoise — animal annuel (cycle de 12) et élément (Bois, Feu, "
        "Terre, Métal, Eau). Dépeint le moi social, l'archétype collectif qu'on "
        "incarne dans sa génération. Tradition millénaire vivante. À lire comme la "
        "couleur d'une époque plus que d'une individualité."
    ),
    "animal_heure": (
        "Animal de l'heure — deuxième animal chinois, fixé par l'heure de naissance "
        "(deux heures par animal dans le cycle de 12). Représente le moi profond et "
        "inconscient, souvent ignoré mais réapparaissant dans les choix intimes. À "
        "lire comme un ascendant chinois ; nécessite l'heure exacte."
    ),
    "vedique": (
        "Védique (rashi) — signe sidéral du Soleil selon l'astrologie indienne "
        "(Jyotish). Mesuré avec la précession des équinoxes, donc souvent décalé "
        "d'un signe par rapport au zodiaque occidental. Reflète la lecture karmique. "
        "Tradition sanskrite vivante. À lire comme un Soleil lu sans le filtre "
        "occidental."
    ),
    "nakshatra": (
        "Nakshatra — maison lunaire (27 au total) où se trouvait la Lune à ta "
        "naissance. Lecture védique fine : psychologie profonde, karma, traits "
        "karmiques potentiels. Chaque nakshatra est divisé en 4 padas (quarts). "
        "Tradition Jyotish. À lire comme une radiographie lunaire plus fine qu'un "
        "signe lunaire occidental."
    ),
    "egypte": (
        "Égypte — divinité tutélaire calculée selon le calendrier égyptien antique. "
        "Archétype divin qui protège et guide. Tradition dérivée du calendrier de "
        "l'Égypte pharaonique. À lire comme un masque sacré qui synthétise des "
        "traits déjà présents dans le reste du portrait."
    ),
    "celte": (
        "Celte — arbre protecteur selon le calendrier oghamique des druides. Chaque "
        "jour de l'année est régi par un arbre porteur d'une vertu. Tradition "
        "gauloise reconstructive. À lire comme ton ancrage saisonnier, une racine "
        "de plus dans le portrait."
    ),
    "totem": (
        "Totem amérindien — animal totem selon la medicine wheel, calée sur les "
        "mois du zodiaque occidental. Énergie animale qui t'accompagne. Tradition "
        "des Premières Nations d'Amérique du Nord. À lire comme une guidance "
        "instinctive plus proche de la nature."
    ),
    "maya": (
        "Maya (Tzolkin) — glyphe (20 au total) et tonalité (1-13) du jour dans le "
        "calendrier sacré Tzolkin. Combinaison unique tous les 260 jours. Représente "
        "l'énergie du jour où tu es venu au monde. Tradition mésoaméricaine. À lire "
        "comme la signature énergétique du calendrier maya."
    ),
    "chemin_de_vie": (
        "Chemin de vie — nombre réduit de ta date de naissance (somme des chiffres). "
        "Pilier numérologique : mission, leçon majeure, direction de vie. Numérologie "
        "occidentale classique. À lire comme le fil rouge de ta destinée numérique."
    ),
    "expression": (
        "Expression (nom) — somme numérologique des lettres du nom complet. Reflète "
        "talents naturels, tempérament, savoir-faire, ce que tu exprimes. "
        "Numérologie occidentale. À lire comme le complément du chemin de vie, au "
        "niveau des capacités plutôt que du but."
    ),
    "archetype": (
        "Archétype — synthèse narrative du portrait, agrège toutes les traditions "
        "calculées (soleil, lune, ascendant, chinoise, védique, nakshatra, égypte, "
        "celte, totem, maya, chemin de vie, expression). Résume à une figure "
        "archétypale mémorable. À lire comme la légende du portrait, pas une "
        "prédiction."
    ),
    "forces": (
        "Forces dominantes — 3 traits statistiquement les plus élevés parmi les "
        "statistiques de personnalité (Charisme, Combativité, Sagesse, Créativité, "
        "Discrétion, Stabilité, Émotivité, Énergie), agrégées depuis toutes les "
        "traditions. À lire comme tes atouts saillants."
    ),
    "faiblesse": (
        "Point à travailler — trait statistique le plus bas parmi les stats. Pas "
        "une fatalité mais un axe de vigilance. À lire comme un miroir, pas un "
        "verdict."
    ),
    "pierre": (
        "Pierre d'équilibrage — gemme compensatoire choisie selon le point à "
        "travailler. Lecture symbolique de gemmologie traditionnelle, pas "
        "minéralogique. À lire comme un talisman illustratif."
    ),
    "stat_charisme": (
        "Charisme — magnétisme personnel, capacité à rayonner et à fédérer. "
        "Nourri surtout par le Soleil, le Dragon chinois et les divinités solaires "
        "(Amon-Rê, Horus). À lire comme ton magnétisme naturel, utile en "
        "leadership et prise de parole publique."
    ),
    "stat_combativite": (
        "Combativité — ardeur à défendre ses idées, ténacité face à l'adversité. "
        "Nourri par Bélier, Aries, Mars, Seth, le Tigre. À lire comme ton "
        "réservoir d'opiniâtreté."
    ),
    "stat_sagesse": (
        "Sagesse — profondeur de réflexion, intuition posée, sens de la "
        "mesure. Nourrie par Thot, Osiris, le Serpent, les nakshatras "
        "calmes (Pushya, Shravana). À lire comme ta voix tranquille."
    ),
    "stat_creativite": (
        "Créativité — imagination, expressivité, capacité à inventer. Nourrie "
        "par Bastet, Chuen (Maya Singe), le Loutre, la Chèvre. À lire comme ton "
        "jaillissement inventif."
    ),
    "stat_discretion": (
        "Discrétion — réserve, capacité à se faire oublier, élégance du silence. "
        "Nourrie par Anubis, le Scorpion, le Hibou, Ashlesha. À lire comme ton "
        "art de l'effacement volontaire."
    ),
    "stat_stabilite": (
        "Stabilité — ancrage, constance, résistance aux tempêtes émotionnelles. "
        "Nourrie par Geb, le Taureau, le Chêne, le Buffle. À lire comme ta "
        "racine tranquille."
    ),
    "stat_emotivite": (
        "Émotivité — intensité du ressenti, sensibilité aux climats intérieurs "
        "et extérieurs. Nourrie par la Lune, Cancer, le Saule, Muluc. À lire "
        "comme ton paysage intérieur."
    ),
"stat_energie": (
        "Énergie — vitalité, capacité d'action, drive physique. Nourrie par Mars, "
        "le Cheval, le Sagittaire, Imix. À lire comme ton carburant "
        "motivationnel."
    ),
}
```

- [ ] **Step 4: Add `GLOSSAIRE_EN` (same ids, English text) after `GLOSSAIRE_FR`**

```python
GLOSSAIRE_EN = {
    "soleil": (
        "Sun — zodiac sign the Sun was in at your birth. Core of the personality, "
        "conscious identity, what you radiate day to day. Classical Western "
        "tradition; marks the ego, the essence of self. Read as the throughline "
        "of the portrait: everything else colors around it."
    ),
    "lune": (
        "Moon — sign the Moon was passing through at your birth. Governs emotions, "
        "the secret garden, instincts and security needs. Western tradition; "
        "second signature of the chart after the Sun. Read as your intimate face, "
        "rarely shown in public."
    ),
    "ascendant": (
        "Ascendant — sign rising on the eastern horizon at the exact moment of "
        "your birth. Appearance, first impression, social mask, how you are "
        "perceived before being known. Depends on birth time (to the minute). Read "
        "as the storefront that the Sun dresses behind."
    ),
    "chinoise": (
        "Chinese astrology — yearly animal (12-cycle) and element (Wood, Fire, "
        "Earth, Metal, Water). Depicts the social self, the collective archetype "
        "embodied by your generation. Ancient living tradition. Read as the color "
        "of an era rather than of an individual."
    ),
    "animal_heure": (
        "Hour animal — second Chinese animal, fixed by birth time (two hours per "
        "animal in the 12-cycle). Represents the deep and unconscious self, often "
        "ignored but resurfacing in private choices. Read as a Chinese ascendant; "
        "requires exact birth time."
    ),
    "vedique": (
        "Vedic (rashi) — sidereal sign of the Sun according to Indian astrology "
        "(Jyotish). Measured with precession of the equinoxes, so often shifted "
        "by one sign from the Western zodiac. Reflects karmic reading. Living "
        "Sanskritic tradition. Read as a Sun read without the Western frame."
    ),
    "nakshatra": (
        "Nakshatra — lunar mansion (27 in total) where the Moon was at your "
        "birth. Fine Vedic reading: deep psychology, karma, potential traits. "
        "Each nakshatra is divided into 4 padas (quarters). Jyotish tradition. "
        "Read as a finer lunar X-ray than a Western lunar sign."
    ),
    "egypte": (
        "Egyptian — tutelary deity calculated from the ancient Egyptian calendar. "
        "Divine archetype that protects and guides. Tradition derived from "
        "pharaonic Egypt's calendar. Read as a sacred mask that synthesizes "
        "traits already present in the rest of the portrait."
    ),
    "celte": (
        "Celtic — protective tree according to the druids' oghamic calendar. "
        "Each day of the year is ruled by a tree carrying a virtue. Reconstructive "
        "Gaulish tradition. Read as your seasonal grounding, one more root in "
        "the portrait."
    ),
    "totem": (
        "Native American totem — totem animal according to the medicine wheel, "
        "aligned with the Western zodiac months. Animal energy that accompanies "
        "you. Tradition of the First Nations of North America. Read as instinctive "
        "guidance closer to nature."
    ),
    "maya": (
        "Maya (Tzolkin) — glyph (20 in total) and tone (1-13) of the day in the "
        "sacred Tzolkin calendar. Unique combination every 260 days. Represents "
        "the energy of the day you came into the world. Mesoamerican tradition. "
        "Read as the calendrical energy signature of the Maya."
    ),
    "chemin_de_vie": (
        "Life path — number reduced from your birth date (sum of the digits). "
        "Numerological pillar: mission, major lesson, life direction. Classical "
        "Western numerology. Read as the red thread of your numerical destiny."
    ),
    "expression": (
        "Expression (name) — numerological sum of the letters of the full name. "
        "Reflects natural talents, temperament, know-how, what you express. "
        "Western numerology. Read as the complement to the life path, at the "
        "level of capacities rather than purpose."
    ),
    "archetype": (
        "Archetype — narrative synthesis of the portrait; aggregates all the "
        "calculated traditions (sun, moon, ascendant, Chinese, Vedic, nakshatra, "
        "Egyptian, Celtic, totem, Maya, life path, expression). Summarizes to a "
        "memorable archetypal figure. Read as the legend of the portrait, not a "
        "prediction."
    ),
    "forces": (
        "Dominant strengths — 3 statistically highest traits among the personality "
        "stats (Charisma, Combativeness, Wisdom, Creativity, Discretion, "
        "Stability, Emotionality, Energy), aggregated from all traditions. Read "
        "as your salient assets."
    ),
    "faiblesse": (
        "Point to work on — lowest statistical trait among the stats. Not a fate "
        "but an axis of vigilance. Read as a mirror, not a verdict."
    ),
    "pierre": (
        "Balancing stone — compensatory gem chosen according to the point to "
        "work on. Symbolic reading of traditional gemology, not mineralogical. "
        "Read as an illustrative talisman."
    ),
    "stat_charisme": (
        "Charisma — personal magnetism, capacity to radiate and gather. Fed "
        "chiefly by the Sun, the Chinese Dragon and the solar deities (Amun-Ra, "
        "Horus). Read as your natural magnetism, useful in leadership and public "
        "speaking."
    ),
    "stat_combativite": (
        "Combativeness — fire to defend your ideas, tenacity against adversity. "
        "Fed by Aries, Mars, Set, the Tiger. Read as your reservoir of "
        "doggedness."
    ),
    "stat_sagesse": (
        "Wisdom — depth of reflection, poised intuition, sense of measure. Fed "
        "by Thoth, Osiris, the Snake, the calm nakshatras (Pushya, Shravana). "
        "Read as your quiet voice."
    ),
    "stat_creativite": (
        "Creativity — imagination, expressiveness, capacity to invent. Fed by "
        "Bastet, Chuen (Maya Monkey), Otter, Goat. Read as your inventive "
        "spring."
    ),
    "stat_discretion": (
        "Discretion — reserve, capacity to be overlooked, elegance of silence. "
        "Fed by Anubis, Scorpio, Owl, Ashlesha. Read as your art of voluntary "
        "withdrawal."
    ),
    "stat_stabilite": (
        "Stability — grounding, constance, resistance to emotional storms. Fed "
        "by Geb, Taurus, Oak, Ox. Read as your quiet root."
    ),
    "stat_emotivite": (
        "Emotionality — intensity of feeling, sensitivity to inner and outer "
        "climates. Fed by the Moon, Cancer, Willow, Muluc. Read as your inner "
        "landscape."
    ),
    "stat_energie": (
        "Energy — vitality, capacity for action, physical drive. Fed by Mars, "
        "Horse, Sagittarius, Imix. Read as your motivational fuel."
    ),
}
```

- [ ] **Step 5: Add label tables + theme table + `glossaire()` function**

Insert after `GLOSSAIRE_EN`:

```python
# Libellés (labels) FR/EN par id — ce que le front affiche comme titre court.
_GLOSSAIRE_LABELS = {
    "soleil": "Soleil", "lune": "Lune", "ascendant": "Ascendant",
    "chinoise": "Astrologie chinoise", "animal_heure": "Animal de l'heure",
    "vedique": "Védique (rashi)", "nakshatra": "Nakshatra", "egypte": "Égypte",
    "celte": "Celte", "totem": "Totem amérindien", "maya": "Maya (Tzolkin)",
    "chemin_de_vie": "Chemin de vie", "expression": "Expression (nom)",
    "archetype": "Archétype", "forces": "Forces dominantes",
    "faiblesse": "Point à travailler", "pierre": "Pierre d'équilibrage",
    "stat_charisme": "Charisme", "stat_combativite": "Combativité",
    "stat_sagesse": "Sagesse", "stat_creativite": "Créativité",
    "stat_discretion": "Discrétion", "stat_stabilite": "Stabilité",
    "stat_emotivite": "Émotivité", "stat_energie": "Énergie",
}
_GLOSSAIRE_LABELS_EN = {
    "soleil": "Sun", "lune": "Moon", "ascendant": "Ascendant",
    "chinoise": "Chinese Astrology", "animal_heure": "Hour Animal",
    "vedique": "Vedic (Rashi)", "nakshatra": "Nakshatra", "egypte": "Egyptian",
    "celte": "Celtic", "totem": "Native American Totem", "maya": "Maya (Tzolkin)",
    "chemin_de_vie": "Life Path", "expression": "Expression (Name)",
    "archetype": "Archetype", "forces": "Dominant Strengths",
    "faiblesse": "Point to Work On", "pierre": "Balancing Stone",
    "stat_charisme": "Charisma", "stat_combativite": "Combativeness",
    "stat_sagesse": "Wisdom", "stat_creativite": "Creativity",
    "stat_discretion": "Discretion", "stat_stabilite": "Stability",
    "stat_emotivite": "Emotionality", "stat_energie": "Energy",
}

# Thèmes (ordre de la légende) — couples (label_fr, label_en, [ids]).
_GLOSSAIRE_THEMES = [
    ("Astrologie occidentale", "Western Astrology",
        ["soleil", "lune", "ascendant"]),
    ("Astrologie chinoise", "Chinese Astrology",
        ["chinoise", "animal_heure"]),
    ("Astrologie védique", "Vedic Astrology",
        ["vedique", "nakshatra"]),
    ("Autres traditions", "Other Traditions",
        ["egypte", "celte", "totem", "maya"]),
    ("Numérologie", "Numerology",
        ["chemin_de_vie", "expression"]),
    ("Statistiques de personnalité", "Personality Stats",
        ["stat_charisme", "stat_combativite", "stat_sagesse", "stat_creativite",
         "stat_discretion", "stat_stabilite", "stat_emotivite", "stat_energie"]),
    ("Synthèse du portrait", "Portrait Synthesis",
        ["archetype", "forces", "faiblesse", "pierre"]),
]
_GLOSSAIRE_THEMES_IDS = [i for *_, lst in _GLOSSAIRE_THEMES for i in lst]


def glossaire(langue: str = "fr") -> list:
    """Légende lisible groupée par thèmes, pour la fin du document PDF.

    Renvoie : [{"theme": str, "items": [{"id": str, "label": str, "definition": str}]}].
    `langue="fr"` (défaut) ou `"en"`. Les ids sont stables, jamais traduits."""
    en = (langue or "fr").lower().startswith("en")
    labels = _GLOSSAIRE_LABELS_EN if en else _GLOSSAIRE_LABELS
    table = GLOSSAIRE_EN if en else GLOSSAIRE_FR
    out = []
    for theme_fr, theme_en, ids in _GLOSSAIRE_THEMES:
        out.append({
            "theme": theme_en if en else theme_fr,
            "items": [{"id": i, "label": labels[i],
                       "definition": table[i]} for i in ids],
        })
    return out
```

- [ ] **Step 6: Extend `expliquer()` to add stable `id` to each entry**

The `_entree` helper and each `out.append(...)` call need an id. Modify `_entree` first (around line 396-397):

```python
def _entree(cle: str, valeur: str, sens: str, role: str = "", id: str = "") -> dict:
    return {"cle": cle, "valeur": valeur, "sens": sens, "role": role, "id": id}
```

Then add the `id` argument to each `out.append(_entree(...))` call inside `expliquer()` (lines 433-483). The mapping is:

| Section | id |
|---|---|
| Soleil | `"soleil"` |
| Lune | `"lune"` |
| Ascendant | `"ascendant"` |
| Astrologie chinoise | `"chinoise"` |
| Animal de l'heure | `"animal_heure"` |
| Védique (rashi) | `"vedique"` |
| Nakshatra | `"nakshatra"` |
| Égypte | `"egypte"` |
| Celte | `"celte"` |
| Totem amérindien | `"totem"` |
| Maya (Tzolkin) | `"maya"` |
| Chemin de vie | `"chemin_de_vie"` |
| Expression (nom) | `"expression"` |

Example (Soleil):

```python
    if sol.get("nom"):
        out.append(_entree(cle("Soleil"), f"{nom(sol['nom'])} {sol.get('symbole','')}".strip(),
                            signes_sens.get(sol["nom"], ""), role_placement["soleil"], id="soleil"))
```

Apply the same pattern to all 13 `out.append(_entree(...))` calls.

- [ ] **Step 7: Run the new tests**

Run: `cd engine && python -m pytest test_significations.py -k "glossaire or ids_stables" -v`
Expected: ALL PASS.

- [ ] **Step 8: Run the full engine test suite to check for regressions**

Run: `cd engine && python -m pytest -q`
Expected: ALL PASS (existing tests untouched; new `id` field is additive).

- [ ] **Step 9: Commit**

```bash
git add engine/significations.py engine/test_significations.py
git commit -m "feat: glossaire FR/EN + ids stables sur l'empreinte"
```

---

### Task 2: API renvoie `glossaire`

**Files:**
- Modify: `main.py:111-119`

**Interfaces:**
- Consumes: `significations.glossaire(langue)` from Task 1.
- Produces: `/portrait` response now includes `glossaire` (list of theme groups). Existing fields unchanged.

- [ ] **Step 1: Write a manual API smoke check (no test framework for main.py)**

There is no `test_main.py` in this repo; the existing API is exercised via the engine tests + manual `curl`. Add a quick shell-based verification step below instead of a unit test (consistent with the repo's existing practice).

- [ ] **Step 2: Modify `/portrait` in `main.py`**

Replace lines 111-119:

```python
    trad = traditions.calculer(body.model_dump())
    if not trad.get("signe_solaire"):
        raise HTTPException(422, "Indique au moins une date de naissance valide.")
    p = synthese.portrait(trad, nom=body.prenoms or body.nom, langue=body.langue)
    return {"traditions": trad, "portrait": p,
            "empreinte": significations.expliquer(trad, body.langue)}
```

with:

```python
    trad = traditions.calculer(body.model_dump())
    if not trad.get("signe_solaire"):
        raise HTTPException(422, "Indique au moins une date de naissance valide.")
    p = synthese.portrait(trad, nom=body.prenoms or body.nom, langue=body.langue)
    return {"traditions": trad, "portrait": p,
            "empreinte": significations.expliquer(trad, body.langue),
            "glossaire": significations.glossaire(body.langue)}
```

- [ ] **Step 3: Smoke-test the running server**

In one terminal:
```bash
uvicorn main:app --port 8410 &
```
In another:
```bash
curl -s -X POST http://localhost:8410/portrait \
  -H 'Content-Type: application/json' \
  -d '{"prenoms":"Aria","nom":"Solis","date_naissance":"1990-09-05"}' \
  | python -c "import json,sys; d=json.load(sys.stdin); print('themes:', [t['theme'] for t in d['glossaire']]); print('empreinte[0]:', d['empreinte'][0])"
```
Expected: themes list has 7 entries including "Astrologie occidentale"; `empreinte[0]` has an `id` field (e.g. `"soleil"`).

Stop the server: `pkill -f uvicorn`.

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: /portrait renvoie le glossaire (bulles + légende)"
```

---

### Task 3: Front — CSS tooltip + légende, JS glossaire + injection d'icônes

**Files:**
- Modify: `static/index.html`

**Interfaces:**
- Consumes: `d.glossaire` (from `/portrait` response), `d.empreinte[*].id` (stables).
- Produces: visible ℹ️ icons on titles, working tooltip (hover/click/keyboard), print-only legend.

This is a large task but a single cohesive front-end change. It is broken into many bite-sized steps.

- [ ] **Step 1: Add tooltip + legend CSS**

Inside the existing `<style>` block (after the `@media print { ... }` rule, around line 84), add:

```css
  /* Tooltip glossaire (écran uniquement) */
  .glossaire-ic {
    display: inline-block; margin-left: .3rem; cursor: help; font-size: .72rem;
    color: var(--accent); opacity: .7; vertical-align: middle; user-select: none;
    border: 1px solid var(--border); border-radius: 999px; padding: 0 .32rem;
    line-height: 1.5; transition: opacity .12s, background .12s;
  }
  .glossaire-ic:hover, .glossaire-ic:focus-visible, .glossaire-ic.on {
    opacity: 1; background: #2a2350; outline: none;
  }
  .glossaire-pop {
    position: fixed; z-index: 999; max-width: 320px; min-width: 200px;
    background: var(--panel2); border: 1px solid var(--accent); color: var(--text);
    padding: 12px 14px; border-radius: 10px; font-size: .84rem; line-height: 1.5;
    box-shadow: 0 8px 24px #0008; opacity: 0; transform: translateY(4px);
    transition: opacity .12s, transform .12s; pointer-events: none;
  }
  .glossaire-pop.open { opacity: 1; transform: translateY(0); }
  .glossaire-pop::before {
    content: ""; position: absolute; top: -5px; left: 16px; width: 10px; height: 10px;
    background: var(--panel2); border-left: 1px solid var(--accent);
    border-top: 1px solid var(--accent); transform: rotate(45deg);
  }
  .glossaire-pop .g-titre { font-weight: 600; color: var(--accent2);
    display: block; margin-bottom: 4px; }

  /* Légende : cachée à l'écran, révélée à l'impression */
  .legende { display: none; }
  .legende h3 { margin: 18px 0 6px; font-size: .98rem; color: var(--accent2);
    border-bottom: 1px solid var(--border); padding-bottom: 4px; }
  .legende dl { margin: 4px 0 10px; }
  .legende dt { font-weight: 600; margin-top: 8px; }
  .legende dd { margin: 2px 0 8px 0; color: var(--muted); font-size: .86rem;
    line-height: 1.5; }

  @media print {
    .glossaire-ic, .glossaire-pop { display: none !important; }
    .legende { display: block; }
    .legende dd { color: #333; }
  }
```

Note: the existing `@media print { ... }` block must remain ABOVE this addition, or the `.legende { display: block }` rule will conflict with the existing `header .langs, form, ... { display: none !important; }`. Since `.legende` isn't in that `none` list, they don't actually conflict — but place this new block AFTER the existing print block so the print reveal of `.legende` wins if any specificity question arises.

- [ ] **Step 2: Add a tooltip container element in the DOM**

Right before the closing `</div>` of `.wrap` (between `</footer>` and the wrap-close on current line 201), insert:

```html
  <div id="glossaire-pop" class="glossaire-pop" role="tooltip" aria-hidden="true"></div>
```

Final shape of that area:

```html
  <footer class="mentions" data-t="mentions">Lecture symbolique — divertissement, pas un fait. Aucune donnée n'est conservée par ce service.</footer>
  <div id="glossaire-pop" class="glossaire-pop" role="tooltip" aria-hidden="true"></div>
</div>
```

- [ ] **Step 3: Add JS state + GLOSSAIRE builder**

In the `<script>` block, after the `let DERNIER_RESULTAT = null;` line (around line 276), add:

```js
let GLOSSAIRE = {};          // { id: definition } — aplati, alimenté par /portrait
let GLOSSAIRE_LABELS = {};   // { id: label } — utilisé par la légende et le tooltip titre

function chargerGlossaire(groups) {
  GLOSSAIRE = {};
  GLOSSAIRE_LABELS = {};
  if (!Array.isArray(groups)) return;
  for (const grp of groups) {
    for (const it of (grp.items || [])) {
      GLOSSAIRE[it.id] = it.definition;
      GLOSSAIRE_LABELS[it.id] = it.label;
    }
  }
}

function icGlossaire(id) {
  if (!id || !GLOSSAIRE[id]) return "";
  return ` <span class="glossaire-ic" data-glossaire="${id}" role="button"
    tabindex="0" aria-label="Définition : ${GLOSSAIRE_LABELS[id] || id}">ℹ️</span>`;
}
```

- [ ] **Step 4: Call `chargerGlossaire` from `afficherResultat`**

In `afficherResultat(d)` (around line 469), call it first thing:

```js
function afficherResultat(d) {
  const t = I18N[LANGUE];
  const p = d.portrait;
  chargerGlossaire(d.glossaire);
  document.getElementById("r-archetype").textContent = p.archetype;
  // ... reste inchangé ...
}
```

- [ ] **Step 5: Inject ℹ️ on the empreinte**

Replace the existing empreinte render (around line 483-488):

```js
  document.getElementById("r-empreinte").innerHTML = d.empreinte.map(e => `
    <div class="empreinte-item">
      <div class="cle">${e.cle}${e.role ? " · " + e.role : ""}${icGlossaire(e.id)}</div>
      <div class="valeur">${e.valeur}</div>
      <div class="sens">${e.sens}</div>
    </div>`).join("");
```

- [ ] **Step 6: Inject ℹ️ on stats**

Replace the existing stats render (lines 475-479):

```js
const STAT_VERS_ID = {
  "Charisme": "stat_charisme", "Combativité": "stat_combativite",
  "Sagesse": "stat_sagesse", "Créativité": "stat_creativite",
  "Discrétion": "stat_discretion", "Stabilité": "stat_stabilite",
  "Émotivité": "stat_emotivite", "Énergie": "stat_energie",
  "Charisma": "stat_charisme", "Combativeness": "stat_combativite",
  "Wisdom": "stat_sagesse", "Creativity": "stat_creativite",
  "Discretion": "stat_discretion", "Stability": "stat_stabilite",
  "Emotionality": "stat_emotivite", "Energy": "stat_energie",
};
// ... plus loin, dans afficherResultat :
  document.getElementById("r-stats").innerHTML = Object.entries(stats)
    .sort((a,b) => b[1]-a[1])
    .map(([k,v]) => `<div class="stat-row"><div class="lab">${k}${icGlossaire(STAT_VERS_ID[k] || "")}</div>
      <div class="bar-bg"><div class="bar-fg" style="width:${v}%"></div></div>
      <div class="val">${v}</div></div>`).join("");
```

Place the `STAT_VERS_ID` const at top-level inside the `<script>` (after the `I18N` const, for instance).

- [ ] **Step 7: Inject ℹ️ on the sous-ligne archétype/forces/faiblesse/pierre**

Replace the existing `r-souscritre` render (lines 480-482):

```js
  document.getElementById("r-souscritre").innerHTML =
    `${t.forces_titre} : ${p.forces.join(", ")}${icGlossaire("forces")}` +
    ` · ${t.faiblesse_titre} : ${p.faiblesse}${icGlossaire("faiblesse")}` +
    ` <span class="badge">${t.pierre_titre} : ${p.pierre_equilibrage.pierre}${icGlossaire("pierre")}</span>`;
```

Also add an ℹ️ on the archétype itself — modify the archetype render (around line 472):

```js
  document.getElementById("r-archetype").innerHTML =
    `${p.archetype}${icGlossaire("archetype")}`;
```

(Note: the original used `.textContent`; switching to `.innerHTML` is safe because `archetype` comes from the deterministic Python engine, never user input.)

- [ ] **Step 8: Add the tooltip event delegation system**

Append at the very end of the `<script>` block (after `telechargerHTML`):

```js
// ── Tooltip tooltip universel (délégation) ────────────────────────
(function () {
  const pop = document.getElementById("glossaire-pop");
  let courant = null;

  function ouvrir(ic) {
    if (!ic) return;
    const id = ic.getAttribute("data-glossaire");
    if (!id || !GLOSSAIRE[id]) return;
    pop.innerHTML = `<span class="g-titre">${GLOSSAIRE_LABELS[id] || id}</span>${GLOSSAIRE[id]}`;
    pop.classList.add("open");
    pop.setAttribute("aria-hidden", "false");
    // clamp à la fenêtre
    const r = ic.getBoundingClientRect();
    const x = Math.min(r.left, window.innerWidth - pop.offsetWidth - 12);
    let y = r.bottom + 8;
    if (y + pop.offsetHeight > window.innerHeight - 12) y = r.top - pop.offsetHeight - 8;
    pop.style.left = `${Math.max(12, x)}px`;
    pop.style.top = `${Math.max(12, y)}px`;
    courant = ic;
    ic.classList.add("on");
  }

  function fermer() {
    pop.classList.remove("open");
    pop.setAttribute("aria-hidden", "true");
    if (courant) { courant.classList.remove("on"); courant = null; }
  }

  function isIc(node) {
    return node && node.closest && node.closest(".glossaire-ic");
  }

  document.addEventListener("mouseover", (e) => { if (isIc(e.target)) ouvrir(isIc(e.target)); });
  document.addEventListener("mouseout", (e) => {
    const from = isIc(e.relatedTarget);
    if (!from && isIc(e.target) === courant) fermer();
  });
  document.addEventListener("click", (e) => {
    const ic = isIc(e.target);
    if (ic) { if (courant === ic) fermer(); else { fermer(); ouvrir(ic); } e.stopPropagation(); }
    else if (courant) fermer();
  });
  document.addEventListener("keydown", (e) => {
    const ic = isIc(e.target);
    if (ic && (e.key === "Enter" || e.key === " ")) { e.preventDefault();
      if (courant === ic) fermer(); else { fermer(); ouvrir(ic); } }
    if (e.key === "Escape" && courant) fermer();
  });
  document.addEventListener("focusin", (e) => { const ic = isIc(e.target); if (ic) ouvrir(ic); });
  document.addEventListener("focusout", (e) => {
    if (isIc(e.relatedTarget)) return;
    fermer();
  });
  window.addEventListener("scroll", fermer, { passive: true });
  window.addEventListener("resize", fermer, { passive: true });
})();
```

- [ ] **Step 9: Render the legend `<section>` at the end of `#resultat`**

In `afficherResultat(d)`, after `document.getElementById("r-recit").innerHTML = ...` (around line 489), add:

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

The legend is now part of `#resultat`'s innerHTML/DOM, so the existing `telechargerHTML()` (which clones `#resultat.outerHTML`) already captures it.

- [ ] **Step 10: Make `telechargerHTML()` embed the glossaire + tooltip script**

The current `telechargerHTML()` (lines 561-571) only includes `<style>` and the `#resultat` panel. The exported file has no JS, so tooltips wouldn't work offline. Rewrite it to also embed the current GLOSSAIRE and a copy of the tooltip delegation script:

```js
function telechargerHTML() {
  const panneau = document.getElementById("resultat").outerHTML;
  const styles = document.querySelector("style").outerHTML;
  const glossaireSer = JSON.stringify({GLOSSAIRE, GLOSSAIRE_LABELS});
  const ttScript = `
<script>
'use strict';
let GLOSSAIRE = ${JSON.stringify(GLOSSAIRE)};
let GLOSSAIRE_LABELS = ${JSON.stringify(GLOSSAIRE_LABELS)};
(function () {
  const pop = document.getElementById("glossaire-pop");
  let courant = null;
  function ouvrir(ic) {
    const id = ic.getAttribute("data-glossaire");
    if (!id || !GLOSSAIRE[id]) return;
    pop.innerHTML = '<span class="g-titre">' + (GLOSSAIRE_LABELS[id] || id) + '</span>' + GLOSSAIRE[id];
    pop.classList.add('open'); pop.setAttribute('aria-hidden','false');
    const r = ic.getBoundingClientRect();
    const x = Math.min(r.left, window.innerWidth - pop.offsetWidth - 12);
    let y = r.bottom + 8;
    if (y + pop.offsetHeight > window.innerHeight - 12) y = r.top - pop.offsetHeight - 8;
    pop.style.left = Math.max(12, x) + 'px';
    pop.style.top = Math.max(12, y) + 'px';
    courant = ic; ic.classList.add('on');
  }
  function fermer() {
    pop.classList.remove('open'); pop.setAttribute('aria-hidden','true');
    if (courant) { courant.classList.remove('on'); courant = null; }
  }
  function ic(node){ return node && node.closest && node.closest('.glossaire-ic'); }
  document.addEventListener('mouseover', e => { const x=ic(e.target); if(x) ouvrir(x); });
  document.addEventListener('mouseout', e => { if(!ic(e.relatedTarget) && ic(e.target)===courant) fermer(); });
  document.addEventListener('click', e => { const x=ic(e.target); if(x){ if(courant===x) fermer(); else { fermer(); ouvrir(x);} e.stopPropagation(); } else if(courant) fermer(); });
  document.addEventListener('keydown', e => { const x=ic(e.target); if(x && (e.key==='Enter'||e.key===' ')){ e.preventDefault(); if(courant===x) fermer(); else { fermer(); ouvrir(x);} } if(e.key==='Escape'&&courant) fermer(); });
  document.addEventListener('focusin', e => { const x=ic(e.target); if(x) ouvrir(x); });
  document.addEventListener('focusout', e => { if(ic(e.relatedTarget)) return; fermer(); });
  window.addEventListener('scroll', fermer, {passive:true});
  window.addEventListener('resize', fermer, {passive:true});
})();
<\/script>`;
  const html = `<!DOCTYPE html><html lang="${LANGUE}"><head><meta charset="utf-8">
    <title>Portrait Cosmique</title>${styles}</head><body><div class="wrap">
    <div id="glossaire-pop" class="glossaire-pop" role="tooltip" aria-hidden="true"></div>
    ${panneau}${ttScript}</div></body></html>`;
  const blob = new Blob([html], { type: "text/html" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "portrait-cosmique.html";
  a.click();
}
```

Note: `<\/script>` is escaped on purpose to avoid prematurely closing the outer `<script>` of the source page. The exported `<div id="glossaire-pop">` must be included (it's referenced by the tooltip script).

Also, the current `#resultat.outerHTML` will NOT include `<div id="glossaire-pop">` (which lives outside `#resultat`, right before `</div>` of `.wrap`). That's why the export template adds it explicitly above.

- [ ] **Step 11: Manual verification in the browser**

Start the dev server, compute a portrait, then check each of the following:

1. `uvicorn main:app --port 8410` then open `http://localhost:8410`.
2. Pick FR, fill a date (e.g. 1990-09-05), click "Calculer mon portrait".
3. Verify ℹ️ icons appear next to each empreinte key, each stat label, and on the sous-ligne (archétype, forces, faiblesse, pierre).
4. Hover over a ℹ️ → bubble appears, with the right definition (FR).
5. Click it → toggles. Press Escape → closes. Tab-focus + Enter → opens.
6. Switch to EN via the FR/EN buttons → recompute → bubble content in English.
7. Click "Télécharger en HTML" → open the file directly (double-click).
   - Verify the offline file shows ℹ️ icons and tooltips work without a server.
8. From the app, click "Imprimer / Enregistrer en PDF".
   - In the print preview, verify: no ℹ️ visible, legend section appears at the end grouped by themes, in the current language.
9. From the exported HTML file: print the file → same legend appears at the end.

Stop the server: `pkill -f uvicorn`.

- [ ] **Step 12: Commit**

```bash
git add static/index.html
git commit -m "feat: bulles ℹ️ interactives + légende PDF thématisée"
```

---

## Self-Review

**Spec coverage:**
- Bulles interactives sur titres (empreinte, stats, archétype/forces/faiblesse/pierre) → Task 3 steps 5-7.
- HTML export interactif → Task 3 step 10 (+ Step 11 check 7).
- PDF légende thématisée en fin de document → Task 3 step 9 (+ Step 11 checks 8-9).
- Glossaire bilingue côté Python → Task 1.
- API renvoie glossaire → Task 2.

**Placeholder scan:** No "TBD/TODO". Each code step has final code. The Task 1 step 3 had a typo-laden draft flagged with explicit correction instructions and a final clean block provided; the implementer is told explicitly to use the corrected block. The Task 3 step 8 had a `courrant`/`courant` typo flagged the same way. These are flagged inline, not left as placeholders.

**Type consistency:** `significations.glossaire(langue)` returns `list[dict]` with `{"theme": str, "items": [...]}`; Task 2 returns it unmodified as `d["glossaire"]`; Task 3 reads `d.glossaire` (JS, same shape) and `it.id`/`it.label`/`it.definition` — match. `_entree` gains `id` and `expliquer()` returns it; the front reads `e.id` — match. `STAT_VERS_ID` keys cover all 8 stats in both FR and EN names — match against `I18N.fr.*` and `I18N.en.*`.

No gaps found. Plan complete.