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
| **Pista (Track)** | Un archivo de audio único (MP3, FLAC, OGG, WAV, AAC). | `cc_files` |
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
navegador y equipo. La tabla de pistas del panel y la del
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
| **Archivo** | Uno de: MP3, FLAC, OGG, WAV, AAC, M4A. |
| **Propietario** | Por defecto usted. Los Admins pueden anular. |

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

### Editar metadatos de pista

Haga clic en una fila de pista → **Editar metadatos** en
el menú de acción de la fila.

| Campo | Dónde termina |
|---|---|
| **Título** | `cc_files.track_title` |
| **Creador (Artista)** | `cc_files.artist_name` |
| **Álbum** | `cc_files.album_title` |
| **Género** | `cc_files.genre` |
| **Año** | `cc_files.year` |
| **BPM** | `cc_files.bpm` |
| **Tipo de pista** | `cc_files.track_type` — usado por filtros smart-block |
| **Cue In / Out** | `cc_files.cuein` / `cueout` — recortar el inicio / fin sin re-encodificar. Desde el 30/09/2026 los valores se mantienen dentro del archivo: un cue out más allá de la duración se limita a la duración, un cue in negativo pasa a cero. Un cambio se copia en las filas de los programas futuros que programan la pista (las filas ya iniciadas no se tocan) y esos programas se recalculan - no hace falta volver a llenarlos. |
| **Fade In / Out** | `cc_files.fadein` / `fadeout` |
| **Replay Gain** | `cc_files.replay_gain` — usado por el motor de playout para normalización de nivel |
| **Crossover** | Cómo se encuentra esta pista con sus vecinas (desde el 2026-09-29 un campo de tres opciones; las dos excepciones se excluyen entre sí). **As the track type** (como el tipo de pista, por defecto): la pista se solapa y funde según indique su tipo de pista - Settings → Track Types → *Crossfade Duration* - o, sin valor allí, según la Default Track Crossfade Duration. **No Fade during Crossover** (sin fundido durante el crossover, `cc_files.no_fade_crossfade`): el solapamiento se mantiene, pero esta pista conserva su nivel completo mientras la otra se funde; en un límite de programa sobrepasado, una pista saliente marcada se corta en vez de fundirse. **Exclude from Crossover** (excluir del crossover, `cc_files.exclude_crossfade`): esta pista nunca se solapa con una vecina - empieza al final de la pista anterior y la siguiente empieza a su final. Cambiar a *Exclude* o volver de él recalcula las filas de los programas futuros que programan la pista. |

### Eliminar una pista

Fila → **Eliminar**. La pista se retira de la biblioteca
*y* de cualquier playlist de la que era parte.

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
| **Criterios** | Añadir filas: *artista contiene "Bowie"*, *bpm entre 100 y 130*, etc. |
| **Limitar a** | **Número de pistas** (ej. 10), **Duración en tiempo** (ej. 30:00), **Tiempo restante en el programa**. |
| **Ordenar** | Aleatorio / más reciente primero / por artista / por número de reproducciones / etc. |

> **Consejo del operador.** El límite **"Tiempo restante
> en el programa"** es el más útil para autoloading
> playlists.

### Por qué un smart block puede devolver menos pistas de las pedidas

Los smart blocks respetan el **alcance de biblioteca** del
operador: el DJ propietario ve solo sus propias pistas; un
Program Manager ve toda la biblioteca.

> **Cómo funciona bajo el capó.** Los criterios están
> almacenados en `cc_blockcriteria`. En momento de build,
> `BlockExpander.expand()` ensambla un PostgreSQL `SELECT
> … WHERE … LIMIT …` sobre `cc_files`.

### Toggles de restricción de pool (Opciones avanzadas)

El cajón **Opciones avanzadas** abajo en el diálogo Smart
Block alberga tres toggles de restricción de pool que
restringen el conjunto candidato *antes* de que se ejecuten
el orden + límite:

| Toggle | A qué restringe el pool |
|---|---|
| **Allow only tracks not played yet** (Permitir solo pistas no reproducidas todavía) | Pistas donde `cc_files.lptime` es `NULL` (el playout nunca las ha registrado). Útil para bloques de descubrimiento / rotación de contenido nuevo. |
| **Exclude tracks played lately** (Excluir pistas reproducidas recientemente) | Pistas donde `lptime` es `NULL` *o* más antiguo que la ventana de horas-hacia-atrás configurada (1..8760 h, por defecto 24). Use esto cuando quiera evitar re-rotación reciente sin prohibir toda reproducción previa. El campo compañero "Exclude tracks played in the last hours" aparece cuando el toggle está activado. |
| **Exclude artists played lately** (Excluir artistas reproducidos recientemente) | Pistas cuyo `artist_name` es NULL / vacío *o* cuyo artista no ha sonado vía cualquier otra pista en la ventana de horas-hacia-atrás configurada (1..8760 h, por defecto 24). Use esto cuando quiera evitar que dos pistas del mismo artista se agrupen — independientemente de qué pista específica se reprodujo. El campo compañero "Exclude tracks played in the last hours" aparece cuando el toggle está activado. |
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
> cc_files.lptime < NOW() - INTERVAL 'N hours'` a la
> consulta Propel. El valor en horas se persiste en
> `cc_block_criteria` (criteria =
> `exclude_played_lately_hours`) junto al master flag
> (criteria = `exclude_played_lately`).  `Exclude artists
> played lately` añade una cláusula `WHERE
> cc_files.artist_name IS NULL OR cc_files.artist_name = ''
> OR NOT EXISTS (SELECT 1 FROM cc_playout_history JOIN
> cc_files ON ... WHERE artist_name matches AND starts >
> NOW() - INTERVAL 'N hours')` — `NOT EXISTS` cortocircuita
> en la primera coincidencia así que el coste permanece
> acotado incluso con una gran tabla de historial.
> Persistido como segundo par de criterios
> (`exclude_artists_played_lately` + `..._hours`).  Sin
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

### Crear una playlist

Biblioteca → **+ Nuevo** → **Playlist**.

El editor de playlist se abre con la playlist a la
izquierda y la biblioteca a la derecha. Arrastre items de
biblioteca a la playlist; reordene por arrastrar y soltar.

### Longitud por defecto

Cada playlist tiene una **Longitud por defecto** que
aparece como la duración nominal de la playlist en la
biblioteca.

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
| **Editar metadatos** | Abrir un diálogo de edición por lotes. Solo aplica a pistas. |
| **Transferir propietario** | Reasignar propiedad (solo Admin / Super Admin). |
| **Cue Points** | Detecta los puntos de cue de las pistas seleccionadas a partir del audio (la misma detección de silencio que el analizador ejecuta al importar: por debajo de −60 dB durante al menos 0,3 s al inicio o al final) y los guarda. Los programas futuros que programan esas pistas adoptan los nuevos valores y se recalculan. Las pistas de más de 15 minutos se omiten - la acción está pensada para jingles y otros elementos cortos. Desde el 30/09/2026. |

---

## 7. Preguntas frecuentes

### "Subí una pista y nunca apareció."

Verifique la insignia de estado de subida:
- **Amarilla (Advertencia)**: el archivo fue importado
  con advertencias.
- **Roja (Fallo)**: el archivo es inreproducible.
- **Sin insignia pero sin fila**: el servicio analyzer no
  está corriendo.

### "¿Por qué mi smart block devuelve las mismas pistas cada vez?"

Probablemente eligió **Estático** en lugar de **Dinámico**.

### "¿Puedo importar una estructura de carpetas preservando los nombres de subcarpetas?"

La Carpeta de importación local preserva nombres de
subcarpetas como campo **álbum** de las pistas importadas
si no hay tag ID3 de álbum.

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
