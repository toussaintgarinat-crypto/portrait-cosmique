# Vérification — extensions holistiques

## Résultats

- Référence initiale : 139 tests Python réussis.
- Après intégration : **162 tests Python réussis** (`python3 -m pytest -q --disable-warnings`). Les avertissements de dépréciation proviennent de l'environnement Python 3.14 / pytest-asyncio / FastAPI préexistant.
- Compilation JavaScript des deux scripts réellement servis : `node --check`, succès.
- Revue backend et intégration : cas année 1, nom sans lettres latines et ordre des scripts au rechargement corrigés ; traductions complémentaires et contrôles inertes dans l'HTML exporté corrigés.

## Navigateur Chromium

Vérifications sur 375, 390, 768 et 1280 pixels :

- Avant correction, à 390 px : roue sticky à 12 px, chevauchement du tableau reproduit.
- Après correction : roue en position statique, aucun chevauchement ni débordement horizontal de page.
- Sélection des points A/C de la matrice au clic et au clavier, résultat attendu affiché.
- Sur téléphone simulé tactile : aide ouverte dès le premier toucher après correction des événements de survol/focus ; régression reproduite puis corrigée.
- Dix aides d'aspects présentes ; aide du semi-sextile contenant 30° ; distinction majeurs/mineurs accessible.
- Heure inconnue : carte masquée, matrice conservée, poster ciel désactivé.
- Passage FR/EN ; nom de naissance, heure inconnue et offset restaurés après sauvegarde et rechargement du profil, puis nouveau calcul réussi.
- SVG téléchargé : vectoriel autonome, sans attributs de contrôle interactif.
- PNG téléchargé : 3 000 × 3 000 px, chunk pHYs à 11 811 pixels/mètre (299,9994 DPI). Décodage et vérification Pillow réussis.
- Export HTML ouvert dans un contexte hors connexion : matrice visible, détails utilisables, cartes d'arcanes statiques, aucune erreur JavaScript.
- Impression : ouverture des sections, couleurs de texte adaptées au papier et matrice conservée ; inspection visuelle des captures.

## Périmètre des preuves

La vérification mobile est une simulation navigateur ; elle ne constitue pas un essai sur chaque appareil Safari/iOS ou Android. Aucun appel payant à un modèle IA : le payload structuré est vérifié avec un transport simulé. Aucun déploiement distant réalisé. Les limites des calculs sont détaillées dans `holistique-conventions.md`.
