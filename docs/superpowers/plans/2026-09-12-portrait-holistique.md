# Portrait holistique — Implementation Plan

> Exécution : subagent-driven-development pour les modules indépendants, intégration et validation par l'agent principal.

**Goal:** Livrer les trois lots validés dans l'application existante.
**Architecture:** Calculs Python purs en modules dédiés ; intégration via traditions.calculer et API existante. SVG générés depuis les résultats, contenus didactiques centralisés ; même calcul pour affichage, IA et export.
**Tech Stack:** Python / FastAPI / HTML CSS JavaScript natif / SVG.

## Global Constraints
- Interface française et anglaise, aucune clé nécessaire aux calculs.
- Ne pas attribuer de résultats aux champs absents ; polarité facultative sans effet mathématique.
- Ne pas confondre Tzolkin traditionnel et Dreamspell, ni correspondance moderne et tradition historique.
- Nom de naissance rétrocompatible, exports et profils conservés.

## Tâches et vérification
- [x] Calculs : créer engine/holistique.py et engine/test_holistique.py. Exposer calculer(fiche)->dict, matrice_destinee(date)->dict ; clés matrice_destinee, bazi, arbre_vie, celte_lunaire et compléments maya/vedique. Tester référence 1990-09-05, réduction 22/23/29/99, année bissextile, absence d'heure, limites des mois solaires. Vérifier avec python3 -m pytest engine/test_holistique.py -q.
- [x] Didactique : compléter engine/significations.py pour les dix aspects, majeur/mineur/orbe/exactitude avec tests engine/test_aspects_pedagogie.py. Relier les identifiants au frontend existant.
- [x] Intégration : main.py, llm.py, engine/traditions.py, engine/theme_complet.py. Données structurées source unique, nom_naissance prioritaire pour numérologie, heure inconnue explicite, aucun résultat lunaire arbitraire. Tests API et prompt sans appel réseau.
- [x] UI : static/index.html et fichiers static/holistique.js/css autonomes servis par FastAPI ; formulaire, filtre des doublons, roue mobile non sticky, cartes des nouvelles traditions et SVG matrice/Arbre de Vie. Réutiliser style existant et aide accessible.
- [x] Exports : intégrer matrice aux posters, fournir SVG propre et PNG dimensionné, inclure dans HTML autonome et print.
- [x] QA : suite pytest complète ; Playwright mobile 375/390/768 et desktop, défilement, aide clavier/tactile, nom/heure sauvegardés, vérification export et rendu imprimé ; revue de diff et rapport des limites.

## Preuves

Voir `docs/verification-2026-09-12.md`. Revue et corrections intégrées. Changements conservés sur `feat/portrait-holistique`, sans publication distante.
