import aspects
import significations as S
import theme_complet as TC


def test_tous_aspects_expliques_dans_les_deux_langues():
    for langue in ('fr', 'en'):
        entries = {x['id']: x for group in S.glossaire(langue) for x in group['items']}
        for key, aspect in aspects.ASPECTS.items():
            entry = entries.get('theme_aspect_' + key)
            assert entry is not None, key
            assert str(aspect['angle']) + '°' in entry['definition']
        for key in ('theme_aspects_majeurs', 'theme_aspects_mineurs', 'theme_orbe', 'theme_exactitude'):
            assert key in entries


def test_sans_heure_aucune_lune_inventee():
    result = TC.theme_complet({'date_naissance':'1990-09-05'})
    assert 'lune' not in result['fondations']
    assert result['meta']['heure_connue'] is False
