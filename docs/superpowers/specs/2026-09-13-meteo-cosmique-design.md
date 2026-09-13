# Horoscope et météo cosmique — périmètre approuvé

Transits personnels calculés depuis les longitudes natales, journée dans le fuseau courant du navigateur, puis météo locale volontaire par géolocalisation ou ville saisie. Aucun appel de géolocalisation avant clic explicite. Refus, expiration ou indisponibilité : horoscope sans localisation conservé. Position de session seulement, indépendante du lieu de naissance, actualisable et désactivable.

Lecture déterministe Ici & Maintenant, trois tendances qualitatives (Focus, Élan, Sociabilité ; discret/modéré/marqué) et leurs facteurs. Les tendances expriment l'intensité symbolique, pas une mesure psychologique. Fenêtres locales calculées aux changements d'ascendant par signe, maisons locales en signes entiers explicitement identifiées. Date et heure affichées dans le fuseau navigateur ; fuseau du lieu choisi affiché également.

Réutiliser les éphémérides approchées du moteur et afficher leur limite (jusqu'à plusieurs degrés pour certaines planètes). Cache borné de séries horaires par journée UTC, interpolation circulaire à la minute. Domification locale recalculée à la minute. Heure natale inconnue : Soleil de midi explicitement approximatif, aucun angle natal inventé.

Tests : transits croisés, conservation des positions globales lors d'un déplacement, rotation des angles, journée UTC/DST, cache, refus GPS, ville, invalidation du profil et des requêtes, affichage mobile. Pas de dépendance ni service payant ajouté.
