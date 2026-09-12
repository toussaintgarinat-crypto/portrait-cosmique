"""Tests de résolution du fuseau de naissance et des transitions DST."""

import pytest

import fuseaux


PARIS = {"latitude": 48.8566, "longitude": 2.3522}
NEW_YORK = {"latitude": 40.7128, "longitude": -74.0060}
KATHMANDU = {"latitude": 27.7172, "longitude": 85.3240}


def test_paris_hiver_1990_est_a_utc_plus_un():
    resultat = fuseaux.resoudre(**PARIS, date_naissance="1990-01-15", heure_naissance="12:00")

    assert resultat == {
        "fuseau": "Europe/Paris",
        "statut": "ok",
        "utc_offset": 1.0,
        "abbreviation": "CET",
    }


def test_paris_ete_1990_est_a_utc_plus_deux():
    resultat = fuseaux.resoudre(**PARIS, date_naissance="1990-07-15", heure_naissance="12:00")

    assert resultat["fuseau"] == "Europe/Paris"
    assert resultat["statut"] == "ok"
    assert resultat["utc_offset"] == 2.0
    assert resultat["abbreviation"] == "CEST"


def test_new_york_applique_le_changement_de_regle_dst_de_2007():
    avant = fuseaux.resoudre(**NEW_YORK, date_naissance="2006-03-20", heure_naissance="12:00")
    apres = fuseaux.resoudre(**NEW_YORK, date_naissance="2007-03-20", heure_naissance="12:00")

    assert avant["fuseau"] == apres["fuseau"] == "America/New_York"
    assert avant["utc_offset"] == -5.0
    assert avant["abbreviation"] == "EST"
    assert apres["utc_offset"] == -4.0
    assert apres["abbreviation"] == "EDT"


def test_kathmandu_conserve_le_decalage_fractionnaire():
    resultat = fuseaux.resoudre(**KATHMANDU, date_naissance="1990-07-15", heure_naissance="12:00")

    assert resultat["fuseau"] == "Asia/Kathmandu"
    assert resultat["statut"] == "ok"
    assert resultat["utc_offset"] == 5.75
    assert resultat["abbreviation"] == "+0545"


def test_heure_ambigue_propose_les_deux_instants():
    resultat = fuseaux.resoudre(**PARIS, date_naissance="2024-10-27", heure_naissance="02:30")

    assert resultat == {
        "fuseau": "Europe/Paris",
        "statut": "heure_ambigue",
        "choix": [
            {"utc_offset": 2.0, "abbreviation": "CEST", "fold": 0},
            {"utc_offset": 1.0, "abbreviation": "CET", "fold": 1},
        ],
    }


def test_heure_inexistante_est_refusee():
    resultat = fuseaux.resoudre(**PARIS, date_naissance="2024-03-31", heure_naissance="02:30")

    assert resultat == {"fuseau": "Europe/Paris", "statut": "heure_inexistante"}


def test_absence_heure_ne_fabrique_pas_de_decalage():
    resultat = fuseaux.resoudre(**PARIS, date_naissance="1990-07-15")

    assert resultat == {"fuseau": "Europe/Paris", "statut": "heure_requise"}


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (91.0, 0.0),
        (-91.0, 0.0),
        (0.0, 181.0),
        (0.0, -181.0),
        (float("nan"), 0.0),
        (0.0, float("inf")),
    ],
)
def test_coordonnees_invalides_levent_une_erreur_claire(latitude, longitude):
    with pytest.raises(ValueError, match="[Cc]oordonnées"):
        fuseaux.resoudre(latitude, longitude, "1990-01-01", "12:00")


@pytest.mark.parametrize("date_naissance", ["", "31/03/2024", "2024-02-30"])
def test_date_invalide_leve_une_erreur_claire(date_naissance):
    with pytest.raises(ValueError, match="date de naissance"):
        fuseaux.resoudre(**PARIS, date_naissance=date_naissance, heure_naissance="12:00")


@pytest.mark.parametrize("heure_naissance", ["", "midi", "25:00", "12:00+02:00"])
def test_heure_invalide_leve_une_erreur_claire(heure_naissance):
    with pytest.raises(ValueError, match="heure de naissance"):
        fuseaux.resoudre(**PARIS, date_naissance="1990-01-01", heure_naissance=heure_naissance)


def test_zero_zero_est_une_coordonnee_valide():
    resultat = fuseaux.resoudre(0.0, 0.0, "1990-01-01")

    assert resultat["statut"] == "heure_requise"
    assert resultat["fuseau"]
