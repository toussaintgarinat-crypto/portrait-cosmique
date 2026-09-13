"""Horoscope endpoints: provider contracts and explicit failures."""
import httpx
import main
from test_api_theme import client


def fake_provider(monkeypatch, payload, status=200):
    calls = []
    class Provider:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url, **kwargs):
            calls.append((url, kwargs))
            return httpx.Response(status, json=payload, request=httpx.Request('GET', url))
        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return httpx.Response(status, json=payload, request=httpx.Request('POST', url))
    monkeypatch.setattr(main.httpx, 'AsyncClient', Provider)
    return calls


def test_api_current_response_contract(monkeypatch):
    calls = fake_provider(monkeypatch, {'data': {'date': '2026-09-12', 'horoscope': 'Daily reading.'}})
    r = client.post('/horoscope-du-jour', json={'mode':'api','date':'2026-09-12','soleil':'Vierge'})
    assert r.status_code == 200
    assert r.json() == {'texte':'Daily reading.','date':'2026-09-12','source':'api','langue':'en'}
    assert calls[0][1]['params']['sign'] == 'Virgo'


def test_ia_reuses_configuration_and_preserves_missing_moon(monkeypatch):
    seen = []
    monkeypatch.setattr(main.llm, '_config', lambda cfg: (seen.append(cfg) or ('https://example.test/v1','secret','test-model')))
    calls = fake_provider(monkeypatch, {'choices':[{'message':{'content':'Une lecture du jour.'}}]})
    r = client.post('/horoscope-du-jour', json={'mode':'ia','date':'2026-09-12','soleil':'Vierge','ascendant':'Scorpion'})
    assert r.status_code == 200
    assert seen == [None]
    payload = calls[0][1]['json']
    assert payload['model'] == 'test-model'
    assert '"lune": null' in payload['messages'][1]['content']
    assert '2026-09-12' in payload['messages'][1]['content']
    assert 'transit' in payload['messages'][0]['content']
    assert r.json()['langue'] == 'fr'


def test_no_ia_configuration_is_explicit(monkeypatch):
    monkeypatch.setattr(main.llm, '_config', lambda cfg: ('','',''))
    r = client.post('/horoscope-du-jour',json={'mode':'ia','date':'2026-09-12','soleil':'Vierge'})
    assert r.status_code == 503
    assert 'texte' not in r.json()


def test_bad_inputs_rejected():
    for patch in ({'date':'invalid'},{'soleil':'invalid'},{'lune':'instructions'},{'mode':'bad'}):
        r = client.post('/horoscope-du-jour',json={'mode':'api','date':'2026-09-12','soleil':'Vierge',**patch})
        assert r.status_code == 422


def test_provider_failure_and_empty_text(monkeypatch):
    for payload, status in (({},503),({'data':{'horoscope':''}},200),({'data':None},200)):
        fake_provider(monkeypatch, payload, status)
        r = client.post('/horoscope-du-jour',json={'mode':'api','date':'2026-09-12','soleil':'Vierge'})
        assert r.status_code == 502
        assert 'texte' not in r.json()


def test_ia_personal_configuration_and_empty_response(monkeypatch):
    config={'base_url':'https://example.test/v1','cle':'test-key','modele':'test-model'}
    seen=[]
    monkeypatch.setattr(main.llm, '_config', lambda cfg: (seen.append(cfg) or (cfg['base_url'],cfg['cle'],cfg['modele'])))
    calls=fake_provider(monkeypatch, {'choices':[{'message':{'content':'   '}}]})
    r=client.post('/horoscope-du-jour',json={'mode':'ia','date':'2026-09-12','soleil':'Virgo','lune':'Aquarius','llm':config})
    assert seen == [config]
    assert calls[0][1]['headers']['Authorization']=='Bearer test-key'
    assert r.status_code==502
    assert 'test-key' not in r.text


def test_api_does_not_mislabel_provider_date(monkeypatch):
    fake_provider(monkeypatch,{'data':{'date':'2026-09-11','horoscope':'Previous day from provider.'}})
    r=client.post('/horoscope-du-jour',json={'mode':'api','date':'2026-09-12','soleil':'Vierge'})
    assert r.status_code==200
    assert r.json()['date']=='2026-09-11'


def test_ia_provider_errors_are_actionable_without_leaking_response(monkeypatch):
    config = {'base_url':'https://example.test/v1','cle':'test-secret','modele':'model'}
    for status, indication in ((401, 'clé API'), (403, 'accès'), (402, 'crédit'), (429, 'limite'), (404, 'modèle')):
        fake_provider(monkeypatch, {'error':'test-secret'}, status)
        r = client.post('/horoscope-du-jour', json={'mode':'ia','date':'2026-09-12','soleil':'Vierge','llm':config})
        assert r.status_code == 502
        assert indication in r.json()['detail']
        assert 'test-secret' not in r.text


def test_api_translation_preserves_provider_date_and_translates_source(monkeypatch):
    calls = fake_provider(monkeypatch, {'data':{'date':'2026-09-11','horoscope':'Take time to rest.'}})
    seen = []
    async def translate(text, config):
        seen.append((text, config))
        return 'Prends le temps de te reposer.'
    monkeypatch.setattr(main.llm, 'traduire_horoscope', translate, raising=False)
    config = {'base_url':'https://example.test/v1','cle':'test-key','modele':'test-model'}
    r = client.post('/horoscope-du-jour', json={'mode':'api','date':'2026-09-12','soleil':'Vierge','traduire_fr':True,'llm':config})
    assert r.status_code == 200
    assert r.json()['texte'] == 'Prends le temps de te reposer.'
    assert r.json()['langue'] == 'fr'
    assert r.json()['date'] == '2026-09-11'
    assert r.json()['source'] == 'api'
    assert seen == [('Take time to rest.', config)]


def test_translation_failure_keeps_english_and_reports_fallback(monkeypatch):
    fake_provider(monkeypatch, {'data':{'date':'2026-09-12','horoscope':'Take time to rest.'}})
    async def translate(*args):
        raise RuntimeError('private-provider-secret')
    monkeypatch.setattr(main.llm, 'traduire_horoscope', translate, raising=False)
    r = client.post('/horoscope-du-jour', json={'mode':'api','date':'2026-09-12','soleil':'Vierge','traduire_fr':True})
    assert r.status_code == 200
    assert r.json()['texte'] == 'Take time to rest.'
    assert r.json()['langue'] == 'en'
    assert 'traduction' in r.json()['avertissement'].lower()
    assert 'private-provider-secret' not in r.text


def test_translation_adapter_uses_config_and_source_only(monkeypatch):
    import asyncio
    calls = fake_provider(monkeypatch, {'choices':[{'message':{'content':'  Prends une pause.  '}}]})
    config = {'base_url':'https://example.test/v1','cle':'test-key','modele':'test-model'}
    result = asyncio.run(main.llm.traduire_horoscope('Take a break.', config))
    assert result == 'Prends une pause.'
    url, request = calls[0]
    assert url == 'https://example.test/v1/chat/completions'
    assert request['headers']['Authorization'] == 'Bearer test-key'
    assert request['json']['model'] == 'test-model'
    assert request['json']['messages'][1]['content'] == 'Take a break.'


def test_empty_translation_keeps_source(monkeypatch):
    fake_provider(monkeypatch, {'data':{'date':'2026-09-12','horoscope':'Take a break.'}})
    async def translate(*args):
        return '   '
    monkeypatch.setattr(main.llm, 'traduire_horoscope', translate)
    r = client.post('/horoscope-du-jour', json={'mode':'api','date':'2026-09-12','soleil':'Vierge','traduire_fr':True})
    assert r.json()['texte'] == 'Take a break.'
    assert r.json()['langue'] == 'en'
    assert r.json()['avertissement']
