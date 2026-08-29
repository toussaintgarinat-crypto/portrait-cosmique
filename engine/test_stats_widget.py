"""Widget Guerre Cosmique : injection de la config (STATS_API_URL / BOUTIQUE_URL)
dans la page d'accueil depuis l'environnement."""
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_ENGINE = _ROOT / "engine"
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

from fastapi.testclient import TestClient
import main

client = TestClient(main.app)


def test_widget_desactive_sans_env(monkeypatch):
    monkeypatch.delenv("STATS_API_URL", raising=False)
    monkeypatch.delenv("BOUTIQUE_URL", raising=False)
    html = client.get("/").text
    # Les placeholders sont substitués par des chaînes vides (JSON) : plus aucun
    # __PLACEHOLDER__ brut ne doit fuiter vers le navigateur.
    assert "__STATS_API_URL__" not in html
    assert "__BOUTIQUE_URL__" not in html
    assert 'const STATS_API_URL = "";' in html


def test_widget_configure_avec_env(monkeypatch):
    monkeypatch.setenv("STATS_API_URL", "https://boutique.example.com/api/stats")
    monkeypatch.setenv("BOUTIQUE_URL", "https://boutique.example.com")
    html = client.get("/").text
    assert 'const STATS_API_URL = "https://boutique.example.com/api/stats";' in html
    assert 'const BOUTIQUE_URL = "https://boutique.example.com";' in html


def test_url_maliceuse_ne_casse_pas_le_script(monkeypatch):
    # Un guillemet dans l'URL ne doit pas sortir du littéral JS (json.dumps échappe).
    monkeypatch.setenv("STATS_API_URL", 'https://x.example.com/a"b')
    monkeypatch.delenv("BOUTIQUE_URL", raising=False)
    html = client.get("/").text
    assert '__STATS_API_URL__' not in html
    assert '\\"' in html  # le guillemet est échappé, pas brut
