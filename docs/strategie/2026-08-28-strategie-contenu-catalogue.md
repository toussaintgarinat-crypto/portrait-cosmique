# Portrait Cosmique — Stratégie de Contenu & Catalogue Graphique

**Date :** 2026-08-28
**Statut :** référence stratégique (document fondateur, fourni par l'auteur du projet)
**Liens :** premier sous-projet dérivé → `superpowers/specs/2026-08-28-dashboard-stats-design.md`

Ce document récapitule la stratégie de gamification par les statistiques ainsi que
l'inventaire complet des éléments graphiques et métriques à développer pour l'application
Portrait Cosmique et ses déclinaisons en Print on Demand (T-shirts, Mugs, Posters, Tote-bags).

## 1. Concept global de gamification par la data

L'objectif est d'utiliser les données d'achat et d'utilisation de l'application pour créer
un levier d'engagement viral et de preuve sociale. En affichant les statistiques de vente
selon les caractéristiques astrologiques et numérologiques des utilisateurs, on active la
curiosité, l'esprit de clan et l'achat impulsif.

## 2. Grille des éléments & formes pour la création graphique

Matrice complète des symboles, formes et thématiques à concevoir ultérieurement sous forme
de visuels vectoriels (SVG / PNG haute résolution) pour l'impression textile et objet.

| Catégorie | Élément / Thématique | Formes & Symboles à dessiner | Supports produits adaptés |
|---|---|---|---|
| Astrologie occidentale | 12 signes du zodiaque | Glyphes astrologiques, constellations, illustrations minimalistes des constellations (Bélier à Poissons) | T-shirts (poitrine/dos), mugs, posters encadrés, tote-bags |
| Éléments astraux | Feu, Terre, Air, Eau | Triangle vers le haut (Feu), triangle barré (Terre), triangle avec ligne (Air), triangle inversé (Eau) | Hoodies, casquettes, design dos de t-shirt |
| Astrologie chinoise | 12 animaux du zodiaque | Illustrations stylisées (Rat, Bœuf, Tigre, Lapin, Dragon, Serpent, Cheval, Chèvre, Singe, Coq, Chien, Cochon) | Mugs gourdes, posters de naissance, carnets de notes |
| Numérologie | Chemins de vie (1 à 9, 11, 22, 33) | Géométrie sacrée, chiffres stylisés filaires, cercles concentriques et mandalas numérologiques | Posters minimalistes A3/A4, mugs céramique |
| Cartographie céleste | Carte du ciel & thème astral | Roue zodiacale complète, lignes d'aspects (trigones, carrés), position des planètes en cercle vectoriel | Posters grand format, t-shirts oversize dos |
| Polarités & énergies | Yin & Yang / Solstice | Symbole Yin-Yang revisité, soleil et lune entrelacés, phases lunaires | Tote-bags, gourdes inox, sweatshirts |

## 3. Dashboard de stats ludiques : duels & comparaisons

Indicateurs et widgets à implémenter pour la section statistiques du site :

- **La Guerre des Éléments** — jauge en pourcentage (Feu vs Terre vs Air vs Eau) des
  acheteurs du mois.
- **Le Podium Zodiaque** — classement en direct du Top 3 des signes les plus acheteurs.
- **Le Match des Opposés** — duel visuel en temps réel (ex. Bélier vs Balance, Lion vs
  Scorpion).
- **Statistiques d'achat** — comparaison « Achat pour soi-même » vs « Cadeau offert »
  selon le signe.
- **Les Nombres Maîtres** — compteur dédié pour les chemins de vie 11, 22 et 33.

## 4. Feuille de route d'exécution

1. Finaliser le prototype web et l'export des visuels.
2. Créer le lot de visuels pour chaque signe, animal et forme géométrique.
3. Connecter l'API de Print on Demand (Printify / Gelato) avec Stripe.
4. Déployer le widget de statistiques anonymisées sur l'application Vercel.
