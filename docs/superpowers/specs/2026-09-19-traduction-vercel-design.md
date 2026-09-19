# Traduction française sur Vercel

## Problème

L'endpoint public `POST /horoscope-du-jour` renvoie une erreur 503 pour une
demande `langue: "fr"`. Le navigateur affiche : « La traduction française
locale est indisponible ».

La traduction EN→FR est actuellement livrée uniquement dans le Dockerfile :
`requirements-translation.txt` est installé et `scripts/installer_traduction.py`
télécharge le modèle Argos/OPUS au build de l'image. Vercel n'exécute pas ce
Dockerfile. Il ne reçoit ni les dépendances `ctranslate2` / `sentencepiece` /
`numpy`, ni le modèle `models/en-fr/` (ignoré par Git).

## Décision

Conserver l'architecture actuelle de l'endpoint et rendre le déploiement Vercel
autonome :

1. Les dépendances de traduction font partie de `requirements.txt`, le fichier
   que le runtime Python Vercel installe.
2. Une commande de build Vercel lance l'installateur existant. Celui-ci
   télécharge le modèle, vérifie son SHA-256 puis l'extrait dans
   `models/en-fr/`.
3. La configuration Vercel inclut explicitement `models/en-fr/**` dans le
   bundle de `main.py` et réserve une durée d'exécution suffisante à la
   première inférence.
4. Le téléchargement reste strictement au build ; aucune requête de modèle ni
   clé supplémentaire n'est requise à l'exécution.

## Hors périmètre

- Aucun changement de texte, de bouton ni de contrat de l'API horoscope.
- Aucun envoi vers un traducteur tiers.
- Aucun changement de l'option IA personnalisée.
- Aucun rapatriement de l'API vers Proxmox/Workplace dans ce correctif.

## Vérification

Après déploiement, appeler l'endpoint public avec `mode: "api"`, `langue:
"fr"` et un signe valide. Le statut doit être 200, `langue` doit être `fr` et
le texte doit être non vide. Le même parcours sera contrôlé dans le navigateur
via le bouton « Horoscope gratuit · français ».

## Limites assumées

Le modèle et ses bibliothèques ajoutent environ 250 Mo décompressés à la
fonction. Cela reste sous la limite Python Vercel documentée de 500 Mo, mais
augmente le temps de build et peut allonger un démarrage à froid. Le futur
backend Docker/Proxmox pourra supprimer cette contrainte de Vercel.
