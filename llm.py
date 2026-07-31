"""Adaptateur LLM pour la lecture approfondie — bonus optionnel de Portrait Cosmique.

Le portrait déterministe (stats/archétype/récit) ne dépend JAMAIS de ceci : il est
calculé en Python pur, gratuit et instantané (voir engine/). Ce module ne sert qu'à
réécrire ce récit en version littéraire, via un modèle de langage, si l'un de ces
fournisseurs est configuré sur l'instance :

  • OPENROUTER_API_KEY — modèle gratuit OpenRouter ($0 réel), prioritaire ;
  • OPENAI_API_KEY (+ OPENAI_BASE_URL optionnel) — tout endpoint OpenAI-compatible
    (OpenAI, OpenCode, Azure, etc.), utilisé si OpenRouter est absent ;
  • ou un BYOK par requête (champ `llm: {base_url, cle, modele}`) — aucun coût
    porté par cette instance.

Sans aucun de ces fournisseurs, la fonctionnalité est simplement absente (repli
honnête sur le récit déterministe, déjà géré par l'appelant)."""
from __future__ import annotations

import os

import httpx

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-3-27b-it:free")
OPENROUTER_BASE = "https://openrouter.ai/api/v1"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

OPENCODE_GO_API_KEY = os.getenv("OPENCODE_GO_API_KEY", "")
OPENCODE_GO_BASE_URL = os.getenv("OPENCODE_GO_BASE_URL", "https://opencode.ai/zen/go/v1")
OPENCODE_GO_MODEL = os.getenv("OPENCODE_GO_MODEL", "deepseek-v4-pro")

PROMPT_LECTURE = (
    "Tu es un INTERPRÈTE SYMBOLIQUE. On te donne le profil DÉJÀ CALCULÉ d'une personne : "
    "un archétype, des forces, un point faible avec sa pierre d'équilibrage, et une empreinte "
    "multi-traditions (chaque élément vient avec son sens). Tu rédiges une lecture symbolique "
    "fluide et évocatrice qui TISSE ces éléments entre eux et dégage un fil conducteur. "
    "Règles STRICTES : n'invente AUCUN fait absent des données ; pas de prédiction, pas de "
    "conseil médical/financier ; ton sobre et bienveillant. C'est du divertissement."
)


def _config(llm: dict | None) -> tuple[str, str, str]:
    """(base_url, cle, modele) : BYO si fourni et complet, sinon OpenRouter en priorité,
    puis OpenCode Go, puis OpenAI comme fournisseurs par défaut de l'instance."""
    llm = llm or {}
    base = (llm.get("base_url") or "").strip()
    if base:   # mode BYO
        return base.rstrip("/"), (llm.get("cle") or "").strip(), (llm.get("modele") or "").strip()
    model = (llm.get("modele") or "").strip()
    if OPENROUTER_API_KEY:
        return OPENROUTER_BASE, OPENROUTER_API_KEY, model or OPENROUTER_MODEL
    if OPENCODE_GO_API_KEY:
        return OPENCODE_GO_BASE_URL, OPENCODE_GO_API_KEY, model or OPENCODE_GO_MODEL
    if OPENAI_API_KEY:
        return OPENAI_BASE_URL, OPENAI_API_KEY, model or OPENAI_MODEL
    return "", "", ""


async def approfondir_lecture(portrait: dict, empreinte: list,
                              langue: str = "français", llm: dict | None = None) -> str:
    """Réécrit la lecture symbolique en version littéraire, à partir des SEULES données
    calculées. Lève si rien n'est configuré (BYO absent ET pas de clé par défaut sur cette
    instance) — l'appelant retombe alors sur le récit déterministe (repli honnête)."""
    base, cle, modele = _config(llm)
    if not cle or not modele:
        raise RuntimeError("Aucun modèle LLM configuré (ni BYO, ni clé par défaut de l'instance).")

    lignes = [f"- {e.get('cle')} : {e.get('valeur')} → {e.get('sens')}"
              for e in (empreinte or []) if e.get("sens")]
    pierre = portrait.get("pierre_equilibrage") or {}
    tache = (
        f"Rédige en {langue}, 4 à 6 courts paragraphes, sans liste à puces.\n"
        f"Archétype : {portrait.get('archetype','')}\n"
        f"Forces dominantes : {', '.join(portrait.get('forces', []))}\n"
        f"Point à travailler : {portrait.get('faiblesse','')} "
        f"(pierre d'équilibrage : {pierre.get('pierre','')} — {pierre.get('vertu','')})\n"
        f"Empreinte multi-traditions (valeur → sens) :\n" + "\n".join(lignes) +
        "\n\nTisse ces éléments en une lecture cohérente avec un fil conducteur. "
        "N'invente aucun fait. Termine sans formule de politesse."
    )
    headers = {"Authorization": f"Bearer {cle}"} if cle else {}
    payload = {"model": modele, "temperature": 0.4,
               "messages": [{"role": "system", "content": PROMPT_LECTURE},
                            {"role": "user", "content": tache}]}
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{base}/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
        return (r.json()["choices"][0]["message"]["content"] or "").strip()


async def lister_modeles(base_url: str, cle: str) -> list[str]:
    """Liste les modèles disponibles chez un fournisseur OpenAI-compatible."""
    headers = {"Authorization": f"Bearer {cle}"}
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(f"{base_url.rstrip('/')}/models", headers=headers)
        r.raise_for_status()
        data = r.json()
    return sorted(
        [m["id"] for m in data.get("data", []) if m.get("id")],
        key=lambda x: x.lower())
