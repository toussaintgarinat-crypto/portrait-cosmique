"""Transits et ciel local déterministes, sans réseau ni données personnelles en cache.

Les positions restent celles du moteur approché existant. Le cache global contient
25 échantillons horaires par jour UTC ; interpolation sur l'arc court à la minute.
Les maisons locales sont en signes entiers, indépendantes des maisons natales.
"""
from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache

import ephemeride as E
import fuseaux
import maisons as M
import theme_complet
import traditions as T

CORPS = tuple(E.CORPS[:10])
ASPECTS = (('conjonction', 0, 'mobilisation'), ('sextile', 60, 'fluidité'),
           ('carré', 90, 'tension'), ('trigone', 120, 'fluidité'),
           ('opposition', 180, 'tension'))
ORBE = 3.0
DOMAINES = (
    ('Initiative', 'Choisir une première action à ta portée.'),
    ('Ressources', 'Faire le point sur tes moyens et tes priorités.'),
    ('Échanges', 'Clarifier une idée avant de la partager.'),
    ('Ancrage', 'Prévoir un moment pour retrouver tes repères.'),
    ('Créativité', 'Donner une forme concrète à une envie créative.'),
    ('Organisation', 'Ajuster ton rythme et simplifier une tâche.'),
    ('Relations', 'Faire une place à l’écoute et à la réciprocité.'),
    ('Transformation', 'Identifier ce que tu souhaites laisser évoluer.'),
    ('Exploration', 'Prendre du recul ou découvrir un autre point de vue.'),
    ('Contribution', 'Préciser ce que tu souhaites apporter à un projet.'),
    ('Collectif', 'Partager une idée avec les personnes concernées.'),
    ('Recul', 'Garder un espace de calme avant la prochaine action.'),
)
LIMITES = [
    'Lecture symbolique : les tendances ne mesurent ni ton état mental ni ton énergie physique.',
    'Éphémérides approchées du moteur existant : écarts possibles de plusieurs degrés pour certaines planètes. Les aspects proches du seuil sont indicatifs.',
    'Positions interpolées entre échantillons horaires UTC ; angles et fenêtres calculés au pas d’une minute, sans garantie de précision astronomique à la minute.',
]


def maintenant():
    return datetime.now(timezone.utc)


@lru_cache(maxsize=8)
def ephemerides_jour(jour: date):
    """Cache immuable, global et borné ; aucune coordonnée ni donnée natale."""
    debut = datetime.combine(jour, time())
    return tuple(tuple(E.longitude(nom, debut + timedelta(hours=h), 0, 0, 0)['longitude']
                       for nom in CORPS) for h in range(25))


def positions_utc(instant: datetime):
    utc = instant.astimezone(timezone.utc)
    serie = ephemerides_jour(utc.date())
    fraction = utc.minute / 60
    result = {}
    for i, nom in enumerate(CORPS):
        a, b = serie[utc.hour][i], serie[utc.hour+1][i]
        lon = (a + ((b-a+180) % 360-180)*fraction) % 360
        result[nom] = {'longitude':round(lon, 6), 'signe':T.SIGNES[int(lon//30)][0]}
    return result


def transits(mobiles: dict, natal: dict, origine='transit'):
    """Aspects croisés uniquement (jamais les aspects internes à un des thèmes)."""
    result = []
    for nom, p in mobiles.items():
        for cible, n in natal.items():
            ecart = abs((p['longitude'] - n['longitude'] + 180) % 360 - 180)
            for aspect, angle, tonalite in ASPECTS:
                orb = abs(ecart-angle)
                if orb <= ORBE:
                    result.append({'mobile':nom, 'natal':cible, 'aspect':aspect,
                                   'orb':round(orb, 4), 'tonalite':tonalite, 'origine':origine})
    return sorted(result, key=lambda a:(a['orb'], a['mobile'], a['natal']))


def tendances(aspects: list):
    result = []
    for nom, corps in [('Focus', {'Mercure'}), ('Élan', {'Soleil','Mars'}),
                       ('Sociabilité', {'Vénus','Jupiter'})]:
        facteurs = [a for a in aspects if a['mobile'] in corps or a['natal'] in corps]
        force = max((1-a['orb']/ORBE for a in facteurs), default=0)
        niveau = 'marqué' if force >= 2/3 else 'modéré' if force >= 1/3 else 'discret'
        tons = {a['tonalite'] for a in facteurs}
        tonalite = next(iter(tons)) if len(tons)==1 else 'contrastée' if tons else 'sans aspect retenu'
        result.append({'nom':nom, 'niveau':niveau, 'tonalite':tonalite,
                       'explication':('Intensité symbolique de l’aspect le plus proche : '
                                      'discret au-delà de 2° d’orbe ou sans aspect, modéré de 1° à 2°, marqué jusqu’à 1°. '
                                      'Un niveau marqué peut indiquer de la tension comme de la fluidité.'),
                       'facteurs':facteurs})
    return result


def angles_locaux(instant, latitude, longitude):
    # traditions accepte une heure locale naïve et un décalage explicite.
    d = T.theme_astral(instant.astimezone(timezone.utc).replace(tzinfo=None), 0, latitude, longitude)
    return d['ascendant'], d['milieu_du_ciel']


def ciel_local(instant, latitude, longitude):
    asc, mc = angles_locaux(instant, latitude, longitude)
    return {'ascendant':asc, 'milieu_du_ciel':mc,
            'maisons':M.maisons(asc['longitude'], mc['longitude'], latitude, 'whole_sign'),
            'systeme':'whole_sign',
            'fuseau':fuseaux.resoudre(latitude, longitude, instant.date().isoformat())['fuseau']}


def fenetres_jour(instant, fuseau, latitude, longitude):
    """Partition de la journée civile navigateur, bornes ISO UTC et pas d'une minute.

    Le calcul UTC continu conserve les deux occurrences d'une heure d'automne.
    Les fenêtres se terminent lorsque le signe de l'ascendant change réellement.
    """
    jour = instant.astimezone(fuseau).date()
    debut = datetime.combine(jour, time(), fuseau).astimezone(timezone.utc)
    fin = datetime.combine(jour+timedelta(days=1), time(), fuseau).astimezone(timezone.utc)
    result = []
    t = debut
    while t < fin:
        asc, _ = angles_locaux(t, latitude, longitude)
        signe = asc['signe']
        if not result or result[-1]['ascendant'] != signe:
            if result:
                result[-1]['fin'] = t.isoformat()
            sun = positions_utc(t)['Soleil']['longitude']
            maison = (int(sun//30)-int(asc['longitude']//30)) % 12 + 1
            domaine, conseil = DOMAINES[maison-1]
            result.append({'debut':t.isoformat(), 'fin':fin.isoformat(), 'ascendant':signe,
                           'maison_solaire':maison, 'domaine':domaine, 'conseil':conseil})
        t += timedelta(minutes=1)
    return result


def calculer(fiche, fuseau, localisation=None):
    zone = fuseaux._charger_fuseau(fuseau)
    now = maintenant().astimezone(timezone.utc).replace(second=0, microsecond=0)
    theme = theme_complet.theme_complet(fiche)
    natal = dict(theme.get('dix_corps', {}))
    complet = bool(natal)
    limites = list(LIMITES)
    if not natal:
        sun = theme.get('fondations', {}).get('soleil')
        if not sun:
            raise ValueError('Indique une date de naissance valide.')
        natal = {'Soleil':sun}
        limites.append('Heure de naissance inconnue : seul le Soleil natal approximé à midi est utilisé. Aucun angle natal ni position lunaire natale n’est inventé.')
    else:
        for cle, nom in [('ascendant','Ascendant'), ('milieu_du_ciel','Milieu du Ciel')]:
            if cle in theme['fondations']:
                natal[nom] = theme['fondations'][cle]
    positions = positions_utc(now)
    aspects = transits(positions, natal)
    local = None
    fenetres = []
    if localisation:
        latitude, longitude = localisation['latitude'], localisation['longitude']
        # Aux très hautes latitudes l'ascendant peut changer de branche : afficher
        # une limite plutôt que fabriquer une partition temporelle trompeuse.
        if abs(latitude) >= 66:
            limites.append('Ciel local non proposé au-delà de 66° de latitude : les levers des signes deviennent irréguliers. Les transits personnels restent disponibles.')
        else:
            local = ciel_local(now, latitude, longitude)
            aspects += transits({'Ascendant local':local['ascendant'],
                                 'Milieu du Ciel local':local['milieu_du_ciel']}, natal, 'local')
            fenetres = fenetres_jour(now, zone, latitude, longitude)
    indicateurs = tendances(aspects)
    lecture = ' · '.join(f"{t['nom']} : {t['niveau']} ({t['tonalite']})" for t in indicateurs) + '.'
    if aspects:
        a = min(aspects,key=lambda x:x['orb'])
        lecture += f" Repère du moment : {a['mobile']} en {a['aspect']} avec {a['natal']} natal (orbe {a['orb']:.2f}°)."
        lecture += (' Prends un temps pour vérifier tes attentes avant d’agir.' if a['tonalite']=='tension'
                    else ' Choisis une action concrète et observe ce qu’elle produit.')
    else:
        lecture += ' Aucun aspect majeur dans l’orbe de 3° retenu ; cela ne préjuge pas de ta journée.'
    if local:
        sun_house = (int(positions['Soleil']['longitude']//30)-int(local['ascendant']['longitude']//30)) % 12+1
        domaine, conseil = DOMAINES[sun_house-1]
        lecture += f" Ici : Soleil en maison locale {sun_house}, thème symbolique « {domaine} ». {conseil}"
        limites.append('Fenêtres : changement de signe de l’ascendant local, maisons en signes entiers. Le domaine correspond à la maison locale du Soleil au début du créneau, pas à une promesse de réussite.')
    return {'instant_utc':now.isoformat(), 'date_locale':now.astimezone(zone).date().isoformat(),
            'fuseau':fuseau, 'positions':positions, 'transits':aspects,
            'tendances':indicateurs, 'lecture':lecture, 'limites':limites,
            'natal_complet':complet, 'local':local, 'fenetres':fenetres}
