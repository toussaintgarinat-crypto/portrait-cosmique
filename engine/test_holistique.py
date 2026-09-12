from datetime import date

import pytest

from engine import holistique as H


def test_reduction_matrice_additionne_les_chiffres_jusqua_22():
    assert [H._reduire_22(n) for n in (22, 23, 29, 99)] == [22, 5, 11, 18]


def test_matrice_destinee_reference_1990_09_05():
    resultat = H.matrice_destinee("1990-09-05")
    assert resultat["points"] == {"A": 5, "B": 9, "C": 19, "D": 6, "E": 12}
    assert resultat["arcanes"]["C"]["numero"] == 19
    assert resultat["arcanes"]["C"]["nom_fr"] == "Le Soleil"
    assert "somme des chiffres" in resultat["methode"].lower()


def test_bazi_reference_et_comptages_1990_09_05():
    resultat = H.calculer({
        "prenoms": "Toussaint Michel Rémi",
        "nom": "Garinat",
        "date_naissance": "1990-09-05",
        "heure_naissance": "11:05",
        "utc_offset": 2,
    })["bazi"]
    assert {cle: pilier["gan_zhi"] for cle, pilier in resultat["piliers"].items()} == {
        "annee": "庚午", "mois": "甲申", "jour": "癸酉", "heure": "戊午"
    }
    assert resultat["maitre_du_jour"]["caractere"] == "癸"
    assert sum(resultat["elements"].values()) == 8
    assert sum(resultat["polarites"].values()) == 8


def test_bazi_change_d_annee_a_li_chun_et_signale_la_proximite():
    avant = H._bazi({
        "date_naissance": "2024-02-03", "heure_naissance": "12:00", "utc_offset": 0
    })
    apres = H._bazi({
        "date_naissance": "2024-02-05", "heure_naissance": "12:00", "utc_offset": 0
    })
    assert avant["piliers"]["annee"]["gan_zhi"] == "癸卯"
    assert apres["piliers"]["annee"]["gan_zhi"] == "甲辰"
    proche = H._bazi({
        "date_naissance": "2024-02-04", "heure_naissance": "08:00", "utc_offset": 0
    })
    assert isinstance(proche["precision"]["limite_proche"], bool)


def test_bazi_est_omis_sans_heure_ou_sans_offset():
    base = {"date_naissance": "1990-09-05", "prenoms": "Ada", "nom": "Lovelace"}
    assert "bazi" not in H.calculer(base)
    assert "bazi" not in H.calculer({**base, "heure_naissance": "11:05"})


def test_arbre_vie_est_une_correspondance_moderne_bornee_a_dix():
    arbre = H.calculer({
        "prenoms": "Ada", "nom_naissance": "Byron", "nom": "Lovelace",
        "date_naissance": "1815-12-10",
    })["arbre_vie"]
    assert set(arbre["nombres"]) == {"date", "nom", "combinaison"}
    assert all(1 <= nombre <= 10 for nombre in arbre["nombres"].values())
    assert len(arbre["sephiroth"]) == 10
    assert "moderne" in arbre["convention"].lower()


@pytest.mark.parametrize(
    "jour,arbre,index,intercalaire",
    [
        (date(2023, 12, 23), None, None, True),
        (date(2023, 12, 24), "Bouleau", 1, False),
        (date(2024, 1, 20), "Bouleau", 1, False),
        (date(2024, 1, 21), "Sorbier", 2, False),
        (date(2024, 2, 29), "Frêne", 3, False),
        (date(2024, 12, 22), "Sureau", 13, False),
    ],
)
def test_calendrier_des_treize_arbres_et_jours_intercalaires(jour, arbre, index, intercalaire):
    resultat = H.celte_lunaire(jour)
    assert resultat["arbre"] == arbre
    assert resultat["index"] == index
    assert resultat["intercalaire"] is intercalaire
    assert resultat["annee_bissextile"] is (jour.year % 4 == 0 and (jour.year % 100 != 0 or jour.year % 400 == 0))


def test_calculer_rejette_sans_exception_une_date_invalide():
    assert H.calculer({"date_naissance": "pas-une-date"}) == {}


def test_heure_inconnue_prioritaire_sur_heure_residuelle():
    assert 'bazi' not in H.calculer({'date_naissance':'1990-09-05','heure_naissance':'11:05','utc_offset':2,'heure_inconnue':True})
