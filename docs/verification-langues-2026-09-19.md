# FR/EN et horoscope traduit sans clé — 19 septembre 2026

- FR/EN transmis aux lectures IA et à la météo ; l’horoscope gratuit utilise sa source anglaise en EN et le modèle local Argos/OPUS EN→FR en FR.
- Voix choisie dans la langue du texte ; changement de langue annule les anciennes lectures et invalide les réponses périmées.
- Textes météo, conseils horaires, signes, légendes, valeurs de traditions et interface localisés. Les noms propres traditionnels restent des noms propres.
- Traduction CTranslate2 CPU, modèle EN→FR 1.9 épinglé et téléchargement SHA-256 vérifié. Cache mémoire limité à 128 textes publics ; aucune base de données, clé ou appel de traduction distant.
- Docker installe le modèle pendant le build, avec sa notice OPUS-MT CC-BY 4.0. Installation locale documentée dans les README.

## Vérification

- `python -m pytest engine -q --disable-warnings` : 227 réussis (Python 3.11).
- `node --test tests/*.test.js` : 19 réussis.
- Traduction réelle avec `socket.socket.connect` remplacé par une exception : réussie sans réseau. « Take time to rest today. Share your ideas with someone you trust, and keep an open mind. » devient « Prenez le temps de vous reposer aujourd'hui. Partagez vos idées avec quelqu'un en qui vous avez confiance, et gardez l'esprit ouvert. »
- Playwright visible, vrai serveur : calcul portrait, GPS, conseils horaires, horoscope API réel traduit localement, transitions FR → EN → FR, clé vide, vue mobile 390 px, aucune erreur JavaScript ni débordement horizontal.
- Noms de signes conservés en anglais par le modèle normalisés en français (test ajouté après contrôle du résultat réel).
- `git diff --check` : propre.

## Limite de vérification

Docker n’était pas démarré sur cette machine : l’image complète n’a pas été construite ici. Le téléchargement du modèle, son empreinte, l’inférence locale et les parcours serveur/navigateur ont été exécutés. Une reconstruction de l’image est nécessaire pour livrer le modèle au serveur déployé.
