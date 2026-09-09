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
| **Nombre de stream / URL / Género / Descripción** | Metadatos ICY anunciados a los oyentes. |

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
que simplemente cierra la conexión se detecta cuando vence el tiempo
de espera de red del motor, 30 segundos; desconectar a un DJ desde el
panel es inmediato.

> **Consejo del operador.** Master DJ tiene precedencia
> sobre Show DJ.

### Conectarse como Fuente en vivo

Los presentadores usan cualquier software de difusión de
audio (BUTT, Mixxx, RadioDJ, SAM Broadcaster) configurado
con:

| Campo | Valor |
|---|---|
| Servidor | Hostname / IP público de la emisora |
| Puerto | 8001 (puerto de entrada source, *no* el puerto de oyente 8000) |
| Mount | `/show` para Show DJ, `/master` para Master DJ |
| Usuario | Credenciales configuradas |
| Contraseña | Credenciales configuradas |
| Formato | MP3 |

> **Cómo funciona bajo el capó.** El puerto de entrada
> source (8001) es un mount Icecast separado que llama de
> vuelta a PHP vía `icecast-source-auth.php` para validar
> credenciales. Vea ARCHITECTURE §10.5.

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

Los metadatos ICY se establecen automáticamente por el
playout para pistas planificadas. El contenido de fuente
en vivo no tiene metadatos ICY — establézcalos vía su
software de difusión.

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
