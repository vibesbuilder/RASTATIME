# Streams

> **Dónde está usted en el manual.** Este capítulo cubre
> los **streams salientes** — lo que RASTATIME publica a
> los oyentes. Para los *entrantes*, vea
> [Webstreams](./WEBSTREAMS.md). Para la salida de
> tarjeta de sonido del lado de la máquina-operador, vea
> [Máquina local](./LOCAL_MACHINE.md).

Un **stream** es un mountpoint Icecast (o Shoutcast) que
RASTATIME emite a los oyentes. Una emisora puede
configurar hasta **cuatro streams de salida**:

- **Calidad principal** (192-320 kbps) para oyentes
  escritorio / fijos.
- **Calidad móvil** (96-128 kbps) para oyentes celulares.
- **Sin pérdida / archivo** (FLAC).
- **Reserva / standby**.

---

## 1. La página de configuración Streams

Configuración → **Streams**. Cada una de las cuatro
tarjetas de stream tiene el mismo conjunto de campos.

### Campos por stream

| Campo | Notas |
|---|---|
| **Habilitado** | Interruptor maestro. |
| **Tipo** | **Icecast** (recomendado), **Shoutcast**, **Custom**. |
| **Servidor / Puerto** | `localhost:8000` para la instalación por defecto. |
| **Mount** | El path URL del mountpoint, con `/` inicial. ej. `/rastatime`. |
| **Usuario fuente / Contraseña** | Credenciales que Icecast espera de un cliente source. |
| **Formato** | **MP3**, **AAC**, **OGG Vorbis**, **OPUS**, **FLAC**. |
| **Bitrate** | Kbps. La decisión más consecuente por stream; vea §2. |
| **Canales** | **Estéreo** (por defecto), **Mono**. |
| **Frecuencia de muestreo** | 22,05 / 32 / 44,1 / 48 kHz. |
| **Nombre de stream / URL / Género / Descripción** | Metadatos ICY anunciados a los oyentes. Desde el 2026-09-13 se renderizan los cuatro; un Nombre o una Descripción vacíos recurren al nombre de la emisora (Icecast mostraba "Unspecified name"). |

### Stream Label y Off Air Metadata

Lo que los oyentes ven como título "sonando ahora" en su reproductor.
Ambos campos están en la página Streams sobre los bloques por stream; el
nombre de la emisora viene de Configuración → General.

| Fuente en el aire | Artist - Title | Show - Artist - Title | Station name - Show name |
|---|---|---|---|
| Pista programada | Artista - Título | Programa - Artista - Título | RASTATIME - Programa |
| Webstream con títulos propios | título del flujo fuente | Programa - título del flujo fuente | RASTATIME - Programa |
| Webstream sin títulos, Line-In | RASTATIME - Programa | RASTATIME - Programa | RASTATIME - Programa |
| DJ (BUTT / Mixxx) | título enviado por el software DJ, si no RASTATIME - Programa | Programa - título enviado por el software DJ, si no RASTATIME - Programa | RASTATIME - Programa |
| Nada programado | texto Off Air Metadata | texto Off Air Metadata | texto Off Air Metadata |

- **Off Air Metadata** sustituye el título de la última pista en cuanto no
  hay nada en el aire (antes del 2026-09-13 el título viejo permanecía horas).
- Un cambio en cualquiera de los dos campos surte efecto en el siguiente
  refresco de la parrilla (unos dos minutos), sin reinicio.
- La etiqueta se escribe en los metadatos de título del flujo: aplica a
  MP3/AAC (ICY), a OGG (in-band) y a las grabaciones.

### Insignia de estado del stream

| Insignia | Significado |
|---|---|
| ● **Conectado** (verde) | Playout conectado; emitiendo. |
| ◐ **Conectando** (amarillo) | En medio de intento de conexión. |
| ● **Desconectado** (rojo) | Playout no puede conectarse. |
| ◯ **Deshabilitado** (gris) | Stream configurado pero interruptor apagado. |

La insignia se actualiza cada 5 segundos vía el endpoint
`/api/v2/streams`.

> **Consejo del operador.** Una insignia roja en Stream 1
> significa que los oyentes no oyen nada. Verifique
> Icecast (`Get-Service icecast2`), credenciales, puerto
> 8000.

---

## 2. Elegir un bitrate

| Caso de uso | Formato | Bitrate | Canales | Freq. |
|---|---|---|---|---|
| Música, calidad principal | MP3 | 192 kbps | Estéreo | 44,1 kHz |
| Música, premium / fans FLAC | MP3 | 320 kbps | Estéreo | 44,1 kHz |
| Música, archivo FLAC | FLAC | ~700-1000 kbps | Estéreo | 44,1 kHz |
| Talk-show / hablado | MP3 | 96 kbps | Mono | 44,1 kHz |
| Móvil / celular | AAC | 64 kbps | Estéreo | 44,1 kHz |
| Reserva / debug | MP3 | 128 kbps | Estéreo | 44,1 kHz |

### Matemática de ancho de banda

Cada stream habilitado usa ancho de banda =
`bitrate × oyentes_concurrentes_máx`. Un stream 192 kbps
con 50 oyentes concurrentes usa ~9,6 Mbps salientes.

Para más de ~50-100 oyentes, ejecute Icecast en un
servidor cloud con un uplink grueso.

---

## 3. Fuentes en vivo

Además del contenido planificado, RASTATIME acepta dos
conexiones de **fuente en vivo** por programa:

| Fuente | Propósito |
|---|---|
| **Show DJ** | Login por-programa. El presentador principal del programa se conecta desde cualquier lugar. |
| **Master DJ** | Login a nivel emisora. Un productor / ingeniero puede tomar el control en cualquier momento. |

Cuando una fuente en vivo se conecta, el conmutador de fuentes
enruta su audio a la salida en lugar del contenido programado y
vuelve a la programación cuando se desconecta. Desde el 2026-09-09 el
motor comunica cada conexión y desconexión a la emisión en el
momento en que ocurre, así que el cambio es inmediato; la emisión
solo lo verifica por su enlace de mandos (ajuste de máquina
`RASTATIME_DJ_RECONCILE_SECONDS`, 600 segundos por defecto). Un DJ
que simplemente cierra la conexión se detecta dentro del tiempo de
espera de red del motor, 5 segundos (ajuste de máquina
`RASTATIME_HARBOR_TIMEOUT_SECONDS`); un DJ cuya conexión se congela más
tiempo es desconectado y debe reconectarse, cosa que BUTT hace solo.
Desconectar a un DJ desde el panel es inmediato.

> **Consejo del operador.** Master DJ tiene precedencia
> sobre Show DJ.

**Switch Transition Fade (s)** (Settings → Streams, desde el 2026-09-28,
valor inicial 1 s) da forma al relevo: cuando un DJ se conecta, entra en
antena de inmediato y la programación se desvanece por debajo durante
estos segundos; cuando el DJ se desconecta, el DJ se desvanece durante el
mismo tiempo y la programación vuelve al instante a volumen completo. 0 =
cambio seco. La cadena de audio aplica el valor unos segundos después de
guardar (reinicio planificado en un momento tranquilo o en un límite de
pista). Antes del 2026-09-28 el campo no tenía efecto; ambos sentidos
eran un cambio de 50 ms.

### Conectarse como Fuente en vivo

Los presentadores usan cualquier software de difusión de
audio (BUTT, Mixxx, RadioDJ, SAM Broadcaster) configurado
con:

| Campo | Valor |
|---|---|
| Servidor | Hostname / IP público de la emisora |
| Puerto | El **Master Source Port** / **Show Source Port** que muestra Ajustes → Streams (8001 por defecto; 8000 es el puerto de oyentes) |
| Mount | El **Master Source Mount** / **Show Source Mount** que muestra Ajustes → Streams (`main` y `show` por defecto) |
| Usuario | Master DJ: el usuario de Ajustes → Streams → **Master Source**. Show DJ: el login RASTATIME de un presentador registrado, o el usuario personalizado de la sección **Live Stream Input** del programa |
| Contraseña | La contraseña correspondiente |
| Formato | MP3 |

> **Cómo funciona bajo el capó.** El puerto de entrada source es
> un harbor de Liquidsoap dentro del motor de emisión. Cada
> login se comprueba en el momento de conectar (desde el
> 2026-09-10): el motor pregunta a la emisión, la emisión
> pregunta a la aplicación web, que aplica los ajustes de arriba.
> Para el Show DJ cuenta el programa que está en antena ahora
> mismo; un Show DJ no puede entrar antes de que empiece el
> programa. Solo mientras la propia emisión no esté accesible el
> motor recurre a la contraseña estática del harbor de
> `libretime.conf`. Vea ARCHITECTURE §23.27 (addendum 2026-09-10).

---

## 4. Monitorear la salud de streams

### Desde la interfaz

Configuración → Streams muestra la insignia por stream.
La página **Estado del sistema** resume estado de
conexión por stream, contador de oyentes actual, pico de
oyentes hoy.

### Desde la interfaz admin Icecast

`http://<servidor>:8001/admin/`.

### Desde la API

`GET /api/v2/streams` devuelve el estado completo de cada
stream como JSON.

---

## 5. Auth de stream (lado del oyente)

Por defecto, todos los streams son **públicos**. Para
restringir la escucha:

1. Configurar auth de oyente en `config/icecast.xml`.
2. Reiniciar Icecast.
3. El script `icecast-auth.php` autentica contra
   `cc_subjs`.

---

## 6. Múltiples servidores Icecast

Cada uno de los cuatro streams puede apuntar a un
**servidor Icecast diferente**:

- **Local + cloud**: Stream 1 a Icecast local, Stream 2 a
  Icecast cloud.
- **Distribución geográfica**: Stream 1 a Icecast EU,
  Stream 2 a Icecast US.

> **Cómo funciona bajo el capó.** Cada stream mapea a una
> fuente `libvlc_VLM`. Vea ARCHITECTURE §10.

---

## 7. Preguntas frecuentes

### "¿Cuántos oyentes concurrentes puede manejar RASTATIME?"

RASTATIME mismo solo codifica una vez por stream. La
capacidad de oyentes depende de Icecast (maneja miles en
hardware modesto) y del uplink de red.

### "¿Puedo tener una salida HLS / DASH?"

No directamente — use un repackager externo
(`ffmpeg -i icecast-url -hls_time 6 ...`).

### "¿Por qué el contador de oyentes de mi stream está siempre en 0?"

Tres posibilidades: nadie está escuchando, la insignia
está mal (refresque la página), o los oyentes se conectan
a un mountpoint diferente.

### "Cambié el bitrate pero los oyentes dicen que suena igual."

La mayoría del software de reproductor cachea la
conexión. Los oyentes necesitan reconectarse.

### "¿Puedo cambiar el bitrate del stream mientras está reproduciendo?"

Sí. Los oyentes ven ~5 s de silencio durante la
reconexión.

### "¿Cómo añadir metadatos ICY?"

Ya están: el playout etiqueta cada paquete de metadatos según **Stream
Label** (vea §1), muestra el texto **Off Air Metadata** mientras no hay
nada en el aire, y pasa los títulos que envía un webstream o el software
DJ por la misma etiqueta.  Una fuente en vivo sin títulos propios se
etiqueta con el programa en curso.

---

## A dónde ir después

* [Máquina local](./LOCAL_MACHINE.md) — la salida de
  tarjeta de sonido del lado de la máquina-operador.
* [Panel](./DASHBOARD.md) — salud rápida de streams
  visible en cada página.
* [Webstreams](./WEBSTREAMS.md) — el contrapunto
  *entrante*.
* [`docs/operator/CRASH_RECOVERY.md`](../../operator/CRASH_RECOVERY.md)
  — cuando un stream se vuelve rojo.
