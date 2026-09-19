import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_vercel_embarque_le_moteur_et_le_modele_de_traduction():
    requirements = (ROOT / "requirements.txt").read_text()
    assert "ctranslate2==4.8.2" in requirements
    assert "sentencepiece==0.2.0" in requirements
    assert "numpy==1.26.4" in requirements
    assert (ROOT / ".python-version").read_text().strip() == "3.12"

    config = json.loads((ROOT / "vercel.json").read_text())
    assert config["buildCommand"] == "python scripts/installer_traduction.py"
    function = config["functions"]["main.py"]
    assert function["includeFiles"] == "models/en-fr/**"
    assert function["maxDuration"] == 60
