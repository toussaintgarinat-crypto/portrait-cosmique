"""Tests de l'éphéméride — cas pivots J2000 et réutilisation de traditions."""
from datetime import datetime

import ephemeride as E
import traditions as T


def test_corps_constante():
    assert E.CORPS == ["Soleil", "Lune", "Mercure", "Vénus", "Mars", "Jupiter",
                       "Saturne", "Uranus", "Neptune", "Pluton", "Chiron", "Lilith",
                       "Nœud Nord"]


def test_delta_t_j2000():
    assert 60.0 < E._delta_t(2000) < 70.0


def test_delta_t_2020():
    assert 65.0 < E._delta_t(2020) < 75.0


def test_contexte_j2000():
    dt = datetime(2000, 1, 1, 12, 0)
    c = E._contexte(dt, 0.0)
    assert abs(c.jj - 2451545.0) < 0.001
    assert abs(c.t) < 1e-6


def test_longitude_soleil_reutilise_traditions():
    dt = datetime(2000, 1, 1, 12, 0)
    attendu = T.soleil_longitude(dt, 0.0)
    res = E.longitude("Soleil", dt, 0.0, 0.0, 0.0)
    assert abs(res["longitude"] - attendu) < 1e-6
    assert res["methode"] == "meeus_soleil"
    assert "vitesse_deg_j" in res
    assert "retrograde" in res


def test_longitude_lune_reutilise_traditions():
    dt = datetime(2000, 1, 1, 12, 0)
    attendu = T.lune_longitude(dt, 0.0)
    res = E.longitude("Lune", dt, 0.0, 0.0, 0.0)
    assert abs(res["longitude"] - attendu) < 1e-4
    assert res["methode"] == "elp_abrege"


def test_longitude_corps_non_implante_leve_notreparable():
    dt = datetime(2000, 1, 1, 12, 0)
    try:
        E.longitude("Mercure", dt, 0.0, 0.0, 0.0)
        assert False, "doit lever NotImplementedError"
    except NotImplementedError:
        pass
