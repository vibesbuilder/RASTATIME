# Machine locale

> **Où vous êtes dans le manuel.** Ce chapitre couvre la
> page Paramètres → **Machine locale**, qui possède chaque
> aspect lié à la *machine de l'opérateur elle-même* —
> sortie carte son, périphériques d'entrée line-in et
> dossier d'import local. Pour les streams sortants côté
> réseau, voir [Streams](./STREAMS.md). Pour le type
> d'item de bibliothèque qui *référence* une entrée carte
> son, voir [Line-In](./LINE_IN.md).

La page **Machine locale** est où vous informez RASTATIME
sur les ressources physiques de la machine de
l'opérateur : quelle sortie haut-parleur jouer, quels
périphériques comptent comme candidats line-in, et quel
dossier l'analyzer doit surveiller pour les pistes
importées.

La page remplace la page "Soundcard" de LibreTime d'origine
et ajoute la fonctionnalité dossier d'import. L'URL legacy
fonctionne toujours ; seuls le titre de la page et le slug
changent.

---

## 1. La page

Paramètres → **Machine locale**.

Trois sections indépendantes : Carte son (sortie + entrée),
Dossier d'import local.

---

## 2. Carte son — Périphériques de sortie

La liste montre chaque périphérique de sortie audio que la
machine de l'opérateur expose.

### Sortie par défaut (le "moniteur")

Le périphérique sélectionné est la sortie **moniteur /
cue** :

- Le bouton **Écouter** du tableau de bord joue dessus.
- Le bouton **Aperçu** de la bibliothèque joue dessus.
- L'aperçu du show-builder joue aussi dessus.

> **Ce que ce n'est PAS.** La sortie par défaut n'est
> *pas* le stream public. Les auditeurs n'entendent pas
> ce qui est joué ici.

### Pourquoi choisir un périphérique spécifique

- **Stations à opérateur unique** avec un seul jeu de
  haut-parleurs — laissez par défaut.
- **Stations à deux moniteurs** avec un haut-parleur
  "air-check" et un haut-parleur "interne" — choisissez
  ici l'haut-parleur interne.
- **Stations seulement-casque** — choisissez le
  périphérique casque.

### Pseudo-périphérique "(Défaut système)"

La première entrée est toujours **(Défaut système)**.
Ceci suit ce que le système Windows / Linux a marqué
comme sortie audio par défaut.

> **Comment ça marche sous le capot.** Les périphériques
> sont énumérés via `audio.soundcard.windows_manager`
> (WASAPI sous Windows, portaudio sous Linux). Le
> périphérique sélectionné est persisté dans `cc_pref`
> comme `default_output_device_id`. Voir ARCHITECTURE §9.

### Appliquer un changement — « Appliquer maintenant »

Enregistrer mémorise le périphérique ; cela ne déplace **pas**
encore le moniteur local. Le moteur de diffusion compile le
périphérique choisi dans son script Liquidsoap au démarrage du
service, et Liquidsoap ne lit ce script qu'à son *propre*
démarrage. Appliquer un changement exige donc le redémarrage
des deux services, dans cet ordre.

Plutôt que de redémarrer silencieusement à l'enregistrement —
ce qui couperait le flux public sans prévenir — la page
propose un bouton explicite sous le sélecteur :

**Appliquer maintenant (redémarre la chaîne audio)** —
redémarre RASTATIME-PLAYOUT (qui regénère le script avec le
nouveau périphérique) puis RASTATIME-LIQUIDSOAP (qui le
charge).

Au-dessus du bouton, la page indique **quelle sortie pilote
réellement le moniteur**, lue depuis le script Liquidsoap généré et
non depuis le réglage enregistré. Si les deux diffèrent — changement
pas encore appliqué, ou périphérique impossible à ouvrir — la ligne
le signale en ambre. Une valeur enregistrée ne prouve pas qu'elle
soit utilisée.


> **Impact à l'antenne.** Le second redémarrage coupe les
> connexions source Icecast pendant quelques secondes ; les
> auditeurs entendent un bref silence. À faire entre deux
> émissions. Le bouton demande confirmation.

> **Comment le périphérique est identifié.** PortAudio liste le
> même point de terminaison une fois par API hôte Windows (MME,
> DirectSound, WASAPI, WDM-KS), et la copie qui fonctionne
> réellement dépend du matériel. RASTATIME teste donc les
> candidats au démarrage — via l'API **bloquante** de PortAudio,
> celle qu'utilise Liquidsoap — et retient le premier qui
> s'ouvre vraiment. Mesuré à 44,1 kHz sur la machine du studio :
> MME et DirectSound fonctionnent pour un casque USB ; WASAPI
> fonctionne lorsque le format Windows du point de terminaison
> correspond (voir la note suivante), et WDM-KS ne gère pas du tout
> l'API bloquante. Si aucun candidat ne s'ouvre,
> RASTATIME conserve le point de terminaison par défaut du
> système et consigne chaque raison d'échec dans le journal.

> **Le périphérique est inscrit dans le script par son nom, pas par
> son numéro.** PortAudio numérote ses périphériques dans l'ordre
> d'énumération, et sur une machine où des points de terminaison
> apparaissent tard après un redémarrage ou vont et viennent (casques
> USB, audio HDMI), ces numéros se décalent. Depuis le 2026-09-05, le
> script nomme donc le point de terminaison (`device_name="…"`) ;
> Liquidsoap cherche ce nom quand *il* démarre, de sorte qu'un numéro
> qui a changé entre les deux démarrages de services ne peut plus
> envoyer le moniteur sur la mauvaise prise. Le nom n'est utilisé que
> si l'entrée qu'il sélectionne est connue pour jouer (MME ou WASAPI,
> ouverte dans le même test que ci-dessus) ; sinon RASTATIME revient
> au numéro et l'explique dans le journal de diffusion. La ligne
> « actif » ci-dessus montre ce qui est en service.

> **Le format Windows du périphérique doit être 44,1 kHz.** Liquidsoap
> tourne à 44,1 kHz, et WASAPI en mode partagé exige exactement la
> fréquence de mixage configurée du point de terminaison. Un
> périphérique dont le format par défaut Windows est à 48 kHz est
> refusé par toutes les API hôtes et semble mort — mesuré sur le
> Tascam US-16x08, inutilisable jusqu'au réglage de son format à
> 44,1 kHz (Paramètres son Windows → la sortie → Avancé → format par
> défaut). Le journal de diffusion indique ce correctif dès qu'une
> fréquence est refusée. Une réinstallation de pilote peut réinitialiser
> le format ; la ligne « active » ci-dessus signale alors l'écart.
> Sortie et capture Line-In sur la même interface fonctionnent
> simultanément.

### Redémarrages automatiques et avertissements de santé

Deux situations redémarrent le moteur audio sans le bouton, et deux
avertissements du tableau de bord le surveillent (le tout depuis le
2026-09-05) :

- **Après un redémarrage de la machine.** Les deux services
  démarrent en parallèle, et le moteur peut charger l'ancien script
  avant que la diffusion n'ait rendu le nouveau. Si la diffusion
  constate que son rendu a modifié le script dans les dix premières
  minutes après le démarrage, elle redémarre elle-même
  RASTATIME-LIQUIDSOAP. Rien n'est à l'antenne si tôt. Les
  changements ultérieurs nécessitent toujours le bouton ou l'ordre
  manuel : la diffusion d'abord, puis Liquidsoap.
- **Une fois par nuit.** La version Windows de Liquidsoap perd
  lentement de la mémoire en fonctionnant. La diffusion le redémarre
  donc une fois par jour dans une fenêtre calme qui s'ouvre à 04:00
  (réglage machine `RASTATIME_LIQUIDSOAP_NIGHTLY_RESTART`, `HH:MM`
  ou `off`) — seulement si rien n'est à l'antenne, rien n'est en
  préchauffage et aucune émission ne commence dans les cinq minutes.
  Les auditeurs entendent une coupure de quelques secondes ; une
  émission qui dure toute la nuit reporte le redémarrage jusqu'à la
  fermeture de la fenêtre.
- **Avertissement mémoire.** La bannière du tableau de bord affiche
  *Liquidsoap utilise N Mo* lorsque la mémoire du moteur dépasse
  2048 Mo (réglage machine `RASTATIME_LIQUIDSOAP_MEMORY_WARN_MB`).
  Redémarrez la diffusion puis Liquidsoap dans un moment calme.
- **Avertissement Main Output.** La bannière affiche *Main Output :
  Liquidsoap joue sur … au lieu de …* lorsque le moteur ne détient
  aucune session audio sur le périphérique de sortie choisi alors
  qu'il tourne depuis un moment. Le moniteur est alors sur la
  mauvaise prise ; redémarrez la diffusion puis Liquidsoap.

---

## 3. Carte son — Périphériques d'entrée

La liste montre chaque périphérique d'entrée audio que la
machine de l'opérateur expose. La case à cocher contrôle
lesquels sont **candidats** pour utilisation comme
Line-Ins nommés.

### Lesquels activer

| Périphérique | Cocher ? | Pourquoi |
|---|---|---|
| **Microphone studio** | Oui | La raison pour laquelle la plupart des stations ont un line-in. |
| **Sortie mixeur** (XLR / TRS via interface) | Oui | Le mix studio complet comme source unique. |
| **Microphone intégré** | Seulement si utilisé | Décocher le supprime du menu déroulant de création Line-In. |
| **Microphone webcam** | Non (généralement) | Basse qualité, souvent sélectionné par accident. |
| **Jack line-in à l'arrière** (si non utilisé) | Non | Même prévention d'accident. |

Cocher / décocher ne **désactive** pas le périphérique au
niveau OS — Windows le voit toujours. RASTATIME le retire
juste du menu déroulant de création Line-In.

### Du périphérique d'entrée au Line-In nommé

Pour utiliser un périphérique comme source de
planification, créez un Line-In nommé dans la section
**Line-In Sources** de cette page même (au-dessus d'Import
Folder depuis le 2026-08-31) — cet éditeur complet choisit
aussi les **canaux d'entrée** (paire stéréo ou mono) sur les
interfaces multicanal. Une création rapide épurée existe
aussi dans la bibliothèque sous **Line Inputs → + Nouveau**
(canaux 1/2 par défaut). Voir [Line-In](./LINE_IN.md).

---

## 4. Sortie par défaut pour cue / moniteur

Le menu déroulant sous la liste des périphériques de
sortie répète le défaut en forme à ligne unique.

---

## 5. Dossier d'import local

Le Dossier d'import local est un répertoire sur la machine
de l'opérateur que l'analyzer surveille pour de nouveaux
fichiers. Tout ce qui est déposé dans le dossier est
automatiquement importé dans la bibliothèque au prochain
cycle de poll de l'analyzer (par défaut toutes les 60 s).

### Configurer le dossier

| Champ | Notes |
|---|---|
| **Chemin du dossier** | Un chemin absolu sur la machine de l'opérateur. Doit exister et être lisible par le service RASTATIME-ANALYZER. Par défaut : `C:\rastatime\import\`. Laisser vide pour désactiver. |
| **Dernier scan** | Quand l'analyzer a tourné un scan en dernier + résumé du résultat. |

Le bouton **Scanner maintenant** déclenche un scan
immédiat sans attendre le poll de 60 s.

### Comment les fichiers sont traités

Pour chaque nouveau fichier que l'analyzer trouve :

1. Le fichier est déplacé (pas copié) dans une zone de
   staging (`C:\rastatime\import\.staging\`).
2. L'analyzer exécute ffprobe + vérification de
   jouabilité ffmpeg.
3. En cas de succès, le fichier est déplacé vers
   `C:\rastatime\media\<owner>\<year>\<month>\<filename>`
   et une ligne `cc_files` est insérée.
4. En cas d'échec dur, le fichier est déplacé vers
   `C:\rastatime\import\.failed\` avec un fichier
   `.err` à côté.
5. En cas d'échec mou, le fichier est importé avec un
   badge d'avertissement jaune.

### Sous-dossiers

Les sous-dossiers sont scannés récursivement. Les
fichiers dans des sous-dossiers sont importés, et le
**nom du sous-dossier** devient le champ de métadonnées
`album` de la piste importée si le propre tag album ID3
du fichier est vide.

### Propriété

Les fichiers importés appartiennent au
**propriétaire-d'import par défaut** configuré (défini
sous Préférences générales → Propriétaire d'import par
défaut). Par défaut `admin`.

> **Comment ça marche sous le capot.** Le poller du
> Dossier d'import local est l'un des jobs d'arrière-plan
> du service `RASTATIME-WORKER` (le `LocalImportJob`).
> Voir ARCHITECTURE §16.

---

## 6. Dossiers d'enregistrement (lié)

Paramètres → Machine locale a **deux** dossiers de sortie
d'enregistrement :

### Show Recording Folder

Où [Enregistrement par émission](./RECORD_PER_SHOW.md) écrit un
fichier par émission marquée « enregistrer ». *(Renommé depuis
« Recording Folder » lors de l'ajout de l'enregistrement 24/7 —
2026-06-06.)*

Par défaut : `C:\rastatime\recordings\`.

### 24/7 Recording Folder

Où l'[enregistrement 24/7](./RECORD_PER_HOUR.md) permanent écrit
un fichier par heure d'horloge (plus un fichier de repères
`.cues.json`), indépendamment des émissions. Vous l'activez,
choisissez un format / débit et fixez une fenêtre de
suppression automatique directement dans cette section.
Gardez-le **séparé** du Show Recording Folder pour que le
nettoyage de rétention ne touche jamais les fichiers par
émission. Le dossier est créé à l'enregistrement s'il n'existe
pas encore.

Aucun des deux dossiers n'est candidat pour la Bibliothèque —
les enregistrements sont des fichiers autonomes pour
téléchargement / archive, non auto-importés.

> **Appliquez les modifications en redémarrant le service de
> diffusion.** Les réglages d'enregistreur sont intégrés au
> script Liquidsoap au démarrage ; après une modification,
> redémarrez donc **RASTATIME-PLAYOUT** (le dialogue Save le
> rappelle). Seule la valeur 24/7 **Delete after (days)** prend
> effet sans redémarrage.

---

## 7. Foire aux questions

### "Mon micro USB apparaît dans Windows, mais pas dans RASTATIME."

Trois choses à vérifier :

1. Le micro est **coché** sur la liste Périphériques
   d'entrée sur cette page.
2. Le service `RASTATIME-API` tourne et l'endpoint
   `/api/v2/audio/devices` renvoie le micro.
3. Le driver audio Windows permet encore l'accès à
   l'entrée.

### "Le Dossier d'import local n'importe rien."

Ordre de diagnostic :

1. Le chemin du dossier est correct et existe.
2. Le service `RASTATIME-ANALYZER` tourne.
3. Le service `RASTATIME-WORKER` tourne (il possède le
   poller).
4. Vérifiez **Dernier scan** — s'il montre "N fichiers
   échoués", regardez dans `.failed\` pour les fichiers
   `.err`.

### "Pourquoi déplacer et pas copier dans le Dossier d'import local ?"

Un workflow basé sur copie laisse l'opérateur avec deux
copies de chaque fichier importé et aucune propriété
claire.

### "Le Dossier d'import local peut-il être sur un partage réseau ?"

Oui, avec deux mises en garde : le partage doit être
monté au chemin que RASTATIME voit (ex. `Z:\import\`).
Les chemins UNC `\\server\share\import` ne sont *pas*
fiables avec les services lancés par NSSM sous Windows.

### "Puis-je avoir plusieurs Dossiers d'import local ?"

Non. Le poller scanne un répertoire configuré.

### "Quelle est la différence entre le Dossier d'import local et le bouton Téléverser ?"

| | Téléverser | Dossier d'import local |
|---|---|---|
| Origine | Côté navigateur | Système de fichiers côté serveur |
| Meilleur pour | Un ou deux fichiers | Lots de plusieurs fichiers |
| Timeout | Navigateur peut timeout | Pas de timeout |
| Propriété | Utilisateur connecté | Propriétaire par défaut configuré |

### "La sélection de périphérique de sortie affecte-t-elle ce que les auditeurs entendent ?"

Non. Le périphérique de sortie sur cette page est la
sortie **moniteur / cue**. Les auditeurs entendent la
sortie [Streams](./STREAMS.md).

---

## Où aller ensuite

* [Line-In](./LINE_IN.md) — transformer un périphérique
  d'entrée coché en item de bibliothèque planifiable
  nommé.
* [Bibliothèque](./LIBRARY.md) → §2 — alternatives au
  Dossier d'import local.
* [Streams](./STREAMS.md) — la sortie audio côté
  auditeur.
* [`docs/operator/DEVICE_MISSING.md`](../../operator/DEVICE_MISSING.md)
  — quand un périphérique précédemment configuré disparaît.
