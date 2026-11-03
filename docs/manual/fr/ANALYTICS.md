# Analytics

> **Où vous êtes dans le manuel.** Ceci est un chapitre de
> **Sortie et infrastructure**, un compagnon de
> [Streams](./STREAMS.md). Streams couvre la *configuration* de
> vos sorties et leur surveillance en direct ; ce chapitre couvre
> le **rétroviseur** — ce qui est réellement passé à l'antenne, et
> combien de personnes écoutaient pendant ce temps.

Le menu **Analytics** de la barre de navigation regroupe cinq
pages :

| Page | Question à laquelle elle répond |
|---|---|
| **Playout History** | Qu'est-ce que la station a réellement diffusé, minute par minute ? |
| **History Templates** | Quelles colonnes le journal de diffusion doit-il enregistrer et exporter ? |
| **Listener Stats** | Combien d'auditeurs étaient connectés à chaque flux, au fil du temps ? |
| **Show Listener Stats** | Quelle audience chaque *émission* a-t-elle réalisée ? |
| **Participants** | Combien de personnes ont fait les émissions d'une année ? Voir [Archivage](./ARCHIVING.md) § 6 (depuis le 2026-11-03). |
| **Yearly Report** (rapport annuel) | Minutes de programme des productions propres et aperçu des participants, une année à la fois, CSV. Voir § 5 (depuis le 2026-11-03). |

Les deux premières existent pour la **traçabilité** — déclarations
de droits d'auteur, journaux réglementaires, appels du type « quel
était ce titre à 14 h 32 ? ». Les deux dernières existent pour les
**décisions de programmation** — quels créneaux et quelles
émissions attirent réellement un public.

---

## 1. Playout History

**Analytics → Playout History** montre tout ce que le moteur de
diffusion a réellement envoyé à l'antenne, quelle que soit la façon
dont c'est arrivé dans la grille (émission du calendrier, Auto DJ,
override manuel, DJ en direct).

En haut, un **sélecteur de plage date/heure** avec **Filter
History** restreint chaque vue à une fenêtre — par défaut, le jour
courant.

Trois onglets en dessous (les DJ ne voient que le troisième, avec les
émissions qu'ils animent ; ils y ajoutent, modifient et suppriment des
entrées - les Program Managers et les Admins modifient toutes les
entrées) :

* **Log Sheet** — le journal brut de diffusion, une ligne par
  élément joué, avec ses heures de début / fin et les colonnes de
  métadonnées définies par votre modèle actif (voir §2). C'est la
  vue que vous exportez pour les sociétés de gestion des droits.
* **File Summary** — la même fenêtre agrégée **par piste** :
  combien de fois chaque fichier est passé sur la période. Triable
  par n'importe quelle colonne.
* **Show Summary** — la même fenêtre groupée **par instance
  d'émission**. Dépliez une émission pour voir ce qui y est passé.

> **Astuce opérateur.** Le Log Sheet enregistre ce que le *moteur*
> a joué. Un DJ en direct qui parle sur le flux ne laisse aucune
> ligne ici — seule la lecture de fichiers et de webstreams est
> journalisée.

> **Comment ça marche sous le capot.** Le service playout écrit
> une ligne par élément diffusé dans `cc_playout_history` (plus
> `cc_playout_history_metadata`) au moment où l'élément démarre.
> Les trois onglets sont des vues DataTables sur
> `/playouthistory/{playout-history-feed,file-history-feed,show-history-feed}`,
> toutes filtrées côté serveur selon la plage choisie.

> **Un titre supprimé garde son historique (depuis le 2026-10-08).**
> Chaque ligne de fichier porte le titre, le créateur, la durée, le
> compositeur et le copyright du moment de la diffusion. Supprimer le
> titre de la bibliothèque vide seulement la référence au fichier ; la
> ligne reste et s'affiche à partir de ces valeurs - comme les lignes
> de webstream et de line-in. L'onglet *File Summary* compte les titres
> qui existent encore. Avant, LibreTime supprimait les lignes avec le
> titre.

---

## 2. History Templates

**Analytics → History Templates** contrôle **quelles colonnes de
métadonnées** le Log Sheet et le File Summary enregistrent et
affichent. Il existe deux types de modèles — **Log Sheet
Template** et **File Summary Template** — et exactement un de
chaque est le modèle par défaut actif.

Ajoutez des champs par nom et type (chaîne / entier / date …),
ordonnez-les, puis **Set Default Template**. Les nouvelles lignes
d'historique enregistrent les champs du modèle actif *au moment de
la diffusion* ; changer de modèle ne réécrit pas les anciennes
lignes.

> **Astuce opérateur.** Configurez votre modèle **une fois,
> avant** d'avoir besoin de votre premier rapport de droits, puis
> n'y touchez plus. Les champs d'origine (artiste, titre,
> date/heure de diffusion) satisfont la plupart des obligations
> déclaratives.

---

## 3. Listener Stats

**Analytics → Listener Stats** trace le nombre d'**auditeurs
connectés simultanément par point de montage** sur la plage
choisie, une ligne colorée par montage (p. ex. `rastatime`,
`rastatime-aac`). Utilisez le même sélecteur de date/heure que
dans Playout History ; les cases de la légende activent ou
masquent chaque montage.

Les chiffres proviennent de votre serveur de streaming : ils
comptent donc les auditeurs *directs* du flux. Les auditeurs
derrière un relais, un CDN ou un agrégateur apparaissent comme
**une seule** connexion.

> **Comment ça marche sous le capot.** Le service playout
> interroge toutes les **120 secondes** le `/admin/stats.xml` de
> chaque serveur Icecast configuré, avec les identifiants admin de
> la configuration du flux, et stocke un point de données par
> montage dans `cc_listener_count`. Seuls les flux dont le **Admin
> Password** est renseigné dans **Settings → Streams** sont
> interrogés ; les flux sans mot de passe sont ignorés avec un
> avertissement dans `logs/playout.log`.
> *(Rétabli sous Windows dans RASTATIME 2026-08-30 — sur les
> versions antérieures, ce graphique restait vide car aucun
> collecteur ne tournait.)*

**Stream Data Collection Status** (l'encadré à droite, depuis le
26/10/2026) : une ligne par flux actif avec son point de montage.
**OK** signifie que la dernière requête a réussi.  Sinon, la ligne
indique la cause et depuis quand : Icecast refuse l'utilisateur/mot de
passe admin (vérifiez-les dans **Settings → Streams**), est
injoignable, ne répond pas à temps, envoie une page de statistiques
illisible ou répond par une autre erreur.  À la première requête
réussie après le problème, la ligne revient d'elle-même à OK - avant
le 26/10/2026, une erreur restait affichée pour de bon et disait
toujours « vérifier utilisateur/mot de passe admin ».  Un flux sans
Admin Password indique qu'aucune statistique n'est collectée pour lui.

**Graphique vide ?** Par ordre de probabilité :

1. Le service **RASTATIME-PLAYOUT** ne tourne pas (c'est lui qui
   héberge le collecteur).
2. Le **Admin Password** du flux dans **Settings → Streams** est
   vide ou incorrect — cherchez dans `logs/playout.log` un
   avertissement de saut ou un HTTP 401.
3. Vous regardez une plage antérieure au début de la collecte —
   les données ne s'accumulent qu'à partir du premier passage du
   collecteur.

---

## 4. Show Listener Stats

**Analytics → Show Listener Stats** replie les mêmes données
d'audience **par instance d'émission** : pour chaque émission de
la plage choisie, vous obtenez le nombre **moyen** et le nombre
**maximum** d'auditeurs simultanés pendant son passage à
l'antenne.

C'est la page des décisions de programmation — comparez les
chiffres d'une émission sur plusieurs semaines, ou deux émissions
sur le même créneau.

> **Les chiffres d'émission exigent des données d'émission.** Une
> émission diffusée avant le début de la collecte (ou pendant un
> arrêt du playout) affiche des zéros — l'agrégation ne peut
> replier que les points de données existant dans
> `cc_listener_count` pour la fenêtre horaire de l'émission.

## 5. Rapport annuel (depuis le 2026-11-03)

**Analytics → Yearly Report** rassemble sur une page les chiffres de la
déclaration annuelle aux autorités, avec un sélecteur d'année (heure de
la station ; l'année en cours jusqu'à aujourd'hui).

**Minutes de programme.**  Cochez **Own production** (production propre)
dans une émission (Edit Show → What ; unique ou récurrente, les modèles
et l'Import/Export la portent comme `own_production`).  La page compte
les épisodes des émissions cochées diffusés dans l'année - terminés, non
supprimés, sans ancienne rediffusion - avec leur durée **planifiée**,
arrondie en minutes par émission et par mois.  Les émissions configurées
comme [Rediffusion d'une autre émission](./CALENDAR.md) ont leur propre
colonne (premières diffusions / rediffusions), car la plupart des
autorités les déclarent séparément.  Les émissions sans la case
apparaissent grisées avec leurs minutes sous « autres émissions (non
comptées) », pour voir ce qui manque.  Un tableau par mois et
**Download CSV (minutes)** (par émission, totaux, par mois) complètent la
section.

**Participants.**  Les mêmes chiffres que [Archivage](./ARCHIVING.md)
§ 6 (personnes impliquées par émission, épisodes avec valeur propre,
participations, équipes éditoriales), avec des liens vers le filtre
« émissions sans valeur » et le CSV des participants.

Les Program Managers et les Admins ouvrent cette page.
