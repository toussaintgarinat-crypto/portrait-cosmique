# 🔮 Portrait Cosmique

*[Version française](README.md)*

Enter your first name(s), last name, date, time, and place of birth: get a full portrait
that crosses **numerology, Western astrology, Chinese astrology, Vedic astrology, Egyptian,
Celtic, Native American, and Maya (Tzolkin) traditions**. Free, instant, self-hostable.

> Symbolic reading — entertainment, not fact. What the engine calculates (astral
> positions, numerology paths, calendar correspondences) is exact; what it draws from it
> (archetype, strengths/weakness, narrative) is an interpretation.

## Installation

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose (bundled with Docker Desktop).
- `git`.

### One-liner

```bash
curl -fsSL https://raw.githubusercontent.com/toussaintgarinat-crypto/portrait-cosmique/main/install.sh | bash
```

Clones the repo into `./portrait-cosmique`, builds the image, and starts the service —
nothing else (no `sudo`, no writes outside that folder). Running the same command later
**updates** (`git pull` + rebuild) instead of re-cloning. The script is short and
readable; if you'd rather inspect it first:

```bash
curl -fsSL https://raw.githubusercontent.com/toussaintgarinat-crypto/portrait-cosmique/main/install.sh -o install.sh
less install.sh   # read it
bash install.sh
```

### Or manually

```bash
git clone https://github.com/toussaintgarinat-crypto/portrait-cosmique.git
cd portrait-cosmique
docker compose up -d --build
```

Either way, check it's up:

```bash
curl http://localhost:8410/sante
# {"statut":"ok","service":"portrait-cosmique","version":"0.1.0","lecture_approfondie_configuree":false}
```

Then open **http://localhost:8410** in your browser: fill in the form (at minimum a date
of birth), click "Calculate my portrait".

No key, no account required, no data retained: every computation happens on the fly,
nothing is written to disk (no database).

**Stop / update**:

```bash
docker compose down                        # stop
git pull && docker compose up -d --build   # update then restart
```

**Without Docker** (local dev): `pip install -r requirements.txt` then
`uvicorn main:app --reload --port 8410` from the repo root (`main.py` auto-detects the
`engine/` subfolder locally).

## What you get

- **Personality stats** (Charisma, Drive, Wisdom, Creativity, Discretion, Stability,
  Emotionality, Energy) aggregated across every tradition computed.
- **Archetype**, **dominant strengths**, **a point to work on** + **balancing stone**
  (compensatory gemmology picked based on your weak point).
- **Multi-tradition imprint**: Sun, Moon, Ascendant, Chinese astrology, Vedic Nakshatra,
  Egyptian deity, Celtic tree, Native American totem, Maya glyph, life path, name
  expression — every value explained in keywords.
- **A symbolic narrative** weaving it all into a coherent reading.
- **French or English** — same engine, same data, your choice of language (FR/EN button).

## Real cost: zero

All of the above is computed by a **100% Python** engine (numerology, celestial
mechanics, calendars), no database, no network call, no API key, no LLM. Zero cost,
zero external dependency for the core feature.

## Enabling the in-depth reading (optional AI bonus)

By default the narrative is already written (deterministic, see above) — the in-depth
reading is a purely optional **AI literary rewrite** of that same content. Two ways to
enable it:

### Option A — one key for the whole instance (handy for family/personal use)

1. Create a free account on [openrouter.ai](https://openrouter.ai) and generate an API
   key (Settings → Keys). It's free as long as you use a model tagged **`:free`**.
2. Pick a free model on [openrouter.ai/models](https://openrouter.ai/models) (filter by
   "Free") — this repo defaults to `google/gemma-3-27b-it:free`, but any `:free` model
   works (function-calling is not required here).
3. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
4. Edit `.env`:
   ```bash
   OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   OPENROUTER_MODEL=google/gemma-3-27b-it:free
   ```
5. Restart:
   ```bash
   docker compose up -d --build
   ```
6. Verify: `curl http://localhost:8410/sante` should return
   `"lecture_approfondie_configuree":true`. The "✨ Deepen with AI" button (under the
   portrait, "Deepen with AI" section) now works for **every visitor** of this instance,
   with nothing for them to fill in.

⚠️ **If this instance is exposed publicly** (not just on your local network), any visitor
consumes this key — even at $0, you're still subject to the free model's rate limits, and
a bad actor could exhaust them for everyone. Reserve option A for private/family use; for
public use, prefer option B below (or both: a visitor's BYOK key, when supplied, always
takes priority over the instance's default key).

### Option B — each visitor supplies their own key (BYOK, suited for public use)

Nothing to configure server-side. Each visitor:
1. Opens "Advanced options" in the form.
2. Fills in their own endpoint (any OpenAI-compatible chat service):
   - **Base URL** (e.g. `https://openrouter.ai/api/v1`, another provider's endpoint, or a
     local model like Ollama/LM Studio);
   - **API key**;
   - **Model** (e.g. `openai/gpt-4o-mini`, `anthropic/claude-3-5-haiku`…).
3. Computes their portrait, then clicks "✨ Deepen with AI": the call goes out under
   THEIR key, zero cost for the instance's host.

### Either way

- With nothing configured (neither A nor B), the button still tries the call, fails
  cleanly, and **falls back to the deterministic narrative** (`"source":"repli"` on the
  API side) — never an error shown, never a blocked experience.
- The rewrite's language follows the interface's chosen language (FR/EN).

## Export

- **Download as HTML**: a self-contained file, generated client-side, to keep or share.
- **Print / Save as PDF**: opens the browser's print dialog with a dedicated layout (form
  and buttons hidden).

## Origin

Extracted from the holistic engine of the [Workplace](https://github.com/toussaintgarinat-crypto)
project — `engine/` (`traditions.py`, `synthese.py`, `significations.py`) is a **verbatim**
copy, synced from the source. `main.py`, `llm.py`, and `static/` are specific to this product.

## License

Apache-2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
