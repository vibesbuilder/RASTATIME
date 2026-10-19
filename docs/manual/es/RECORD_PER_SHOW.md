# Grabación por programa

> **Dónde está usted en el manual.** Este es un toggle
> por-programa en el formulario de edición de programa
> (vea [Calendario](./CALENDAR.md) §2.3). La función
> reemplaza la casilla original "Record from Line In?" por
> una captura más amplia "grabar todo lo que pasa al aire
> durante el programa". Sección 23.13 en ARCHITECTURE
> cubre las decisiones técnicas.

**Grabación por programa** escribe un archivo de todo lo
que estuvo al aire durante un programa — la música, el
micro en vivo, el relevo de webstream, todo — para
archivo, replay, podcast o uso de cumplimiento.

La grabación es un **tap de salida** paralelo: no cambia
nada sobre cómo el programa está planificado o
reproducido. El grabador simplemente escucha la salida
Icecast pública y la escribe a un archivo durante la
duración del programa.

---

## 1. Por qué funciona así

### Lo que hacía LibreTime original

La función original "Record from Line In?" grababa *solo*
la fuente line-in (una entrada física específica), usando
Liquidsoap. Era útil para "un presentador con un micro en
el estudio" pero rota para todo lo demás.

### Lo que hace RASTATIME

El nuevo modelo graba la **salida completa al aire** — lo
que los oyentes escuchan durante el programa,
independientemente de la fuente.

> **Actualización arquitectónica — Phase-C5 (2026-05-28).**
> El pipeline de grabación migró de un subproceso
> FFmpeg-Icecast-tap separado a un bloque Liquidsoap
> `output.file` que se conecta directamente al bus de audio
> interno. Ambas arquitecturas entregan el mismo
> comportamiento visible para el operador (grabación
> por-programa en una carpeta); el tap del bus es solo más
> simple, más fiable, y usa MP3 fijo de 320 kbps de mayor
> calidad. Vea ARCHITECTURE §23.13.bis para el detalle
> técnico.

La implementación es un bloque Liquidsoap
`output.file(id="recording")` en el subproceso Liquidsoap
de larga duración. Se conecta al mismo bus de audio
interno que alimenta las salidas Icecast públicas y lo
codifica en el formato y la tasa de bits elegidos en Ajustes →
Máquina local → **Show Recording** (MP3 320 kbps por defecto; desde
2026-10-18 también AAC, OGG Vorbis y Opus de 96 a 320 kbps).  Con el
valor por defecto, el bloque renderizado es:

```liquidsoap
output.file(
  id="recording",
  %ffmpeg(format="mp3", %audio(codec="libmp3lame", b="320k", samplerate=44100)),
  {recording_path()},
  fallible=true,
  bus,
)
```

Los hooks start/stop por-programa de Pypo controlan el
ciclo de vida vía la interfaz telnet de Liquidsoap:

```
recording.stop
var.set recording_path = C:/.../<YYYY-MM-DD HH-MM-SS> - <show>.mp3
recording.start
```

| Propiedad | Valor |
|---|---|
| **Coste CPU** | ~3 % de un núcleo en Intel i3-1315U (un codificador libmp3lame) |
| **Calidad** | MP3 320 kbps por defecto (Ajustes → Máquina local → Show Recording: MP3 / AAC / OGG Vorbis / Opus, 96–320 kbps) — misma fuente que el stream Icecast principal |
| **Cambios de fuente** | Capturados automáticamente (la grabación se conecta al mismo bus interno que el stream en vivo) |
| **Aislamiento de fallos** | `fallible=true` en `output.file` evita que un fallo de una sola salida (disco lleno, bloqueo de scan AV) se propague en el grafo de fuentes |

> **Formato y tasa de bits** se eligen en Ajustes → Máquina local →
> Show Recording (desde 2026-10-18; por defecto MP3 320 kbps, el
> valor fijo del 2026-05-27).  El playout aplica un cambio en su
> próximo momento tranquilo (o en el siguiente límite de pista); los
> archivos ya escritos conservan su formato, y la extensión sigue al
> formato (`.mp3` / `.aac` / `.ogg` / `.opus`).  El antiguo
> `PlayoutConfig.record_bitrate` se ignora.

> **La grabación la escribe Liquidsoap** (`output.file` en el
> bus interno). Phase-C5 Teil 2d eliminó la ruta de código
> heredada FfmpegRecorder; desde el 2026-09-10 Liquidsoap es
> el único motor de playout, así que cada programa con
> grabación activada se graba.

---

## 2. Habilitar Grabación por programa

### 2.1 En un nuevo programa

Calendario → Nuevo programa → expandir **Grabación** →
marcar **Grabar este programa:** → Guardar.

### 2.2 En un programa existente

Calendario → clic en el programa → **Editar programa** →
expandir **Grabación** → marcar → Guardar.

> **Consejo del operador.** Muchas emisoras graban cada
> programa por defecto. La forma más rápida: marque
> **Grabar este programa:** en una plantilla, guarde como
> Plantilla de programa, luego aplique esa plantilla a
> cada programa. Vea
> [Plantillas de programa](./SHOW_TEMPLATES.md).

> **Cómo funciona bajo el capó.** El toggle establece
> `cc_show.record = TRUE`. Al inicio del programa, el
> constructor de planning del motor de playout emite un
> evento `SHOW_RECORD_START`. El handler en
> `backend/playout/libretime_playout/playout_scheduler.py`
> envía un comando `recording.start` al telnet de
> Liquidsoap, que abre el archivo .mp3 por-programa. Al
> final del programa, el motor emite `SHOW_RECORD_END` y
> el handler envía `recording.stop` para cerrar el archivo
> limpiamente. Vea ARCHITECTURE §23.13 (diseño FFmpeg
> original) y §23.13.bis (migración Liquidsoap Phase-C5).

---

## 3. Dónde vive la grabación

Por defecto, las grabaciones se escriben a:

```
   C:\rastatime\recordings\<show-id>-<starts-at>.mp3
```

Ejemplo:

```
   C:\rastatime\recordings\1234-2026-05-21_14-00-00.mp3
```

El directorio y la plantilla de nombre de archivo se
configuran en `config\libretime.conf` bajo la sección
`[recording]`.

Placeholders disponibles: `{show_id}`, `{show_name}`,
`{starts_at}` (datetime), `{ends_at}` (datetime).

## 3.5 La exclusión antivirus es OBLIGATORIA

> ⚠️ **Importante — se aplica a cada ordenador de estudio
> que ejecuta RASTATIME.**

El software antivirus en tiempo real (Bitdefender, Windows
Defender, Kaspersky, McAfee, ESET, …) escanea cada
escritura de archivo — incluyendo el archivo .mp3 en
crecimiento que se está grabando. Para programas largos
(>30 min), el coste de scan-lock-por-escritura se acumula
hasta el punto en que el pipeline de audio de Liquidsoap
descarta frames intentando mantener el ritmo.

Reality-test 2026-05-28: un programa de 60 min sin
exclusión antivirus grabó solo 52 min 53 s de audio
(~88 % de la duración programada); el mismo pipeline con
la carpeta excluida del antivirus alcanzó reproduciblemente
el 100 %.

**Mitigación: agregar la carpeta de grabación a la lista
de excepciones de su antivirus.**

- **Bitdefender** (el más común en los despliegues
  RASTATIME): GUI Bitdefender → **Protección** →
  **Antivirus** → **Configuración** → **Gestionar
  excepciones** → agregar la ruta de la carpeta de
  grabación (por ejemplo `C:\Users\studio\Music\Show Recordings\`
  o lo que configuró en Settings → Local Machine →
  Show Recording Folder).
- **Windows Defender**: Configuración → **Actualización y
  seguridad** → **Seguridad de Windows** → **Protección
  contra virus y amenazas** → **Administrar
  configuración** → **Agregar o quitar exclusiones** →
  agregar la carpeta de grabación.
- **Otros AVs**: consulte su documentación; la opción
  suele llamarse «Exclusión», «Excepción» o «Lista blanca».

Después de agregar la excepción, no se necesita reinicio;
la grabación del próximo programa se ejecutará con calidad
completa.

> **Consejo del operador.** Agregue la excepción durante
> la configuración inicial de RASTATIME ANTES de que se
> grabe el primer programa. De lo contrario, podría tener
> unas horas de grabaciones cortas antes de notar el
> problema.

---

## 3.6 Copiar las grabaciones a la biblioteca *(desde 2026-10-19)*

Ajustes → Máquina local → **Show Recording** ofrece la casilla
**Copiar las grabaciones de programas a la biblioteca**.  Si está
marcada, cada programa grabado se importa a la biblioteca de medios
en cuanto se cierra su archivo de grabación:

- Se importa una **copia**; el archivo de la carpeta de grabaciones
  permanece exactamente donde está (su archivo histórico no se toca).
- La copia recibe el tipo de pista **Recordings** (se crea en el
  primer uso), el título `<nombre del programa> <AAAA-MM-DD HH:MM>`,
  el nombre del programa como artista y el álbum `Show Recordings`,
  para encontrarla fácilmente en la biblioteca.
- La pista queda **vinculada a la instancia del programa** (el
  «archivo grabado» del calendario), de modo que una repetición
  posterior de un programa en directo pueda usarla.
- Una grabación ya importada se reconoce por su suma de comprobación
  y no se importa dos veces.

Cómo funciona: el playout informa del archivo cerrado a la aplicación
web, que comprueba que la ruta está dentro de la carpeta Show
Recording configurada, etiqueta la copia con ffmpeg y la entrega al
analizador como cualquier subida.  La casilla surte efecto para los
programas que terminan tras un único reinicio del servicio
RASTATIME-PLAYOUT después de la actualización; después puede
activarse o desactivarse en cualquier momento sin reiniciar.

## 4. Encontrar y descargar una grabación

### Desde el calendario

Clic en el programa → **Ver archivo grabado** en el menú
contextual. Aparece solo después de que la grabación ha
terminado de escribir.

### Desde el sistema de archivos

Navegue `C:\rastatime\recordings\` directamente.

---

## 5. Planificación del tamaño de archivo

Tamaño aproximado para una grabación de 1 hora:

| Bitrate de stream | Tamaño 1 hora |
|---|---|
| 96 kbps MP3 | ~43 MB |
| 128 kbps MP3 | ~58 MB |
| 192 kbps MP3 | ~86 MB |
| 256 kbps MP3 | ~115 MB |
| 320 kbps MP3 | ~145 MB |

Una emisora que corre 24/7 a 192 kbps con todos los
programas grabados llena alrededor de **2 GB por día** o
**730 GB por año**.

Las grabaciones no se auto-eliminan. Para rotarlas,
configure una tarea programada:

```powershell
# Eliminar grabaciones más viejas que 90 días
Get-ChildItem "C:\rastatime\recordings\" -File |
   Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-90) } |
   Remove-Item
```

Vea [`docs/operator/BACKUP.md`](../../operator/BACKUP.md).

---

## 6. Qué incluyen las grabaciones

| Fuente | ¿Incluido? |
|---|---|
| Pistas planificadas | Sí |
| Webstreams | Sí |
| Line-ins | Sí |
| Show DJ (fuente en vivo remota) | Sí |
| Master DJ | Sí |
| Fallback Auto-DJ | Sí |
| Silencio | Sí (como silencio real en el archivo) |

### Lo que las grabaciones NO incluyen

- Audio pre-fader del estudio.
- Múltiples variantes de stream (solo el **primer
  configurado** se graba).
- Metadatos de stream de salida (actualizaciones ICY).

---

## 7. Usar grabaciones como podcasts / catchup

Un workflow de seguimiento común:

1. Grabaciones escritas a `C:\rastatime\recordings\`.
2. Una tarea programada las copia a un directorio
   accesible por web.
3. Un generador de feed RSS produce un feed de podcast.
4. Los oyentes se suscriben.

RASTATIME no entrega un generador RSS integrado.

---

## 8. Grabación de cumplimiento

Algunas jurisdicciones requieren que las emisoras de
difusión guarden un registro de difusión durante N días.
Grabación por programa con cada programa grabado + una
copia de archivo por-día es suficiente para la mayoría
de las regulaciones, pero:

- Verifique que el **bitrate** sea aceptable para su
  regulador.
- Configure **almacenamiento fuera de máquina** para
  resiliencia.
- Documente la **cadena de custodia**.

---

## 9. Deshabilitar Grabación por programa

Editar programa → expandir **Grabación** → desmarcar
**Grabar este programa:** → Guardar.

Las instancias ya grabadas no se ven afectadas. Las
instancias futuras no inician el subproceso FFmpeg.

---

## 10. Preguntas frecuentes

### "¿Por qué la grabación comienza unos segundos antes del programa?"

El subproceso FFmpeg toma ~1-2 segundos para arrancar. El
grabador inicia ~3 segundos *antes* de `starts_at`.

Para retirar el padding pre-programa:

```
ffmpeg -ss 00:00:03 -i input.mp3 -c copy output.mp3
```

### "¿Por qué la grabación está silenciosa?"

Si toda la grabación está silenciosa, el grabador se
adjuntó al stream pero el stream mismo estaba silencioso
durante el programa.

### "¿Puedo grabar solo parte de un programa?"

No. El toggle es por-programa.

### "¿Pueden dos programas emitiendo simultáneamente en diferentes salidas grabar ambos?"

El modelo de planning de RASTATIME es single-show: en
cualquier momento, como máximo un programa está al aire,
en paralelo en todos los streams de salida configurados.
La grabación se conecta al bus interno de Liquidsoap (el
mismo audio que alimenta todas las salidas Icecast), por
lo que «diferentes programas en diferentes salidas» no es
un caso soportado arquitectónicamente.

### "¿Grabación por programa captura la fuente Live DJ?"

Sí. Mientras la fuente Live DJ esté al aire (audible en
el stream público), se captura. La grabación no distingue
fuente — es lo que está en el bus interno de Liquidsoap
(= lo que los oyentes escuchan).

### "¿Por qué el tamaño del archivo de grabación es mayor que duración × bitrate?"

La estructura de frame MP3 tiene unos bytes de sobrecarga
por frame. Para un archivo de 320 kbps de una hora, el
tamaño real es típicamente 144-145 MB en lugar de los
144 MB matemáticos.

### "¿Por qué una grabación larga es más corta que la duración programada del programa?"

Casi con certeza su antivirus está escaneando el archivo
.mp3 en crecimiento y bloqueando el codificador Liquidsoap
lo suficiente como para descartar frames. Vea
[Sección 3.5](#35-la-exclusión-antivirus-es-obligatoria)
— agregar la carpeta de grabación a la lista de
excepciones de su antivirus soluciona esto.

Una pequeña diferencia residual (1–3 segundos en un
programa de una hora) es normal y proviene del
alineamiento de límites de frames MP3.

### "¿Puedo grabar a un bitrate diferente del stream?"

Sí — desde 2026-10-18 en Ajustes → Máquina local → **Show
Recording**: formato MP3 / AAC / OGG Vorbis / Opus y tasa de bits
96–320 kbps (por defecto MP3 320 kbps).  La grabación es un bloque
Liquidsoap `output.file` separado con su propio codificador, así que
es independiente de los ajustes de los streams públicos.  El playout
aplica un cambio en su próximo momento tranquilo; sin reinicio
manual.

---

## A dónde ir después

* [Streams](./STREAMS.md) — el stream de salida que
  Record-per-Show toca.
* [Calendario](./CALENDAR.md) — donde habilitar /
  deshabilitar por programa.
* [Plantillas de programa](./SHOW_TEMPLATES.md) — sellar
  grabación en cada nuevo programa.
* [`docs/operator/BACKUP.md`](../../operator/BACKUP.md) —
  plantilla de política de retención.
