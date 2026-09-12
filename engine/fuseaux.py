"""Résolution du fuseau IANA correspondant au lieu et à l'heure de naissance.

Les frontières géographiques viennent du jeu de données contemporain de
``tzfpy``. Les décalages à la date de naissance viennent des règles IANA
historiques fournies à :class:`zoneinfo.ZoneInfo`.
"""

from datetime import date, datetime, time, timezone
from functools import lru_cache
from importlib import resources
import math
from zoneinfo import ZoneInfo

from tzfpy import get_tz


def _valider_coordonnees(latitude: float, longitude: float) -> None:
    try:
        valides = (
            not isinstance(latitude, bool)
            and not isinstance(longitude, bool)
            and math.isfinite(latitude)
            and math.isfinite(longitude)
            and -90.0 <= latitude <= 90.0
            and -180.0 <= longitude <= 180.0
        )
    except TypeError:
        valides = False
    if not valides:
        raise ValueError(
            "Coordonnées invalides : latitude attendue entre -90 et 90 et "
            "longitude entre -180 et 180."
        )


def _lire_date(valeur: str) -> date:
    try:
        if not isinstance(valeur, str):
            raise TypeError
        return date.fromisoformat(valeur)
    except (TypeError, ValueError) as exc:
        raise ValueError("La date de naissance doit être au format ISO AAAA-MM-JJ.") from exc


def _lire_heure(valeur: str) -> time:
    try:
        if not isinstance(valeur, str) or not valeur:
            raise TypeError
        resultat = time.fromisoformat(valeur)
        if resultat.tzinfo is not None:
            raise ValueError
        return resultat
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "L'heure de naissance doit être une heure locale ISO, par exemple HH:MM."
        ) from exc


@lru_cache(maxsize=None)
def _charger_fuseau(nom: str) -> ZoneInfo:
    """Privilégie le paquet tzdata, déterministe entre systèmes, s'il existe."""
    try:
        ressource = resources.files("tzdata.zoneinfo").joinpath(*nom.split("/"))
        with ressource.open("rb") as fichier:
            return ZoneInfo.from_file(fichier, key=nom)
    except (ImportError, ModuleNotFoundError, FileNotFoundError):
        return ZoneInfo(nom)


def _choix(local: datetime, fuseau: ZoneInfo, fold: int) -> dict | None:
    candidate = local.replace(tzinfo=fuseau, fold=fold)
    retour = candidate.astimezone(timezone.utc).astimezone(fuseau)
    if retour.replace(tzinfo=None) != local or retour.fold != fold:
        return None

    decalage = candidate.utcoffset()
    if decalage is None:
        return None
    return {
        "utc_offset": decalage.total_seconds() / 3600,
        "abbreviation": candidate.tzname(),
        "fold": fold,
    }


def resoudre(
    latitude: float,
    longitude: float,
    date_naissance: str,
    heure_naissance: str | None = None,
) -> dict:
    """Résout un fuseau et qualifie l'heure locale à la date de naissance."""
    _valider_coordonnees(latitude, longitude)
    jour = _lire_date(date_naissance)

    nom_fuseau = get_tz(longitude, latitude)
    if not nom_fuseau:
        raise ValueError("Aucun fuseau IANA trouvé pour ces coordonnées.")

    base = {"fuseau": nom_fuseau}
    if heure_naissance is None:
        return {**base, "statut": "heure_requise"}

    heure = _lire_heure(heure_naissance)
    local = datetime.combine(jour, heure)
    fuseau = _charger_fuseau(nom_fuseau)
    choix = [
        resultat
        for fold in (0, 1)
        if (resultat := _choix(local, fuseau, fold)) is not None
    ]

    if not choix:
        return {**base, "statut": "heure_inexistante"}
    if len(choix) == 2:
        return {**base, "statut": "heure_ambigue", "choix": choix}

    unique = choix[0]
    return {
        **base,
        "statut": "ok",
        "utc_offset": unique["utc_offset"],
        "abbreviation": unique["abbreviation"],
    }
