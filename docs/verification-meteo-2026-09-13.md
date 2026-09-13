# Vérification — Météo cosmique — 13 septembre 2026

## Périmètre

Horoscope : transits majeurs réels calculés par le moteur approché existant, tendances qualitatives expliquées, lieu courant opt-in GPS ou ville confirmée, Ici & Maintenant et fenêtres locales. Les lectures API/IA historiques restent distinctes et ne consomment pas ces transits.

## Résultats

- Baseline : 197 tests Python passaient avant modification dans `/private/tmp/portrait-tz-venv` (le `.venv` du dépôt ne possédait pas tzfpy).
- Suite livrée : **215 tests Python passent**, dont 18 nouveaux cas météo. Commande : `python -m pytest -q -p no:asyncio --disable-warnings`. Les avertissements restants sont les dépréciations FastAPI/Starlette sous Python 3.14.
- **7 tests JavaScript passent** : `node --test tests/meteo-cosmique.test.js`. Dates Intl, normalisation du formulaire, profil invalide, réponse GPS après désactivation, réponse météo après changement de profil, temporisation de l’actualisation pendant localisation, résultat conservé après échec réseau.
- Playwright Chromium visible : vrai formulaire → API portrait/fuseau → transits → refus GPS → confirmation de ville → calcul local/fenêtres → désactivation → invalidation profil. Vérification du panneau initialement masqué, coexistence avec les lectures complémentaires, maintien des détails ouverts au rafraîchissement, absence de coordonnées courantes dans localStorage et absence de modification de la naissance.
- Affichage contrôlé à 1280 px et 390 px : pas de débordement horizontal ni erreur JavaScript. Captures examinées dans `/private/tmp/meteo-desktop.png` et `/private/tmp/meteo-mobile.png`.
- Tests navigateur reproductibles : `node /Users/garinat_t/.agents/skills/playwright-skill/run.js /private/tmp/playwright-test-meteo-cosmique.js` ; URL par défaut `http://127.0.0.1:6244`, variable `METEO_URL` possible.
- Géocodage réel `/geo?ville=Castres%20France` : réponse valide Nominatim. Un homonyme dans l’Aisne a été renvoyé, ce qui confirme l’importance de la sélection explicite du résultat et d’une recherche précisant le département. Le parcours automatisé utilise une réponse de géocodage contrôlée pour Paris ; les calculs météo restent réels.
- `node --check` sur les scripts modifiés et `git diff --check` : conformes.

## Garanties testées et limites

Les positions globales et aspects géocentriques sont invariants au changement de lieu ; les angles changent. Les fenêtres couvrent sans trou les jours locaux de 23, 24 et 25 heures, leurs bornes correspondent aux changements effectifs de signe au pas d’une minute. L’erreur ajoutée par l’interpolation a été comparée au moteur direct sur des échantillons (moins de 0,01°) : ce test ne valide pas la précision du moteur lui-même.

Le cache global immuable est borné à huit journées UTC, avec 25 échantillons horaires par jour et aucune donnée personnelle. Les coordonnées de session ne sont ni suivies en continu ni persistées par l’application. Le comportement natif de consentement est simulé dans les tests ; aucun GPS physique n’a été mesuré.

Les éphémérides existantes peuvent différer de plusieurs degrés de références précises. Les niveaux sont symboliques, non des mesures de santé ou de psychologie. Sans heure natale : Soleil approximé à midi uniquement. Ciel local non proposé à partir de 66° de latitude, avec maintien des transits et explication. Maisons locales en signes entiers ; les fenêtres ne sont pas des prédictions de réussite. Aucune validation d’exactitude scientifique ou de pertinence prédictive n’est revendiquée.
