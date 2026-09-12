# Vérification navigation et fuseau automatique — 12 septembre 2026

Vérifications réalisées avant publication. Commit et push autorisés ensuite par l’utilisateur.

- Suite Python : **190 tests réussis** (`/private/tmp/portrait-tz-venv/bin/python -m pytest engine -q --disable-warnings`). Avertissements de dépréciation existants pytest/Pydantic.
- Navigateur Chromium avec viewport tactile 390 × 844, puis largeurs 375, 768 et 1280 : aucun débordement horizontal détecté.
- UTC automatique : Toulouse été/hiver 1990, Kathmandu +5:45, invalidation du lieu précédent, heure répétée du 27 octobre 2024 avec choix explicite, heure inexistante du 31 mars 2024.
- Exemple de nom de famille, six modules dans Traditions natales, matrice absente du Portrait et présente dans son onglet.
- Aides tactiles BaZi et point A de la matrice ; dix icônes dans la matrice ; activation SVG du point A.
- Rechargement du profil avec recalcul du fuseau, parcours sans heure et traduction anglaise.
- Export SVG sans tabindex interactif ; export HTML autonome ouvert dans un second onglet avec matrice visible. Aucune erreur JavaScript dans les deux pages.
- Contrôle visuel de la capture mobile ; correction du libellé DST masqué que le CSS global rendait visible, puis nouvelle exécution réussie du parcours.

Serveur local testé : http://127.0.0.1:8413. Script navigateur : `/private/tmp/playwright-test-portrait-mobile.js` via le lanceur du skill Playwright. Seul le géocodage `/geo` est simulé (Toulouse/Kathmandu) ; `/fuseau`, `/portrait` et les exports sont réels. Le contrôle de production est effectué après le push.
