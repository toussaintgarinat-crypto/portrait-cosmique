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
