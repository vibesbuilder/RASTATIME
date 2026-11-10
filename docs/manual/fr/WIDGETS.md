# Widgets publics intégrables

> **Où vous êtes dans le manuel.** Ce chapitre couvre les
> widgets prêts-à-l'emploi qu'un site externe (votre page
> d'accueil publique de station, un site partenaire, un
> écran d'information) peut intégrer via un simple
> `<iframe>`. Les widgets puisent dans les données live
> de RASTATIME et ne nécessitent aucune connexion — ils
> sont conçus pour être visibles publiquement.  Les pages
> **Widgets** de RASTATIME (codes d'intégration, paramètres
> des widgets) sont réservées aux Program Managers et aux
> Admins ; les invités et les DJ ne voient pas le menu
> (depuis le 25/10/2026).

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
| **Next Shows** | `/embed/next-shows` | Widget liste. Titre de l'émission + liste chronologique des prochains épisodes d'une émission récurrente. |
| **Latest Shows** | `/embed/latest-shows` | Widget liste. Titre de l'émission + liste chronologique inverse des derniers épisodes passés d'une émission récurrente. |
| **On Air Today** | `/embed/on-air-today` | Widget grille-du-jour. Bande d'en-tête + émission actuelle + prochaines du jour, chaque ligne "HH:MM – HH:MM   Nom (lien)". |
| **Weekly Schedule** | `/embed/weekly-program` | Widget à onglets sur sept jours. En-tête avec ◀ / ▶ navigation hebdomadaire + libellé de plage de dates ; onglets de jour ; liste de lignes par onglet avec HH:MM – HH:MM + nom d'émission (lien). Image de fond optionnelle via `?bg=URL`. |
| **Multi-View Schedule** | `/embed/multi-view-schedule` | Widget calendrier basé sur FullCalendar 6 (hébergé localement). Vues Day / 2-Day / Week commutables via boutons in-widget ou `?view=`. Créneaux d'émission colorés depuis `cc_show.background_color`. Clic → modal avec description + bouton URL. Auto-scroll vers la ligne now. |
| **Track History** | `/embed/track-history` | Journal de lecture des pistes (7 derniers jours). Date-picker HTML5 + time-picker + bouton Now + dropdown pagesize (10/20/50/100). Lignes "HH:MM - HH:MM Artiste - Titre"; clic → modal avec contexte d'émission + lien URL. Bouton Load-more avec cap dur à 1000 lignes. |
| **Stream Player** | `/embed/player` | Bouton d'écoute en direct avec lignes now-playing / next et curseur de volume. Layouts carte et barre inférieure pleine largeur. Choisit le premier stream décodable par le navigateur, bascule sur le suivant en cas de panne. |

D'autres widgets sont prévus (voir [BACKLOG.md](../../../BACKLOG.md)).

**Langue.**  Depuis le 25/10/2026, tous les widgets utilisent la
**langue de la station** (Paramètres → Général → Langue par
défaut), et non celle du navigateur du visiteur : dates, noms des
mois et des jours de la semaine et leurs abréviations, ordre de la
date et boutons (Today, Day / 2 Days / Week).  Seuls les sélecteurs
de date et d'heure du widget Track History sont dessinés par le
navigateur lui-même et gardent le format du visiteur.  Une langue
de station modifiée apparaît au prochain chargement du widget (au
plus tard après la durée `cache`).

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
(configurable — voir §7).

### Paramètres URL

| Paramètre | Valeurs | Défaut | Effet |
|---|---|---|---|
| `theme` | `auto`, `dark`, `light` | `auto` | Couleur du texte. `auto` suit le `prefers-color-scheme` du navigateur. Fond toujours transparent. |
| `cache` | entier secondes, 10–3600 | `60` | TTL du cache HTTP côté serveur. Plus bas = données plus fraîches + plus de hits backend. |
| `overflow` | `ellipsis`, `marquee` | `ellipsis` | Que faire des noms d'émission / piste plus larges que le widget de 340 px. `ellipsis` tronque avec `…` ; `marquee` fait défiler le texte vers la gauche pendant 24 s. |
| `timezone` | tout fuseau horaire standard (`Europe/Paris`) | défaut station | Toutes les heures rendues dans cette zone. |

> **Note.** Le corps du widget est limité à **340 px de large**
> pour s'adapter aux mises en page de barre latérale typiques
> des sites de stations.  Définissez la largeur de l'iframe à
> 340 dans le HTML d'intégration pour un ajustement précis.
> (Les widgets Next-Shows / Latest-Shows sont plafonnés à
> 300 px — ils servent un cas d'usage de barre latérale plus
> étroit.)

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

Widgets jumeaux qui listent plusieurs épisodes **d'une seule
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
- **Titre** : peut être masqué (réglage **Show the show name
  as heading**, ou `?title=0` pour une seule intégration) ;
  la taille de police vient de **Font size (px)** ou
  `?size=`, la couleur du texte de **Text color** (sélecteur
  de couleur ; **Theme colors** vide le champ et le thème
  décide à nouveau) ou `?color=` (depuis le 2026-11-10)
- **Gras** : réglage **Bold text** ou `?bold=1` (depuis le
  2026-11-10)
- **Police** : réglage **Font** - police système (défaut),
  Archivo, Arial, Verdana, Georgia, Times New Roman,
  Monospace ; ou `?font=`.  Archivo (SIL Open Font License)
  est servie depuis `public/fonts/archivo` sur ce serveur, le
  widget n'interroge donc aucun CDN de polices (depuis le
  2026-11-10)
- **Couleur de fond** : réglage **Background color**
  (sélecteur de couleur ; **Transparent** vide le champ et la
  page qui intègre transparaît de nouveau) ou `?bgcolor=`
  (depuis le 2026-11-10)
- **Lignes liste** : une ligne par épisode, la date à
  gauche, `H:MM - H:MM` à droite
- **Format de date** (depuis le 2026-11-10) : se choisit
  sous Paramètres → Widgets → Next/Latest Shows → **Date
  format**, pour les deux widgets.  Quatre variantes dans la
  langue de la station (Paramètres → Général → Langue par
  défaut) ; en français : `mar. 15 déc.` (défaut),
  `mar 15 déc`, `mar 15/12`, `15/12`.  La liste déroulante
  montre chaque variante dans la langue de la station.
- La date et l'heure sont écrites par le serveur, dans le
  fuseau de la station ou `?timezone=`.  Les lignes sont donc
  complètes même si la page qui intègre bloque les scripts
  (certains éditeurs de CMS ajoutent d'eux-mêmes
  `sandbox=""` à un iframe) ; seul le rafraîchissement
  automatique a besoin des scripts - sans eux la liste est
  mise à jour au rechargement de la page.

La liste se rafraîchit toutes les `cache` secondes (voir §7).
Quand la ligne du haut d'un widget Next-Shows passe dans le
passé (l'émission a effectivement commencé), un rafraîchissement
anticipé se déclenche en ~1 s pour que la ligne disparaisse
sans attendre la TTL du cache.

### Paramètres URL

| Paramètre | Valeurs | Défaut | Effet |
|---|---|---|---|
| `show_id` | entier (cc_show.id) | — | Identifie l'émission. Stable face aux renommages et aux changements d'épisodes récurrents — tous les épisodes d'une émission récurrente partagent cet id. **Recommandé par rapport à `show`.** |
| `show` | chaîne (cc_show.name) | — | Fallback quand `show_id` est absent.  Match exact sensible à la casse — **correspond à toutes les émissions qui partagent le nom**, donc une station avec une émission "BBC News" par jour de semaine peut toutes les lister avec un seul embed `?show=BBC%20News`.  `show_id` gagne quand les deux sont définis. |
| `limit` | entier 1..20 | 4 (next), 3 (latest) | Nombre d'épisodes à lister. |
| `theme` | `auto`, `dark`, `light` | `auto` | Identique aux widgets deux lignes — voir §2. |
| `cache` | entier secondes 10..3600 | `60` | Identique aux widgets deux lignes — voir §7. |
| `overflow` | `ellipsis`, `marquee` | `ellipsis` | Comportement du titre d'émission quand plus large que 300 px. |
| `title` | `0`, `1` | réglage **Show the show name as heading** (activé) | `0` masque le titre avec le nom de l'émission (p. ex. sur la page de l'émission elle-même), `1` l'affiche.  Sans paramètre, le réglage sous Widgets → Next/Latest Shows s'applique (depuis le 2026-11-10). |
| `size` | entier px 10..32 | réglage **Font size (px)** (14) | Taille de police de tout le widget ; titre et lignes suivent.  Sans paramètre, le réglage s'applique (depuis le 2026-11-10). |
| `bold` | `0`, `1` | réglage **Bold text** (désactivé) | `1` met les lignes en gras (le titre un cran plus épais), `0` normal.  Sans paramètre, le réglage s'applique (depuis le 2026-11-10). |
| `font` | `system`, `archivo`, `arial`, `verdana`, `georgia`, `serif`, `mono` | réglage **Font** (`system`) | Police de tout le widget.  `archivo` est servie par RASTATIME lui-même (aucun CDN de polices), les autres existent sur pratiquement tous les appareils.  Sans paramètre, le réglage s'applique (depuis le 2026-11-10). |
| `color` | hex `rrggbb` (avec ou sans `#`, `#` en `%23`) | réglage **Text color** (vide = couleurs du thème) | Couleur du texte de tout le widget, remplace les couleurs du thème ; le texte d'état vide l'utilise à 70 %.  Sans paramètre, le réglage s'applique (depuis le 2026-11-10). |
| `bgcolor` | hex `rrggbb` (avec ou sans `#`, `#` en `%23`) | réglage **Background color** (vide = transparent) | Fond de tout l'iframe ; sans couleur, la page qui intègre transparaît.  Sans paramètre, le réglage s'applique (depuis le 2026-11-10). |
| `timezone` | tout fuseau standard | défaut station | Toutes les heures rendues dans cette zone. |

> **Conseil.** Choisissez l'émission depuis le menu déroulant
> de la page Paramètres (section suivante) plutôt que de taper
> l'id à la main — la page affiche un aperçu en direct et copie
> un snippet iframe prêt à l'emploi avec l'id pré-rempli.

### Épisodes modifiés / annulés

Les épisodes individuels que l'opérateur a déplacés ou
annulés (`cc_show_instances.modified_instance = TRUE`) sont
filtrées de la liste, suivant la convention que
`Application_Model_Show::getNextShows` utilise sur le tableau
de bord interne.  Un épisode reporté ne laisse donc pas de
ligne fantôme dans le widget public.

---

## 5. Widget On-Air-Today

Widget compact de grille-du-jour qui liste le programme
d'aujourd'hui — de l'émission actuellement en ondes aux
prochaines émissions, plafonné à minuit de la station pour
que le widget ne déborde jamais sur le programme de demain.

iframe prêt à l'emploi :

```html
<iframe src="https://votre-station.example/embed/on-air-today"
        width="340" height="250" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Ce qu'il affiche

```
On Air Today                       ← bande d'en-tête
────────────────────────────────
16:00 - 16:30    Newslink           ← ligne actuelle (gras)
16:30 - 17:00    Pages of History (EN)
17:00 - 17:30    L'Info Chez-Vous
17:30 - 04:00    Pages d'histoire
18:30 - 19:00    Choices (EN)
19:00 - 19:30    L'Info chez vous (FR)
```

- **En-tête** : le titre réglé sur la page Widgets (défaut « On
  Air Today »), ou "On Air *<date>*" quand un jour spécifique est
  épinglé via `?day`
- **Lignes** : `HH:MM - HH:MM` à gauche, nom de l'émission
  à droite.  La ligne actuellement en ondes est rendue en
  **gras** pour que l'opérateur (et l'auditeur) voie d'un
  coup d'œil quelle ligne est live.
- **Liens** : une émission avec une **Émission → Modifier →
  URL** configurée rend son nom comme lien cliquable qui
  s'ouvre dans un nouvel onglet (`target="_blank"
  rel="noopener noreferrer"`).  Les émissions sans URL
  rendent comme texte brut.

La liste se rafraîchit toutes les `cache` secondes (voir §7).
Quand l'heure de fin de la ligne actuelle passe, un
rafraîchissement anticipé se déclenche en ~1 s pour que le
surlignage gras migre vers la ligne suivante sans attendre
la TTL du cache.

### Paramètres URL

| Paramètre | Valeurs | Défaut | Effet |
|---|---|---|---|
| `limit` | entier 1..20 | `6` | Total de lignes (current + suivantes).  Défaut = 1 current + 5 suivantes. |
| `day` | `YYYY-MM-DD` | aujourd'hui | Épingle un jour spécifique (dans le fuseau résolu) pour rendre des aperçus historiques ou futurs.  Quand omis ou égal à aujourd'hui, le widget filtre les émissions déjà diffusées ; pour tout autre jour il liste toutes les émissions dont le début tombe dans la fenêtre 24 h. |
| `theme` | `auto`, `dark`, `light` | `auto` | Identique aux autres widgets — voir §2. |
| `cache` | entier secondes 10..3600 | `60` | Identique aux autres widgets — voir §7. |
| `overflow` | `ellipsis`, `marquee` | `ellipsis` | Comportement des noms d'émission plus larges que 340 px. |
| `link` | `underline`, `plain` | `plain` | Rendu des liens pour les noms d'émission : `plain` (défaut) supprime le soulignement pour que les noms se fondent dans le texte en gras des lignes ; `underline` réactive l'affordance hyperlien classique.  Avec `plain`, l'affordance ne survit que via le curseur pointer au survol. |
| `timezone` | tout fuseau IANA | défaut station | Définit "aujourd'hui" et rend toutes les heures dans cette zone. |

> **Limite du jour.** "Aujourd'hui" est le jour calendaire
> de la station — 00:00 à 24:00 dans le fuseau de la station
> (ou dans `?timezone` quand surchargé).  Une émission
> démarrée hier 23:30 et toujours en ondes à 14:00
> aujourd'hui compte comme la ligne actuelle.  Une émission
> qui démarre demain 00:30 n'est **pas** listée même si le
> `limit` laisserait sinon de la place — le plafond est dur.

### Épisodes modifiés / annulés

Même convention que les widgets Next-Shows / Latest-Shows —
les lignes avec `cc_show_instances.modified_instance = TRUE`
sont filtrées pour qu'un épisode reporté / annulé ne
laisse pas de ligne fantôme dans le widget public.

### Page Paramètres

**Paramètres → Widgets → On Air Today** héberge :

- **Title** (depuis le 25/10/2026) : le texte de l'en-tête ; vide
  = « On Air Today » dans la langue de la station.
- Le libellé d'état vide (défaut `No shows on air today`,
  fallback à l'anglais par défaut quand vide).
- Une prévisualisation iframe en direct sur fond sombre.
- Le code `<iframe>` d'intégration prêt à l'emploi avec
  l'URL absolue de la station pré-remplie.

Pas de sélecteur d'émission — le widget puise
automatiquement dans le programme en direct pour toute la
journée station.

---

## 6. Widget Weekly Schedule

Un widget à onglets sur 7 jours — le remplacement modernisé
de l'ancien embed jQuery + Handlebars.  En-tête compact avec
navigation ◀ / ▶, onglets jour-de-semaine, et liste de lignes
par jour.

iframe prêt à l'emploi :

```html
<iframe src="https://votre-station.example/embed/weekly-program"
        width="400" height="560" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Ce qu'il affiche

```
◀  21 May – 27 May 2026                ▶            ← bande d'en-tête
MON  TUE  WED  THU  FRI  SAT  SUN                   ← onglets
 21   22   23   24   25   26   27                      (aujourd'hui encerclé)
─────────────────────────────────────────────────
06:00 - 08:00    Matinale                            ← liste de lignes
08:00 - 10:00    Newslink                              (par onglet actif)
...
```

- **Bande d'en-tête** : ◀ bouton → semaine précédente,
  libellé de plage hebdomadaire centré (p.ex.
  "21 May – 27 May 2026"), ▶ bouton → semaine suivante.
  Cliquer met à jour le paramètre `week_offset` de l'URL
  iframe en place via `history.pushState` et recharge.
- **Onglets jour** : 7 onglets (Lun … Dim dans la langue de la
  station).  L'onglet d'aujourd'hui est décoré d'un anneau
  pill subtil autour du numéro du jour.
- **Liste de lignes** : par onglet, une ligne par émission.
  Heure à gauche, nom à droite.  Les noms liés à une
  `cc_show.url` rendent comme liens ouvrant dans un
  nouvel onglet.

### Paramètres URL

| Paramètre | Valeurs | Défaut | Effet |
|---|---|---|---|
| `week_offset` | entier -2..4 | `0` | Épingle la fenêtre à ±N semaines de la semaine en cours, qui commence le jour réglé sous Paramètres → Général → La semaine commence le (depuis le 25/10/2026 ; avant, la fenêtre commençait aujourd'hui).  Cap serré (-2 / +4) car les cas d'usage homepage publique ont rarement besoin d'une plage plus large ; les boutons ◀ / ▶ se désactivent à la limite. |
| `theme` | `auto`, `dark`, `light` | `auto` | Identique aux autres widgets — voir §2. |
| `cache` | entier secondes 10..3600 | `60` | Identique aux autres widgets — voir §8. |
| `overflow` | `ellipsis`, `marquee` | `ellipsis` | Comportement des noms d'émission plus larges que 400 px. |
| `link` | `underline`, `plain` | `plain` | Rendu des liens de noms d'émission (voir On-Air-Today §5). |
| `bg` | URL d'une image | aucune | Image de fond optionnelle (cover-positionnée) au lieu du remplissage transparent par défaut. |
| `bgcolor` | couleur hex, p.ex. `#222222` | aucune | Couleur de fond optionnelle comme chaîne hex (3, 6 ou 8 caractères avec alpha — p.ex. `#fff`, `#112233`, `#11223388`).  Rend derrière `?bg` quand les deux sont définis.  Les valeurs non-hex sont rejetées pour des raisons de sécurité. |
| `timezone` | tout fuseau IANA | défaut station | Toutes les heures rendues dans cette zone. |

> **Onglet du jour + état actif.**  L'onglet jour-de-
> semaine correspondant à la date d'aujourd'hui est
> rempli de la couleur d'accent (défaut LibreTime teal
> `#459B8F`) pour que l'opérateur voie d'un coup d'œil
> où il se trouve dans la semaine.  L'onglet du panneau
> actuellement actif reçoit un soulignement couleur
> d'accent.  Le survol d'un onglet ou des boutons
> ◀ / ▶ allume la même couleur d'accent en alpha
> faible — indice d'interactivité subtil.

> **Défilement automatique vers l'émission en cours.**
> Quand l'onglet actif est aujourd'hui, le widget fait
> défiler l'émission actuellement diffusée au centre du
> viewport du panneau — pour que le visiteur atterrisse
> directement sur "ce qui passe maintenant" au lieu de
> devoir faire défiler par-dessus le programme du petit
> matin.  L'émission en cours est aussi marquée d'une
> bordure gauche couleur d'accent pour que le visiteur la
> repère après le défilement.  Sans effet quand
> aujourd'hui a une lacune de programme ou quand un autre
> jour est actif.

> **Largeur.** Le widget Weekly Schedule fait **670 px de large**
> (élargi depuis 400 px le 2026-05-25 sur demande de l'opérateur —
> toutes les polices, paddings et la max-height du panneau de jour
> ont été mis à l'échelle proportionnellement ; l'iframe dans le
> snippet d'intégration recommandé est `width="670" height="670"`).
> Réglez l'iframe sur ces valeurs dans le HTML d'intégration pour
> un ajustement précis.
>
> **Smartphones.** En dessous de 670 px, le widget suit la largeur de
> l'iframe ; il tient sur un écran de smartphone de 350 px (iframe
> `width="100%"`).  Depuis le 25/10/2026, l'heure et le nom de
> l'émission ont une police plus petite (environ 14 px au lieu de
> 19 px), si bien que la plupart des noms tiennent sur une ligne ; un
> nom très long se termine par « … ».

### Épisodes modifiés / annulés

Même convention que les autres widgets —
`modified_instance = TRUE` sont filtrées.

### Page Paramètres

**Paramètres → Widgets → Weekly Schedule** héberge la
personnalisation du libellé d'état vide ("No shows scheduled
on this day" par défaut), un aperçu iframe en direct sur
fond sombre, et le code `<iframe>` d'intégration prêt à
l'emploi.

---

## 7. Widget Multi-View Schedule

Widget calendrier basé sur **FullCalendar 6.1.10** (intégré
localement, sans dépendance CDN).  Trois vues commutables :
**Day**, **2-Day**, **Week**.  Layout time-grid avec créneaux
d'émission colorés, ligne now-indicator, auto-scroll vers
l'émission actuellement diffusée, et modal d'ouverture au
clic avec description + lien URL.

iframe prêt à l'emploi :

```html
<iframe src="https://votre-station.example/embed/multi-view-schedule"
        width="100%" height="600" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Ce qu'il affiche

- **Bande d'en-tête** : bouton **Today** tout à gauche
  (revient à maintenant et re-déclenche l'auto-scroll),
  ◀ / ▶ navigation, libellé de plage de dates centré,
  commutateur de vue (DAY / 2-DAY / WEEK).  La vue WEEK
  commence le jour réglé sous Paramètres → Général → La
  semaine commence le.
- **Time-grid** : 24h, créneaux 15 min, libellés horaires
  60 min.  Ligne now-indicator en couleur d'accent.
- **Créneaux d'émission** : depuis `cc_show_instances`
  JOIN `cc_show`.  Couleur de fond depuis le
  `background_color` configuré (Calendrier → Émission →
  Modifier → Style).  L'émission actuellement diffusée
  reçoit un anneau d'accent.
- **Clic** : ouvre un modal avec nom, plage horaire,
  description et lien click-through vers l'URL de
  l'émission (si configurée).

### Paramètres URL

| Paramètre | Valeurs | Défaut | Effet |
|---|---|---|---|
| `view` | `day`, `2day`, `week` | `day` | Vue initiale.  Le visiteur peut toujours changer via les boutons in-widget. |
| `theme` | `auto`, `dark`, `light` | `auto` | Identique aux autres widgets — voir §2. |
| `clock` | `24`, `12`, `auto` | `24` | Format heure-du-jour sur l'axe horaire, dans les créneaux d'émission et dans le modal.  `24` force le style `17:00` quelle que soit la locale ; `12` force `5 PM` ; `auto` laisse FullCalendar choisir selon la locale. |
| `cache` | entier secondes 10..3600 | `300` (5 min) | TTL cache HTTP côté serveur pour le flux JSON.  Défaut plus élevé que les autres widgets. |
| `bg` | URL d'une image | aucune | Identique au widget Weekly Schedule — voir §6. |
| `bgcolor` | couleur hex | aucune | Identique au widget Weekly Schedule — voir §6. |
| `timezone` | tout fuseau IANA | défaut station | Toutes les heures rendues dans cette zone. |

### Page Paramètres

**Paramètres → Widgets → Multi-View Schedule** héberge le
libellé d'état vide, un aperçu iframe en direct sur fond
sombre, et des snippets de code d'intégration prêts à
l'emploi pour les trois vues par défaut.

### Performance

- **FullCalendar hébergé localement** sous
  `/js/libs/fullcalendar/` (~282 KB JS + ~26 KB locales).
  Pas de round-trip CDN, pas de dépendance réseau externe.
- **CSS bundlé dans le JS** par FullCalendar 6 — pas de
  chargement de feuille de style séparée.
- **Lazy event-fetch** : FullCalendar récupère uniquement
  les événements de la plage actuellement visible.

---

## 8. Widget Track History

Journal de lecture des pistes — le visiteur choisit un jour
des 7 derniers, sélectionne une taille de page (10 / 20 /
50 / 100), et le widget affiche les pistes diffusées en
ordre chronologique inverse.  Clic sur une ligne → modal
avec métadonnées + contexte d'émission + lien URL.

iframe prêt à l'emploi (~500 px de haut) :

```html
<iframe src="https://votre-station.example/embed/track-history"
        width="100%" height="500" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Paramètres URL

| Paramètre | Valeurs | Défaut | Effet |
|---|---|---|---|
| `date` | `YYYY-MM-DD` | aujourd'hui | Jour à charger.  Limité à `[aujourd'hui - 6 jours, aujourd'hui]`. |
| `time` | `HH:MM` (24h) | maintenant (aujourd'hui) / 23:59 (jour passé) | Borne supérieure de l'heure.  Pistes terminées AVANT ce point, plus récentes en premier. |
| `pagesize` | `10`, `20`, `50`, `100` | `10` | Pistes par page. |
| `exclude_short` | `0`, `1` | Préférence (défaut `1`) | Masquer les pistes plus courtes que `min_sec` secondes (jingles / station IDs). |
| `min_sec` | entier 1..3600 | Préférence (défaut `60`) | Seuil en secondes pour le filtre exclude-short. |
| `theme` | `auto`, `dark`, `light` | `auto` | Identique aux autres widgets. |
| `cache` | entier secondes 10..3600 | `60` | TTL cache HTTP. |
| `bg`, `bgcolor` | URL / hex | aucune | Identique aux autres widgets. |
| `timezone` | tout fuseau IANA | défaut station | Toutes les heures dans cette zone. |

**Format de ligne** : `HH:MM - HH:MM Artiste - Titre` — heure de début + fin à gauche, puis artiste / titre en **gras**.

La page **Paramètres → Widgets → Track History** héberge en plus la case **Exclude short tracks** + le champ de seuil en secondes (style Auto-Expiry — le champ secondes n'apparaît que quand la case est cochée).

Source : `cc_playout_history` LEFT JOIN `cc_files` LEFT JOIN
`cc_show_instances` → `cc_show` avec fallback sur
`cc_playout_history_metadata`.  Six types de lignes :

1. **Lectures de fichier programmées** (`file_id IS NOT
   NULL`) — titre / artiste depuis `cc_files`.
2. **Items webstream programmés** (`file_id IS NULL`) —
   écrites par `insertPlayedItem()` pour les items avec
   `stream_id`.  Bloc synthétique avec
   `title = cc_webstream.description` (fallback sur
   `name` si description est vide) et
   `artist = cc_webstream.name`.
3. **Items line-in programmés** (`file_id IS NULL`,
   **RASTATIME uniquement**, requiert la migration 0047
   `cc_schedule.linein_id`) — écrites par
   `insertPlayedItem()` pour les items avec `linein_id`
   (opérateur a glissé une line-in depuis la Library
   dans une émission, ex. "Jabra-Mikro").  Bloc
   synthétique avec `title =
   rastatime_linein.description` (texte libre, fallback
   sur le nom court si description vide) et
   `artist = rastatime_linein.name` (libellé court).
   `linein_id` lu via SQL brut car les classes ORM
   Propel ont été générées avant la migration RastaTime.
4. **Pistes webstream** (`file_id IS NULL`) — écrites
   par `insertWebstreamMetadata()` à chaque métadonnée
   ICY entrante.
5. **Sessions Live-Show** (`file_id IS NULL`) — nouveau
   2026-05-23.  Écrites par `ensureLiveShowLogged()` en
   side-effect sur `/api/live-info(-v2)`.  Détecte les
   épisodes avec `time_filled = '00:00:00'`.
   Artist = "Live Show".
6. **Bascules manuelles Dashboard** (`file_id IS NULL`)
   — écrites par `insertLineInLog()` lors d'un toggle
   Master/Show Source.  Artist = "Master Source" /
   "Show Source".

Libellé pour types 5+6 configurable sous Paramètres →
Widgets → Track History → "Line-Input label".  Le type
3 utilise à la place le `name` par-line-in de
`rastatime_linein`, défini par l'opérateur dans la
Line-In Library.

Dans le modal : la légende **"Played in the show:"**
précède la ligne du nom d'émission.  Pour les entrées
webstream sans liaison d'épisode, le bloc contexte
d'émission est masqué.

**Paramètres → Widgets → Track History** héberge le libellé
d'état vide, le texte du bouton Load more (**Load more
button text**, vide = valeur traduite de la langue de la
station, p. ex. « Charger plus » ; depuis le 2026-11-10),
l'aperçu en direct, et deux snippets prêts à l'emploi
(pagesize 10 + 50).

Le widget occupe exactement la hauteur de l'iframe.  Si
les lignes ne tiennent pas (pagesize plus grand, Load
more), la liste défile avec sa propre barre ; l'en-tête et
le bouton Load more restent visibles (depuis le
2026-11-10).

---

## Widget Stream Player (`/embed/player`)

> Reconstruit le 18/09/2026 dans le style des vagues — le lecteur
> jQuery de 2015 a disparu.  Les anciennes URL d'intégration
> fonctionnent sans changement.

Bouton d'écoute en direct pour la page d'accueil publique.  Joue
les streams activés sous **Settings → Streams** : le widget
préfère les streams mobiles sur petits écrans, ne garde que les
formats décodables par le navigateur du visiteur et bascule
automatiquement sur le stream suivant en cas de panne.  Les lignes
now-playing, émission et **Next** se rafraîchissent via l'endpoint
de données des widgets ; un hôte Icecast configuré en localhost
est réécrit vers l'hôte de la page pour les auditeurs distants.

Deux layouts :

* **card** (défaut) — panneau compact, avec curseur de volume
  (mémorisé par navigateur).
* **bar** — barre pleine largeur de 56 px, pensée fixée en bas de
  page (la page d'accueil de la station l'utilise).

Paramètres d'URL (tous optionnels) :

| Paramètre | Valeurs | Signification |
|---|---|---|
| `title` | texte | Texte d'en-tête ; sans lui, l'en-tête est masqué. |
| `theme` | `auto` / `dark` / `light` | Même theming que chaque widget. |
| `layout` | `card` / `bar` | Layout ; l'ancien `style=premium` pointe toujours vers `bar`. |
| `stream` | `auto` / nom du stream | Épingler un stream configuré au lieu du choix automatique. |
| `cache` | `10`..`3600` | Cache du poll de métadonnées en secondes. |

Les codes d'intégration avec aperçu sont sous **Settings →
Widgets → Player**.  Les libellés d'état vide sont partagés avec
les widgets Now-Playing (section 9).

---

## 9. Personnaliser les libellés d'état vide

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

## 10. Le paramètre `cache` — quel TTL ?

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

## Pochettes (`?art=`)

> Ajouté le 18/09/2026.

Deux widgets peuvent afficher la pochette du titre en cours :

| Widget | Défaut | Comment le changer |
|---|---|---|
| Stream Player | case **Show cover artwork** sous Settings → Widgets → Player (activée d'usine) | par intégration : `?art=on` / `?art=off` |
| Now Playing — Track | **désactivé** | par intégration : `?art=on` |

La case du lecteur est un réglage enregistré : elle s'applique aussi
aux intégrations sans paramètre `art` — y compris la barre de la
page d'accueil de la station.  Un `?art=` explicite dans l'URL
d'intégration l'emporte toujours.

Now Playing reste volontairement *désactivé* par défaut : ce widget
est documenté avec `height="50"`, les pochettes sont donc en opt-in.
Avec `?art=on` la boîte atteint environ 48 px — donnez alors
`height="56"` ou plus à l'iframe.

La Track History n'affiche pas de pochettes.

À quoi s'attendre :

* **D'abord la pochette du titre, puis l'image de l'émission.**  Un
  titre avec pochette affiche la sienne.  Pour tout le reste —
  webstream, Line-In, titre sans pochette — le widget affiche depuis
  le 2026-09-30 l'**image de l'émission en cours** (Calendar →
  émission → *Show image*) : un relais en direct comme l'heure BBC
  porte ainsi l'image que vous avez donnée à cette émission.  Sans
  image d'émission, c'est la **pochette par défaut** qui s'affiche
  (Settings → Widgets → Player, depuis le 2026-10-01 ; réduite à
  256 px au téléversement), et sans elle l'image est simplement omise
  et le texte prend sa place.  L'image de l'émission est servie telle
  qu'elle a été téléversée (pas de vignette) — gardez-la légère,
  quelques centaines de Ko au plus.
* **Le Stream Player suit le Stream Label.**  Avec *Artist - Title*
  ou *Show - Artist - Title* (Settings → Streams), le lecteur
  fonctionne comme ci-dessus.  Avec *Station name - Show name*,
  l'auditeur n'apprend pas le titre ; le lecteur nomme donc (depuis
  le 2026-10-01) l'émission en titre, le nom de la station dessous,
  affiche l'image de l'émission ou la pochette par défaut — jamais une
  pochette de titre — et sa ligne *Next* nomme l'émission suivante.
  Le widget Now Playing — Track garde l'ordre « titre d'abord » : c'est
  par définition un widget de titre.
* **Les pochettes nécessitent l'API publique.**  Elles viennent du
  même endpoint que le widget Song Request, soumis à Settings →
  Preferences → *Public API*.  Interrupteur éteint : les widgets
  fonctionnent toujours, sans images.

Si les pochettes apparaissent rarement, la cause est presque toujours
la médiathèque et non le widget : seuls les fichiers dont la pochette
a été importée en ont une.

---

## 11. Thèmes

Trois modes, contrôlés via le paramètre `theme` :

| `theme=` | Effet |
|---|---|
| `auto` (défaut) | Texte clair sur pages d'intégration sombres, texte sombre sur claires. Détecté via la media query `prefers-color-scheme` du navigateur. |
| `dark` | Force le texte clair. |
| `light` | Force le texte sombre. |

Le fond du widget est **toujours transparent** pour qu'il
se fonde dans la page d'intégration.

---

## 12. Authentification

Aucune. Les widgets Now-Playing sont intentionnellement
publics : tout l'intérêt est que n'importe quel visiteur
du site public de votre station puisse voir ce qui est à
l'antenne.

Ils n'exposent **pas** : nombres d'auditeurs, état de la
source stream, noms d'opérateurs, état d'enregistrement,
IDs internes.

---

## 13. Intégration cross-origin

Deux réglages décident si un navigateur affiche un widget
dans un autre site.  Les deux doivent l'autoriser, sinon le
navigateur affiche un espace réservé à la place du widget
(Firefox : « n'est pas autorisé à ouvrir cette page
intégrée »).

1. **Côté RASTATIME (hôte HTTPS public).** L'interface du
   studio est envoyée avec `X-Frame-Options: SAMEORIGIN`
   pour qu'aucun autre site ne puisse l'intégrer.  Pour les
   widgets sous `/embed/`, cet en-tête est remplacé par
   `Content-Security-Policy: frame-ancestors 'self' <sites>`
   dès que les sites autorisés sont inscrits dans
   `config\apache-site.conf` (depuis le 2026-11-10) :
   ```
   Define RT_EMBED_ANCESTORS "https://radio.example.org https://www.radio.example.org"
   ```
   Séparés par des espaces, chacun avec `https://` ;
   redémarrez ensuite Apache (`RASTATIME-APACHE` ; les flux
   d'écoute sous `/stream/` se reconnectent, choisissez donc
   un moment calme).  Sans cette ligne, seul l'hôte
   RASTATIME peut afficher les widgets.  L'adresse LAN en
   http n'envoie aucun des deux en-têtes.
2. **Côté de votre site.** Si votre site envoie lui-même un
   en-tête `Content-Security-Policy`, celui-ci doit
   autoriser les cadres de l'hôte RASTATIME, par ex.
   `frame-src 'self' https://rastatime.example.org;`.
   Une politique limitée à `default-src 'self'` bloque tous
   les widgets intégrés.  Cela se règle sur le serveur web
   ou dans le CMS de votre site, pas dans RASTATIME.

Vérification : ouvrez le site, puis la console du
navigateur (F12).  « Refused to display … X-Frame-Options »
ou « frame-ancestors » désigne le côté 1, « violates …
frame-src / default-src » le côté 2.

---

## 14. Dépannage

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

### "Le widget On-Air-Today est vide alors que des émissions sont programmées"

- Vérifiez que *aujourd'hui* dans le fuseau de la station
  a encore des émissions à venir : tard dans la nuit, le
  widget devient légitimement vide jusqu'à la prochaine
  minuit station.  Pour regarder devant, épinglez un jour
  spécifique via `?day=YYYY-MM-DD`.
- Vérifiez que les émissions sont effectivement programmées
  dans le Calendrier — les épisodes annulés
  (`modified_instance = TRUE`) sont filtrées by-design.
- Si l'URL de l'iframe contient `?timezone=...`, cela
  surcharge le fuseau de la station pour le calcul de
  "aujourd'hui".  Un embed `?timezone=Asia/Tokyo` montrera
  l'aujourd'hui de Tokyo, qui peut déjà être demain à la
  station.

### "Le widget Next / Latest Shows affiche le placeholder vide"

- Vérifiez que l'URL de l'iframe contient `?show_id=N`
  (préféré) ou `?show=Nom`.  La page Paramètres (§5)
  génère le snippet avec l'id déjà intégré — copiez-le
  de là plutôt que de bricoler l'URL à la main.
- Confirmez que l'émission a effectivement des épisodes
  futurs dans le calendrier (pour Next Shows) ou a été
  diffusée au moins une fois (pour Latest Shows).  Une
  émission toute neuve sans épisodes diffusés affiche le
  placeholder vide dans le widget Latest jusqu'à la fin
  du premier épisode.
- Les lignes `modified_instance = TRUE` sont filtrées
  by-design (correspond au tableau de bord interne).
  Une émission dont le seul épisode à venir a été
  déplacé ou annulé affiche vide jusqu'à ce qu'un
  nouvel épisode soit généré.

---

## Où aller ensuite

* [Tableau de bord](./DASHBOARD.md) — la version interne
  des mêmes données.
* [Streams](./STREAMS.md) — les streams audio sous-jacents.
* [BACKLOG.md](../../../BACKLOG.md) — vagues de widgets à
  venir.
