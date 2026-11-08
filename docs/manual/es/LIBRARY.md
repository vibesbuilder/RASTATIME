# Biblioteca

> **Dónde está usted en el manual.** Este es uno de los
> capítulos **Contenido y biblioteca**. Para detalles por
> tipo de entrada, vea también [Webstreams](./WEBSTREAMS.md)
> y [Line-In](./LINE_IN.md).

La **Biblioteca** es el inventario de cada pieza de audio
que RASTATIME puede poner al aire. Tiene cinco tipos de
items:

| Tipo | Qué es | Dónde viven las filas |
|---|---|---|
| **Pista (Track)** | Un archivo de audio único (MP3, M4A, OGG, Opus, ...; WAV y FLAC se convierten a MP3 al importar por defecto). | `cc_files` |
| **Smart Block** | Una *consulta* — "elegir N pistas donde género = pop y BPM > 100", evaluada en momento de build. | `cc_block` + `cc_blockcontents` |
| **Playlist** | Una lista ordenada de items: pistas, smart blocks, webstreams o line-ins. | `cc_playlist` + `cc_playlistcontents` |
| **Webstream** | Una URL apuntando a otra fuente Icecast / Shoutcast / HTTP audio. | `cc_webstream` |
| **Line-In** | Una entrada de audio en vivo nombrada en la máquina del operador. | `rastatime_linein` |

La Biblioteca es de donde usted arrastra cuando rellena un
programa.

---

## 1. La página Biblioteca

Biblioteca → abre la vista de tabla con una fila por item.

### Chips de filtro

Los chips encima de la tabla restringen las filas visibles.
Se combinan con **Y**: establecer *tipo = Pista* y *género
= pop* muestra solo pistas pop. Borre cualquier chip con
su **×**.

| Chip | Por qué filtra |
|---|---|
| **Tipo** | Pista / Smart Block / Playlist / Webstream / Line-In. |
| **Creador** | El creador (artista) de metadatos de la pista, no el propietario de subida. |
| **Género** | Tag de género de metadatos. |
| **Longitud** | Cubos gruesos (< 30 s, 30 s – 2 min, 2 – 10 min, > 10 min, ∞). |
| **Propietario** | El usuario RASTATIME que importó el item. Los DJs están restringidos a sus propios items; los Admins ven todo. |

### Búsqueda de texto libre

La caja **Buscar** funciona sobre **título, creador,
álbum, género, nombre de archivo** para pistas; **nombre**
para blocks / playlists / webstreams / line-ins. Usa
correspondencia de subcadena.

**Indicador de filtro activo (desde 2026-10-09).** Mientras haya
texto de búsqueda o un campo de la búsqueda avanzada rellenado, la
caja de búsqueda recibe un borde en el color de acento y muestra, a
la derecha, cuántos elementos del tipo elegido coinciden («13 de
11.108 pistas», «0 de 32 bloques inteligentes»; desde 2026-10-18 el
recuento nombra el tipo: pistas, listas, bloques inteligentes,
retransmisiones, podcasts, entradas de línea). La **×** junto a ese
número borra el texto y todos los campos de la búsqueda avanzada de
una vez.

**Podcasts (desde 2026-10-21).** La lista de podcasts tiene la misma
caja de búsqueda: busca en el **título** y el **creador** del podcast,
sin distinguir mayúsculas, y muestra «X of N podcasts» y la **×** de la
misma manera.  La flecha de la búsqueda avanzada está oculta allí:
pertenece a los otros tipos.

> **Cómo funciona bajo el capó.** La búsqueda es del lado
> del servidor vía `LibraryController::contentsFeedAction`.
> El widget DataTable envía el término de búsqueda + el
> estado actual de chips como parámetros URL; el
> controlador ensambla una consulta PostgreSQL `ILIKE`.

### Disposición de la tabla

Arrastre una columna por su encabezado para moverla; el
botón **Columnas** (icono de lista) sobre la tabla muestra u
oculta columnas, y el selector **Mostrar** debajo fija las
filas por página. RASTATIME recuerda esta disposición — orden
de columnas, columnas visibles, filas por página y orden —
**por usuario en el servidor**, así que le sigue a cualquier
navegador y equipo. Desde el 2026-10-24 las **columnas visibles
se recuerdan por tipo de medio**: Pistas, Listas, Bloques
inteligentes, Webstreams y Entradas de línea tienen cada uno su
propio conjunto, y el botón **Columnas** edita siempre el
conjunto de la pestaña abierta. Una pestaña nunca ajustada
empieza con un valor por defecto razonable (pistas: carátula,
título, creador, tipo, género, duración, subido; listas y
bloques inteligentes: título, descripción, duración, creador,
última modificación; webstreams: título, descripción, sitio
web, duración, creador, última modificación; entradas de línea:
título, descripción, duración, última modificación). La tabla de pistas del panel y la del
diálogo **Programar pistas** del calendario tienen cada una
su propia disposición (el diálogo no tiene columna
*Actions*); la tabla *Scheduled Shows* de al lado comparte
una sola disposición entre ambos lugares. Las búsquedas y la
página actual no se recuerdan — la tabla siempre abre en la
página 1. Al desplazarse por las filas, la línea de búsqueda,
los encabezados de columna y el paginador permanecen visibles.

---

## 2. Pistas

### Importar pistas

Tres maneras:

#### 2.1 Subida del navegador (puntual)

Biblioteca → **Subir** → arrastre archivos al área de
subida.

| Campo | Notas |
|---|---|
| **Archivo** | Uno de: MP3, M4A, MP4, AAC, OGG, OGA, Opus, FLAC, WAV, MP2, MP1, AU - desde el 2026-10-14 la misma lista que aceptan la carpeta de importación local y la importación FTP. Los archivos sin pérdida se convierten a MP3 al importar por defecto (vea *Formatos de archivo al importar* más abajo). |
| **Propietario** | Por defecto usted. Los Admins pueden anular. |

> **Dónde queda el archivo (desde el 2026-10-24).**  El analyzer
> archiva cada pista bajo `imported/<artista>/<álbum>/` dentro de la
> biblioteca (artista y álbum tal como están etiquetados; sin tag de
> álbum solo `imported/<artista>/`).  Un archivo **sin tag de
> artista** va a `imported/tagless/` - antes del 2026-10-24 esos
> archivos quedaban directamente en `imported/`.  La carpeta es solo
> el lugar de almacenamiento; la biblioteca muestra la pista según
> sus tags en todo caso.  Etiquete el archivo antes si quiere verlo
> archivado bajo su artista.
>
> **Portadas.**  Una portada incrustada se guarda en cinco tamaños
> JPG (32 a 512 px) bajo `imported/artwork/`; desde el 2026-10-24 no
> se escribe nada más para ella.  Las miniaturas pequeñas de la
> biblioteca y del editor se generan a partir de esos JPG cuando la
> página las pide.

#### 2.2 Carpeta de importación local (lote)

Configure una vez Configuración → **Máquina local** →
**Carpeta de importación local**. Luego suelte archivos en
ese directorio; aparecen en la biblioteca en el próximo
poll del analyzer (por defecto cada 60 s). Subcarpetas son
escaneadas recursivamente. Vea
[Máquina local](./LOCAL_MACHINE.md).

> **Consejo del operador.** Use la Carpeta de importación
> local para cualquier lote de más de una docena de
> archivos.

> **Tiempo restante y crossfades (desde 2026-10-06).** Las filas de
> música se solapan por su crossfade (valor de la casa 3 s, o el del
> tipo de pista; jingles 0), así que el tiempo restante de un programa
> es el tiempo *dispuesto*: del final de la última fila al final del
> programa — la cifra del pie del Show Builder. Un smart block «Tiempo
> restante en el programa» se elige contra ese tiempo, entre sus vecinos
> reales, de modo que la última fila termina a un segundo o así del
> final del programa (el solucionador del bloque es aleatorio; el pool
> decide lo que es posible). Un bloque limitado por *Duración en tiempo*
> se elige igual (decisión del operador 2026-10-06): 12 minutos son 12
> minutos **en antena**, no la suma de las pistas, así que una ID de la
> emisora tras tres bloques así cae en 12:00, 24:xx y 36:xx de la hora.
> Un jingle entre dos pistas musicales cuesta su propia duración más los
> 3 s de solapamiento que interrumpe.

#### 2.3 Suscripción podcast (recurrente)

Configuración → **Podcasts** → **Suscribirse**. Pegue una
URL de feed RSS, opcionalmente un tipo de pista por
defecto, una política de auto-expiración.

> **Cómo funciona bajo el capó.** La obtención de podcasts
> dependía antes de Celery; en RASTATIME (Windows) corre
> de forma síncrona en la API (disparada desde la interfaz web
> o la comprobación del feed), que escribe directamente el
> archivo y su entrada de biblioteca.
>
> **Los archivos de episodios (desde el 17/09/2026)** llegan a
> una carpeta por podcast dentro de la biblioteca:
> `imported/<nombre del podcast>/`.  Renombrar un podcast abre
> una carpeta nueva para episodios futuros; los archivos
> existentes se quedan donde están.

### Formatos de archivo al importar (desde el 2026-10-14)

Llegue una pista por la vía que llegue - subida, carpeta de
importación local, importación FTP o importación masiva -, el
analyzer examina el audio que contiene el archivo (no su extensión)
antes de archivarlo:

- **MP3, MP2, MP1, AAC en M4A / MP4, OGG Vorbis y Opus** se importan
  tal cual y nunca se recodifican.
- **El AAC en bruto (`.aac`)** siempre se reempaqueta en un `.m4a`
  sin recodificar: un archivo AAC en bruto no tiene índice, su
  duración solo puede estimarse, y no puede llevar etiquetas.
- **El audio sin pérdida** - WAV, FLAC, AU, Apple Lossless en M4A -
  se convierte a **MP3 de 320 kbps** mientras Configuración →
  **Máquina local** → **Formato de importación** esté activado (por
  defecto).  El original sin pérdida no se conserva; las etiquetas,
  las fechas Expiry y Enable, el país y una carátula incrustada se
  mantienen.  Si una
  conversión falla, el original se importa sin cambios.  Detalles:
  [Máquina local](./LOCAL_MACHINE.md), sección 5.
- **Las etiquetas se leen en todos los formatos.**  Además del ID3 de
  los archivos MP3, el analyzer lee las etiquetas de los archivos WAV
  (bloque ID3 y RIFF INFO), los comentarios de los archivos FLAC, OGG
  y Opus y los campos de los archivos M4A, incluidos descripción /
  comentario, las fechas y el país (sección siguiente).  Antes del
  2026-10-14 las etiquetas de los archivos WAV no se leían, y un
  `.aac` en bruto con etiqueta ID3 fallaba al importar.

Los episodios de podcast no forman parte de esto: se descargan
directamente en la biblioteca (sección 2.3) y conservan su formato.
Desde el 2026-10-24 cada episodio descargado se **mide en sonoridad**
(EBU R128) justo después de la descarga, para que la emisión aplique
su ganancia real por pista en lugar de una aproximación. Los episodios
anteriores a esa fecha se recuperan con **Settings → Streams → Measure
loudness**, que solo mide archivos sin valores.

### Fechas y país desde las etiquetas (desde 2026-11-08)

Tres campos del editor de pista se rellenan al importar desde las
etiquetas del archivo: tramas ID3 `TXXX` en los archivos MP3, y los
mismos nombres como comentarios de los archivos FLAC, OGG y Opus,
campos libres de los archivos M4A o en el bloque ID3 de un archivo WAV:

| Nombre de la etiqueta | Campo | Formato |
|---|---|---|
| `Expiry` o `Expiry Date` | **Fecha de caducidad** | `2026-11-08` o `20261108` |
| `Enable Date` o `Enabled From` | **Activo desde** | `2026-11-08` o `20261108` |
| `Country` | **País** | texto libre como en la etiqueta, p. ej. `Austria` |

Mayúsculas y minúsculas, espacios, guiones bajos y guiones en el nombre
de la etiqueta no importan (`EXPIRY_DATE` es `Expiry Date`).  Una fecha
en otro formato se ignora; el registro del analyzer nombra el archivo.
Una fecha de caducidad alcanzada o una fecha de activación aún por
llegar desactiva la pista de inmediato.  El país solo se rellena si la
pista aún no tiene ninguno.

**Releer etiquetas** también toma el país del archivo (un archivo sin
la etiqueta lo borra), pero nunca las dos fechas: una fecha fijada en
RASTATIME se mantiene.  Las pistas importadas antes del 2026-11-08
reciben su país una sola vez desde sus etiquetas con
`manage.py backfill_country --yes` en el equipo del estudio; el comando
solo rellena países vacíos y, sin `--yes`, solo cuenta.

### Editar metadatos de pista

Haga clic en una fila de pista → **Editar metadatos** en
el menú de acción de la fila.  Si se rechaza el guardado (por ejemplo, una fecha con formato incorrecto), el editor permanece abierto e indica el motivo encima de los campos (desde 2026-11-08).

| Campo | Dónde termina |
|---|---|
| **Título** | `cc_files.track_title` |
| **Creador (Artista)** | `cc_files.artist_name` |
| **Álbum** | `cc_files.album_title` |
| **Género** | `cc_files.genre` |
| **Año** | `cc_files.year` |
| **País** (desde 2026-11-08) | `cc_files.country` - texto libre, desde la etiqueta `Country` al importar; el campo sugiere los países ya usados. La base de Analytics → [Music by Country](./ANALYTICS.md); los smart blocks pueden filtrar por él (criterio *País*). Columna de la biblioteca *País* (oculta por defecto, se puede buscar). |
| **BPM** | `cc_files.bpm` |
| **Tipo de pista** | `cc_files.track_type` — usado por filtros smart-block |
| **Cue In / Out** | `cc_files.cuein` / `cueout` — recortar el inicio / fin sin re-encodificar. Desde el 30/09/2026 los valores se mantienen dentro del archivo: un cue out más allá de la duración se limita a la duración, un cue in negativo pasa a cero. Un cambio se copia en las filas de los programas futuros que programan la pista (las filas ya iniciadas no se tocan) y esos programas se recalculan - no hace falta volver a llenarlos. |
| **Fade In / Out** | `cc_files.fadein` / `fadeout` |
| **Replay Gain** | `cc_files.replay_gain` — usado por el motor de playout para normalización de nivel |
| **Play Count** | Columna de la biblioteca (oculta por defecto, selector de columnas), solo lectura: cuántas veces se emitió la pista - un conteo por fila del historial de emisión, la misma cifra que Historial → File Summary. Ordenable; la búsqueda avanzada admite un rango. Desde 2026-10-07. |
| **ID** | Columna de la biblioteca (visible por defecto, selector de columnas), solo lectura: el identificador del archivo en la base de datos, el mismo número que usan la API REST y los registros de emisión. Solo los archivos lo llevan - listas, bloques inteligentes y webstreams tienen sus propios rangos y muestran una celda vacía. Ordenable; la búsqueda avanzada admite un rango. Desde 2026-10-16. |
| **Teaser** / **Teaser para los programas**, **Tipo de teaser** | El programa o programas que anuncia un jingle y cómo (teaser de programa, teaser del día «hoy», teaser del día «mañana»); dos campos del editor de pista y de la edición masiva, mostrados como `Nombre del programa · today` en la columna *Teaser* (oculta por defecto, buscable). Los bloques inteligentes eligen los jingles adecuados con el criterio *Teaser: encaja con la parrilla*; véase [Automatización de teasers](./TEASERS.md). Desde 2026-10-16. |
| **Crossover** | Cómo se encuentra esta pista con sus vecinas (desde el 2026-09-29 un campo de tres opciones; las dos excepciones se excluyen entre sí). **As the track type** (como el tipo de pista, por defecto): la pista se solapa y funde según indique su tipo de pista - Settings → Track Types → *Crossfade Duration* - o, sin valor allí, según la Default Track Crossfade Duration; desde 2026-09-30 hereda también el preajuste *No Fade during Crossover* del tipo. **No Fade during Crossover** (sin fundido durante el crossover, `cc_files.no_fade_crossfade`): el solapamiento se mantiene, pero esta pista conserva su nivel completo mientras la otra se funde; en un límite de programa sobrepasado, una pista saliente marcada se corta en vez de fundirse. **Exclude from Crossover** (excluir del crossover, `cc_files.exclude_crossfade`): esta pista nunca se solapa con una vecina - empieza al final de la pista anterior y la siguiente empieza a su final. Cambiar a *Exclude* o volver de él recalcula las filas de los programas futuros que programan la pista. |
| **Metadatos del stream** (desde 2026-10-14) | Si el artista y el título de esta pista llegan a los reproductores de los oyentes (ICY) y al Live Text. **Como el tipo de pista** (por defecto): el ajuste previo de Settings → Track Types → *Forward Metadata to the Stream*. **Enviar al stream** / **No enviar**: la elección propia de la pista. Mientras suena una pista sin envío, el stream muestra «Nombre de la emisora - Nombre del programa» en todos los formatos de Stream Label, como una fuente en directo sin metadatos. Pensado para jingles, identificaciones y promos; el historial de emisión no cambia. |
| **Activo desde** (desde 2026-11-08) | `cc_files.enabled_from`, formato AAAA-MM-DD, vacío = sin fecha de activación. La pista permanece desactivada hasta las 00:00 de ese día; después la pasada horaria la activa, salvo que se haya desactivado a mano. Debe ser anterior a la fecha de caducidad. Desde la etiqueta `Enable Date` al importar. Columna de la biblioteca *Activo desde* (oculta por defecto). |
| **Fecha de caducidad** | `cc_files.expires_at`, formato AAAA-MM-DD, vacío = sin caducidad. La fecha cuenta desde las 00:00 de ese día: al alcanzarla, la pasada horaria de caducidad marca **Pista desactivada**. Una fecha posterior o vaciada vuelve a activar la pista, salvo que se haya desactivado a mano. Desde la etiqueta `Expiry` / `Expiry Date` al importar. |
| **Pista desactivada** (desde 2026-11-08) | `cc_files.disabled`. Márquela a mano, o se marca automáticamente mientras la fecha de activación está por llegar y en cuanto se alcanza la fecha de caducidad. Los bloques inteligentes ya no eligen una pista desactivada; los programas que ya la tienen la siguen emitiendo, y aún puede programarla a mano. En el editor los campos se siguen antes de guardar: una fecha de caducidad hasta hoy incluido o una fecha de activación posterior a hoy marca la casilla; cambiar o borrar las fechas la desmarca de nuevo, salvo que usted la haya marcado a mano; desmarcar la casilla vacía una fecha de caducidad alcanzada y una fecha de activación aún por llegar. Guardar sin la marca se rechaza con un mensaje mientras una fecha siga desactivando la pista. Una marca a mano se guarda aparte (`cc_files.disabled_by_hand`), así que una pista que usted desactivó sigue desactivada cuando cambian sus fechas. Columna de la biblioteca *Desactivado* (oculta por defecto, selector de columnas). |

### Eliminar una pista

Fila → **Eliminar**. La pista se retira de la biblioteca
*y* de cualquier playlist de la que era parte.

Mientras el servidor elimina, la tabla muestra su capa de carga y el
botón **Eliminar** dice «Eliminando N elemento(s)…»; ambos
desaparecen cuando la petición termina.  Eliminar muchas pistas a la
vez es rápido (desde 2026-11-06 la comprobación de si una repetición
aún necesita la pista tarda milisegundos en lugar de unos dos
segundos por archivo).  Si la petición falla o se agota el tiempo, un
mensaje le pide recargar la página para ver qué elementos se
eliminaron.

> **Cómo funciona bajo el capó.** Eliminar quita la fila
> `cc_files` y todas las filas `cc_playlistcontents` /
> `cc_schedule` que la referencian (CASCADE). El archivo
> en disco se mueve a `C:\rastatime\media\.trash\` en
> lugar de ser desenlazado, así un operador que eliminó
> por accidente puede restaurar durante 7 días.

---

## 3. Smart Blocks

Un **smart block** es una consulta. Cuando el block se
planifica en un programa, la consulta se evalúa en
momento de build y se expande en un conjunto concreto de
pistas.

### Crear un smart block

Biblioteca → **+ Nuevo** → **Smart Block**.

| Campo | Significado |
|---|---|
| **Nombre** | Visible en biblioteca y calendario. |
| **Tipo** | **Estático** — elige una vez al crear; el conjunto nunca cambia. **Dinámico** — re-elige cada vez que el block se planifica. |
| **Criterios** | Añadir filas: *artista contiene "Bowie"*, *bpm está en el rango de 100 a 130*, etc. Las filas se combinan con Y; el **+** junto a una fila añade una alternativa para el mismo campo (O), p. ej. *género es pop* **+** *género es rock*. Desde 2026-11-08 también *País* (p. ej. *país es Austria*; *es* y *no es* comparan exactamente, *no es* y *no contiene* incluyen las pistas sin país). Detalles en [Import / Export → blocks.json](./IMPORT_EXPORT.md#blocksjson). |
| **Limitar a** | **Número de pistas** (ej. 10), **Duración en tiempo** (ej. 30:00), **Tiempo restante en el programa**. |
| **Ordenar** | Aleatorio / más reciente primero / por artista / por número de reproducciones / etc. |

> **Consejo del operador.** El límite **"Tiempo restante
> en el programa"** es el más útil para autoloading
> playlists.

### Por qué un smart block puede devolver menos pistas de las pedidas

Los smart blocks buscan en **toda la biblioteca** para todos
los roles - el smart block de un DJ también toma pistas de
otros usuarios.  Para limitar un bloque a sus propias
pistas, añada el criterio **Owner**.

**Las pistas desactivadas** nunca se eligen.  Desde 2026-11-08 un
smart block lo juzga a la hora de emisión de la franja, no en el
momento de rellenarla: el autoloading rellena un programa una hora
antes, así que una pista cuyo **Activo desde** es el día de un programa
de las 00:07 se elige para él, y una pista cuya **Fecha de caducidad**
es ese día, no.  Una pista desactivada a mano nunca se elige.

> **Cómo funciona bajo el capó.** Los criterios están
> almacenados en `cc_blockcriteria`. En momento de build,
> `BlockExpander.expand()` ensambla un PostgreSQL `SELECT
> … WHERE … LIMIT …` sobre `cc_files`. Los límites de tiempo restante
> se convierten en un tope de duración vía `getSecondsRemaining()` de la
> instancia (desde 2026-10-06 el tiempo libre dispuesto: `time_filled` =
> inicio hasta el final de la última fila; la elección la hace
> `Scheduler::pickRemainingBlock()`).

### Toggles de restricción de pool (Opciones avanzadas)

El cajón **Opciones avanzadas** abajo en el diálogo Smart
Block alberga tres toggles de restricción de pool que
restringen el conjunto candidato *antes* de que se ejecuten
el orden + límite:

| Toggle | A qué restringe el pool |
|---|---|
| **Allow only tracks not played yet** (Permitir solo pistas no reproducidas todavía) | Pistas donde `cc_files.lptime` es `NULL` (el playout nunca las ha registrado). Útil para bloques de descubrimiento / rotación de contenido nuevo. |
| **Exclude tracks played lately** (Excluir pistas reproducidas recientemente) | Pistas donde `lptime` es `NULL` *o* más antiguo que la ventana de retrospección configurada, en **minutos** desde el 2026-10-23 (1..525600 min, por defecto 1440 = 24 h; una ventana guardada en horas se muestra en minutos). Use esto cuando quiera evitar re-rotación reciente sin prohibir toda reproducción previa. El campo compañero "Exclude tracks played in the last minutes" aparece cuando el toggle está activado.  Desde 2026-10-16 la ventana se mide desde el hueco para el que se expande el bloque y **las filas planificadas también cuentan**: una pista programada dentro de la ventana, antes o después del hueco, incluidas las filas que un bloque anterior del mismo relleno colocó en el mismo programa, queda excluida aunque todavía no haya sonado.  Desde el 2026-10-23 esto vale también **dentro de una playlist**: una playlist se expande bloque a bloque antes de insertar nada, y una pista (en el filtro de artistas: un artista) que un bloque anterior o un elemento fijo de la misma playlist ya reunió queda fuera para los bloques siguientes; dos bloques "Dayteaser" de una playlist ya no eligen el mismo teaser. |
| **Exclude artists played lately** (Excluir artistas reproducidos recientemente) | Pistas cuyo `artist_name` es NULL / vacío *o* cuyo artista no ha sonado vía cualquier otra pista en la ventana de retrospección configurada, en **minutos** desde el 2026-10-23 (1..525600 min, por defecto 1440). Use esto cuando quiera evitar que dos pistas del mismo artista se agrupen — independientemente de qué pista específica se reprodujo. El campo compañero "Exclude artists played in the last minutes" aparece cuando el toggle está activado. |
| **Allow only tracks with expiry date** (Permitir solo pistas con fecha de caducidad) | Pistas donde `cc_files.expires_at IS NOT NULL`. Útil para bloques que solo deben extraer de contenido perecedero (segmentos de noticias datados, trailers). |

Los cuatro se componen de forma Y y se combinan con cada
criterio de la sección Criterios principal.

> **Consejo del operador.** El toggle "Exclude tracks played
> lately" es la respuesta correcta a "reproduce 30 min de
> pop, pero nada de las últimas 4 horas". Combínelo con
> `Ordenar: Aleatorio` para un auto-build de rotación fresca
> que nunca suene repetitivo dentro de la ventana
> configurada. Las pistas nunca reproducidas están
> *incluidas* por el filtro — una pista que nunca ha estado
> al aire obviamente no puede haber estado al aire
> "recientemente".
>
> El toggle compañero **"Exclude artists played lately"** es
> la respuesta a "no hagas seguir una pista de los Beatles
> por otra pista de los Beatles durante al menos 6 horas,
> incluso si tengo 50 pistas de los Beatles en el pool". Los
> dos filtros se componen: active ambos para obtener "ni
> pista reciente NI artista reciente" al mismo tiempo.

> **Cómo funciona bajo el capó.** `Exclude played lately`
> añade una sola cláusula `WHERE cc_files.lptime IS NULL OR
> cc_files.lptime < NOW() - INTERVAL 'N minutes'` a la
> consulta Propel. El valor en horas se persiste en
> `cc_block_criteria` (criteria =
> `exclude_played_lately_minutes`) junto al master flag
> (criteria = `exclude_played_lately`).  `Exclude artists
> played lately` añade una cláusula `WHERE
> cc_files.artist_name IS NULL OR cc_files.artist_name = ''
> OR NOT EXISTS (SELECT 1 FROM cc_playout_history JOIN
> cc_files ON ... WHERE artist_name matches AND starts >
> NOW() - INTERVAL 'N minutes')` — `NOT EXISTS` cortocircuita
> en la primera coincidencia así que el coste permanece
> acotado incluso con una gran tabla de historial.
> Persistido como segundo par de criterios
> (`exclude_artists_played_lately` + `..._minutes`).  Sin
> cambio de esquema para ambos filtros — retrocompatible
> con smart blocks creados antes de la función respectiva
> (filas faltantes = deshabilitado). Vea ARCHITECTURE §23.21.
>
> **Spread dentro del bloque (2026-05-25).** El filtro SQL
> anterior mantiene el pool de candidatos libre de artistas
> / pistas que sonaron en las últimas N h *fuera* del bloque.
> Pero el bloque mismo aún puede contener dos pistas de los
> Beatles consecutivas — el SQL solo mira el historial, no
> lo que el bloque está a punto de reproducir.  Una segunda
> pasada se ejecuta tras la construcción de la lista de
> pistas en `Block::applyWithinBlockSpread()`: para cada
> slot de la lista originalmente seleccionada, la pista
> original se prueba primero; si su artista (o file id según
> el filtro activo) está dentro de la ventana de tiempo
> transcurrido de las pistas ya colocadas, el motor toma un
> reemplazo no-conflictivo del pool SQL-filtrado más amplio
> (hasta 500 pistas) en su lugar.  La duración del bloque
> queda igual; solo cambia la elección de pista.  Si no hay
> más reemplazo no-conflictivo en el pool, la original se
> coloca de todos modos y aparece una entrada
> `Logging::warn` en `legacy.log` para que el operador vea
> cuándo el pool era demasiado pequeño para el spread
> configurado.

---

## 4. Playlists

Una **playlist** es una lista ordenada de items, donde
cada item es una pista, un smart block, un webstream o un
line-in. Las playlists son los bloques de construcción
del contenido del programa.

### «Allow last track to exceed time limit» (Opciones avanzadas)

Con un límite de tiempo (minutos, horas, tiempo restante) el bloque
añade pistas hasta alcanzar el límite, y con esta casilla la última
puede sobrepasarlo.  Para el **llenado por autoloading** (desde el
26/10/2026) la casilla significa además: la última pista del bloque
puede sobrepasar el **final del programa** - entera si el programa
siguiente tiene «Allow delayed start», si no cortada al final si
suena al menos la mitad.  Para un bloque de episodios («limit: 1
item») la casilla solo hace falta delante de un programa que debe
empezar puntual; vea [Autoloading
Playlists](./AUTOLOADING_PLAYLISTS.md) §4.

### Crear una playlist

Biblioteca → **+ Nuevo** → **Playlist**.

El editor de playlist se abre con la playlist a la
izquierda y la biblioteca a la derecha. Arrastre items de
biblioteca a la playlist; reordene por arrastrar y soltar.
En lugar de arrastrar también puede seleccionar items y pulsar **Add to
current playlist** en la barra de herramientas de la biblioteca, o
elegir **Add to Playlist** en el menú contextual de una fila (pistas,
bloques inteligentes, retransmisiones, entradas de línea; desde
2026-10-21).  Ambos se refieren a la pestaña de edición activa; con
**Scheduled Shows** activa el botón añade al programa en su lugar.

### Longitud por defecto

Cada playlist tiene una **Longitud por defecto** que
aparece como la duración nominal de la playlist en la
biblioteca.

### Eliminar una playlist que aún usan programas (desde el 28/10/2026)

Al eliminar una playlist de la biblioteca, RASTATIME comprueba primero
qué programas la usan como playlist de **autoloading**, **intro** u
**outro**, y si es la intro / outro predeterminada de la emisora
(Settings → General).  La pregunta de eliminación enumera esos
programas.  Si confirma, los programas pierden la playlist **y** su
casilla *Add Autoloading Playlist* se desactiva, de modo que el
calendario muestra el estado real en vez de un programa que parece
lleno y queda en silencio.  Elija después otra playlist en el diálogo
del programa.  Antes del 28/10/2026 la casilla seguía marcada y el
programa vacío; el panel ahora también avisa de esos programas hasta
48 horas antes (vea [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md),
sección 7).

### Usar una playlist en un programa

Dos caminos:

1. **Puntual**: arrastre la playlist en un programa vacío
   en el show-builder. Los items de la playlist son
   *aplanados* en el planning. La playlist original no
   está vinculada al programa.

2. **Autoloading**: adjunte la playlist a la definición
   del programa en la sección **Autoloading Playlist**
   del formulario de edición de programa. Cada futura
   instancia del programa tendrá los items de la playlist
   construidos automáticamente. Vea
   [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md).

---

## 5. Webstreams y Line-Ins como items de biblioteca

Tanto [Webstreams](./WEBSTREAMS.md) como
[Line-Ins](./LINE_IN.md) aparecen en la biblioteca y se
comportan como pistas cuando se planifican.

---

## 6. Acciones masivas

Marque la casilla al inicio de cada fila, luego use la
barra de herramientas que aparece en la parte inferior de
la tabla:

| Acción | Efecto |
|---|---|
| **Añadir a playlist** | Añadir las filas seleccionadas a una playlist existente de su elección. |
| **Eliminar** | Eliminar las filas seleccionadas. |
| **Editar** | Una pista seleccionada: su pestaña de edición, como antes. **Dos o más pistas seleccionadas (desde 2026-10-08): un solo diálogo para todas** - creador, álbum, género, año, tipo de pista, idioma, mood, sello, compositor, director, copyright, país (desde 2026-11-08), activo desde y fecha de caducidad (`none` las borra), pista desactivada (*Sí* / *No*; desde 2026-11-08, *No* también vacía las fechas de caducidad alcanzadas y las fechas de activación aún por llegar), descripción. Los campos vacíos no cambian; un campo relleno se escribe en cada pista seleccionada; título, número de pista, BPM, puntos de cue y carátula siguen siendo por pista. Solo base de datos, como el editor individual (las etiquetas de los archivos se leen al importar y nunca se reescriben). Las pistas que no puede editar se omiten y se cuentan en el resultado. |
| **Transferir propietario** | Reasignar propiedad (solo Admins). |
| **Cue Points** | Detecta los puntos de cue de las pistas seleccionadas a partir del audio (la misma detección de silencio que el analizador ejecuta al importar: por debajo de −60 dB durante al menos 0,3 s al inicio o al final) y los guarda. Los programas futuros que programan esas pistas adoptan los nuevos valores y se recalculan. Las pistas de más de 15 minutos se omiten - la acción está pensada para jingles y otros elementos cortos. Desde el 30/09/2026. |
| **Releer etiquetas** *(desde 2026-10-21)* | Vuelve a leer las etiquetas de las pistas seleccionadas desde los archivos en disco, para archivos editados en Windows después de la importación.  RASTATIME nunca relee un archivo por sí mismo: la base de datos es la verdad para la biblioteca y el playout.  El botón sustituye título, artista, álbum, género, año, número de pista, compositor, copyright, sello, ISRC, BPM, mood, idioma, comentario y (desde 2026-11-08) país por lo que contiene el archivo (una etiqueta ausente vacía la columna) y actualiza la suma de comprobación y el tamaño; todo lo que se define solo en RASTATIME (tipo de pista, teaser, puntos de cue, sonoridad, fechas de caducidad y de activación, peticiones) se mantiene.  Administradores y gestores de programación para cualquier archivo, los demás para los suyos.  El archivo solo se lee, así que una pista en antena está a salvo; pero edite un archivo en Windows solo mientras no esté programado, el playout reproduce directamente desde la biblioteca. |

---

## 7. Preguntas frecuentes

### "Subí una pista y nunca apareció."

Verifique la insignia de estado de subida:
- **Amarilla (Advertencia)**: el archivo fue importado
  con advertencias.
- **Roja (Fallo)**: el archivo es inreproducible.
- **Sin insignia pero sin fila**: el servicio analyzer no
  está corriendo.

> **Subidas fallidas (desde el 28/10/2026).**  El filtro de la página de
> subida muestra **Failed (N)** en cuanto algo falla, y la fila dice *por
> qué* (el motivo del analyzer, p. ej. «ffprobe could not read the file»).
> **Download** entrega el original tal como se subió, para examinarlo o
> repararlo; **Clear** elimina la fila junto con el original que el
> analyzer conserva en `organize/` para las importaciones fallidas.  El
> panel avisa cuando hay subidas fallidas de más de una hora esperando o
> archivos de más de un día en `organize/`.  Un tipo de daño se repara
> automáticamente: un archivo WAV con un bloque de etiquetas ID3 delante de
> su cabecera RIFF se recorta y se importa.

### "Subí un archivo WAV y la biblioteca muestra un MP3."

Es lo previsto: los archivos sin pérdida se convierten a MP3 de
320 kbps al importar (sección 2, *Formatos de archivo al importar*).
Para conservar un archivo sin pérdida, desactive Configuración →
**Máquina local** → **Formato de importación** antes de subirlo.

### "¿Por qué mi smart block devuelve las mismas pistas cada vez?"

Probablemente eligió **Estático** en lugar de **Dinámico**.

### "¿Puedo importar una estructura de carpetas preservando los nombres de subcarpetas?"

La Carpeta de importación local preserva nombres de
subcarpetas como campo **álbum** de las pistas importadas
si no hay tag ID3 de álbum.  En la biblioteca el archivo queda
luego bajo `imported/<artista>/<álbum>/`; un archivo sin tag de
artista va a `imported/tagless/` (desde el 2026-10-24).

### "¿Cuál es el tamaño máximo de archivo?"

El subidor del navegador está limitado por
`LimitRequestBody` de Apache — por defecto 100 MB.

---

## A dónde ir después

* [Calendario](./CALENDAR.md) — cómo poner items de
  biblioteca al aire.
* [Plantillas de programa](./SHOW_TEMPLATES.md) —
  reutilizar configuración de programa.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) —
  dejar que los programas se rellenen solos desde una
  playlist.
* [Webstreams](./WEBSTREAMS.md) y [Line-In](./LINE_IN.md)
  para detalle por tipo.
