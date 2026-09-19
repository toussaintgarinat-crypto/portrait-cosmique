"""Contrats météo : calculs UTC, localisation optionnelle et aucun natal inventé."""
from datetime import datetime, timezone
import pytest
from test_api_theme import client, _FICHE


def request(**kwargs):
    return client.post('/meteo-cosmique', json={'fiche': _FICHE, 'fuseau': 'Europe/Paris', **kwargs})


def test_meteo_without_location_calculates_real_transits():
    r = request()
    assert r.status_code == 200
    d = r.json()
    assert len(d['positions']) == 10
    assert d['local'] is None and d['fenetres'] == []
    assert d['natal_complet']
    assert [t['nom'] for t in d['tendances']] == ['Concentration', 'Élan', 'Sociabilité']
    assert all(t['niveau'] in ('discret', 'modéré', 'marqué') for t in d['tendances'])
    assert d['lecture'] and d['limites']


@pytest.mark.parametrize('patch', [
    {'fuseau':'Never/Here'}, {'localisation':{'latitude':91,'longitude':0}},
    {'localisation':{'latitude':0}}, {'fiche':{'date_naissance':'oops'}},
    {'fiche':{**_FICHE, 'heure_naissance':'25:00'}},
    {'fiche':{**_FICHE, 'heure_naissance':'1105'}},
    {'fiche':{**_FICHE, 'heure_naissance':'T11:05'}},
    {'fiche':{**_FICHE, 'utc_offset':30}},
])
def test_invalid_input_is_422(patch):
    assert request(**patch).status_code == 422


def test_local_angles_change_not_global_positions(monkeypatch):
    import meteo_cosmique as M
    monkeypatch.setattr(M, 'maintenant', lambda: datetime(2026,9,13,12,tzinfo=timezone.utc))
    a = request(localisation={'latitude':43.6,'longitude':1.44}).json()
    b = request(localisation={'latitude':40.7,'longitude':-74}).json()
    assert a['positions'] == b['positions']
    assert [t for t in a['transits'] if t['origine']=='transit'] == [t for t in b['transits'] if t['origine']=='transit']
    assert a['local']['ascendant'] != b['local']['ascendant']
    assert len(a['local']['maisons']) == 12
    assert a['local']['fuseau'] == 'Europe/Paris'
    assert b['local']['fuseau'] == 'America/New_York'


@pytest.mark.parametrize('now,zone,expected,hours', [
    ('2026-09-13T00:30:00+00:00','America/Los_Angeles','2026-09-12',24),
    ('2026-03-29T12:00:00+00:00','Europe/Paris','2026-03-29',23),
    ('2026-10-25T12:00:00+00:00','Europe/Paris','2026-10-25',25),
])
def test_windows_cover_actual_local_day(monkeypatch, now, zone, expected, hours):
    import meteo_cosmique as M
    monkeypatch.setattr(M,'maintenant',lambda:datetime.fromisoformat(now))
    d = request(fuseau=zone, localisation={'latitude':43.6,'longitude':1.44}).json()
    assert d['date_locale'] == expected
    windows = d['fenetres']
    assert windows and len(windows) < 30
    duration = datetime.fromisoformat(windows[-1]['fin']) - datetime.fromisoformat(windows[0]['debut'])
    assert duration.total_seconds() == hours*3600
    for a,b in zip(windows,windows[1:]):
        assert a['fin'] == b['debut']
        assert a['ascendant'] != b['ascendant']
    assert all(1 <= w['maison_solaire'] <= 12 for w in windows)


def test_unknown_birth_time_is_partial():
    d = request(fiche={**_FICHE,'heure_inconnue':True}).json()
    assert d['natal_complet'] is False
    assert all(t['natal']=='Soleil' for t in d['transits'])
    assert any('heure' in s.lower() for s in d['limites'])


def test_circular_aspect_and_cache():
    import meteo_cosmique as M
    aspects = M.transits({'Mars':{'longitude':359}}, {'Soleil':{'longitude':1}})
    assert len(aspects)==1 and aspects[0]['orb']==2
    assert aspects[0]['aspect']=='conjonction'
    M.ephemerides_jour.cache_clear()
    first = M.positions_utc(datetime(2026,9,13,12,10,tzinfo=timezone.utc))
    M.positions_utc(datetime(2026,9,13,12,11,tzinfo=timezone.utc))
    assert M.ephemerides_jour.cache_info().misses == 1
    assert M.ephemerides_jour.cache_info().hits == 1
    first['Soleil']['longitude'] = -1
    assert M.positions_utc(datetime(2026,9,13,12,10,tzinfo=timezone.utc))['Soleil']['longitude'] >= 0


def test_interpolated_positions_agree_with_engine_samples():
    import ephemeride as E
    import meteo_cosmique as M
    for now in (datetime(2026,9,13,12,tzinfo=timezone.utc), datetime(2026,9,13,23,59,tzinfo=timezone.utc)):
        interpolated = M.positions_utc(now)
        for nom in M.CORPS:
            reference = E.longitude(nom, now.replace(tzinfo=None), 0, 0, 0)['longitude']
            # Interpolation error only; this does not validate the underlying ephemeris.
            assert abs((reference-interpolated[nom]['longitude']+180)%360-180) < .01


def test_windows_start_at_actual_ascendant_change(monkeypatch):
    import meteo_cosmique as M
    from datetime import timedelta
    monkeypatch.setattr(M,'maintenant',lambda:datetime(2026,9,13,12,tzinfo=timezone.utc))
    d = request(localisation={'latitude':43.6,'longitude':1.44}).json()
    durations = set()
    for previous,w in zip(d['fenetres'], d['fenetres'][1:]):
        start = datetime.fromisoformat(w['debut'])
        assert M.angles_locaux(start,43.6,1.44)[0]['signe'] == w['ascendant']
        assert M.angles_locaux(start-timedelta(minutes=1),43.6,1.44)[0]['signe'] == previous['ascendant']
        durations.add((datetime.fromisoformat(w['fin'])-start).total_seconds())
    assert len(durations)>2  # never fake fixed two-hour slots


def test_polar_location_keeps_personal_transits_with_explanation():
    d=request(localisation={'latitude':80,'longitude':10}).json()
    assert d['local'] is None and d['fenetres']==[]
    assert d['positions'] and d['natal_complet']
    assert any('66°' in s for s in d['limites'])


def test_english_weather_translates_reading_without_changing_calculations(monkeypatch):
    import meteo_cosmique as M
    monkeypatch.setattr(M, 'maintenant', lambda: datetime(2026,9,13,12,tzinfo=timezone.utc))
    location = {'latitude':43.6, 'longitude':1.44}
    fr = M.calculer(_FICHE, 'Europe/Paris', location)
    en = M.calculer(_FICHE, 'Europe/Paris', location, langue='en')
    assert [t['nom'] for t in en['tendances']] == ['Focus', 'Drive', 'Sociability']
    assert [t['intensite'] for t in en['tendances']] == [t['intensite'] for t in fr['tendances']]
    assert [t['orb'] for t in en['transits']] == [t['orb'] for t in fr['transits']]
    assert {k:v['longitude'] for k,v in en['positions'].items()} == {k:v['longitude'] for k,v in fr['positions'].items()}
    assert 'Sun in local house' in en['lecture']
    assert 'Symbolic reading' in en['limites'][0]
    assert en['local']['ascendant']['signe'] in M.SIGNES_EN.values()
    for a,b in zip(fr['fenetres'], en['fenetres']):
        assert a['debut'] == b['debut'] and a['maison_solaire'] == b['maison_solaire']
        assert a['conseil'] != b['conseil']
    assert all(t['niveau'] in ('subtle', 'moderate', 'strong') for t in en['tendances'])


def test_english_partial_and_polar_limits():
    import meteo_cosmique as M
    d = M.calculer({**_FICHE, 'heure_inconnue':True}, 'Europe/Paris', {'latitude':80,'longitude':10}, langue='en')
    assert any('Birth time unknown' in s for s in d['limites'])
    assert any('beyond 66°' in s for s in d['limites'])
