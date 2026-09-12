# Portrait holistique — conception validée le 12 septembre 2026

Objectif : enrichir Portrait Cosmique sans dupliquer les modules existants ni inventer de résultats en cas de données absentes.

## 1. Lisibilité
Le Portrait conserve synthèse et traditions, la Carte astro porte les détails occidentaux. Chaque aspect majeur et mineur dispose d'une définition accessible par la même aide que les autres points. Une introduction explique angle, orbe et distinction majeur/mineur. Sur mobile, la roue suit le flux normal et les tableaux restent consultables sans chevauchement.

## 2. Matrice et saisie
Réduction par somme des chiffres jusqu'à 22 (ce n'est pas un modulo arithmétique). A=jour réduit, B=mois, C=somme réduite des chiffres de l'année, D=réduction A+B+C, E=réduction A+B+C+D. Référence : 1990-09-05 → 5,9,19,6,12. Octogramme SVG accessible, points sélectionnables et lecture des 22 arcanes. Canaux amour/finances présentés comme axes symboliques sans nombres non spécifiés. Nom de naissance distinct du nom d'affichage, polarité facultative sans pondération des calculs. Heure inconnue explicite : pas de carte calculée artificiellement à midi.

## 3. Traditions et récit
BaZi : quatre piliers, maître du jour, répartition des cinq éléments et Yin/Yang, convention horaire et calendrier explicités. Védique existant enrichi en position sidérale et pada avec précision honnête. Tzolkin traditionnel enrichi avec numéro de cycle 1–260 sans l'assimiler au Dreamspell. Calendrier des 13 arbres modernes clairement identifié. Arbre de Vie : sephiroth et correspondance personnelle présentées comme convention symbolique moderne, pas comme calcul traditionnel universel. Le récit reçoit les données structurées effectivement calculées, même sans configuration IA le résultat reste lisible.

## 4. Exports
Matrice imprimable, SVG vectoriel autonome sans commandes interactives, poster PNG à taille explicite adaptée à 300 DPI. Conserver exports existants et profils sauvegardés.

## Validation
Tests de référence et limites calendaires ; régression API et heure absente ; glossaire français/anglais ; navigateur desktop/mobile avec défilement, interactions, profils, export SVG/PNG et impression.
