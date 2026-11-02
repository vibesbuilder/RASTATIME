# Machine locale

> **Où vous êtes dans le manuel.** Ce chapitre couvre la
> page Paramètres → **Machine locale**, qui possède chaque
> aspect lié à la *machine de l'opérateur elle-même* —
> sortie carte son, périphériques d'entrée line-in, format
> d'import et dossier d'import local. Pour les streams sortants côté
> réseau, voir [Streams](./STREAMS.md). Pour le type
> d'item de bibliothèque qui *référence* une entrée carte
> son, voir [Line-In](./LINE_IN.md).

La page **Machine locale** est où vous informez RASTATIME
sur les ressources physiques de la machine de
l'opérateur : quelle sortie haut-parleur jouer, quels
périphériques comptent comme candidats line-in, dans quel
format les fichiers sans perte entrent dans la bibliothèque,
et quel dossier l'analyzer doit surveiller pour les pistes
importées.

La page remplace la page "Soundcard" de LibreTime d'origine
et ajoute la fonctionnalité dossier d'import. L'URL legacy
fonctionne toujours ; seuls le titre de la page et le slug
changent.

---

## 1. La page

Paramètres → **Machine locale**.

**Un seul enregistrement pour la page** *(depuis le 2026-10-27)* :
le bouton **Save** en haut à droite et le même en bas enregistrent
chaque section que vous avez modifiée - carte son, format
d'import, dossier d'import (avec la case de l'import en masse),
import FTP, enregistrement 24/7 et enregistrement des émissions -
l'une après l'autre ; les sections inchangées ne sont pas
réenregistrées.  Chaque section affiche son résultat sur sa propre
ligne, un résumé apparaît à côté du bouton.  Les boutons qui
agissent tout de suite - Apply now, Scan Now, Fetch now, Check,
Move library - restent dans leurs sections.

Sections indépendantes : Carte son (sortie + entrée), Format
d'import, Dossier d'import local, puis import FTP, emplacement de
la médiathèque et dossiers d'enregistrement.

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

### « Off - stream only » (depuis le 2026-11-02)

La liste **Main Output** a une entrée permanente **Off - stream only
(no local monitor output)**. Choisissez-la sur une machine sans
périphérique audio utilisable - machine virtuelle, serveur sans carte
son, studio qui écoute le stream Icecast à la place : le moteur de
playout ne rend alors aucune sortie locale. Pourquoi c'est important :
un sous-débit du tampon d'une sortie locale peut arrêter tout le moteur,
streams compris (vu deux fois sur une carte son virtuelle pendant la
répétition d'installation). Appliquez comme tout autre changement de
Main Output (« Appliquer maintenant » ci-dessous) ; la ligne d'état
indique alors **off (stream only)**.

### Appliquer un changement — « Appliquer maintenant »

> **Depuis le 16/09/2026, cela se fait tout seul.** Après
> l'enregistrement, la diffusion remarque le périphérique modifié à son
> prochain rafraîchissement de la grille (sous deux minutes) et
> redémarre la chaîne audio au prochain moment calme - ou, avec un
> programme 24/7, entre deux pistes fichier. Les auditeurs restent
> connectés via les montages de secours. Il en va de même pour
> l'enregistrement 24/7, les durées de fondu enchaîné (titres et
> émissions) et les sorties de flux.
> **Appliquer maintenant** reste le moyen de forcer immédiatement.

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

Deux situations redémarrent le moteur audio sans le bouton, et trois
avertissements du tableau de bord le surveillent (depuis le
2026-09-05 ; la protection et le troisième avertissement depuis le
2026-09-07) :

- **Après un redémarrage de la machine.** Les deux services
  démarrent en parallèle, et le moteur peut charger l'ancien script
  avant que la diffusion n'ait rendu le nouveau. Si la diffusion
  constate que son rendu a modifié le script dans les dix premières
  minutes après le démarrage, elle redémarre elle-même
  RASTATIME-LIQUIDSOAP. Rien n'est à l'antenne si tôt. Les
  changements ultérieurs nécessitent toujours le bouton ou l'ordre
  manuel : la diffusion d'abord, puis Liquidsoap.
- **Redémarrage planifié.** La version Windows de Liquidsoap perd
  lentement de la mémoire en fonctionnant ; la diffusion le
  redémarre donc volontairement. Quand : dans une fenêtre qui s'ouvre
  à 04:00 (réglage machine `RASTATIME_LIQUIDSOAP_NIGHTLY_RESTART`,
  `HH:MM` ou `off`) dès que le moteur a plus de N jours
  (`RASTATIME_LIQUIDSOAP_RESTART_EVERY_DAYS`, 1 par défaut, `0` =
  désactivé) ou occupe plus de `RASTATIME_LIQUIDSOAP_RESTART_AT_MB`
  (1536 par défaut) ; et à toute heure au-delà de
  `RASTATIME_LIQUIDSOAP_RESTART_HARD_MB` (3072 par défaut). Comment
  (depuis le 2026-09-09) : dans un moment calme où rien n'est à
  l'antenne, ou, en programme 24/7, entre deux titres de la playlist
  en cours, de sorte que la coupure d'environ deux secondes remplace
  un fondu enchaîné au lieu de couper un titre. Un webstream ou un
  line-in de part et d'autre de la frontière fait attendre la
  suivante. Depuis le 2026-10-02, le titre qui suit le redémarrage
  entre dans son audio des quelques secondes qu'a pris le redémarrage,
  afin que l'émission garde ses horaires au lieu de finir en retard
  d'autant. Depuis le 2026-09-09, les sources DJ signalent
  elles-mêmes leurs connexions et déconnexions ; la diffusion
  n'interroge donc plus le moteur toutes les cinq secondes, et cette
  interrogation était la principale cause de la croissance. Si la
  mémoire reste stable pendant une semaine,
  `RASTATIME_LIQUIDSOAP_RESTART_EVERY_DAYS` peut être augmenté (7 à 30).
  Surveillez aussi la limite mémoire souple : avec Stereo Tool actif,
  le moteur démarre déjà vers 1000 Mo, et une journée musicale complète
  ajoute 16 à 19 Mo par heure (environ un demi-mégaoctet par titre
  diffusé). La valeur par défaut de 1536 Mo est donc atteinte après
  une trentaine d'heures et le déclencheur mémoire redémarre le moteur
  une nuit sur deux, quel que soit l'intervalle. Relevez
  `RASTATIME_LIQUIDSOAP_RESTART_AT_MB` pour garder de la marge au-dessus
  de cette base (2560 Mo sur une machine avec 16 Go de RAM) ; la limite
  dure de 3072 Mo continue de protéger la machine. Relevez aussi
  l'avertissement du tableau de bord `RASTATIME_LIQUIDSOAP_MEMORY_WARN_MB`
  (2816 Mo, entre les deux limites), sinon la bannière s'affiche le
  dernier jour avant chaque redémarrage planifié.
- **Repli standby pour les auditeurs.** Un second Liquidsoap
  minuscule (service RASTATIME-STANDBY, script `standby.liq` rendu par
  la diffusion avec les mêmes encodeurs) diffuse du silence sur une
  copie `-standby` de chaque point de montage public, et
  `icecast.xml` désigne cette copie comme repli de chaque point
  public. Pendant les deux secondes d'un redémarrage, Icecast déplace
  les auditeurs vers le point standby puis les ramène ; personne
  n'est déconnecté. À installer une fois en administrateur avec
  `backend/playout/config/nssm-install-standby.ps1` après que la
  diffusion a rendu `standby.liq`, puis redémarrer Icecast une fois
  pour qu'il lise les points de repli. Réglez
  `RASTATIME_STANDBY_AUDIO` sur un fichier audio si vous préférez un
  tapis sonore de station au silence. Si vous renommez ou ajoutez une
  sortie de flux, le côté standby suit de lui-même (redémarrez
  RASTATIME-STANDBY quand le journal de la diffusion le demande), mais
  pas les blocs de repli d'Icecast : ajoutez un bloc correspondant pour
  le nouveau point de montage dans `icecast.xml` et redémarrez Icecast.
  La diffusion avertit dans son journal, à chaque démarrage, des points
  publics sans repli.
- **Par nom ou pas du tout.** Juste avant chaque redémarrage
  automatique, la diffusion relit la liste des cartes son et adresse
  le Main Output par le *nom* du périphérique. Si ce n'est pas
  possible à cet instant (l'écran du studio dort et son point de
  terminaison HD-Audio a disparu, le périphérique a été renommé, ou
  seule une entrée DirectSound/WDM-KS correspond), le redémarrage
  automatique est ignoré et le moteur en cours continue de jouer ;
  le journal de la diffusion en donne la raison. Redémarrez
  manuellement une fois le périphérique revenu. Contexte : les
  2026-09-06 et 2026-09-07, le redémarrage de 04:01 a utilisé un
  index de périphérique relevé pendant que l'écran dormait ; le
  nouveau moteur a ouvert le mauvais point de terminaison, est mort
  en deux secondes et a été relancé en boucle jusqu'au matin.
- **Avertissement mémoire.** La bannière du tableau de bord affiche
  *Liquidsoap utilise N Mo* lorsque la mémoire du moteur dépasse
  2048 Mo (réglage machine `RASTATIME_LIQUIDSOAP_MEMORY_WARN_MB`).
  Redémarrez la diffusion puis Liquidsoap dans un moment calme. Depuis le 15/09/2026, le journal de la diffusion enregistre aussi
  toutes les 15 minutes la mémoire du moteur avec sa croissance
  depuis son démarrage ; cherchez `Liquidsoap memory` dans
  `playout-stdout.log` pour voir la tendance.
- **Avertissement Main Output.** La bannière affiche *Main Output :
  Liquidsoap joue sur … au lieu de …* lorsque le moteur ne détient
  aucune session audio sur le périphérique de sortie choisi alors
  qu'il tourne depuis un moment. Le moniteur est alors sur la
  mauvaise prise ; redémarrez la diffusion puis Liquidsoap.
- **Le Main Output reste ouvert.** Depuis le 14/09/2026, le moteur
  ouvre le Main Output une seule fois au démarrage et ne le ferme plus
  tant qu'il tourne. La petite mémoire tampon devant le périphérique
  se vidait auparavant environ deux fois par jour ; le moteur rouvrait
  alors le périphérique avec une liste de périphériques périmée et
  s'arrêtait ou jouait sur un autre périphérique. Désormais, un court
  silence comble ce moment et la mémoire tampon ajuste la vitesse de
  lecture de façon inaudible pour rester remplie. Si vous soupçonnez
  un jour cet ajustement, mettez le réglage machine
  `RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT_ADAPTIVE` sur `false` et
  redémarrez la diffusion puis Liquidsoap ; la sortie reste alors
  ouverte avec une mémoire tampon fixe.
- **Avertissement moteur arrêté.** La bannière affiche *Liquidsoap
  ne tourne pas* ou *Liquidsoap redémarre sans cesse (boucle de
  plantage)* lorsqu'aucun processus du moteur n'existe ou qu'un
  nouveau apparaît à chaque analyse. Lisez la tranche la plus récente
  `logs/liquidsoap-stdout-*.log` (en
  général le périphérique Main Output), corrigez la cause, puis
  redémarrez la diffusion puis Liquidsoap.

---

## 3. Carte son — Périphériques d'entrée

> **Remarque (2026-10-20) :** la liste des périphériques d'entrée ne se
> trouve plus sur cette page. Le périphérique de capture d'un Line-In se
> choisit dans l'entrée Line-In elle-même (Bibliothèque → Line-In → créer ou
> modifier, voir [LINE_IN.md](./LINE_IN.md)). Le reste de cette section
> décrit l'ancienne liste à titre indicatif.

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
planification, créez un Line-In nommé dans la bibliothèque
sous **Line Inputs → + Nouveau** — depuis le 17/09/2026 ce
dialogue est l'unique éditeur complet (nom, périphérique,
canaux) ; l'ancienne section Line-In Sources de cette
page n'existe plus.  Voir [Line-In](./LINE_IN.md).

---

## 4. Sortie par défaut pour cue / moniteur

Le menu déroulant sous la liste des périphériques de
sortie répète le défaut en forme à ligne unique.

---

## 5. Format d'import

*(Depuis le 2026-10-14.)*  Une case à cocher : **Convertir l'audio
sans perte (WAV, FLAC, ...) en MP3 320 kbit/s à l'import** — **activée**
par défaut.  Elle s'applique à toutes les voies par lesquelles une
piste entre dans la bibliothèque : téléversement navigateur, dossier
d'import local, import FTP et commande d'import en masse.  Cliquez sur
**Save** (en haut à droite ou en bas) ; l'import suivant applique la
nouvelle valeur, aucun redémarrage n'est nécessaire.

Ce que l'import fait de chaque fichier :

| Audio dans le fichier | Ce qui se passe |
|---|---|
| MP3, MP2, MP1, AAC en M4A / MP4, OGG Vorbis, Opus | Importé tel quel — jamais réencodé. |
| AAC brut (`.aac`) | Toujours réempaqueté en `.m4a`, **sans** réencodage, que la case soit cochée ou non. Un fichier AAC brut n'a pas d'index : sa durée ne peut qu'être estimée (environ 2 s de trop sur les fichiers vérifiés), et il ne peut pas porter de tags. |
| Windows Media Audio (`.wma`, avec ou sans perte) *(depuis le 2026-10-21)* | Toujours converti en MP3 à 320 kbit/s, que la case soit cochée ou non ; les navigateurs ne lisent pas le WMA et ce serait le seul format non normalisé de la bibliothèque.  L'original n'est pas conservé. |
| Sans perte : WAV, FLAC, AU, Apple Lossless (ALAC) en M4A | Case **cochée** : converti en MP3 à 320 kbit/s avant d'entrer dans la bibliothèque ; l'original sans perte n'est **pas conservé**.  Case **décochée** : importé tel quel. |

- **C'est l'audio qui compte, pas l'extension.**  Un `.m4a` contenant
  de l'Apple Lossless est converti ; un `.wav` contenant des données
  MP3 ne l'est pas.
- **Tags et pochette suivent.**  Titre, artiste, album, genre, année,
  numéro de piste, compositeur, copyright, label, ISRC, BPM, langue,
  commentaire et la date **Expiry** sont écrits dans le MP3, et une
  pochette JPEG ou PNG intégrée est conservée.  Le fichier garde son
  nom avec la nouvelle extension (`Interview.wav` devient
  `Interview.mp3`) ; un fichier sans tag de titre affiche ce nouveau
  nom comme titre, comme tout téléversement sans tags.
- **Fréquence d'échantillonnage et canaux.**  32, 44,1 et 48 kHz
  restent tels quels ; les autres fréquences (par exemple 96 kHz)
  deviennent 44,1 kHz.  Plus de deux canaux sont mixés en stéréo.
- **Mesuré après la conversion.**  Durée, points de cue, ReplayGain et
  loudness proviennent du fichier qui arrive dans la bibliothèque.
- **Une conversion échouée ne coûte jamais l'import** : le fichier
  d'origine est alors importé sans modification.
- La conversion tourne en priorité basse, pour qu'un gros lot ne prenne
  pas de puissance de calcul à la diffusion ; une piste convertie
  apparaît simplement un peu plus tard dans la bibliothèque.
- **Les épisodes de podcast ne sont pas convertis** — ils sont
  téléchargés directement dans la bibliothèque sans passer par
  l'analyse d'import.

> **Pourquoi cela fonctionne ainsi.**  Les streams sont de toute façon
> avec perte, et un FLAC ou un WAV occupe environ trois à quatre fois
> et demie la place d'un MP3 à 320 kbit/s.  Le reste de la
> bibliothèque est en MP3, et le MP3 porte la date **Expiry** de façon
> fiable ; dans un M4A, de nombreux outils la perdent.  L'audio avec
> perte (MP3, AAC, Ogg Vorbis, Opus) n'est pas touché, car réencoder un
> format avec perte dans un autre ne fait que coûter de la qualité.
> Voir ARCHITECTURE §23.57.

> **Pistes importées avant le 2026-10-14.**  Les fichiers sans perte
> déjà présents dans la bibliothèque sont convertis une fois par un
> technicien avec la commande `convert_lossless` (d'abord un essai à
> blanc ; une piste à l'antenne ou programmée dans les six prochaines
> heures est ignorée, et rien n'est converti pendant le déplacement de
> la médiathèque).  La piste garde son id, sa place dans les
> playlists et les émissions et son Cue In ; le loudness est mesuré
> à nouveau sur le MP3.

> **Sous le capot.**  Le réglage est la clé `cc_pref`
> `convert_lossless_to_mp3` (absente = activée).  L'application web
> l'envoie avec chaque message d'import à l'analyzer
> (`options.convert_lossless`) ; son étape `convert_format` s'exécute
> juste après la lecture des tags.  Une piste convertie garde le md5
> de son original dans `cc_files.source_md5`, pour que l'import en
> masse reconnaisse toujours le même WAV ou FLAC comme déjà importé.
> Seul l'import en masse vérifie le md5 ; la page d'envoi et le dossier
> d'import ne l'ont jamais fait.  Depuis le 2026-10-16,
> `bulk_import --allow-duplicates` importe quand même un tel fichier
> (même audio, tags différents) au lieu de l'ignorer.

---

## 6. Dossier d'import local

Le Dossier d'import local est un répertoire sur la machine
de l'opérateur que l'analyzer surveille pour de nouveaux
fichiers. Tout ce qui est déposé dans le dossier est
automatiquement importé dans la bibliothèque au prochain
cycle de poll de l'analyzer (par défaut toutes les 60 s).

**Import en masse : autoriser l'import de doublons** (case sous le chemin du dossier, depuis le
2026-10-16, enregistrée avec le **Save** de la page depuis le 2026-10-27).  C'est la valeur par défaut de
l'import en masse en ligne de commande (`bulk_import`) : désactivée, un
fichier dont le md5 - ou le md5 de son original sans perte - est déjà
dans la bibliothèque est ignoré ; activée, il est importé comme second
titre, par exemple le même audio avec d'autres tags.  La page d'envoi
et ce dossier d'import ne vérifient jamais les doublons ; la case ne
change rien pour eux.  L'option `--allow-duplicates` l'active pour une
seule exécution.

### Configurer le dossier

| Champ | Notes |
|---|---|
| **Chemin du dossier** | Un chemin absolu sur la machine de l'opérateur. Doit exister et être lisible par le service RASTATIME-ANALYZER. Par défaut : `C:\rastatime\import\`. Laisser vide pour désactiver. |
| **Dernier scan** | Quand l'analyzer a tourné un scan en dernier + résumé du résultat. |

Le bouton **Scanner maintenant** déclenche un scan
immédiat sans attendre le poll de 60 s.

### Comment les fichiers sont traités

Le scanner s'exécute toutes les 5 minutes (et immédiatement avec
**Scan Now**).  Pour chaque fichier posé directement dans le dossier :

1. **Les fichiers non audio sont ignorés** et laissés en place — le
   scanner ne prend que les fichiers audio (`mp3`, `wav`, `m4a`,
   `mp4`, `flac`, `ogg`, `oga`, `aac`, `opus`, `mp2`, `mp1`, `au` ;
   depuis le 2026-10-14 exactement la liste qu'accepte le
   téléversement navigateur).  La ligne d'état les compte comme
   « non-audio files left alone ».
2. **Les fichiers pas encore au repos attendent (depuis le
   17/09/2026).**  Un fichier modifié dans les 60 dernières secondes
   est peut-être encore en cours d'écriture (copie lente, envoi FTP) ;
   la ligne d'état le signale comme « still being copied » et un
   passage
   ultérieur le reprend.
3. Chaque fichier audio au repos est confié au **circuit d'envoi
   standard** : une entrée de bibliothèque est créée, le fichier est
   **déplacé** (pas copié) vers la zone `organize` de la
   bibliothèque, et l'analyseur prend le relais — lecture des
   métadonnées, conversion selon le **Format d'import** (section 5),
   contrôle de lisibilité, place définitive dans la bibliothèque.  Il
   se comporte ensuite exactement comme un fichier téléversé par
   l'interface web.
4. **Si la remise échoue, le fichier est déplacé dans le
   sous-dossier `_failed`** du dossier d'import (depuis le 2026-10-14 ;
   auparavant il était supprimé).  Il y garde son chemin relatif
   (`Album/Song.wav` devient `_failed/Album/Song.wav` ; si ce nom est
   pris, un numéro est ajouté : `Song (2).wav`).  Le scanner ne regarde
   jamais dans `_failed` : un fichier cassé n'est donc pas retenté à
   chaque passage — et un fichier refusé n'est jamais supprimé.  Si
   même le déplacement échoue, le fichier reste où il est et le
   passage suivant réessaie.

Le dossier se vide donc de ses fichiers audio après chaque passage —
déplacés dans la bibliothèque en cas de succès, dans `_failed` en cas
d'échec.  Les fichiers non audio restent.  La ligne d'état indique
combien de fichiers sont partis dans `_failed`
(« 2 failed (moved to _failed) »).

### Sous-dossiers et gros lots (depuis le 2026-10-08)

Les sous-dossiers sont **parcourus** : chaque fichier audio du dossier
d'import et de tout sous-dossier est importé, dossier par dossier dans
l'ordre des chemins ; un sous-dossier vidé par les déplacements est
supprimé.  Le sous-dossier `_failed` fait exception : il n'est jamais
parcouru ni supprimé.  La structure des dossiers n'est pas reprise
dans la bibliothèque (elle classe les fichiers d'après leurs
métadonnées) : taguez les fichiers avant de les copier.

Un scan ne transmet rien non plus tant que **300 fichiers ou plus**
attendent encore l'analyseur (il traite environ un fichier par
seconde) ; la ligne d'état affiche cette file.  La bibliothèque reste
ainsi sans lignes qui attendent si longtemps que le nettoyage horaire
les marque comme échouées.

Un scan transmet au plus **300 fichiers** et s'arrête après **20
secondes** ; le reste attend le prochain passage (toutes les 5 minutes
ou **Scan Now**), et la ligne d'état indique combien attendent.  Cela
garde un scan dans la limite de temps de PHP - un scan mort en plein
déplacement laissait autrefois un demi-fichier.  L'analyseur traite
ensuite la file fichier par fichier ; sur cette machine un MP3 de
quatre minutes prend environ 1.1 s (essai de 50 fichiers,
2026-10-08) : comptez environ 3 000 titres par heure de bout en bout et
environ sept heures pour 20 000 titres.  Placez le dossier d'import sur le
même disque que la médiathèque (le déplacement est alors instantané et
atomique), réglez d'abord *Track Type Upload Default* (le
propriétaire n'a pas de réglage : les imports d'arrière-plan
appartiennent au premier administrateur, ceux de Scan Now à vous), et
copiez par lots de quelques milliers.

### Propriété

Avec **Scan Now**, les fichiers importés appartiennent à l'opérateur
qui a cliqué sur le bouton.  Les fichiers pris par le scan d'arrière-
plan appartiennent au premier compte administrateur.

> **Sous le capot.**  Le scanner est la `LocalImportScanTask` du
> gestionnaire de tâches du frontend PHP legacy : elle s'exécute à
> l'occasion des requêtes web normales, au plus toutes les 300 s, et
> met à jour les clés `cc_pref` `local_import_last_run` et
> `local_import_last_status` (la ligne d'état de cette page).  Voir
> ARCHITECTURE §23.12 et, pour le dossier `_failed` et la liste
> d'extensions commune, §23.57.

### Import depuis un serveur FTP

Sous le dossier d'import se trouve une seconde source d'import
(depuis le 17/09/2026) : RASTATIME va chercher toutes les 5 minutes
(ou immédiatement avec **Fetch now**) les fichiers audio d'un serveur
FTP, FTPS ou SFTP et les fait passer par le dossier d'import
ci-dessus — qui doit donc être configuré.  Activez la case, saisissez
serveur, port (vide = défaut du protocole), compte et le dossier
distant **absolu**, puis **Save**.

- **Sémantique de boîte aux lettres.**  Après un téléchargement
  vérifié, le fichier distant est supprimé — le compte a besoin du
  droit de suppression.  Si la suppression échoue, le fichier est
  tout de même importé et l'état avertit, car le cycle suivant irait
  chercher un doublon.
- **Les envois en cours sont sans risque.**  Un fichier n'est
  récupéré que lorsque sa taille est restée inchangée au moins une
  minute entre deux contrôles, et la taille est revérifiée après le
  téléchargement.  D'ici là, l'état le compte comme « settling ».
- **Les fichiers non audio restent sur le serveur.**  Seules les
  extensions audio du dossier d'import sont récupérées.  Une entrée
  distante nommée `_failed` n'est pas touchée.
- **Préférez FTPS ou SFTP** — le FTP en clair transmet le mot de
  passe non chiffré.  Le mot de passe est stocké dans la base des
  réglages comme les autres mots de passe de services, pour que la
  récupération se connecte sans surveillance ; la page ne l'affiche
  plus jamais.
- Chaque cycle lance de nouveaux téléchargements pendant une minute
  au plus ; le reste est repris au cycle suivant (« left for the
  next run » dans l'état).

---

## 7. Emplacement de la médiathèque

Depuis le 16/09/2026, le dossier qui contient la médiathèque (titres
importés, pochettes, images d'émission) est un réglage de cette page et
non plus une ligne de `rastatime.conf`. Le fichier de configuration ne
fournit que la valeur initiale ; dès que vous avez déplacé la
médiathèque une fois, le réglage l'emporte.

La section affiche l'**emplacement actuel**, l'origine de cette valeur
(le réglage ou le fichier de configuration), le nombre de fichiers et
la taille de la médiathèque. Pour la déplacer :

1. Saisissez le **nouvel emplacement** - un chemin absolu sur un disque
   local de cette machine, par exemple `D:\stor`. Le dossier est créé
   si nécessaire. Les chemins réseau ne sont pas pris en charge.
2. Cliquez sur **Vérifier**. RASTATIME confirme qu'il peut y écrire et
   que le disque a assez d'espace libre (la médiathèque plus dix pour
   cent).
3. Cliquez sur **Déplacer la médiathèque** et confirmez. Une barre de
   progression suit la copie.

Ce qui se passe pendant le déplacement :

- Le flux, la grille, les enregistrements et le moniteur local
  continuent ; rien n'est diffusé directement depuis le dossier de la
  médiathèque, la diffusion lit depuis son cache.
- Les imports sont en pause : les envois, l'analyse du dossier d'import
  local, les téléchargements de podcasts et les envois d'images refusent
  avec un court message jusqu'à la fin du déplacement.
- RASTATIME copie la médiathèque avec robocopy, vérifie ensuite que
  chaque fichier est arrivé avec la bonne taille et que chaque titre de
  la base de données se trouve au nouvel endroit. Alors seulement il
  bascule le réglage. L'application web et l'API suivent aussitôt, la
  diffusion à son prochain rafraîchissement de la grille (sous deux
  minutes).
- La **copie précédente reste sur le disque**. Supprimez-la vous-même
  une fois satisfait - et seulement son contenu, pas le dossier nommé
  dans `rastatime.conf`, car l'application web vérifie au démarrage que
  ce dossier existe.

Si le service RASTATIME-API redémarre pendant une copie, la section
affiche le déplacement comme *interrompu*. Saisissez la même cible et
déplacez de nouveau : la copie reprend là où elle s'était arrêtée, les
fichiers déjà copiés sont ignorés. **Annuler le déplacement** arrête une
copie en cours ; ce qui a déjà été copié reste à la cible et un
déplacement ultérieur en repart.

Si l'emplacement configuré venait à manquer ou à être en lecture seule
- un disque non monté, un dossier renommé - la bannière du tableau de
bord affiche *Media library location … is missing* jusqu'à son retour.

---

## 8. Dossiers d'enregistrement (lié)

Paramètres → Machine locale a **deux** dossiers de sortie
d'enregistrement :

### Show Recording

Où [Enregistrement par émission](./RECORD_PER_SHOW.md) écrit un
fichier par émission marquée « enregistrer ». *(Renommé depuis
« Recording Folder » lors de l'ajout de l'enregistrement 24/7 —
2026-06-06.)*

Par défaut : `C:\rastatime\recordings\`.

**Format** et **Bitrate (kbps)** *(depuis le 2026-10-18)* : MP3
(par défaut) / AAC / OGG Vorbis / Opus, 96–320 kbps (320 par
défaut).  Le playout applique un changement à son prochain moment
calme (ou à la prochaine limite de titre) ; les fichiers déjà écrits
gardent leur format, les nouveaux reçoivent l'extension
correspondante.

**Copier les enregistrements d'émission dans la bibliothèque** *(depuis
le 2026-10-19)* : si la case est cochée, une copie taguée de chaque
enregistrement d'émission terminé est importée dans la bibliothèque
(type de piste « Recordings », titre `<émission> <date heure>`, liée à
l'instance de l'émission) ; le fichier du dossier d'enregistrement
reste intact.  Détails dans
[Record-per-Show, section 3.6](./RECORD_PER_SHOW.md).  Enregistré
avec le **Save** de la page ; le playout a besoin d'un
redémarrage après la mise à jour, ensuite l'interrupteur agit
immédiatement.

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

## 9. Foire aux questions

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
2. Le frontend web tourne (`RASTATIME-APACHE`) — le scanner
   s'exécute à l'occasion des requêtes web, **Dernier scan**
   n'avance donc que si l'interface voit du trafic.  **Scan Now**
   force un passage.
3. Un fichier modifié dans les 60 dernières secondes compte comme
   « still being copied » — attendez une minute et relancez.
4. « N failed (moved to _failed) » dans la ligne d'état signifie
   que la remise a échoué et que le fichier se trouve maintenant dans
   le sous-dossier `_failed` (voir la question suivante).  Testez le
   fichier dans un autre lecteur et cherchez la raison dans
   `logs\legacy.log` ; le service `RASTATIME-ANALYZER` doit
   tourner pour finir l'import.

### "Que faire des fichiers dans `_failed` ?"

Chaque fichier qui s'y trouve n'a pas pu être remis à la
bibliothèque.  Cherchez son nom dans `logs\legacy.log` pour connaître
la raison, testez-le dans un autre lecteur, réparez-le ou
réexportez-le si nécessaire, puis remettez-le dans le dossier
d'import — n'importe où en dehors de `_failed` ; le passage suivant
l'importe.  Supprimez ce dont vous n'avez plus besoin : RASTATIME ne
vide jamais `_failed` lui-même.

### "J'ai importé un fichier WAV ou FLAC et la bibliothèque affiche un MP3."

C'est le réglage **Format d'import** (section 5) : les fichiers sans
perte sont convertis en MP3 320 kbit/s à l'import, et l'original sans
perte n'est pas conservé.  Pour importer des fichiers sans perte tels
quels, décochez la case et cliquez sur **Sauvegarder** *avant* de les
importer.

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
