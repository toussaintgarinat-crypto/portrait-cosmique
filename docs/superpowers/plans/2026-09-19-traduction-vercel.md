# Traduction française sur Vercel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre l'horoscope gratuit français opérationnel sur l'instance Vercel publique sans clé API.

**Architecture:** Vercel installe toutes les dépendances Python depuis `requirements.txt`, exécute l'installateur Argos/OPUS pendant le build, puis inclut explicitement le modèle créé dans le bundle de la fonction FastAPI `main.py`. Le modèle reste téléchargé et vérifié au build ; aucune traduction distante n'est ajoutée à l'exécution.

**Tech Stack:** FastAPI, Python 3.12, Vercel Python Runtime, CTranslate2, SentencePiece, Argos/OPUS EN→FR.

## Global Constraints

- Conserver le contrat `POST /horoscope-du-jour` et le comportement FR/EN existants.
- Utiliser exclusivement le modèle local Argos/OPUS EN→FR 1.9, téléchargé au build avec son SHA-256 existant.
- Ne jamais télécharger le modèle pendant une requête utilisateur.
- Conserver le Dockerfile fonctionnel avec les mêmes dépendances consolidées.
- Fixer Python 3.12, version commune au Dockerfile et au runtime Vercel.
- Vérifier l'endpoint public et le bouton navigateur après déploiement.

---

### Task 1: Déclarer le runtime et les ressources de traduction pour Vercel

**Files:**
- Create: `.python-version`
- Create: `vercel.json`
- Modify: `requirements.txt`
- Delete: `requirements-translation.txt`
- Modify: `Dockerfile`
- Modify: `README.md`
- Modify: `README.en.md`
- Test: `engine/test_deploiement_vercel.py`

**Interfaces:**
- Consumes: `scripts/installer_traduction.py`, qui installe le modèle dans `models/en-fr/`.
- Produces: un build Vercel où `main.py` reçoit les paquets de traduction et `models/en-fr/**`.

- [ ] **Step 1: Write the failing test**

```python
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_vercel_embarque_le_moteur_et_le_modele_de_traduction():
    requirements = (ROOT / 'requirements.txt').read_text()
    assert 'ctranslate2==4.8.2' in requirements
    assert 'sentencepiece==0.2.0' in requirements
    assert 'numpy==1.26.4' in requirements
    assert (ROOT / '.python-version').read_text().strip() == '3.12'

    config = json.loads((ROOT / 'vercel.json').read_text())
    assert config['buildCommand'] == 'python scripts/installer_traduction.py'
    function = config['functions']['main.py']
    assert function['includeFiles'] == 'models/en-fr/**'
    assert function['maxDuration'] == 60
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/private/tmp/portrait-lang-0919/bin/python -m pytest -q engine/test_deploiement_vercel.py`

Expected: FAIL because `requirements.txt` does not yet list `ctranslate2` and `vercel.json` does not exist.

- [ ] **Step 3: Write minimal implementation**

Append these runtime packages to `requirements.txt`:

```text
# Traduction locale EN→FR, utilisée aussi dans le runtime Python Vercel.
ctranslate2==4.8.2
sentencepiece==0.2.0
numpy==1.26.4
```

Create `.python-version`:

```text
3.12
```

Create `vercel.json`:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "buildCommand": "python scripts/installer_traduction.py",
  "functions": {
    "main.py": {
      "includeFiles": "models/en-fr/**",
      "maxDuration": 60
    }
  }
}
```

Change the Docker dependency step to install only `requirements.txt`; delete
`requirements-translation.txt`; change both README installation commands to
`pip install -r requirements.txt`.

- [ ] **Step 4: Run test to verify it passes**

Run: `/private/tmp/portrait-lang-0919/bin/python -m pytest -q engine/test_deploiement_vercel.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .python-version vercel.json requirements.txt Dockerfile README.md README.en.md engine/test_deploiement_vercel.py
git rm requirements-translation.txt
git commit -m "fix: embarque la traduction française sur Vercel"
```

### Task 2: Vérifier le build et le parcours public

**Files:**
- Create: `/private/tmp/playwright-test-horoscope-vercel-fr.js`
- Test: `engine/test_traduction.py`

**Interfaces:**
- Consumes: le bundle produit par la configuration Vercel de Task 1.
- Produces: une preuve de la réponse API publique et du texte affiché par le bouton gratuit français.

- [ ] **Step 1: Run local regression tests**

Run: `/private/tmp/portrait-lang-0919/bin/python -m pytest -q engine/test_traduction.py engine/test_horoscope_api.py`

Expected: PASS; la traduction vide reste rejetée et les réponses en français restent libellées `fr`.

- [ ] **Step 2: Push the implementation commit**

```bash
git push origin main
```

Expected: le commit de Task 1 est accepté par `origin/main` et déclenche le build Vercel.

- [ ] **Step 3: Verify the public endpoint**

Run:

```bash
curl --silent --show-error --fail --max-time 90 \
  --request POST https://portrait-cosmique.vercel.app/horoscope-du-jour \
  --header 'Content-Type: application/json' \
  --data '{"mode":"api","langue":"fr","date":"2026-09-19","soleil":"Vierge"}'
```

Expected: HTTP 200, JSON containing a non-empty `texte` and `"langue":"fr"`.

- [ ] **Step 4: Verify the browser path**

Run the Playwright script against `https://portrait-cosmique.vercel.app`. It
must calculate a profile, open the Horoscope tab, click the first
`[data-horoscope-generation]` button, wait for `#horoscope-texte:not(:empty)`,
and assert:

```javascript
assert.equal(await page.locator('#horoscope-texte').getAttribute('lang'), 'fr');
assert.match(await page.locator('#horoscope-statut').textContent(), /traduction française/);
```

Expected: the visible text is non-empty, in French, and no translation-unavailable message appears.

- [ ] **Step 5: Record verification**

Update `docs/verification-langues-2026-09-19.md` with the public endpoint
status, browser assertion, and the deployed commit SHA; commit only this
verification record:

```bash
git add docs/verification-langues-2026-09-19.md
git commit -m "docs: vérifie la traduction française sur Vercel"
git push origin main
```
