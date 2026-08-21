"""Éphéméride géocentrique — longitudes écliptiques tropicales de la date.

Stdlib only. Soleil/Lune réutilisent traditions (Meeus/ELP abrégé).
Mercure→Neptune via VSOP87 tronqué (task 2). Pluton/Chiron/Lilith/Nœud Nord
via formules approchées Meeus (task 3).

Référentiel : longitude géocentrique écliptique tropicale de la date (vraie
équinoxe), en degrés. UT1→TT via ΔT (Espenak-Meeus) pour VSOP87.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

import traditions as T


CORPS = ["Soleil", "Lune", "Mercure", "Vénus", "Mars", "Jupiter",
         "Saturne", "Uranus", "Neptune", "Pluton", "Chiron", "Lilith",
         "Nœud Nord"]


@dataclass
class _Contexte:
    jj: float
    t: float
    heure_ut: float
    delta_t: float


def _delta_t(annee: int) -> float:
    """ΔT (TT - UT1) en secondes — Espenak-Meeus par siècle."""
    if 2000 <= annee < 2100:
        u = annee - 2000
        return 62.92 + 0.32217 * u + 0.005589 * u * u
    elif 1900 <= annee < 2000:
        t = (annee - 1900) / 100.0
        return -2.79 + 1.494119 * t + 0.0006205 * t * t
    elif 2100 <= annee < 2200:
        t = (annee - 2100) / 100.0
        return 111.19 + 4.06246 * t + 0.000118 * t * t
    else:
        return 69.0


def _contexte(dt: datetime, utc_offset_h: float) -> _Contexte:
    heure_ut = dt.hour + dt.minute / 60.0 - utc_offset_h
    jj = T._jour_julien(dt.year, dt.month, dt.day, heure_ut)
    t = (jj - 2451545.0) / 36525.0
    return _Contexte(jj=jj, t=t, heure_ut=heure_ut, delta_t=_delta_t(dt.year))


def _vitesse_et_retro(corps: str, dt: datetime, utc_offset_h: float,
                      lon_a_t: float) -> tuple[float, bool]:
    """Dérivée finie sur 1h → vitesse (deg/jour) + rétrogradation."""
    dt_plus = dt + timedelta(hours=1)
    lon_plus = _longitude_brute(corps, dt_plus, utc_offset_h)
    delta = (lon_plus - lon_a_t + 180) % 360 - 180
    vitesse = delta * 24.0
    return vitesse, vitesse < 0


def _longitude_brute(corps: str, dt: datetime, utc_offset_h: float) -> float:
    """Longitude écliptique brute (deg) — dispatch interne."""
    if corps == "Soleil":
        return T.soleil_longitude(dt, utc_offset_h)
    if corps == "Lune":
        return T.lune_longitude(dt, utc_offset_h)
    raise NotImplementedError(f"Corps {corps!r} non encore implémenté")


def longitude(corps: str, dt: datetime, utc_offset_h: float,
              latitude: float, longitude_geo: float) -> dict:
    """Retourne {corps, longitude, latitude, distance_au, vitesse_deg_j,
    retrograde, methode}."""
    if corps not in CORPS:
        raise ValueError(f"Corps inconnu : {corps!r}")
    lon = _longitude_brute(corps, dt, utc_offset_h)
    vitesse, retro = _vitesse_et_retro(corps, dt, utc_offset_h, lon)
    methodes = {"Soleil": "meeus_soleil", "Lune": "elp_abrege"}
    return {
        "corps": corps,
        "longitude": round(lon % 360, 6),
        "latitude": 0.0,
        "distance_au": 0.0,
        "vitesse_deg_j": round(vitesse, 4),
        "retrograde": retro,
        "methode": methodes.get(corps, "inconnu"),
    }
