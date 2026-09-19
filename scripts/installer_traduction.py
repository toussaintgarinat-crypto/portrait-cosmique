"""Télécharge au build le modèle Argos/OPUS EN→FR 1.9 ; aucune clé nécessaire."""
import hashlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import Request, urlopen
import shutil
import zipfile

MODEL_URL = 'https://argos-net.com/v1/translate-en_fr-1_9.argosmodel'
MODEL_SHA256 = '3a65ed83364f4e7b06e30f9dd823db1934899ed3ce839e63f46dc7b09dc797b4'


def installer():
    cible = Path(os.environ.get('PORTRAIT_TRANSLATION_DIR', Path(__file__).resolve().parents[1] / 'models' / 'en-fr'))
    with TemporaryDirectory() as dossier:
        fichier = Path(dossier) / 'en_fr.argosmodel'
        with urlopen(Request(MODEL_URL, headers={'User-Agent': 'Portrait-Cosmique/1.0'}), timeout=120) as response, fichier.open('wb') as output:
            shutil.copyfileobj(response, output)
        if hashlib.sha256(fichier.read_bytes()).hexdigest() != MODEL_SHA256:
            raise RuntimeError('Empreinte du modèle inattendue : installation interrompue.')
        with zipfile.ZipFile(fichier) as archive:
            for name in archive.namelist():
                relative = Path(*Path(name).parts[1:])
                # Seuls les fichiers nécessaires à l’inférence et leur licence sont extraits.
                if '..' in relative.parts or relative.is_absolute():
                    raise ValueError('Chemin de modèle invalide.')
                if relative.parts and (relative.parts[0] == 'model' or str(relative) in ('sentencepiece.model', 'metadata.json', 'README.md')) and not name.endswith('/'):
                    destination = cible / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(name) as source, destination.open('wb') as output:
                        shutil.copyfileobj(source, output)
    print('Modèle anglais → français 1.9 installé et vérifié.')


if __name__ == '__main__':
    installer()
