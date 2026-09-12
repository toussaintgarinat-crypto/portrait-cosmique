# Corrections navigation et fuseau automatique

Demandes : nom de famille sans répétition des prénoms ; UTC automatique depuis lieu/date/heure ; matrice dans un onglet ; modules complémentaires intégrés aux Traditions natales avec le même glossaire interactif.

- [x] Résoudre localement le fuseau IANA depuis les coordonnées et le décalage historique via tzdata. Tester été/hiver, fractions d'heure, date de naissance historique, heures ambiguës/inexistantes et coordonnées invalides.
- [x] Intégrer /fuseau et recalcul côté /portrait et /theme, sans écraser les conventions des anciens clients explicites. Formulaire en mode automatique ; invalider les résultats obsolètes quand date, heure ou ville change. Restaurer les profils sans réutiliser un offset périmé.
- [x] Libellé nom de famille et exemple Dupont-Martin sans prénoms ; onglet Matrice de destinée ; toutes les autres nouvelles cartes dans la section Traditions natales existante. Conserver exports et navigation mobile.
- [x] Ajouter les définitions FR/EN au glossaire central ; icônes identiques aux anciennes, aide sur modules, champs et points/axes de matrice, clavier/tactile et export HTML.
- [x] Vérifier suite Python, navigateur bureau/mobile, changement de date et lieu, rechargement des profils, export HTML et poster SVG.
- Commit et push autorisés par la nouvelle demande utilisateur ; contrôle du déploiement après publication.
