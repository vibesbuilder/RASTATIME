# RASTATIME — Manual del usuario (Español)

> 🌐 **Idiomas:** [English](../../../USER_MANUAL.md) ·
> [Deutsch](../de/USER_MANUAL.md) ·
> [Français](../fr/USER_MANUAL.md) ·
> **Español**

> **Acerca de este manual.** RASTATIME es un fork
> Windows-first de LibreTime para operar una emisora de
> radio comunitaria / comercial pequeña. Este documento es
> el compañero orientado al operador de los documentos
> técnicos
> [ARCHITECTURE](../../../RASTATIME_ARCHITECTURE_DRAFT_v0.1.md)
> e [INSTALL](../../operator/INSTALL.md). Cubre **cómo
> operar una emisora con RASTATIME día a día** — no cómo
> instalar o depurar el servidor.

> **Nota de consistencia.** El código, las cadenas de UI en
> el repositorio y todos los componentes backend están en
> inglés. Esta traducción describe el uso; en caso de
> discrepancias entre esta traducción y el original en
> inglés, el original en inglés es la versión oficial.

---

## Audiencia y convenciones

Este manual está escrito para dos lectores en paralelo:

* **Operadores** — Directores de emisora, responsables de
  programación, presentadores, DJs. Usted se conecta a la
  interfaz web por la mañana, planifica el día, hace clic
  en "Guardar" y sigue adelante. Todo lo que necesita para
  esto está en el cuerpo principal de cada capítulo.

* **Técnicos** — Administradores, ingenieros,
  integradores. También necesita saber qué pasa por
  debajo: qué tabla de base de datos escribe la interfaz,
  qué endpoint API dispara el botón, qué servicio necesita
  estar activo. Busque los recuadros **Cómo funciona bajo
  el capó**; cubren los detalles internos sin abultar el
  flujo del operador.

### Convenciones visuales

| Marca | Significado |
|---|---|
| **Negrita** | Etiqueta de botón, elemento de menú o nombre de campo como aparece en la interfaz. |
| `código` | Valor literal que el operador escribe o que el sistema muestra textualmente — un nombre de archivo, una clave de configuración, una URL de stream. |
| > Bloque de cita | Nota al margen, advertencia o consejo del operador. Puede saltarse en una primera lectura. |
| **Cómo funciona bajo el capó** | Recuadro técnico — tabla de base de datos, endpoint API, decisión del scheduler. Los operadores pueden saltar. |
| **Por qué funciona así** | Recuadro de decisión de diseño — apunta al número de sección ARCHITECTURE correspondiente cuando es relevante. |

### URL y rutas por defecto

A menos que su instalación los redefina en
`config/libretime.conf`:

| Qué | Por defecto |
|---|---|
| Interfaz web (frontend Apache) | `http://<station-host>/` |
| API REST Django | `http://localhost:8765/api/v2/` |
| Servidor de streaming Icecast | `http://localhost:8000/` |
| Raíz de instalación | `C:\rastatime\` |
| Directorio de logs | `C:\rastatime\logs\` |
| Biblioteca de medios en disco | `C:\rastatime\media\` |
| Caché de audio local del operador | `C:\rastatime\scheduler\` |
| Archivo de configuración | `C:\rastatime\config\libretime.conf` |

Si su emisora usa rutas diferentes, sustituya en todo el
documento.

---

## Cómo está organizado RASTATIME

RASTATIME es **dirigido por calendario**. Todo lo que sale
al aire es:

1. Un **programa** colocado en el calendario a una hora
   específica, o
2. El **fallback** que rellena el tiempo de aire cuando
   ningún programa está activo.

Un programa es un slot en el calendario; el slot se *rellena*
con contenido (pistas, smart blocks, webstreams, line-ins)
ya sea manualmente en el show-builder, automáticamente vía
una autoloading playlist, o ambas. Cuando el slot comienza,
el motor de playout reproduce el contenido rellenado.

El **panel** en la esquina superior derecha muestra qué
está al aire ahora, qué viene después, y qué streams de
salida están sanos.

```
   ┌──────────────────────────┐         ┌────────────────────────────────┐
   │      OPERADOR (usted)    │         │     CALENDARIO (planificación)  │
   │                          │  crea   │                                │
   │  • Planifica el horario  │────────▶│  • Programas en horas fijas   │
   │  • Rellena los programas │         │  • Cada programa = 1 fila      │
   │  • Gestiona biblioteca   │         │    en cc_show_instances        │
   └──────────────────────────┘         └─────────────────┬──────────────┘
              ▲                                           │
              │ ven en el panel                           │ scheduler despacha
              │                                           ▼
   ┌──────────┴───────────────┐         ┌────────────────────────────────┐
   │  EN VIVO (salida)        │◀────────│ MOTOR PLAYOUT (VLC)            │
   │                          │ alimenta│                                │
   │  • Icecast :8000         │         │  • Reproduce archivos/streams │
   │  • Archivo grabación     │         │  • Cambia a fuente en vivo    │
   │  • Salida estudio opc.   │         │  • Emite eventos start/end    │
   └──────────────────────────┘         └────────────────────────────────┘
```

Todo en este manual cuelga de una de estas cuatro cajas.

---

## El manual a primera vista

Cada enlace abajo abre un sub-documento enfocado en
[`docs/manual/es/`](.). Léalos en cualquier orden — el
documento maestro arriba es lo único que todos asumen.

### Operación de difusión diaria

| Capítulo | Contenido |
|---|---|
| [Primeros pasos](./GETTING_STARTED.md) | Primer inicio de sesión, recorrido del panel, conceptos básicos, vista general de roles. Lea esto primero si nunca ha usado RASTATIME. |
| [Panel](./DASHBOARD.md) | Widget En reproducción, estado de fuente, anulación manual, poner la emisora en vivo desde un micrófono. |
| [Calendario](./CALENDAR.md) | Crear programas, editar, arrastrar y soltar, programas recurrentes, repeticiones, presentadores. |
| [Plantillas de programa](./SHOW_TEMPLATES.md) | Reutilizar configuración de programa sin reescribir cada semana. |
| [Importar / Exportar](./IMPORT_EXPORT.md) | Exportar usuarios, programas, listas, bloques inteligentes, webstreams y suscripciones a podcasts como CSV/JSON, mantenerlos en una hoja de cálculo y reimportarlos con vista previa. |
| [Inicio diferido de programa](./DELAYED_START.md) | Dejar que un programa inscrito empiece tarde cuando el programa anterior se sobrepasó, en lugar de recortar ese programa. El retraso se propaga a través de programas inscritos consecutivos hasta la primera ancla a hora fija. |

### Contenido y biblioteca

| Capítulo | Contenido |
|---|---|
| [Biblioteca](./LIBRARY.md) | Pistas, smart blocks, playlists. Búsqueda, importación, organización. |
| [Webstreams](./WEBSTREAMS.md) | Incluyendo la longitud por defecto con precisión de segundos (2026-05-19). |
| [Line-In](./LINE_IN.md) | La vista combinada biblioteca-y-playlist para entradas en vivo nombradas. |

### Automatización

| Capítulo | Contenido |
|---|---|
| [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) | Dejar que una playlist se construya para cada instancia de un programa, incluyendo gestión de reserva de outro. |
| [Automatización de teasers](./TEASERS.md) | Vincular jingles con el programa que anuncian; un criterio de bloque inteligente emite los teasers «hoy» y «mañana» el día correcto. |
| [Auto DJ](./AUTO_DJ.md) | El rellenador en segundo plano que crea programas en huecos del calendario y completa programas incompletos. |
| [Peticiones de canciones](./SONG_REQUESTS.md) | Dejar que los oyentes pidan pistas desde un widget público, que suenan automáticamente dentro de un request show. |
| [Alertas de tráfico](./TRAFFIC_ALERTS.md) | Introducir MP3s de boletines de tráfico de último momento en el programa en curso mediante un smart block — en unos ~10 minutos, en el siguiente espacio de tráfico, sin intervenir en el playout. |
| [Grabación por programa](./RECORD_PER_SHOW.md) | Capturar la salida completa al aire de un programa en un archivo. |
| [Grabación 24/7](./RECORD_PER_HOUR.md) | Grabar toda la salida al aire las 24 horas, un archivo por hora — para cumplimiento, escucha diferida y copia de seguridad de emergencia. |

### Salida e infraestructura

| Capítulo | Contenido |
|---|---|
| [Streams](./STREAMS.md) | Configurar hasta cuatro streams de salida, monitorear contadores de oyentes, solución de problemas. |
| [Analytics](./ANALYTICS.md) | Playout History (qué salió realmente al aire, registros exportables), History Templates, Listener Stats (audiencia por flujo y por programa a lo largo del tiempo). |
| [Máquina local](./LOCAL_MACHINE.md) | Salida de tarjeta de sonido, entrada line-in, formato de importación (sin pérdida a MP3), carpeta de importación local. |
| [Copia de seguridad](./BACKUP.md) | Copias de la base de datos + configuración con un clic en una carpeta elegida; descarga; el procedimiento de restauración documentado. |
| [Widgets públicos integrables](./WIDGETS.md) | Widgets listos-para-usar para el sitio web público de su emisora (Now Playing — Show / Track, Weekly Program, Player). |

### Administración

| Capítulo | Contenido |
|---|---|
| [Usuarios y roles](./USERS_AND_ROLES.md) | Admin, Program Manager, DJ, Invitado — qué puede hacer cada rol. |
| [Configuración](./SETTINGS.md) | Recorrido de cada página bajo el menú Configuración. |
| [Idiomas (i18n)](./I18N.md) | Cambiar el idioma de la interfaz; añadir una traducción. |

---

## Cuando algo no funciona

Este manual cubre el **camino feliz normal**. Cuando algo
no se comporta como el manual lo describe, los
procedimientos de recuperación viven en otro lugar:

* [`docs/operator/DEVICE_MISSING.md`](../../operator/DEVICE_MISSING.md)
  — Una tarjeta de sonido o line-in configurado ya no está
  enchufado.
* [`docs/operator/LINE_IN_BROKEN.md`](../../operator/LINE_IN_BROKEN.md)
  — Line-in presente pero produce silencio o ruido.
* [`docs/operator/CRASH_RECOVERY.md`](../../operator/CRASH_RECOVERY.md)
  — Un servicio ha caído; orden de reinicio.
* [`docs/operator/RESTART_ORDER.md`](../../operator/RESTART_ORDER.md)
  — Arrancar en frío toda la pila en el orden correcto.
* [`docs/operator/BACKUP.md`](../../operator/BACKUP.md)
  — Hacer, verificar y restaurar una copia de seguridad.
* [`docs/operator/UPGRADE.md`](../../operator/UPGRADE.md)
  — Actualizar a una nueva versión de RASTATIME.

Estos runbooks están actualmente disponibles solo en
inglés.

---

## A dónde ir después

* Si acaba de **instalar** RASTATIME y quiere poner una
  emisora al aire por primera vez, comience con
  [Primeros pasos](./GETTING_STARTED.md), luego
  [Calendario](./CALENDAR.md), luego [Streams](./STREAMS.md).

* Si está **migrando desde LibreTime / Airtime**, las
  diferencias dignas de conocer primero son:
  [Grabación por programa](./RECORD_PER_SHOW.md) (ahora
  captura toda la salida al aire, no solo el line-in),
  [Auto DJ](./AUTO_DJ.md) (nuevo en RASTATIME), y
  [Máquina local](./LOCAL_MACHINE.md) (reemplaza la
  antigua página "Soundcard").

* Si necesita **instalar RASTATIME** desde cero, este
  manual no es el documento correcto — vea
  [`docs/operator/INSTALL.md`](../../operator/INSTALL.md).

* Si necesita **entender por qué** una característica está
  diseñada como está, cada sección aquí remite al capítulo
  correspondiente en
  [ARCHITECTURE](../../../RASTATIME_ARCHITECTURE_DRAFT_v0.1.md).

---

## Glosario

| Término | Significado |
|---|---|
| **Show / Programa** | Un slot en el calendario con inicio, fin, nombre y (normalmente) contenido programado. Persistido en `cc_show` + `cc_show_instances`. |
| **Instancia** | Una ocurrencia concreta de un programa. Un programa diario es una fila `cc_show` + muchas filas `cc_show_instances`. |
| **Schedule item** | Una fila dentro del planning de una instancia de programa — típicamente un archivo, pero también un smart block, webstream o line-in. Persistido en `cc_schedule`. |
| **Playlist** | Una lista ordenada reutilizable de items. Persistida en `cc_playlist` + `cc_playlistcontents`. |
| **Smart Block** | Una consulta dentro de una playlist que se expande en un conjunto de pistas en el momento de build, opcionalmente limitada a "tiempo restante en el programa". Persistido en `cc_block`. |
| **Webstream** | Una URL apuntando a otra fuente Icecast / Shoutcast / HTTP MP3/AAC. Persistido en `cc_webstream`. |
| **Line-In** | Una entrada de audio en vivo nombrada en la máquina del operador (un micrófono, un mezclador, un reproductor CD externo). Persistido en `rastatime_linein`. |
| **Autoloading playlist** | Una playlist adjunta a una *definición de programa* para que cada instancia del programa tenga los contenidos de la playlist construidos en su planning automáticamente. |
| **Auto DJ** | Un proceso en segundo plano que crea programas en huecos del calendario y completa programas incompletos. Distinto de autoloading playlists. |
| **Inicio diferido** | Un opt-in por programa (`cc_show.allow_delayed_start`) que permite a un programa empezar más tarde que su slot del calendario cuando el programa precedente se sobrepasó, manteniendo su propio fin fijo. Una tarea en segundo plano lo aplica unos minutos antes del aire. |
| **Song request (petición de canción)** | Un deseo de pista enviado por un oyente, recogido por un widget público y emitido automáticamente por un request show (un programa con autoloading playlist y un Smart Block *Use requests*). Persistido en `rastatime_song_request`. |
| **Alerta de tráfico (Traffic Alert)** | Un MP3 de boletín de tráfico que llega de último momento y debe sonar en el programa en curso en unos ~10 minutos. La fuente es un smart block elegido en los ajustes (`traffic_alert_block_id`); un programa con ese bloque en su Autoloading Playlist se llena de forma incremental y reproduce la alerta más antigua aún no planificada en el siguiente espacio de tráfico. |
| **Stream de salida** | Uno de hasta cuatro mountpoints Icecast a los que el playout transmite. Configurado bajo Configuración → Streams. |
| **Source switcher** | El mecanismo interno que decide qué fuente de audio (scheduler, line-in, master DJ, show DJ) está actualmente al aire. |
| **Cola de fallback** | Un bucle configurado que se reproduce cuando ningún programa está planificado y Auto DJ está deshabilitado. |
| **Carpeta de importación local** | Un directorio en la máquina del operador que el analyzer vigila para nuevos archivos; todo lo que se suelta aquí se auto-importa a la biblioteca. |

---

*Este documento está versionado en el repositorio RASTATIME.
Vea el [CHANGELOG](../../../CHANGELOG.md) para qué cambió
en el manual mismo; vea los sub-documentos por capítulo
para qué cambió en cada característica.*
