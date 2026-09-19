"""Offline translator: bounded cache, no network calls and no cached failures."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import traduction


def test_translates_once_and_reuses_cache(monkeypatch):
    calls = []
    monkeypatch.setattr(traduction, '_traduire', lambda text: calls.append(text) or 'Bonjour.')
    traduction._cache.clear()
    assert traduction.traduire_horoscope('Hello.') == 'Bonjour.'
    assert traduction.traduire_horoscope('Hello.') == 'Bonjour.'
    assert calls == ['Hello.']


def test_failed_translation_not_cached(monkeypatch):
    import pytest
    traduction._cache.clear()
    monkeypatch.setattr(traduction, '_traduire', lambda text: '')
    with pytest.raises(RuntimeError):
        traduction.traduire_horoscope('Hello.')
    assert not traduction._cache


def test_cache_bounded(monkeypatch):
    traduction._cache.clear()
    monkeypatch.setattr(traduction, '_traduire', lambda text: 'Traduction ' + text)
    for i in range(150):
        traduction.traduire_horoscope(str(i))
    assert len(traduction._cache) == 128
    assert '0' not in traduction._cache


def test_french_reading_localises_zodiac_names(monkeypatch):
    traduction._cache.clear()
    monkeypatch.setattr(traduction, '_traduire', lambda text: 'Pour Virgo, prenez une pause. Aries et Aquarius aussi.')
    assert traduction.traduire_horoscope('For Virgo, take a break.') == 'Pour Vierge, prenez une pause. Bélier et Verseau aussi.'
