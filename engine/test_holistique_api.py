from test_api_theme import client
import traditions as T


def test_naissance_nom_et_heure_inconnue():
    r = client.post('/portrait', json={'date_naissance':'1990-09-05','prenoms':'Éloïse','nom':'Usage','nom_naissance':'Naissance','heure_naissance':'11:05','heure_inconnue':True})
    assert r.status_code == 200
    d=r.json()
    assert d['traditions']['numerologie_nom']==T.numerologie_nom('Éloïse','Naissance')
    assert 'lune' not in d['theme_complet']['fondations']
    assert 'nakshatra' not in d['traditions']
    assert d['donnees_synthetiques']['matrice_destinee']['centre_E']==12
    assert d['donnees_synthetiques']['profil']['heure'] is None


def test_maya_cycle_unique():
    from datetime import date,timedelta
    results=[T.tzolkin(date(2000,1,1)+timedelta(days=i)) for i in range(260)]
    assert {r.get('kin') for r in results}==set(range(1,261))
    for r in results:
        assert (r['kin']-1)%13+1==r['tonalite']
        assert T.GLYPHES_MAYA[(r['kin']-1)%20]==r['glyphe']


def test_numerologie_unicode_non_latine_ne_plante_pas():
    r=client.post('/portrait',json={'date_naissance':'2000-01-01','prenoms':'李 Éloïse','nom':'王'})
    assert r.status_code==200


def test_polarite_ne_change_pas_les_calculs():
    fiche={'date_naissance':'1990-09-05','prenoms':'Test','nom':'Unit'}
    a=client.post('/portrait',json={**fiche,'polarite':'feminine'}).json()
    b=client.post('/portrait',json={**fiche,'polarite':'masculine'}).json()
    assert a['traditions']==b['traditions']


def test_date_minimale_valide_ne_plante_pas():
    assert client.post('/portrait', json={'date_naissance':'0001-01-01'}).status_code == 200


def test_aucune_correspondance_de_nom_inventee():
    r=client.post('/portrait',json={'date_naissance':'2000-01-01','prenoms':'李雷'})
    assert r.status_code==200
    assert 'arbre_vie' not in r.json()['traditions']


def test_lecture_ia_recoit_les_donnees_structurees(monkeypatch):
    import llm
    import asyncio
    captured={}
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'choices':[{'message':{'content':'Lecture test'}}]}
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,url,**kwargs):
            captured.update(kwargs['json'])
            return Response()
    monkeypatch.setattr(llm.httpx,'AsyncClient',Client)
    d=client.post('/portrait',json={'date_naissance':'1990-09-05','prenoms':'Test'}).json()
    result=asyncio.run(llm.approfondir_lecture(d['portrait'],d['empreinte'],'français',{'base_url':'https://test.invalid','cle':'test','modele':'test'},d['donnees_synthetiques']))
    assert result=='Lecture test'
    prompt=captured['messages'][1]['content']
    assert '"centre_E": 12' in prompt
    assert '"heure": null' in prompt
    assert '"bazi"' not in prompt
