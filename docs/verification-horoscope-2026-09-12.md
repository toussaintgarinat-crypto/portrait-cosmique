# Horoscope du jour — intégration et vérification

## Fonctionnement

- Onglet intégré à la navigation existante et à l’export HTML.
- Mode API gratuit via le serveur : signe solaire uniquement, texte anglais, date exacte du fournisseur affichée. L’ancien domaine redirige vers `https://freehoroscopeapi.com/api/v1/get-horoscope/daily`. Contrat réel vérifié : `data.horoscope`, `data.date`.
- Mode IA : configuration existante personnelle ou serveur (`llm._config`), Soleil/Lune/ascendant disponibles et date locale du navigateur. Texte français ; pas de transits inventés ni de remplacement silencieux par le portrait natal.
- Audio natif demandé en `fr-FR` : écouter, arrêter, fin et erreur, arrêt au changement d’onglet ou de profil. La voix française ne traduit pas le texte API anglais.
- Réponses obsolètes annulées/ignorées, texte rendu par `textContent`, nouveau calcul exigé si le formulaire a changé.
- JavaScript dans `static/horoscope.js`, injecté dans le HTML servi comme les autres modules existants ; pas de dépendance supplémentaire.

## Vérifications

- `python -m pytest engine -q --disable-warnings` avec `/private/tmp/portrait-tz-venv/bin/python` : **197 tests réussis**. Avertissements de dépréciation existants.
- Sept tests serveur ajoutés : schéma fournisseur actuel, prompt et configuration IA, absences de signes, validation, erreurs fournisseur, texte vide, conservation de la date fournisseur.
- Chromium tactile 390 × 844, puis 375/768/1280 px : onglet, requête réelle à l’API gratuite via le serveur local, export HTML autonome, lecture sans heure de naissance, texte non interprété comme HTML, changement de profil, réponse tardive ignorée, interface anglaise ; aucun débordement horizontal ni erreur JavaScript.
- Audio : API simulée pour vérifier `fr-FR`, écouter/arrêter/fin et changement d’onglet. Le son audible et les voix installées sur le téléphone réel ne sont pas vérifiés.
- IA : réponses et erreurs simulées, transmission de la configuration et du prompt vérifiée ; aucun appel payant réel au fournisseur LLM.
- Capture mobile inspectée : `/private/tmp/portrait-horoscope-mobile.png`.
- Test navigateur : `/private/tmp/playwright-test-portrait-mobile.js`, serveur `http://127.0.0.1:8414`.

Vérifications avant publication sur `feat/horoscope-du-jour`. Commit et push sur main autorisés ensuite ; contrôle de production après déploiement.
