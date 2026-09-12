"""Portrait Cosmique — portrait multi-traditions à partir d'un état-civil.

Extrait du moteur holistique de Workplace (briques/personnages), périmètre volontairement
réduit au mode « fiche complète » : prénoms/nom/date/heure/lieu de naissance → portrait.
Le calcul (engine/) est 100% Python, déterministe, gratuit et instantané — sans réseau,
sans clé, sans LLM. Un bonus optionnel (lecture approfondie IA) existe si configuré,
avec repli honnête sur le récit déterministe sinon.

Stateless : rien n'est stocké, pas de compte, pas d'auth par défaut — le produit est
pensé pour être public (un formulaire, une réponse).
"""
import json
import os
import sys
from pathlib import Path
from typing import Optional, Literal

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, model_validator

_ENGINE_DIR = Path(__file__).parent / "engine"
if _ENGINE_DIR.is_dir():   # dev local (repo tel quel) ; en Docker les fichiers sont aplatis
    sys.path.insert(0, str(_ENGINE_DIR))

import fuseaux
import significations
import synthese
import theme_complet
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
    nom_naissance:  str = ""
    polarite: Literal["", "feminine", "masculine", "neutre"] = ""
    heure_inconnue: bool = False
    utc_auto: bool = False
    utc_fold: Optional[Literal[0, 1]] = None
    date_naissance: str = ""               # "YYYY-MM-DD"
    heure_naissance: Optional[str] = None   # "HH:MM"
    latitude:       Optional[float] = None
    longitude:      Optional[float] = None  # EST-positive
    utc_offset:     Optional[float] = None  # décalage local→UTC à la naissance
    systeme_numerologie: str = "classique"  # "classique" (A=1…Z=26) ou "pythagoricien"
    langue:         str = "fr"              # "fr" ou "en" — langue du portrait déterministe
    systeme_maisons: str = "whole_sign"      # "whole_sign" | "placidus" | "equal_house"
    methode_dominantes: str = "comptage_dignite"  # "comptage_dignite" | "score_complexe"


    @model_validator(mode="after")
    def normaliser_heure(self):
        if self.heure_inconnue:
            self.heure_naissance = None
        return self


class LectureApprofondieBody(BaseModel):
    """Bonus optionnel : réécriture IA du récit déjà calculé (pas de recalcul ici)."""
    portrait:  dict
    empreinte: list = []
    donnees_synthetiques: dict = {}
    langue:    str = "français"     # texte libre pour le LLM (ex. "français"/"english")
    llm:       Optional[dict] = None


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def accueil():
    html = Path(__file__).parent.joinpath("static/index.html").read_text(encoding="utf-8")
    # Widget « Guerre Cosmique » (stats boutique) : opt-in via l'environnement.
    # json.dumps produit un littéral JS sûr (guillemets échappés) — l'URL vient de
    # l'opérateur de l'instance, jamais de l'utilisateur.
    html = html.replace("__HOLISTIQUE_CSS__", Path(__file__).parent.joinpath("static/holistique.css").read_text(encoding="utf-8"))
    html = html.replace("__HOLISTIQUE_JS__", "\n".join(Path(__file__).parent.joinpath("static", name).read_text(encoding="utf-8") for name in ("holistique.js", "interface-support.js", "fuseau-auto.js")))
    return (html
            .replace("__STATS_API_URL__", json.dumps(os.getenv("STATS_API_URL", "")))
            .replace("__BOUTIQUE_URL__", json.dumps(os.getenv("BOUTIQUE_URL", ""))))


@app.get("/sante", tags=["système"])
def sante():
    return {"statut": "ok", "service": "portrait-cosmique", "version": app.version,
            "lecture_approfondie_configuree": bool(llm.OPENROUTER_API_KEY or llm.OPENCODE_GO_API_KEY or llm.OPENAI_API_KEY),
            "fournisseur_actif": "openrouter" if llm.OPENROUTER_API_KEY else ("opencode-go" if llm.OPENCODE_GO_API_KEY else ("openai" if llm.OPENAI_API_KEY else None))}


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


@app.post("/fuseau", tags=["portrait"])
def fuseau_naissance(body: Fiche):
    try:
        return fuseaux.resoudre(body.latitude, body.longitude, body.date_naissance, body.heure_naissance)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def fiche_calcul(body: Fiche) -> dict:
    fiche = body.model_dump()
    if not fiche.get("heure_naissance"):
        if body.utc_auto:
            fiche["utc_offset"] = None
        return fiche
    coords = body.latitude is not None and body.longitude is not None
    if body.utc_auto and not coords:
        raise HTTPException(422, "Indique et localise le lieu de naissance pour calculer le fuseau automatiquement.")
    if coords and (body.utc_auto or body.utc_offset is None):
        resultat = fuseau_naissance(body)
        if resultat["statut"] == "heure_ambigue":
            choix = next((c for c in resultat["choix"] if c["fold"] == body.utc_fold), None)
            if choix is None:
                raise HTTPException(422, "Cette heure a eu lieu deux fois : choisis la première ou la seconde occurrence.")
            fiche["utc_offset"] = choix["utc_offset"]
        elif resultat["statut"] == "heure_inexistante":
            raise HTTPException(422, "Cette heure locale n'existe pas à cette date (changement d'heure). Vérifie l'heure de naissance.")
        else:
            fiche["utc_offset"] = resultat["utc_offset"]
        fiche["fuseau"] = resultat["fuseau"]
    return fiche


@app.get("/modeles", tags=["portrait"])
async def modeles(cle: str = Query(...), base_url: str = Query("")):
    """Liste les modèles disponibles pour une API OpenAI-compatible (BYO)."""
    cle = cle.strip()
    if not cle:
        raise HTTPException(422, "Une clé API est nécessaire.")
    base = (base_url or "").strip()
    if not base:
        raise HTTPException(422, "Une URL de base est nécessaire.")
    try:
        return {"modeles": await llm.lister_modeles(base, cle)}
    except Exception as e:
        raise HTTPException(502, f"Impossible de récupérer les modèles : {str(e)[:150]}")
@app.post("/theme", tags=["portrait"])
def theme(body: Fiche):
    """Carte astrologique complète (fondations, 10 corps, points évolutifs,
    maisons, aspects, dominantes). Seule la date est absolument requise —
    sans heure/lieu, seules les fondations Soleil/Lune sont calculées
    (Lune approximative sans heure) ; le reste en repli honnête."""
    tc = theme_complet.theme_complet(fiche_calcul(body))
    if not tc.get("fondations", {}).get("soleil"):
        raise HTTPException(422, "Indique au moins une date de naissance valide.")
    return tc


@app.post("/portrait", tags=["portrait"])
def portrait(body: Fiche):
    """Fiche → traditions calculées → portrait (stats/archétype/forces/faiblesse/pierre/
    récit) → empreinte lisible. Étendu : inclut désormais `theme_complet` intégré
    pour que le récit déterministe et l'empreinte exploitent les nouvelles données."""
    fiche = fiche_calcul(body)
    trad = traditions.calculer(fiche)
    if not trad.get("signe_solaire"):
        raise HTTPException(422, "Indique au moins une date de naissance valide.")
    tc = theme_complet.theme_complet_depuis_traditions(trad, fiche)
    p = synthese.portrait(trad, theme_complet=tc, nom=body.prenoms or body.nom, langue=body.langue)
    en = (body.langue or "fr").lower().startswith("en")
    donnees = llm.donnees_synthetiques(fiche, trad, tc)
    p["recit"] += llm.complement_symbolique(trad, body.langue)
    return {"traditions": trad, "theme_complet": tc, "donnees_synthetiques": donnees,
            "portrait": p,
            "empreinte": significations.expliquer(trad, body.langue, theme_complet=tc),
            "glossaire": significations.glossaire(body.langue),
            "didactique": significations.didactique(body.langue),
            "signes_sens": (significations.SIGNES_SENS_EN if en
                            else significations.SIGNES_SENS)}


@app.post("/lecture-approfondie", tags=["portrait"])
async def lecture_approfondie(body: LectureApprofondieBody):
    """Réécriture littéraire optionnelle du récit déjà calculé. Repli HONNÊTE : si aucune
    IA n'est configurée (ni clé par défaut de l'instance, ni BYO) ou si l'appel échoue, on
    renvoie le récit déterministe (`source="repli"`) — jamais d'erreur côté utilisateur."""
    try:
        texte = await llm.approfondir_lecture(body.portrait, body.empreinte, body.langue, body.llm, body.donnees_synthetiques)
        if texte:
            return {"lecture": texte, "source": "llm"}
    except Exception as e:  # noqa: BLE001 — repli honnête
        import logging
        logging.getLogger("portrait-cosmique").warning(
            "lecture-approfondie : repli déterministe activé — %s: %s",
            type(e).__name__, str(e)[:200])
    return {"lecture": body.portrait.get("recit", ""), "source": "repli"}
