# Line-In

> **Dónde está usted en el manual.** Este capítulo cubre
> el tipo de item de biblioteca **Line-In** — entradas de
> audio en vivo nombradas que puede arrastrar a playlists
> y programas. Para la configuración de tarjeta de sonido
> del lado de la máquina-operador, vea
> [Máquina local](./LOCAL_MACHINE.md). Para el
> procedimiento de emergencia cuando un line-in cae en
> silencio o ruido, vea
> [`docs/operator/LINE_IN_BROKEN.md`](../../operator/LINE_IN_BROKEN.md).

Un **Line-In** es una entrada de audio en vivo nombrada
desde un dispositivo de tarjeta de sonido en la máquina
del operador — un micrófono, una salida de mezclador, un
reproductor CD, una interfaz de audio externa — que
RASTATIME expone como item de biblioteca.

Los Line-Ins son nuevos en RASTATIME (2026-05-12).
Reemplazan el slot "Line In" único codificado que
LibreTime original tenía.

---

## 1. Vista general del concepto

Un Line-In tiene dos capas:

| Capa | Qué es | Dónde vive |
|---|---|---|
| **Dispositivo físico** | La entrada real de tarjeta de sonido — un micrófono USB, un jack line incorporado, una interfaz XLR, etc. Identificado por su ID de dispositivo del lado del OS. | La configuración de tarjeta de sonido de la máquina del operador; vea [Máquina local](./LOCAL_MACHINE.md). |
| **Line-In nombrado** | Una fila de biblioteca que *referencia* un dispositivo físico por ID, más un nombre de visualización y configuración. | Tabla `rastatime_linein`. |

Un solo dispositivo físico puede respaldar **como máximo
un** Line-In a la vez.

---

## 2. La página Line-In Library

Configuración → **Line-In Library** (o haga clic en el
chip Line-In verde en la página Biblioteca principal).

Cada fila es un Line-In nombrado. Las columnas:

| Columna | Significado |
|---|---|
| **Nombre** | El nombre de visualización. |
| **Dispositivo** | El dispositivo de tarjeta de sonido que el Line-In referencia. |
| **Longitud por defecto** | La duración por defecto que una fila Line-In ocupa cuando se arrastra a una playlist o programa. `∞` significa "se reproduce hasta que se le diga que pare". |

La barra de herramientas:

| Botón | Qué hace |
|---|---|
| **+ Nuevo** | Abrir el diálogo nuevo-Line-In. |
| **Editar** | Abrir el diálogo de edición. |
| **Habilitar / Deshabilitar** | Alternar el estado disponible sin eliminar. |
| **Eliminar** | Retirar el Line-In. |

> **Cómo funciona bajo el capó.** Todas las acciones
> mutantes son finos pass-through desde
> `application/controllers/LineinController.php` a la API
> REST Django en `/api/v2/audio/linein[/<id>]`. El
> controlador solo aplica ACL (Admin + Super Admin); el
> lado Python en `backend/api/libretime_api/linein/` posee
> validación y persistencia en `rastatime_linein`. Vea
> ARCHITECTURE §14.

---

## 3. Crear un Line-In

Line-In Library → **+ Nuevo**.

| Campo | Notas |
|---|---|
| **Nombre** | Requerido. Único. La etiqueta visible en todas partes. |
| **Dispositivo** | Requerido. El menú desplegable lista cada dispositivo de entrada que el OS ve ahora. Si su dispositivo falta, vea [Máquina local](./LOCAL_MACHINE.md). |
| **Longitud por defecto** | Requerida. Formato `HHh MMm SSs` (mismo parser que Webstreams). Para "se reproduce hasta que se le diga que pare" use `0h 0m 0s`. |
| **Habilitado** | Por defecto activado. |

> **¿Dónde están los canales de entrada?** Este editor rápido se
> mantiene deliberadamente sencillo — el selector de **Canales de
> entrada** (y la prioridad / la tabla de gestión completa) vive en
> el editor completo bajo **Settings → Local Machine → Line-In
> Sources**; el diálogo enlaza allí. Un Line-In creado aquí captura
> los canales 1/2 hasta que elija otro par en el editor completo.

### Interfaces multicanal: un Line-In por estudio

Si la interfaz de audio de la emisora tiene más de dos entradas
(p. ej. un Tascam US-16x08 de 16 entradas con varios estudios
cableados), cree **un Line-In por estudio** — mismo
**Dispositivo**, distintos **Canales de entrada** (elegidos en
**Settings → Local Machine → Line-In Sources**):

- `Estudio A` → Dispositivo `US-16x08`, Canales `Stereo 1/2`
- `Estudio B` → Dispositivo `US-16x08`, Canales `Stereo 5/6`
- `Micro invitado Estudio C` → Dispositivo `US-16x08`, Canales `Mono 7`

Cada Line-In se comporta entonces como su propia fuente en la
biblioteca y en los programas; programas consecutivos desde
estudios distintos en la misma interfaz conmutan limpiamente en el
límite del programa.

> **Cómo funciona por dentro.** Cada Line-In — incluido el simple
> `Stereo 1/2` desde el 2026-09-03 — pasa por un pequeño feeder de
> captura. El feeder lee el dispositivo por la API MME (la única
> API de Windows que demostrablemente entrega todos los canales sin
> tocar ajustes del sistema), extrae los canales elegidos y los
> inyecta por el punto de montaje local `/linein-capture` al motor
> de emisión. Hasta el 2026-09-03 el simple `Stereo 1/2` tomaba en
> su lugar una ruta DirectShow directa; esa ruta direcciona el
> dispositivo por su GUID de punto final de audio de Windows, que
> DirectShow no conoce — en una interfaz multicanal no lograba
> abrir el dispositivo y el slot quedaba en silencio. Cualquier
> otra selección de canales nunca pudo usarla de todos modos: el
> pin DirectShow de una interfaz multicanal solo ofrece dos
> canales. El feeder necesita el nombre visible del dispositivo
> guardado en la fila, así que **los Line-Ins creados antes de esta
> función deben volver a guardarse una vez** — sin ese nombre caen
> a la antigua ruta DirectShow y pueden emitir silencio.

### La longitud por defecto importa

- Para un **micrófono** en un estudio normal de solo
  habla, establezca la Longitud por defecto a la longitud
  típica del segmento de habla (5 min es común).
- Para una **salida de mezclador** que conduce todo el
  programa, establézcala a la longitud completa del
  programa (ej. 60 min) o infinito.
- Para un **reproductor CD** u otra fuente cronometrada,
  establézcala a la longitud típica de pista (3 min).

---

## 4. Usar un Line-In en un programa

> **En la vista previa de audio del programa (desde el 17/09/2026)**,
> un Line-In programado aparece como una fila atenuada marcada *live
> input* — una entrada de hardware no tiene fuente que el navegador
> pueda reproducir; la fila está por completitud y la vista previa
> continúa con la siguiente pista reproducible.

Dos caminos:

### 4.1 Arrastre directo a un programa

Show-builder → arrastre la fila Line-In del panel
Biblioteca al programa. Un item de planning aparece con
el nombre y la Longitud por defecto del Line-In.

### 4.2 Dentro de una playlist

Editor de playlist → arrastre el Line-In desde la
Biblioteca.

> **Cómo funciona bajo el capó.** Migración 0054
> (2026-05-19) añadió `cc_playlistcontents.linein_id`
> como foreign key nullable a `rastatime_linein`, más una
> restricción CHECK de que exactamente uno de `file_id` /
> `stream_id` / `block_id` / `linein_id` es no-NULL por
> fila. Tipo 3 en `cc_playlistcontents.type` indica una
> fila Line-In. ARCHITECTURE §23.18 cubre la decisión de
> esquema.

### Qué se reproduce cuando el slot del Line-In comienza?

**Ruta del motor Liquidsoap (default de producción desde 2026-05-29):**

1. Pypo inicia el subproceso FfmpegLineinCapture para el
   dispositivo de tarjeta de sonido configurado (Windows
   feeder de captura MME → MP3 → mount Icecast local
   `http://localhost:8000/linein-capture`).
2. Pypo envía un único comando telnet a Liquidsoap:
   `linein.start` — la fuente `input.http` dedicada
   comienza a consumir el mount de captura local.
3. Liquidsoap bufferiza poco audio (1,0 s desde 2026-09-04).
   Una vez que `source.is_ready` cambia a true, el bus-switch
   enruta el audio a la fuente linein — los oyentes escuchan el
   micrófono. La fuente acompañante `input.http` se arma *en
   paralelo* al arranque de la captura, así su búfer se llena
   mientras la captura calienta en vez de estrictamente
   después.
4. A la duración configurada, Pypo envía `linein.stop` y
   detiene FfmpegLineinCapture; el switch vuelve a scheduled.
   Desde el 2026-09-04 el relevo es una **mezcla, no un corte**: el
   Line-In se retira de antena mediante una *puerta* (gate) en el
   bus de Liquidsoap, el bus lo funde bajo el sucesor durante la
   duración de crossfade por defecto (Settings → General; 0 = el
   sucesor arranca de inmediato a nivel completo y el Line-In se
   desvanece por debajo, «ducking»), y solo después se detienen la
   captura y la fuente — así las últimas palabras del presentador,
   aún en la cadena, se oyen en vez de perderse.  Lo que sigue — un
   jingle, un webstream — libera el Line-In del mismo modo al
   arrancar, así que el micrófono nunca puede quedar en antena más
   allá de su slot.  La única excepción es un **encadenado real** en
   el mismo dispositivo (el siguiente Line-In arranca en ~2 s): ese
   hereda la captura en marcha sin corte.

**Comportamiento de grabación (nuevo desde Phase F,
2026-05-29):** los line-inputs planificados ahora fluyen
por el bus interno de Liquidsoap al que `output.file` está
conectado, y se incluyen en el archivo de grabación `.mp3`
por programa — misma cobertura que pistas y webstreams.
Antes de Phase F, los programas solo-line-input tenían
grabaciones silenciosas.

**Por qué FfmpegLineinCapture en vez del `input.portaudio`
de Liquidsoap:** input.portaudio no tiene método
`set_device` en tiempo de ejecución, no tiene auto-reconnect
al desconexión USB, y usa índices PortAudio-enteros en vez
de los GUIDs de endpoint de audio Windows que la biblioteca
frontend sigue. El watchdog de FfmpegLineinCapture maneja
unplug-replug transparentemente; Liquidsoap consume su
mount Icecast local sin preocuparse por la identidad del
dispositivo.

**Latencia — inicio y fin del slot:** la ruta line-in tiene una
latencia de extremo a extremo: lo que se dice en el instante de
estudio *t* llega al stream en *t + L*. Dos consecuencias: el
inicio del slot queda en silencio aproximadamente L mientras la
cadena se llena, y al final del slot los últimos L segundos siguen
en la cadena cuando se cierra la fuente — **nunca llegan al
stream**. Medido en emisión el 2026-09-04 (contando segundos en el
micrófono): L era ~6 s. Cinco de ellos eran la *autodetección de
formato* de FFmpeg en el punto de montaje de captura: un oyente se
incorpora al flujo Icecast a mitad de stream, sin cabecera a la
vista, y el decodificador escanea ~5 s antes de enganchar. Desde el
2026-09-04 el formato se fuerza (`format="mp3"`, la captura siempre
muxea MP3), el búfer `input.http` es de 1,0 s (ajustable por
`RASTATIME_LIQUIDSOAP_LINEIN_HTTP_MAX_BUFFER_SECONDS`) y la
comprobación de salud al arranque de la captura es de 0,75 s.
Medido después: hueco de inicio 2 s, pérdida al final del slot 2 s.

Esos dos segundos restantes se abordan desde el 2026-09-04 (por la
tarde): **precalentamiento** — 10 s antes de un slot Line-In el
playout ya arranca la captura y conecta la fuente de Liquidsoap con
la puerta del bus cerrada, de modo que al inicio del slot solo se
abre la puerta y el Line-In está en antena en un frame; y la
**mezcla al cerrar la puerta** al final del slot (ver el paso 4),
que reproduce la cola almacenada bajo el sucesor en lugar de
descartarla. No se precalienta cuando otro Line-In está en antena
(una captura a la vez) ni cuando la fila no tiene nombre de
dispositivo guardado; esos slots arrancan por la vía normal
(~2 s).

Cuando la duración del slot transcurre, el motor envía un
evento `LINEIN_END` y el source switcher regresa al
planning.

---

## 5. Editar o retirar un Line-In

### Editar

Line-In Library → clic en la fila → **Editar**. Cambie
nombre, dispositivo, longitud por defecto o estado
habilitado. **Guardar**.

- **Cambio de nombre** se propaga a la lista Biblioteca y
  al widget En reproducción en la próxima actualización.
- **Cambio de dispositivo** se propaga a *cada* uso
  futuro.
- **Cambio de longitud por defecto** afecta solo *nuevos*
  usos.
- **Habilitado = apagado** retira el Line-In
  inmediatamente de la biblioteca de arrastre.

### Deshabilitar

Menú contextual de fila → **Deshabilitar**.

### Eliminar

Menú contextual de fila → **Eliminar**. Confirme. El
Line-In se retira *y* cada fila `cc_playlistcontents` y
`cc_schedule` que lo referencia se retira (CASCADE).

> **Consejo del operador.** Prefiera **Deshabilitar**
> sobre **Eliminar** a menos que esté seguro de que nunca
> usará el Line-In de nuevo.

---

## 6. La dependencia del dispositivo físico

Un Line-In referencia un dispositivo de tarjeta de sonido
por **ID del lado del OS**. Ese ID es estable a través de
reinicios mientras:

- El dispositivo permanezca enchufado.
- Ningún otro software de audio haya sido instalado que
  reasigne IDs de dispositivo.

Si el dispositivo desaparece:

- El Line-In sigue en la Biblioteca.
- Su fila en Configuración → Line-In Library muestra una
  insignia de **signo de exclamación rojo** junto a la
  columna dispositivo.
- Cualquier planning que intente reproducir el Line-In lo
  salta con una advertencia "Device not found" en el log
  de playout.
- El fallback (silencio o bucle fallback) se reproduce.

Vea
[`docs/operator/DEVICE_MISSING.md`](../../operator/DEVICE_MISSING.md)
para el runbook de recuperación.

---

## 7. Permisos

Solo los roles **Admin (A)** y **Super Admin (S)** pueden
crear, editar o eliminar Line-Ins.

DJs (H) y Program Managers (P) pueden arrastrar Line-Ins
existentes a sus propias playlists / programas, pero no
pueden crear o modificar las definiciones de Line-In
subyacentes.

---

## 8. Preguntas frecuentes

### "¿Dónde está la configuración 'Show Source' / 'Master Source' / 'Line In' original?"

LibreTime original tenía tres entradas codificadas
configuradas bajo **Configuración → Live Sources**.
RASTATIME mantiene Show Source y Master Source (estas son
entradas DJ remotas sobre Icecast) pero reemplaza el
"Line In" único codificado por la función Line-In
nombrado.

### "¿Pueden dos Line-Ins referenciar el mismo dispositivo físico?"

Sí, pero solo uno tendrá éxito en cualquier momento. La
mayoría de drivers de tarjeta de sonido conceden acceso
exclusivo al primer abridor.

### "¿Puede un Line-In ser el único contenido de la autoloading playlist?"

Sí. Cree una playlist conteniendo exactamente una fila
Line-In con Longitud por defecto = la longitud del
programa (o infinito).

### "¿Se graba el audio del Line-In si Record-per-Show está habilitado?"

Sí (desde Phase F, 2026-05-29). En el modo de motor
Liquidsoap, el audio del line-in fluye por el mismo bus
interno de audio al que `output.file` está conectado para
el archivo MP3 por programa, y es capturado nativamente —
junto con las pistas regulares o webstreams planificados
del mismo programa. Vea
[Grabación por programa](./RECORD_PER_SHOW.md).

### "¿Puedo añadir una fuente de audio de red (ej. AES67 / Dante) como Line-In?"

Solo si la fuente se presenta como dispositivo de entrada
de tarjeta de sonido Windows — muchos drivers AES67 /
Dante entregan una tarjeta de sonido virtual.

---

## A dónde ir después

* [Máquina local](./LOCAL_MACHINE.md) — configuración
  física de tarjeta de sonido.
* [Biblioteca](./LIBRARY.md) — los Line-Ins aparecen
  también en la Biblioteca principal.
* [Panel](./DASHBOARD.md) → Estado de fuente — vea qué
  Line-In está actualmente al aire.
* [`docs/operator/LINE_IN_BROKEN.md`](../../operator/LINE_IN_BROKEN.md)
  — procedimiento de emergencia.
* [`docs/operator/DEVICE_MISSING.md`](../../operator/DEVICE_MISSING.md)
  — cuando el dispositivo subyacente desaparece.
