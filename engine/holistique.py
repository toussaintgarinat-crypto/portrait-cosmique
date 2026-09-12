"""Calculs symboliques complémentaires du Portrait Cosmique.

Les résultats décrivent des conventions de lecture et ne constituent ni des faits
scientifiques, ni des prédictions. Le module est pur et ne dépend que de la stdlib.
"""
from __future__ import annotations

import calendar
import math
import unicodedata
from datetime import date, datetime


_ARCANES = (
    ("Le Bateleur", "The Magician", "initiative et potentiel", "initiative and potential"),
    ("La Papesse", "The High Priestess", "intuition et maturation", "intuition and gestation"),
    ("L'Impératrice", "The Empress", "création et expression", "creation and expression"),
    ("L'Empereur", "The Emperor", "structure et stabilité", "structure and stability"),
    ("Le Pape", "The Hierophant", "transmission et repères", "teaching and shared values"),
    ("L'Amoureux", "The Lovers", "choix et relation", "choice and relationship"),
    ("Le Chariot", "The Chariot", "élan et direction", "drive and direction"),
    ("La Justice", "Justice", "équilibre et responsabilité", "balance and accountability"),
    ("L'Hermite", "The Hermit", "recul et recherche", "reflection and inquiry"),
    ("La Roue de Fortune", "Wheel of Fortune", "cycle et changement", "cycles and change"),
    ("La Force", "Strength", "courage et maîtrise", "courage and composure"),
    ("Le Pendu", "The Hanged Man", "pause et nouveau regard", "pause and a new perspective"),
    ("L'Arcane sans nom", "Death", "transformation et passage", "transformation and transition"),
    ("Tempérance", "Temperance", "ajustement et circulation", "adjustment and flow"),
    ("Le Diable", "The Devil", "désir et attachement", "desire and attachment"),
    ("La Maison Dieu", "The Tower", "rupture et révélation", "disruption and revelation"),
    ("L'Étoile", "The Star", "confiance et inspiration", "trust and inspiration"),
    ("La Lune", "The Moon", "imaginaire et incertitude", "imagination and uncertainty"),
    ("Le Soleil", "The Sun", "clarté et vitalité", "clarity and vitality"),
    ("Le Jugement", "Judgement", "appel et renouveau", "calling and renewal"),
    ("Le Monde", "The World", "accomplissement et intégration", "completion and integration"),
    ("Le Mat", "The Fool", "liberté et commencement", "freedom and beginnings"),
)


def _reduire_22(nombre: int) -> int:
    """Addition répétée des chiffres, en conservant toute valeur de 1 à 22."""
    nombre = abs(int(nombre))
    while nombre > 22:
        nombre = sum(int(chiffre) for chiffre in str(nombre))
    return nombre


def _date(valeur: str | date) -> date:
    return valeur if isinstance(valeur, date) else date.fromisoformat(str(valeur).strip())


def matrice_destinee(naissance: str | date) -> dict:
    naissance = _date(naissance)
    a = _reduire_22(naissance.day)
    b = _reduire_22(naissance.month)
    c = _reduire_22(sum(int(c) for c in f"{naissance.year:04d}"))
    d = _reduire_22(a + b + c)
    e = _reduire_22(a + b + c + d)
    points = {"A": a, "B": b, "C": c, "D": d, "E": e}

    def arcane(numero: int) -> dict:
        nom_fr, nom_en, sens_fr, sens_en = _ARCANES[numero - 1]
        return {"numero": numero, "nom_fr": nom_fr, "nom_en": nom_en,
                "sens_fr": sens_fr, "sens_en": sens_en}

    return {
        "points": points,
        "arcanes": {point: arcane(numero) for point, numero in points.items()},
        "methode": (
            "Réduction par somme des chiffres jusqu'à une valeur ≤ 22 : "
            "A=jour, B=mois, C=année, D=A+B+C, E=A+B+C+D."
        ),
        "axes_symboliques": {
            "amour": "Axe de réflexion relationnelle, sans score ni prédiction.",
            "finances": "Axe de réflexion matérielle, sans score ni prédiction.",
        },
    }


_TIGES = (
    ("Jia", "甲", "Bois", "Yang"), ("Yi", "乙", "Bois", "Yin"),
    ("Bing", "丙", "Feu", "Yang"), ("Ding", "丁", "Feu", "Yin"),
    ("Wu", "戊", "Terre", "Yang"), ("Ji", "己", "Terre", "Yin"),
    ("Geng", "庚", "Métal", "Yang"), ("Xin", "辛", "Métal", "Yin"),
    ("Ren", "壬", "Eau", "Yang"), ("Gui", "癸", "Eau", "Yin"),
)
_BRANCHES = (
    ("Zi", "子", "Rat", "Eau", "Yang"), ("Chou", "丑", "Buffle", "Terre", "Yin"),
    ("Yin", "寅", "Tigre", "Bois", "Yang"), ("Mao", "卯", "Lapin", "Bois", "Yin"),
    ("Chen", "辰", "Dragon", "Terre", "Yang"), ("Si", "巳", "Serpent", "Feu", "Yin"),
    ("Wu", "午", "Cheval", "Feu", "Yang"), ("Wei", "未", "Chèvre", "Terre", "Yin"),
    ("Shen", "申", "Singe", "Métal", "Yang"), ("You", "酉", "Coq", "Métal", "Yin"),
    ("Xu", "戌", "Chien", "Terre", "Yang"), ("Hai", "亥", "Cochon", "Eau", "Yin"),
)


def _tige(index: int) -> dict:
    nom, caractere, element, polarite = _TIGES[index % 10]
    return {"index": index % 10, "nom": nom, "caractere": caractere,
            "element": element, "polarite": polarite}


def _branche(index: int) -> dict:
    nom, caractere, animal, element, polarite = _BRANCHES[index % 12]
    return {"index": index % 12, "nom": nom, "caractere": caractere, "animal": animal,
            "element": element, "polarite": polarite}


def _pilier(tige_index: int, branche_index: int) -> dict:
    tige, branche = _tige(tige_index), _branche(branche_index)
    return {"tige": tige, "branche": branche,
            "gan_zhi": tige["caractere"] + branche["caractere"],
            "romanise": f'{tige["nom"]}-{branche["nom"]}'}


def _longitude_solaire(moment_local: datetime, utc_offset: float) -> float:
    """Longitude apparente du Soleil, approximation Meeus basse précision (~0,01°)."""
    heure_ut = moment_local.hour + moment_local.minute / 60 + moment_local.second / 3600 - utc_offset
    j2000 = moment_local.date().toordinal() - date(2000, 1, 1).toordinal() + heure_ut / 24 - 0.5
    g = math.radians((357.529 + 0.98560028 * j2000) % 360)
    q = (280.459 + 0.98564736 * j2000) % 360
    return (q + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)) % 360


def _bazi(fiche: dict) -> dict:
    naissance = _date(fiche["date_naissance"])
    heure = datetime.strptime(str(fiche["heure_naissance"]).strip(), "%H:%M").time()
    offset = float(fiche["utc_offset"])
    moment = datetime.combine(naissance, heure)
    longitude = _longitude_solaire(moment, offset)

    # L'année solaire commence à 315° (Li Chun). Janvier et le début février
    # appartiennent donc encore à l'année sexagésimale précédente.
    annee_solaire = naissance.year - 1 if naissance.month <= 2 and longitude < 315 else naissance.year
    index_annee = (annee_solaire - 4) % 60
    tige_annee, branche_annee = index_annee % 10, index_annee % 12

    numero_mois = int(((longitude - 315) % 360) // 30) + 1
    branche_mois = (numero_mois + 1) % 12  # premier mois = Yin (index 2)
    tige_mois = (2 * (tige_annee % 5) + 2 + numero_mois - 1) % 10

    # 2000-01-07 est Jia-Zi ; date civile et bascule du jour à minuit.
    index_jour = (naissance.toordinal() + 14) % 60
    tige_jour, branche_jour = index_jour % 10, index_jour % 12
    branche_heure = ((heure.hour + 1) // 2) % 12
    tige_heure = (2 * (tige_jour % 5) + branche_heure) % 10

    piliers = {
        "annee": _pilier(tige_annee, branche_annee),
        "mois": _pilier(tige_mois, branche_mois),
        "jour": _pilier(tige_jour, branche_jour),
        "heure": _pilier(tige_heure, branche_heure),
    }
    elements = {element: 0 for element in ("Bois", "Feu", "Terre", "Métal", "Eau")}
    polarites = {polarite: 0 for polarite in ("Yin", "Yang")}
    for pilier in piliers.values():
        for signe in (pilier["tige"], pilier["branche"]):
            elements[signe["element"]] += 1
            polarites[signe["polarite"]] += 1

    distance = min((longitude - (315 + 30 * n)) % 360 for n in range(12))
    distance = min(distance, 30 - distance)
    return {
        "piliers": piliers,
        "maitre_du_jour": piliers["jour"]["tige"],
        "elements": elements,
        "polarites": polarites,
        "convention": (
            "Heure civile et décalage UTC fournis ; année à Li Chun (315°), mois aux jie "
            "successifs de 30°, jour à minuit civil, sans correction en temps solaire vrai."
        ),
        "precision": {
            "termes_solaires": "longitude solaire approximative ; vérifier près d'une limite",
            "longitude_solaire": round(longitude, 4),
            "distance_limite_deg": round(distance, 4),
            "limite_proche": distance < 0.25,
        },
    }


_SEPHIROTH = (
    ("Keter", "Couronne", "orientation et unité"),
    ("Chokhmah", "Sagesse", "élan créateur"),
    ("Binah", "Intelligence", "forme et compréhension"),
    ("Chesed", "Bonté", "expansion et générosité"),
    ("Gevurah", "Rigueur", "limite et discernement"),
    ("Tiferet", "Beauté", "cohérence et harmonie"),
    ("Netzach", "Victoire", "désir et endurance"),
    ("Hod", "Splendeur", "langage et analyse"),
    ("Yesod", "Fondement", "liaison et imaginaire"),
    ("Malkhut", "Royaume", "présence et concrétisation"),
)


def _reduire_10(nombre: int) -> int:
    while nombre > 10:
        nombre = sum(int(c) for c in str(nombre))
    return max(1, nombre)


def _valeur_nom(nom: str) -> int | None:
    ascii_nom = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    valeurs = ((ord(c) - ord("A")) % 9 + 1 for c in ascii_nom.upper() if "A" <= c <= "Z")
    total = sum(valeurs)
    return _reduire_10(total) if total else None


def arbre_vie(naissance: date, nom_complet: str) -> dict:
    nombre_date = _reduire_10(sum(int(c) for c in naissance.isoformat() if c.isdigit()))
    nombre_nom = _valeur_nom(nom_complet)
    if nombre_nom is None:
        return {}
    nombres = {"date": nombre_date, "nom": nombre_nom,
               "combinaison": _reduire_10(nombre_date + nombre_nom)}
    sephiroth = []
    for numero, (nom, nom_fr, potentiel) in enumerate(_SEPHIROTH, 1):
        active_par = [cle for cle, valeur in nombres.items() if valeur == numero]
        sephiroth.append({"numero": numero, "nom": nom, "nom_fr": nom_fr,
                          "potentiel": potentiel, "active_par": active_par})
    return {
        "nombres": nombres,
        "sephiroth": sephiroth,
        "convention": (
            "Correspondance symbolique moderne : réduction 1–10 de la date et du nom "
            "par alphabet cyclique 1–9 ; ce n'est pas une méthode kabbalistique universelle."
        ),
    }


_ARBRES = (
    ("Bouleau", "Birch"), ("Sorbier", "Rowan"), ("Frêne", "Ash"),
    ("Aulne", "Alder"), ("Saule", "Willow"), ("Aubépine", "Hawthorn"),
    ("Chêne", "Oak"), ("Houx", "Holly"), ("Noisetier", "Hazel"),
    ("Vigne", "Vine"), ("Lierre", "Ivy"), ("Roseau", "Reed"),
    ("Sureau", "Elder"),
)


def celte_lunaire(naissance: str | date) -> dict:
    naissance = _date(naissance)
    bissextile = calendar.isleap(naissance.year)
    commun = {
        "annee_bissextile": bissextile,
        "jour_bissextile": naissance.month == 2 and naissance.day == 29,
        "convention": (
            "Calendrier moderne de 13 arbres × 28 jours, cycle au 24 décembre ; "
            "le 23 décembre est intercalaire et le 29 février répète le jour précédent."
        ),
    }
    if naissance.month == 12 and naissance.day == 23:
        return {"index": None, "arbre": None, "nom_en": None, "periode": "Jour intercalaire",
                "jour_cycle": None, "intercalaire": True, **commun}

    # Projeter sur une année non bissextile conserve les bornes jour/mois,
    # y compris pour l'an 1 (aucune construction d'une année zéro).
    reference = date(2001, naissance.month, min(naissance.day, 28) if naissance.month == 2 else naissance.day)
    jour_cycle = (reference.toordinal() - date(2001, 12, 24).toordinal()) % 365 + 1
    index = (jour_cycle - 1) // 28 + 1
    index = min(index, 13)
    arbre, nom_en = _ARBRES[index - 1]
    # La période textuelle stable est plus utile à l'UI que des dates dépendant de l'année.
    bornes = (
        "24 déc.–20 jan.", "21 jan.–17 fév.", "18 fév.–17 mars", "18 mars–14 avr.",
        "15 avr.–12 mai", "13 mai–9 juin", "10 juin–7 juil.", "8 juil.–4 août",
        "5 août–1 sept.", "2–29 sept.", "30 sept.–27 oct.", "28 oct.–24 nov.",
        "25 nov.–22 déc.",
    )
    return {"index": index, "arbre": arbre, "nom_en": nom_en, "periode": bornes[index - 1],
            "jour_cycle": jour_cycle, "intercalaire": False, **commun}


def calculer(fiche: dict) -> dict:
    try:
        naissance = _date(fiche.get("date_naissance", ""))
    except (TypeError, ValueError):
        return {}
    resultat = {
        "matrice_destinee": matrice_destinee(naissance),
        "celte_lunaire": celte_lunaire(naissance),
    }
    nom = " ".join(partie.strip() for partie in (
        str(fiche.get("prenoms") or ""),
        str(fiche.get("nom_naissance") or fiche.get("nom") or ""),
    ) if partie.strip())
    if nom:
        arbre = arbre_vie(naissance, nom)
        if arbre:
            resultat["arbre_vie"] = arbre
    if not fiche.get("heure_inconnue") and fiche.get("heure_naissance") not in (None, "") and fiche.get("utc_offset") not in (None, ""):
        try:
            resultat["bazi"] = _bazi(fiche)
        except (TypeError, ValueError):
            pass
    return resultat
