# Widgets publics intégrables

> **Où vous êtes dans le manuel.** Ce chapitre couvre les
> widgets prêts-à-l'emploi qu'un site externe (votre page
> d'accueil publique de station, un site partenaire, un
> écran d'information) peut intégrer via un simple
> `<iframe>`. Les widgets puisent dans les données live
> de RASTATIME et ne nécessitent aucune connexion — ils
> sont conçus pour être visibles publiquement.

RASTATIME livre une petite famille de widgets HTML que
les sites externes peuvent intégrer pour afficher ce qui
est à l'antenne, ce qui vient ensuite, le programme
hebdomadaire, etc. Chaque widget est une URL d'iframe
autonome que vous insérez dans le HTML de votre page
d'accueil.

Ce chapitre est la référence opérateur : quels widgets
existent, quels paramètres URL ils acceptent, et comment
les intégrer sur un site externe.

---

## 1. La famille de widgets

| Widget | URL | But |
|---|---|---|
| **Now Playing — Show** | `/embed/now-playing-show` | Widget texte deux lignes. Nom de l'émission actuelle + durée restante ; nom de l'émission suivante + heures début-fin. |
| **Now Playing — Track** | `/embed/now-playing-track` | Widget texte deux lignes. Piste actuelle "Artiste - Titre" + durée restante ; piste suivante + heures début-fin. |
| **Next Shows** | `/embed/next-shows` | Widget liste. Titre de l'émission + liste chronologique des prochaines instances d'une émission récurrente. |
| **Latest Shows** | `/embed/latest-shows` | Widget liste. Titre de l'émission + liste chronologique inverse des dernières instances passées d'une émission récurrente. |
| **Weekly Program** | `/embed/weekly-program` | (Existant) Vue grille calendrier sept jours du planning. |
| **Audio Player** | `/embed/player` | (Existant) Lecteur audio HTML5 intégré pour le stream public. |

D'autres widgets sont prévus (voir [BACKLOG.md](../../../BACKLOG.md)).

---

## 2. Widget Now Playing — Show

iframe prêt à l'emploi :

```html
<iframe src="https://votre-station.example/embed/now-playing-show"
        width="100%" height="50" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Ce qu'il affiche

Deux lignes, chacune avec un nom à gauche et une heure à
droite :

```
Matinale                                                  -25:14
Music Hour                                          10:00 - 11:30
```

- **Ligne 1** : nom de l'émission actuelle + compte à rebours jusqu'à la fin (`-MM:SS` ou `-H:MM:SS`)
- **Ligne 2** : nom de l'émission suivante + sa fenêtre `HH:MM - HH:MM`

Le compte à rebours se met à jour chaque seconde côté
client, donc l'affichage paraît fluide. Les données
sous-jacentes se rafraîchissent toutes les 60 secondes
(configurable — voir §6).

### Paramètres URL

| Paramètre | Valeurs | Défaut | Effet |
|---|---|---|---|
| `theme` | `auto`, `dark`, `light` | `auto` | Couleur du texte. `auto` suit le `prefers-color-scheme` du navigateur. Fond toujours transparent. |
| `cache` | entier secondes, 10–3600 | `60` | TTL du cache HTTP côté serveur. Plus bas = données plus fraîches + plus de hits backend. |
| `overflow` | `ellipsis`, `marquee` | `ellipsis` | Que faire des noms d'émission / piste plus larges que le widget de 300 px. `ellipsis` tronque avec `…` ; `marquee` fait défiler le texte vers la gauche pendant 24 s. |
| `timezone` | tout fuseau horaire standard (`Europe/Paris`) | défaut station | Toutes les heures rendues dans cette zone. |

> **Note.** Le corps du widget est limité à **300 px de large**
> pour s'adapter aux mises en page de barre latérale typiques
> des sites de stations.  Définissez la largeur de l'iframe à
> 300 dans le HTML d'intégration pour un ajustement précis.

---

## 3. Widget Now Playing — Track

iframe prêt à l'emploi :

```html
<iframe src="https://votre-station.example/embed/now-playing-track"
        width="100%" height="50" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Ce qu'il affiche

Même mise en page deux lignes que le widget show, mais
pour les pistes :

```
The Beatles - Hey Jude                                    -02:14
Pink Floyd - Comfortably Numb                       16:00 - 17:30
```

- **Ligne 1** : piste actuelle `Artiste - Titre` + compte à rebours jusqu'à la fin
- **Ligne 2** : piste suivante `Artiste - Titre` + sa fenêtre `HH:MM - HH:MM`

Si une piste n'a pas de métadonnée artiste, seul le titre
est affiché (et vice-versa). Si ni l'un ni l'autre n'est
disponible, la ligne affiche "No track playing" / "No
upcoming track" en style atténué.

### Paramètres URL

Identique au widget show — voir §2.

---

## 4. Widgets Next-Shows / Latest-Shows

Widgets jumeaux qui listent plusieurs instances **d'une seule
émission récurrente** plutôt que l'enveloppe "ce qui passe
maintenant" des deux widgets Now-Playing.  Utile pour une page
de détail d'émission sur votre site : déposez le widget dans
la barre latérale et les auditeurs voient les quatre prochains
épisodes (ou les trois derniers, selon le widget intégré).

iframe prêt à l'emploi (next shows) :

```html
<iframe src="https://votre-station.example/embed/next-shows?show_id=42"
        width="300" height="140" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

iframe prêt à l'emploi (latest shows) :

```html
<iframe src="https://votre-station.example/embed/latest-shows?show_id=42"
        width="300" height="120" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Ce qu'il affiche

```
Matinale
mar. 21 mai                                 06:00 - 08:00
mer. 22 mai                                 06:00 - 08:00
jeu. 23 mai                                 06:00 - 08:00
ven. 24 mai                                 06:00 - 08:00
```

- **Ligne titre** : nom de l'émission depuis `cc_show.name`
- **Lignes liste** : une ligne par instance, `Jour DD Mois`
  à gauche, `HH:MM - HH:MM` à droite

La liste se rafraîchit toutes les `cache` secondes (voir §6).
Quand la ligne du haut d'un widget Next-Shows passe dans le
passé (l'émission a effectivement commencé), un rafraîchissement
anticipé se déclenche en ~1 s pour que la ligne disparaisse
sans attendre la TTL du cache.

### Paramètres URL

| Paramètre | Valeurs | Défaut | Effet |
|---|---|---|---|
| `show_id` | entier (cc_show.id) | — | Identifie l'émission. Stable face aux renommages et aux changements d'instances récurrentes — toutes les instances d'une émission récurrente partagent cet id. **Recommandé par rapport à `show`.** |
| `show` | chaîne (cc_show.name) | — | Fallback quand `show_id` est absent.  Match exact sensible à la casse.  `show_id` gagne quand les deux sont définis. |
| `limit` | entier 1..20 | 4 (next), 3 (latest) | Nombre d'instances à lister. |
| `theme` | `auto`, `dark`, `light` | `auto` | Identique aux widgets deux lignes — voir §2. |
| `cache` | entier secondes 10..3600 | `60` | Identique aux widgets deux lignes — voir §6. |
| `overflow` | `ellipsis`, `marquee` | `ellipsis` | Comportement du titre d'émission quand plus large que 300 px. |
| `timezone` | tout fuseau standard | défaut station | Toutes les heures rendues dans cette zone. |

> **Conseil.** Choisissez l'émission depuis le menu déroulant
> de la page Paramètres (section suivante) plutôt que de taper
> l'id à la main — la page affiche un aperçu en direct et copie
> un snippet iframe prêt à l'emploi avec l'id pré-rempli.

### Instances modifiées / annulées

Les instances individuelles que l'opérateur a déplacées ou
annulées (`cc_show_instances.modified_instance = TRUE`) sont
filtrées de la liste, suivant la convention que
`Application_Model_Show::getNextShows` utilise sur le tableau
de bord interne.  Un épisode reporté ne laisse donc pas de
ligne fantôme dans le widget public.

---

## 5. Personnaliser les libellés d'état vide

Quand il n'y a pas d'émission ou de piste actuelle / suivante,
le widget affiche un court texte placeholder.  Les opérateurs
peuvent personnaliser les quatre placeholders sans toucher au
code sous :

**Paramètres → Widgets → Current Show/Track**

| Libellé du paramètre | Valeur par défaut |
|---|---|
| No show on air: | `No show on air` |
| No upcoming show: | `No upcoming show` |
| No track playing: | `No track playing` |
| No upcoming track: | `No upcoming track` |

Les modifications sont persistées dans `cc_pref` et reprises
par le widget dans le délai d'un TTL de cache (par défaut
60 secondes).  Laissez un champ vide pour revenir au défaut
anglais affiché dans son placeholder.

La même page de paramètres héberge aussi :

- une **prévisualisation en direct** des deux widgets côte à
  côte ;
- le **code d'intégration `<iframe>` prêt-à-l'emploi** pour
  chaque widget avec l'URL absolue de la station pré-remplie.

Les widgets Next-Shows / Latest-Shows ont leur propre page
de libellés sous :

**Paramètres → Widgets → Next/Latest Shows**

| Libellé du paramètre | Valeur par défaut |
|---|---|
| No upcoming shows: | `No upcoming shows` |
| No past shows: | `No past shows` |

Cette page héberge également un **menu déroulant de sélection
d'émission** qui pilote les iframes de prévisualisation et les
snippets de code d'intégration — choisissez l'émission,
cliquez sur Enregistrer, et copiez le bloc `<iframe ...>`
généré avec `show_id` déjà intégré dans l'URL.

---

## 6. Le paramètre `cache` — quel TTL ?

Le serveur met en cache les données sous-jacentes pendant
`cache` secondes avant de les regénérer. Le polling JS
dans l'iframe correspond à cette cadence, donc sous forte
charge chaque visiteur frappe le **cache navigateur**
plutôt que votre backend.

Valeurs recommandées :

| `cache=` | Quand |
|---|---|
| `30` | Affichage haute précision, ex. écran de hall à la station. ~2 hits backend/min par navigateur. |
| `60` (défaut) | Page d'accueil publique à trafic modéré. Bon équilibre fraîcheur / charge. |
| `120`–`300` | Intégration à très fort trafic. Échangez jusqu'à 5 min d'obsolescence contre un ordre de grandeur moins de hits backend. |
| `> 600` | Non recommandé — l'émission / piste affichée est souvent déjà terminée quand le navigateur redemande. |

> **Conseil opérateur.** Le widget compense les données
> obsolètes : quand l'heure de fin de l'item actuel passe
> (calculée côté client à partir des timestamps absolus du
> payload), le JS déclenche un poll immédiat sans attendre
> le prochain intervalle. Donc une intégration `cache=300`
> bascule quand même vers la piste suivante en ~1 s — la
> obsolescence n'affecte que le premier affichage après
> une longue pause inactive.

> **Comment ça marche sous le capot.** Les deux endpoints
> de widget définissent `Cache-Control: public,
> max-age=<cache>`. Apache sert le HTML d'iframe ; le JS
> dans l'iframe interroge `/embed/now-playing-data` (même
> TTL de cache) pour les payloads de rafraîchissement.
> L'endpoint JSON tire de
> `Application_Model_Schedule::GetPlayOrderRange()` — la
> même source que `/api/live-info` — mais réduit à ~1-2
> kB de payload pour que l'aller-retour reste bon marché.

---

## 7. Thèmes

Trois modes, contrôlés via le paramètre `theme` :

| `theme=` | Effet |
|---|---|
| `auto` (défaut) | Texte clair sur pages d'intégration sombres, texte sombre sur claires. Détecté via la media query `prefers-color-scheme` du navigateur. |
| `dark` | Force le texte clair. |
| `light` | Force le texte sombre. |

Le fond du widget est **toujours transparent** pour qu'il
se fonde dans la page d'intégration.

---

## 8. Authentification

Aucune. Les widgets Now-Playing sont intentionnellement
publics : tout l'intérêt est que n'importe quel visiteur
du site public de votre station puisse voir ce qui est à
l'antenne.

Ils n'exposent **pas** : nombres d'auditeurs, état de la
source stream, noms d'opérateurs, état d'enregistrement,
IDs internes.

---

## 9. Intégration cross-origin

Les iframes fonctionnent cross-origin nativement — aucune
configuration supplémentaire nécessaire.

---

## 10. Dépannage

### "Le widget affiche 'No show on air' mais une émission tourne"

- Vérifiez via le [Tableau de bord](./DASHBOARD.md).
- Le cache côté serveur peut encore avoir des données
  obsolètes. Attendez jusqu'à `cache` secondes ou
  rechargez la page parente.

### "Le widget n'affiche rien (iframe vide)"

- Vérifiez que l'URL est accessible depuis le contexte
  du navigateur de la page d'intégration.
- Vérifiez la console du navigateur pour les erreurs JS.

### "Le fond du widget est blanc mais je veux du sombre"

Ajoutez `?theme=dark` à l'URL.

### "Le compte à rebours affiche -00:00 et reste là"

L'heure de fin de l'item actuel est passée mais le widget
n'a pas encore pris les nouvelles données. Auto-récupère
en ~1 s. Si ça persiste, le moteur de playout peut être
arrêté — vérifiez `Get-Service RASTATIME-PLAYOUT`.

### "Le widget Next / Latest Shows affiche le placeholder vide"

- Vérifiez que l'URL de l'iframe contient `?show_id=N`
  (préféré) ou `?show=Nom`.  La page Paramètres (§5)
  génère le snippet avec l'id déjà intégré — copiez-le
  de là plutôt que de bricoler l'URL à la main.
- Confirmez que l'émission a effectivement des instances
  futures dans le calendrier (pour Next Shows) ou a été
  diffusée au moins une fois (pour Latest Shows).  Une
  émission toute neuve sans épisodes diffusés affiche le
  placeholder vide dans le widget Latest jusqu'à la fin
  du premier épisode.
- Les lignes `modified_instance = TRUE` sont filtrées
  by-design (correspond au tableau de bord interne).
  Une émission dont la seule instance à venir a été
  déplacée ou annulée affiche vide jusqu'à ce qu'une
  nouvelle instance soit générée.

---

## Où aller ensuite

* [Tableau de bord](./DASHBOARD.md) — la version interne
  des mêmes données.
* [Streams](./STREAMS.md) — les streams audio sous-jacents.
* [BACKLOG.md](../../../BACKLOG.md) — vagues de widgets à
  venir.
