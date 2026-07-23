"""Portrait Cosmique — portrait multi-traditions à partir d'un état-civil.

Extrait du moteur holistique de Workplace (briques/personnages), périmètre volontairement
réduit au mode « fiche complète » : prénoms/nom/date/heure/lieu de naissance → portrait.
Le calcul (engine/) est 100% Python, déterministe, gratuit et instantané — sans réseau,
sans clé, sans LLM. Un bonus optionnel (lecture approfondie IA) existe si configuré,
avec repli honnête sur le récit déterministe sinon.

Stateless : rien n'est stocké, pas de compte, pas d'auth par défaut — le produit est
pensé pour être public (un formulaire, une réponse).
"""
import os
import sys
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

_ENGINE_DIR = Path(__file__).parent / "engine"
if _ENGINE_DIR.is_dir():   # dev local (repo tel quel) ; en Docker les fichiers sont aplatis
    sys.path.insert(0, str(_ENGINE_DIR))

import significations
import synthese
import traditions

import llm

app = FastAPI(title="Portrait Cosmique", version="0.1.0")

_cors = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()] or ["*"]
app.add_middleware(CORSMiddleware, allow_origins=_cors, allow_methods=["*"], allow_headers=["*"])


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


class LectureApprofondieBody(BaseModel):
    """Bonus optionnel : réécriture IA du récit déjà calculé (pas de recalcul ici)."""
    portrait:  dict
    empreinte: list = []
    langue:    str = "français"     # texte libre pour le LLM (ex. "français"/"english")
    llm:       Optional[dict] = None


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def accueil():
    return Path(__file__).parent.joinpath("static/index.html").read_text(encoding="utf-8")


@app.get("/sante", tags=["système"])
def sante():
    return {"statut": "ok", "service": "portrait-cosmique", "version": app.version,
            "lecture_approfondie_configuree": bool(llm.OPENROUTER_API_KEY)}


@app.get("/geo", tags=["portrait"])
async def geo(ville: str):
    """Géocode une ville → latitude / longitude (OpenStreetMap Nominatim, gratuit, sans clé).

    Repli honnête si le service est injoignable. Longitude EST-positive (convention fiche)."""
    q = (ville or "").strip()
    if not q:
        raise HTTPException(422, "Indique une ville.")
    try:
        async with httpx.AsyncClient(timeout=8) as cli:
            r = await cli.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": q, "format": "json", "limit": 1, "accept-language": "fr"},
                headers={"User-Agent": "portrait-cosmique/0.1 (contact via GitHub)"})
        data = r.json()
    except Exception as e:  # noqa: BLE001 — repli honnête
        raise HTTPException(502, f"Géocodage injoignable : {str(e)[:120]}")
    if not data:
        raise HTTPException(404, f"Ville introuvable : {q}")
    top = data[0]
    return {"ville": top.get("display_name", q),
            "latitude": float(top["lat"]), "longitude": float(top["lon"])}


@app.post("/portrait", tags=["portrait"])
def portrait(body: Fiche):
    """Fiche → traditions calculées → portrait (stats/archétype/forces/faiblesse/pierre/
    récit) → empreinte lisible. Un seul appel, la langue choisie s'applique aux deux."""
    trad = traditions.calculer(body.model_dump())
    if not trad.get("signe_solaire"):
        raise HTTPException(422, "Indique au moins une date de naissance valide.")
    p = synthese.portrait(trad, nom=body.prenoms or body.nom, langue=body.langue)
    return {"traditions": trad, "portrait": p,
            "empreinte": significations.expliquer(trad, body.langue)}


@app.post("/lecture-approfondie", tags=["portrait"])
async def lecture_approfondie(body: LectureApprofondieBody):
    """Réécriture littéraire optionnelle du récit déjà calculé. Repli HONNÊTE : si aucune
    IA n'est configurée (ni clé par défaut de l'instance, ni BYO) ou si l'appel échoue, on
    renvoie le récit déterministe (`source="repli"`) — jamais d'erreur côté utilisateur."""
    try:
        texte = await llm.approfondir_lecture(body.portrait, body.empreinte, body.langue, body.llm)
        if texte:
            return {"lecture": texte, "source": "llm"}
    except Exception as e:  # noqa: BLE001 — repli honnête
        import logging
        logging.getLogger("portrait-cosmique").warning(
            "lecture-approfondie : repli déterministe activé — %s: %s",
            type(e).__name__, str(e)[:200])
    return {"lecture": body.portrait.get("recit", ""), "source": "repli"}
