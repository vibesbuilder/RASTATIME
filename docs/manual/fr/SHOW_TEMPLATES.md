# Modèles d'émission

> **Où vous êtes dans le manuel.** Lisez d'abord
> [Calendrier](./CALENDAR.md) si ce n'est pas déjà fait —
> les Modèles d'émission sont un accélérateur sur le
> formulaire Nouvelle émission / Modifier l'émission du
> calendrier.

Un **Modèle d'émission** est un instantané enregistré des
valeurs des champs du formulaire Nouvelle émission. Quand
vous appliquez un modèle à une nouvelle émission, chaque
champ capturé est pré-rempli en un clic. Quand vous
enregistrez une émission comme modèle, chaque champ du
formulaire est capturé (avec quelques exceptions
délibérées).

Les modèles sont **à l'échelle station** : tout Admin ou
Program Manager peut appliquer ou modifier n'importe quel
modèle.

---

## 1. Pourquoi utiliser des modèles

Sans modèles, créer une émission musicale récurrente
typique prend environ 90 secondes de remplissage de
formulaire : nom, URL, genre, description, deux
animateurs, couleur de fond, couleur de texte, image
d'émission, autoloading playlist, "Ajouter Autoloading
Playlist ?", durée. Les stations avec un planning
hebdomadaire de 15-20 émissions ont passé 30 minutes par
semaine à retaper les mêmes champs.

Avec les modèles, cela tombe à environ 5 secondes par
émission :

1. Nouvelle émission → choisir **Modèles → Matinale** dans
   le menu déroulant.
2. Définir l'heure de début.
3. **Enregistrer**.

---

## 2. Créer un modèle

Deux chemins :

### 2.1 Enregistrer une émission existante comme modèle

Ouvrez l'émission dans le calendrier → **Enregistrer comme
modèle** dans le menu contextuel. Un dialogue demande :

| Champ | Notes |
|---|---|
| **Nom du modèle** | Unique. Par défaut, le nom actuel de l'émission. Le prochain menu déroulant Nouvelle émission affichera ce nom. |

Cliquez sur **Enregistrer**. Le modèle est créé depuis
l'état actuel du formulaire d'édition de l'émission —
chaque champ capturé ci-dessous est pris *tel quel* au
moment de l'enregistrement.

### 2.2 Enregistrer le formulaire Nouvelle émission avant d'enregistrer l'émission

Dans Nouvelle émission → remplissez les champs que vous
voulez capturer → développez **Modèles** → cliquez sur
**Enregistrer comme modèle**. Choisissez un nom. Le modèle
est enregistré sans encore créer une émission.

> **Conseil opérateur.** C'est utile quand vous voulez
> définir un modèle pour "le type d'émission que nous
> faisons le week-end" avant d'en avoir réellement besoin.
> Vous pouvez aussi enregistrer des modèles partiels de
> cette façon — remplissez seulement les couleurs et
> animateurs que vous utilisez toujours, puis enregistrez.

---

## 3. Appliquer un modèle

Lors de la création d'une nouvelle émission :

1. Nouvelle émission → développez **Modèles**.
2. Choisissez un modèle dans le menu déroulant **Sélectionner
   un modèle**.
3. Cliquez sur **Appliquer**.
4. Les autres sections du formulaire sont pré-remplies
   depuis le modèle.
5. Modifiez tout champ que vous voulez surcharger, puis
   **Enregistrer** normalement.

Le modèle surcharge chaque champ capturé. Les champs que
vous avez déjà remplis sont *remplacés* — il n'y a pas de
"fusion". Un bouton **Annuler l'application** apparaît
pendant dix secondes pour revenir en arrière.

### Lors de l'application d'un modèle sur une émission existante

Vous pouvez aussi ré-appliquer un modèle à une émission
qui existe déjà, via **Appliquer un modèle** dans le menu
contextuel du calendrier. C'est utile pour "nous avons
changé les animateurs en milieu de saison, appliquez le
nouveau modèle à chaque émission future".

> **Pourquoi ne pas auto-propager les modifications de
> modèle ?** RASTATIME 2026-05-19 a choisi un modèle de
> **tampon unidirectionnel**. Modifier un modèle ne change
> jamais les émissions créées à partir de lui. Raisons :
>
> - Prévisibilité : un opérateur modifiant un modèle
>   n'aurait aucune idée du nombre d'émissions existantes
>   qui changeraient silencieusement.
> - Surcharges par émission : un opérateur qui a modifié
>   la couleur d'une émission après application du modèle
>   perdrait la surcharge si le modèle se re-propageait.
> - Mode de défaillance : une modification de modèle qui
>   casserait un champ casserait chaque émission utilisant
>   ce modèle, nécessitant un nettoyage par émission.
>
> Si vous devez mettre à jour en masse les émissions
> existantes, utilisez **Appliquer un modèle** sur chacune
> (ou le menu **Actions en masse** — voir
> [Calendrier](./CALENDAR.md) §8). Voir ARCHITECTURE
> §23.16 pour le journal de décision complet.

### Lors de l'application d'un modèle sur un formulaire Modifier l'instance

Vous ne pouvez pas. RASTATIME 2026-05-19 supprime la
section **Modèles** dans le dialogue Modifier l'instance
(une instance d'une émission récurrente). Re-tamponner une
seule instance se propagerait silencieusement aux frères
et sœurs (viole le modèle de tampon unidirectionnel) ou
n'aurait aucun effet sur eux (ce qui tromperait
l'opérateur).

Si vous devez surcharger une instance, modifiez ses
champs directement sans utiliser le chemin de modèle.

---

## 4. Ce qu'un modèle capture

Ces champs sont enregistrés dans l'instantané JSONB du
modèle :

| Groupe | Champs |
|---|---|
| **Identité** | Nom d'émission (utilisé comme défaut pour la prochaine Nouvelle émission), URL, genre, description |
| **Visuels** | Couleur de fond, couleur de texte, référence à l'image d'émission |
| **Durée** | Longueur par défaut |
| **Répétitions** | Type de répétition, jours de répétition, date de fin / drapeau aucune-fin |
| **Enregistrement** | Enregistrement activé (oui/non) |
| **Autoloading playlist** | ID de playlist, ID de playlist intro, ID de playlist outro, drapeau "répéter jusqu'à plein" |
| **Auth** | Noms d'utilisateur d'animateur (PAS le mot de passe live-stream par émission — voir ci-dessous) |
| **Source Show DJ** | Live-stream par émission autorisé (oui/non) |

### Ce qu'un modèle ne capture PAS

Délibérément exclu :

| Champ | Raison |
|---|---|
| **Date / heure de début** | Par utilisation ; le modèle est réutilisable à travers plusieurs heures de début. |
| **Mot de passe live-stream** | Sécurité — un modèle enregistré ne devrait pas porter de credentials. L'opérateur définit le mot de passe par émission. |
| **Descriptions par instance** | Spécifiques à l'instance (ex. "l'invité de cette semaine est X"). |

> **Comment ça marche sous le capot.** Les modèles vivent
> dans la table `cc_show_template` (`id`, `name UNIQUE`,
> `template_data JSONB`, `created_at`, `updated_at`). Le
> service PHP `Application_Service_ShowTemplateService`
> possède CRUD via 5 actions JSON enregistrées sur
> `ScheduleController`. Au moment de l'application, le
> JSONB du modèle est plié dans le tableau consommé par
> `populateForm()`. La dérive de schéma est tolérée : un
> modèle manquant un champ au moment de l'application
> tombe sur la valeur par défaut du formulaire ; un
> modèle portant un champ inconnu est silencieusement
> ignoré.

### Image d'émission stockée comme référence, pas comme copie

Si un modèle capture une image d'émission, seul le chemin
vers le fichier image existant est enregistré — pas une
copie des octets de l'image. C'était un compromis
délibéré :

- Pour : l'utilisation du stockage reste plate quel que
  soit le nombre d'émissions tamponnées depuis un modèle.
- Contre : supprimer l'image source (ex. de
  `C:\rastatime\media\<owner>\.../show-logo.png`) laisse
  le modèle (et chaque émission tamponnée depuis lui) sans
  image.

Si vous supprimez ou déplacez une image d'émission,
re-téléversez-la sous le même chemin, ou ré-enregistrez le
modèle avec une image actuelle.

---

## 5. Renommer ou supprimer un modèle

Deux chemins :

### 5.1 Depuis la page Paramètres → Modèles d'émission

Paramètres → **Modèles d'émission** ouvre une liste de
chaque modèle de la station. Chaque ligne a :

| Colonne | Action |
|---|---|
| **Nom** | Cliquer pour renommer. Le nouveau nom doit être unique. |
| **Dernière mise à jour** | Triable. |
| **Utilisé par** | Un compte des émissions utilisant actuellement ce modèle (informationnel ; les modèles ne "suivent" pas l'utilisation rétroactivement). |
| **Modifier** | Ouvrir le JSON du modèle dans un visualiseur en lecture seule — utile pour le lecteur technique pour vérifier ce qui a été capturé. |
| **Supprimer** | Confirme, puis supprime le modèle. Les émissions tamponnées depuis lui ne sont pas affectées. |

> **Conseil opérateur.** La page Paramètres est le moyen le
> plus facile de renommer un modèle après une faute de
> frappe. Renommer via **Enregistrer comme modèle** du
> formulaire Nouvelle émission avec le même nom qu'un
> modèle existant invite à **Écraser ?** — facile à faire
> par accident.

### 5.2 Depuis le dialogue Nouvelle émission / Modifier l'émission

Développez **Modèles** → choisissez le modèle dans le
menu déroulant → une icône **Modifier** apparaît à côté
du menu déroulant → ouvre le dialogue
renommer / supprimer en ligne.

---

## 6. Comportement écraser-en-cas-de-doublon

Si vous enregistrez un nouveau modèle avec un nom qui
existe déjà, la requête d'enregistrement renvoie une
réponse de type 409 Conflict et l'interface demande :

> **Un modèle nommé "Matinale" existe déjà. Écraser ?**

| Cliquez | Effet |
|---|---|
| **Annuler** | Abandonne le nouveau modèle ; l'existant est inchangé. |
| **Écraser** | Remplace le `template_data` du modèle existant par les valeurs actuelles du formulaire. `updated_at` est incrémenté. Le nom est inchangé. |

> **Comment ça marche sous le capot.** L'endpoint API
> `Schedule/save-show-template` renvoie
> `{ "conflict": true, "template_id": <existing> }` au
> lieu de `{ "ok": true }` en cas de collision de nom. Le
> JS dans `add-show.js` affiche l'invite et re-poste avec
> `overwrite=true` si l'opérateur a confirmé. Sans
> écrasement, la ligne existante reste intacte.

---

## 7. Exemple travaillé : une émission matinale hebdomadaire

Une station diffuse **Matinale** Lun-Ven 07:00–10:00 avec :

- Animateurs : Anna + Ben
- Couleur de fond : bleu foncé
- Couleur de texte : blanc
- Image d'émission : matinale-logo.png
- Autoloading playlist : "Playlist Matinale" avec intro +
  outro
- Enregistrement activé
- Live-stream autorisé pour animateur invité les mercredis

**Première fois :**

1. Créer l'occurrence du lundi : Nouvelle émission,
   remplir tous les champs, enregistrer.
2. Ouvrir l'émission du lundi → **Enregistrer comme
   modèle** → nommer `Matinale`.

**Pour mardi, mercredi, jeudi, vendredi :**

1. Nouvelle émission → Modèles → **Matinale** → Appliquer.
2. Définir la date de début.
3. Enregistrer.

**Ou pour une définition d'émission récurrente
(préféré) :**

1. Nouvelle émission → Modèles → **Matinale** → Appliquer.
2. Définir la date de début.
3. Cocher **Se répète** → Hebdomadaire → Lun, Mar, Mer,
   Jeu, Ven.
4. Enregistrer.

Ceci génère tous les cinq jours comme instances d'une
définition d'émission récurrente. Modifier la définition
d'émission plus tard change les cinq.

---

## 8. Foire aux questions

### "Puis-je créer un modèle qui n'a que les couleurs, aucun autre champ ?"

Oui. Ouvrez un formulaire Nouvelle émission vierge,
remplissez seulement couleur de fond et de texte, puis
**Enregistrer comme modèle** avec un nom comme
`Couleur : Bleu foncé`. Lors de l'application, seuls ces
deux champs sont surchargés ; tout le reste reste aux
valeurs par défaut du formulaire.

### "Un DJ peut-il enregistrer / appliquer des modèles ?"

Non. Les modèles se trouvent dans la boîte de dialogue de
l'émission, et seuls les Program Managers et les Admins
créent et modifient des émissions ; ce sont aussi eux qui
enregistrent, renomment et suppriment les modèles, dans la
boîte de dialogue et sur la page d'aperçu Paramètres →
Show Templates.

### "J'ai changé la liste d'animateurs sur le modèle — pourquoi les émissions existantes sont-elles inchangées ?"

Par conception — voir §3, "Pourquoi ne pas auto-propager
les modifications de modèle ?". Utilisez **Appliquer un
modèle** sur chaque émission existante qui devrait
hériter du changement.

### "Puis-je exporter un modèle pour l'utiliser sur une autre station ?"

Pas via l'interface. La solution technique :
`SELECT * FROM cc_show_template WHERE name = 'Matinale'`
sur la station source, puis
`INSERT … ON CONFLICT DO NOTHING` sur la station cible.
Notez que les IDs de playlist référencés et les chemins
d'image ne se résoudront pas à travers les stations.

### "Quel est le nombre maximum de modèles ?"

Il n'y a pas de limite stricte. Le menu déroulant
**Modèles** dans le formulaire Nouvelle émission défile
s'il y a plus de 20 entrées. Les stations avec 50+
modèles peuvent vouloir utiliser une convention de
préfixe de nom (`Musique — Pop`, `Musique — Jazz`,
`Info — Horaire`).

---

## Où aller ensuite

* [Calendrier](./CALENDAR.md) — où les modèles sont
  appliqués.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) —
  la raison la plus courante pour laquelle les modèles
  sont utiles.
* [Paramètres](./SETTINGS.md) — tour de chaque
  sous-page Paramètres y compris Modèles d'émission.
