from test_api_theme import client


def test_fuseau_paris_ete():
    r=client.post('/fuseau',json={'latitude':43.6,'longitude':1.44,'date_naissance':'1990-09-05','heure_naissance':'11:05'})
    assert r.status_code==200
    assert r.json()['fuseau']=='Europe/Paris'
    assert r.json()['utc_offset']==2


def test_portrait_utc_automatique_ne_reutilise_pas_offset_perime():
    r=client.post('/portrait',json={'latitude':43.6,'longitude':1.44,'date_naissance':'1990-01-05','heure_naissance':'11:05','utc_offset':2,'utc_auto':True})
    assert r.status_code==200
    assert r.json()['donnees_synthetiques']['profil']['utc_offset']==1


def test_heure_ambigue_exige_choix():
    fiche={'latitude':48.86,'longitude':2.35,'date_naissance':'2024-10-27','heure_naissance':'02:30','utc_auto':True}
    assert client.post('/portrait',json=fiche).status_code==422
    assert client.post('/portrait',json={**fiche,'utc_fold':0}).json()['donnees_synthetiques']['profil']['utc_offset']==2
    assert client.post('/portrait',json={**fiche,'utc_fold':1}).json()['donnees_synthetiques']['profil']['utc_offset']==1


def test_aides_holistiques_partagent_glossaire_existant():
    for langue in ('fr','en'):
        d=client.post('/portrait',json={'date_naissance':'1990-09-05','langue':langue}).json()
        ids={v['id'] for g in d['glossaire'] for v in g['items']}
        assert {'matrice_destinee','matrice_A','matrice_E','matrice_amour','bazi','bazi_elements','arbre_vie','celte_13','numerologie_nom','numerologie_ame','maya_kin'} <= ids


def test_theme_refuse_heure_inexistante_et_lieu_manquant():
    fiche={'date_naissance':'2024-03-31','heure_naissance':'02:30','utc_auto':True}
    assert client.post('/theme',json=fiche).status_code==422
    assert client.post('/theme',json={**fiche,'latitude':48.86,'longitude':2.35}).status_code==422


def test_heure_inconnue_ignore_offset_sauvegarde_sans_lieu():
    r=client.post('/portrait',json={'date_naissance':'1990-09-05','heure_naissance':'11:05','heure_inconnue':True,'utc_auto':True,'utc_offset':2})
    assert r.status_code==200
    assert r.json()['donnees_synthetiques']['profil']['utc_offset'] is None


def test_fuseau_coordonnees_manquantes_retourne_erreur_validation():
    assert client.post('/fuseau',json={'date_naissance':'1990-09-05'}).status_code==422
