"""Traduction anglaise → française locale, sans clé ni téléchargement à l'exécution.

Seuls les textes publics d'horoscope sont conservés dans ce cache mémoire borné.
Installer le modèle avec scripts/installer_traduction.py avant le démarrage.
"""
from collections import OrderedDict
from threading import Lock
from functools import lru_cache
from pathlib import Path
import os
import re

_cache: OrderedDict[str, str] = OrderedDict()
_lock = Lock()


@lru_cache(maxsize=1)
def _moteur():
    import ctranslate2
    import sentencepiece
    dossier = Path(os.environ.get('PORTRAIT_TRANSLATION_DIR', Path(__file__).parent / 'models' / 'en-fr'))
    tokenizer = sentencepiece.SentencePieceProcessor(model_file=str(dossier / 'sentencepiece.model'))
    moteur = ctranslate2.Translator(str(dossier / 'model'), device='cpu', compute_type='int8',
                                  inter_threads=1, intra_threads=2)
    return tokenizer, moteur


def _traduire(texte: str) -> str:
    # Inférence directe du modèle Argos/OPUS : aucune dépendance à un LLM distant.
    tokenizer, moteur = _moteur()
    paragraphes = []
    for paragraphe in texte.split('\n'):
        if not paragraphe.strip():
            paragraphes.append('')
            continue
        phrases = re.split(r'(?<=[.!?])\s+', paragraphe.strip())
        tokens = [tokenizer.encode(phrase, out_type=str) for phrase in phrases]
        sorties = moteur.translate_batch(tokens, beam_size=4, replace_unknowns=True,
                                          max_input_length=0, max_decoding_length=1024,
                                          length_penalty=0.2)
        # Décodeur SentencePiece du paquet Argos (ses tokens incluent le marqueur ▁).
        paragraphes.append(' '.join(''.join(r.hypotheses[0]).replace('▁', ' ').strip() for r in sorties))
    return '\n'.join(paragraphes)


def traduire_horoscope(texte: str) -> str:
    if not isinstance(texte, str) or not texte.strip():
        raise ValueError('Texte à traduire vide.')
    if len(texte) > 20000:
        raise ValueError('Texte à traduire trop long.')
    texte = texte.strip()
    with _lock:
        if texte in _cache:
            _cache.move_to_end(texte)
            return _cache[texte]
        resultat = _traduire(texte)
        if not isinstance(resultat, str) or not resultat.strip():
            raise RuntimeError('Traduction locale vide.')
        signes = dict(zip(
            ('Aries', 'Taurus', 'Gemini', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'),
            ('Bélier', 'Taureau', 'Gémeaux', 'Lion', 'Vierge', 'Balance', 'Scorpion', 'Sagittaire', 'Capricorne', 'Verseau', 'Poissons'),
        ))
        for anglais, francais in signes.items():
            resultat = re.sub(r'\b' + anglais + r'\b', francais, resultat)
        _cache[texte] = resultat.strip()
        while len(_cache) > 128:
            _cache.popitem(last=False)
        return _cache[texte]
