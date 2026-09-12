# Conventions des calculs holistiques

Ce document fixe les règles du module `engine.holistique`. Les sorties sont des supports
symboliques et culturels, pas des mesures scientifiques ni des prédictions. Les champs
absents ne sont jamais remplacés par une heure, un lieu ou un fuseau arbitraires.

## Contrat de sortie

`calculer(fiche)` accepte `prenoms`, `nom`, `nom_naissance`, `date_naissance`,
`heure_naissance`, `utc_offset`, `latitude` et `longitude`. La date est au format
`YYYY-MM-DD`, l'heure au format `HH:MM` et `utc_offset` est un nombre d'heures par rapport
à UTC, par exemple `2` pour UTC+02:00.

- `matrice_destinee` et `celte_lunaire` sont produits pour toute date valide ;
- `arbre_vie` exige une date et au moins une partie du nom. `nom_naissance` a priorité
  sur `nom` ;
- `bazi` exige date, heure civile et décalage UTC. Sans décalage, il est omis car le
  rapport à une limite de terme solaire ne peut pas être établi proprement ;
- une date invalide produit `{}`. Une heure ou un décalage invalide omet seulement BaZi.

La latitude et la longitude sont acceptées pour la compatibilité du formulaire mais ne
sont pas utilisées dans cette version : aucune correction en temps solaire vrai n'est
appliquée.

## Matrice de destinée

La réduction additionne les chiffres tant que le résultat dépasse 22. Elle n'utilise pas
un modulo. Les cinq points sont :

- A : jour réduit ; B : mois réduit ; C : somme des chiffres de l'année réduite ;
- D : réduction de A+B+C ; E : réduction de A+B+C+D.

Pour le 5 septembre 1990, les valeurs sont A=5, B=9, C=19, D=6 et E=12. Les arcanes
suivent la numérotation 1–21 puis 22 pour Le Mat. Les axes amour et finances sont des
libellés de réflexion sans valeur numérique, score ou promesse prédictive.

## BaZi

Les dix tiges, les douze branches, leur cycle sexagésimal et les tables des tiges de mois
et d'heure suivent la présentation du [Hong Kong Observatory](https://www.weather.gov.hk/en/gts/time/stemsandbranches.htm).
Chaque pilier compte sa tige et sa branche dans les répartitions des cinq éléments et du
Yin/Yang. Le maître du jour est la tige du pilier du jour.

Conventions choisies :

- l'année solaire change à Li Chun, lorsque la longitude solaire atteint 315° ;
- les mois changent aux douze *jie*, espacés ici par secteurs de 30° à partir de 315° ;
- le jour civil change à minuit, avec le 7 janvier 2000 comme jour Jia-Zi de référence ;
- les heures sont les douze périodes civiles de deux heures, Zi allant de 23:00 à 00:59 ;
- l'heure fournie et `utc_offset` servent à construire l'instant. Les coordonnées ne
  corrigent pas l'heure vers un temps solaire local.

La longitude solaire utilise une approximation basse précision des termes usuels de
Jean Meeus (longitude moyenne et équation du centre). Elle convient loin des limites,
mais ne remplace pas une éphéméride. `precision.limite_proche` devient vrai à moins de
0,25° d'un *jie* ; dans ce cas il faut vérifier le pilier avec une éphéméride et les règles
de fuseau historiques. Cette limite représente environ six heures de mouvement solaire.
Les changements exacts peuvent donc différer près d'une frontière. Le choix du passage
du jour à minuit est explicite car certaines écoles utilisent la première moitié de
l'heure Zi.

Le HKO confirme que le cycle commence par Jia-Zi, que les quatre Gan-Zhi forment les
« Eight Characters » et donne les correspondances des mois et heures. Son
[almanach sur les 24 termes solaires](https://www.hko.gov.hk/en/gts/astron2022/files/HKO_almanac_2022.pdf)
décrit leur rôle astronomique. L'interprétation divinatoire n'est pas calculée ici.

## Arbre de Vie

Le module conserve la structure traditionnelle des dix sephiroth et leurs noms. Le fait
qu'il existe dix sephiroth est documenté, entre autres, par
[l'Encyclopædia Britannica de 1911](https://en.wikisource.org/wiki/1911_Encyclop%C3%A6dia_Britannica/Kabbalah).

La personnalisation, elle, est délibérément moderne : somme des chiffres de la date,
valeur cyclique A=1… I=9 du nom latinisé, puis réduction de chaque résultat entre 1 et 10.
Cette méthode n'est pas présentée comme une gématrie hébraïque ou comme une pratique
kabbalistique universelle. Aucun chemin traditionnel entre sephiroth n'est fabriqué.

## Calendrier moderne des treize arbres

Il s'agit du calendrier popularisé au XXe siècle à partir de Robert Graves : treize
périodes de 28 jours, du Bouleau au Sureau, du 24 décembre au 22 décembre. Ce système ne
doit pas être attribué aux druides historiques. Une présentation du National Parks and
Wildlife Service irlandais le décrit explicitement comme le calendrier conçu par Graves
dans ce [cahier sur les arbres et l'ogham](https://www.nationalparks.ie/app/uploads/2022/09/Tree-Tales-An-Ogham-Workbook.pdf).

Le 23 décembre est un jour intercalaire sans arbre. Pour conserver les mêmes bornes lors
des années bissextiles, le 29 février répète le jour précédent dans la période du Frêne
et porte `jour_bissextile=true`. Malgré la clé historique `celte_lunaire`, ces périodes
fixes de 28 jours ne décrivent pas les lunaisons astronomiques d'environ 29,5 jours.
