# Cache navigateur multi-profils

**Sous-projet 1/5** du découpage global (cache → Portrait/intros → auth+DB → transits → Stripe).

## Objectif

Permettre à l'utilisateur de sauvegarder plusieurs profils nataux dans le cache
navigateur pour ne pas retaper ses informations à chaque visite. Feature 100 %
frontend, sans backend, sans DB.

## Contexte

Aujourd'hui les champs du formulaire (`static/index.html`) sont vierges à chaque
chargement. La config LLM est déjà sauvegardée dans `localStorage` sous la clé
`portrait-cosmique-llm`. Ce sous-projet ajoute une seconde zone de cache pour
les **données de fiche** (pas la config IA).

## Structure de données

Clé `localStorage` : `portrait-cosmique-profils`

```json
{
  "profils": [
    {
      "id": "p1",
      "label": "Moi",
      "prenoms": "Jean",
      "nom": "Dupont",
      "date_naissance": "1990-01-15",
      "heure_naissance": "14:30",
      "ville": "Toulouse",
      "latitude": 43.6043,
      "longitude": 1.4446,
      "utc_offset": 1,
      "systeme_numerologie": "classique"
    }
  ],
  "profil_actif": "p1"
}
```

- `id` : identifiant stable, généré `p + Date.now()` (court, unique local).
- `label` : nom affiché, modifiable.
- Les champs `latitude/longitude/utc_offset` sont stockés pour éviter un
  re-géocodage réseau au chargement.
- `systeme_numerologie` est le seul champ « options avancées » persisté. La
  config LLM (fournisseur/clé/modèle) reste sur sa clé existante et **n'est
  pas** par-profil.

## UI

Ajout dans le formulaire, au-dessus du champ « Prénoms » :

```
[Profil : Moi ▼]   [✏️ Renommer]   [🗑️]   [＋ Nouveau]   [💾 Enregistrer sous…]
```

### Sélecteur déroulant

- `<select>` listant les profils existants (label affiché).
- Dernier option fixe : `＋ Nouveau profil` (valeur spéciale `__nouveau__`).
- Changement de sélection :
  - `__nouveau__` → vide tous les champs, `profil_actif` devient `null`
    (profil non persistant jusqu'à la prochaine sauvegarde explicite ou Calculer).
  - Profil existant → charge ses valeurs dans tous les champs, met à jour
    `profil_actif`.

### Boutons d'action

- **✏️ Renommer** : `prompt()` pour saisir un nouveau label. Met à jour le
  profil actif. Refuse label vide.
- **🗑️** : `confirm()` puis supprime le profil actif. Le premier profil
  restant (s'il y en a) devient actif. Si plus aucun profil : formulaire
  vidé, `profil_actif = null`.
- **＋ Nouveau** : raccourci équivalent à sélectionner `__nouveau__` dans le
  select. Vide les champs.
- **💾 Enregistrer sous…** : `prompt()` pour label, crée une copie des
  champs courants dans un nouveau profil (nouvel `id`), devient actif.

## Comportement auto-save

- À chaque soumission du formulaire (Calculer), les champs courants
  écrasent silencieusement le profil **actif**.
- Si `profil_actif` est `null` au moment du Calculer (cas « ＋ Nouveau » non
  encore enregistré), un profil est créé automatiquement avec le label
  par défaut `I18N[LANGUE].p_label_defaut` (« Profil 1 » / « Profile 1 »),
  incrémenté si déjà pris.
- Si aucun profil n'existe au chargement de la page : le formulaire reste
  vierge, `profil_actif = null`. La première soumission crée le premier
  profil automatiquement.

## Chargement de la page

- Lire `portrait-cosmique-profils`.
- Si profils existent : charger le `profil_actif` (ou le premier si
  `profil_actif` pointe vers un id manquant) dans les champs.
- Si aucun profil : champs vierges.
- Mettre à jour la liste du `<select>` pour refléter l'état courant.

## Périmètre exclus

- L'export HTML (bouton « Télécharger en HTML ») reste un instantané
  autonome — la logique de cache multi-profils n'est pas embarquée dans
  l'export (un export est un snapshot, pas une session interactive).
- La config LLM n'est pas migrée vers le cache multi-profils ; elle reste
  globale et inchangée.
- Aucune synchro backend ni cloud : stockage strictement local. Perte du
  navigateur = perte des profils (accepté, lead magnet gratuit).

## Tests

Pas de tests backend (feature 100 % frontend). Vérification manuelle :

1. Page vierge → Calculer → profil « Profil 1 » créé, visible au reload.
2. ＋ Nouveau → champs vidés → Calculer → profil « Profil 2 » créé.
3. Renommer un profil → label mis à jour dans le select.
4. Supprimer le profil actif → bascule sur le profil suivant.
5. Enregistrer sous… → copie créée, profil actif bascule dessus.
6. Recharger la page → profil actif pré-rempli correctement.
7. Basculer LANGUE → labels des boutons traduits.
8. Coords/utc_offset restaurés (pas de re-géocodage réseau).

## i18n

Nouvelles clés FR/EN :

| clé | FR | EN |
|-----|----|----|
| `l_profil` | Profil | Profile |
| `b_renommer` | ✏️ Renommer | ✏️ Rename |
| `b_supprimer` | 🗑️ Supprimer | 🗑️ Delete |
| `b_nouveau` | ＋ Nouveau | ＋ New |
| `b_sous` | 💾 Enregistrer sous… | 💾 Save as… |
| `p_label_defaut` | Profil {n} | Profile {n} |
| `p_confirm_suppr` | Supprimer ce profil ? | Delete this profile? |
| `p_prompt_label` | Nom du profil | Profile name |
| `p_prompt_renommer` | Nouveau nom | New name |
