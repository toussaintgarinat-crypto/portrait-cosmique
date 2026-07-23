# 🔮 Portrait Cosmique

*[Version française](README.md)*

Enter your first name(s), last name, date, time, and place of birth: get a full portrait
that crosses **numerology, Western astrology, Chinese astrology, Vedic astrology, Egyptian,
Celtic, Native American, and Maya (Tzolkin) traditions**. Free, instant, self-hostable.

> Symbolic reading — entertainment, not fact. What the engine calculates (astral
> positions, numerology paths, calendar correspondences) is exact; what it draws from it
> (archetype, strengths/weakness, narrative) is an interpretation.

## 30-second start

```bash
git clone <this-repo> portrait-cosmique && cd portrait-cosmique
docker compose up -d --build
```

Open http://localhost:8410 — fill in the form, get your portrait. No key, no account, no
data retained: everything is computed on the fly and nothing is stored.

## What you get

- **Personality stats** (Charisma, Drive, Wisdom, Creativity, Discretion, Stability,
  Emotionality, Energy) aggregated across every tradition computed.
- **Archetype**, **dominant strengths**, **a point to work on** + **balancing stone**
  (compensatory gemmology picked based on your weak point).
- **Multi-tradition imprint**: Sun, Moon, Ascendant, Chinese astrology, Vedic Nakshatra,
  Egyptian deity, Celtic tree, Native American totem, Maya glyph, life path, name
  expression — every value explained in keywords.
- **A symbolic narrative** weaving it all into a coherent reading.
- **French or English** — same engine, same data, your choice of language.

## Real cost: zero

The portrait is computed by a **100% Python** engine (numerology, celestial mechanics,
calendars), no database, no network call, no API key, no LLM. Zero cost, zero external
dependency for the core feature.

## Optional bonus: AI-deepened reading

A literary rewrite of the narrative is available as an option, if:
- you set a free **OpenRouter** key (`OPENROUTER_API_KEY` in `.env`, see `.env.example`)
  with a free model (`OPENROUTER_MODEL`, e.g. `google/gemma-3-27b-it:free`) — enables the
  bonus for **every visitor** of your instance;
- or each visitor supplies **their own key** from the form ("Advanced options") — any
  OpenAI-compatible endpoint, zero cost on your side.

⚠️ **If you expose this instance publicly** and set a default key, any visitor consumes
it (even at $0, you're still subject to the free model's rate limits). Keep this setting
for private/family use, or leave it blank so only visitors who bring their own key get the
bonus.

Without any configuration, the (already rich) deterministic narrative stands — an honest
fallback, never an error shown to the user.

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
