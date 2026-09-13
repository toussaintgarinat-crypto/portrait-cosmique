# Météo cosmique Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development for isolated UI work and review. Parent implements engine/API and integrates.

**Goal:** Livrer des transits personnels et une météo locale opt-in fonctionnels dans Horoscope.
**Architecture:** Moteur pur `engine/meteo_cosmique.py`, endpoint POST `/meteo-cosmique`, contrôleur `static/meteo-cosmique.js`. Réutilisation Fiche, fiche_calcul, theme_complet, ephemeride, maisons, fuseaux.
**Tech Stack:** Python/FastAPI, JavaScript natif, CSS existant, pytest, Playwright.

## Global Constraints
- Aucun GPS automatique ; aucune persistance des coordonnées.
- Aucun aspect inventé ni jauge numérique ; limites astronomiques visibles.
- Données natales indépendantes du lieu courant ; UTC serveur, fuseau IANA client.

## Tasks
- [x] Engine/API : écrire tests de contrat avant implémentation ; lancer `python -m pytest engine/test_meteo_cosmique.py -q` et constater endpoint 404 ; construire positions globales horaires en cache UTC borné, transits majeurs (orbe 3°), angles locaux et fenêtres aux changements de signe à la minute ; valider fuseau, coordonnées et fiche. Tests jour local, DST, géocentrisme, invalides, heure inconnue et fenêtre continue.
- [x] UI (agent) : ajouter panneau avant lectures existantes et contrôleur séparé. Tests navigateur des permissions, sélection ville, profil invalidé, réponses périmées et mobile. Parent ajoute injection du script.
- [x] Intégration : exécuter suite Python et parcours navigateur sur serveur isolé, examiner erreurs et captures ; corriger les défauts prouvés.
- [x] Revue : examiner le diff complet et vérifier exigences ; documenter résultats et limites dans README et rapport de vérification ; intégrer livraison dans le répertoire utilisateur.

## API contract
Request: `{fiche: Fiche, fuseau: string, localisation?: {latitude:number, longitude:number}}`.
Response: `{instant_utc, date_locale, fuseau, positions, transits, tendances, lecture, limites, natal_complet, local, fenetres}`.
`positions` = dict corps → `{longitude,signe}`. `transits` = array `{mobile,natal,aspect,orb,tonalite,origine}` (origine transit/local). `tendances` = array `{nom,niveau,tonalite,explication,facteurs: transits[]}`. `lecture` string ; `limites` string[]. `local` null or `{ascendant:{longitude,signe},milieu_du_ciel:{longitude,signe},maisons:[{maison,cuspe,signe}],fuseau,systeme}`. `fenetres` array `{debut,fin,ascendant,maison_solaire,domaine,conseil}` timestamps UTC ISO covering local browser day. `natal_complet` boolean.
