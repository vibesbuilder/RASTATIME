# Configuración

> **Dónde está usted en el manual.** Este capítulo es el índice del menú
> Ajustes.  Documenta directamente las páginas *General* y *Estado* y
> remite al capítulo dedicado de cada otra página.  Revisado frente a la
> interfaz el 25/10/2026.

El menú Ajustes es la superficie de configuración de la emisora.  La
mayoría de las páginas pertenecen a los **Admins**;
un **Program Manager** ve *Mi Perfil*, *Show Templates* y *Auto DJ*; los
invitados y los DJ solo ven *Mi Perfil*.  Vea
[Usuarios y roles](./USERS_AND_ROLES.md) §2 para la matriz completa de
permisos.

---

## 1. El menú Ajustes

Navegación izquierda → **Ajustes** abre el submenú:

| Página | Para qué | Quién | Capítulo |
|---|---|---|---|
| **General** | Nombre y descripción de la emisora, idioma, inicio de semana, API pública, página de radio, logo, fondo de la página de inicio, favicon, color principal, crossfades, tipo de pista de las subidas, listas de automatización, Live Text Info, TuneIn, Dangerous Options. | Admin | Este capítulo §2 |
| **Mi Perfil** | Su nombre, correo, contraseña, idioma de la interfaz y zona horaria. | todos | [Usuarios y roles](./USERS_AND_ROLES.md) §4 |
| **Usuarios** | Crear, editar y eliminar usuarios y definir su tipo. | Admin | [Usuarios y roles](./USERS_AND_ROLES.md) §3 |
| **Tipos de pista** | Tipos de pista con sus ajustes previos de crossfade, crossover y metadatos del stream. | Admin | [Biblioteca](./LIBRARY.md) |
| **Show Templates** | Resumen de las plantillas de programa guardadas: renombrar, eliminar. | Program Manager, Admin | [Plantillas de programa](./SHOW_TEMPLATES.md) |
| **Auto DJ** | Relleno de huecos y completado de programas incompletos. | Program Manager, Admin | [Auto DJ](./AUTO_DJ.md) |
| **Streams** | Streams de salida (bitrate, punto de montaje, códec), entradas para conexiones en directo, credencial Master. | Admin | [Streams](./STREAMS.md) |
| **Máquina local** | Tarjeta de sonido, carpeta y formato de importación, carpeta y formato de grabación, ubicación de la biblioteca. | Admin | [Máquina local](./LOCAL_MACHINE.md) |
| **Importar / Exportar** | Usuarios, programas, listas, bloques inteligentes, webstreams y suscripciones a podcasts como archivos CSV/JSON, con vista previa al importar. | Admin | [Importar / Exportar](./IMPORT_EXPORT.md) |
| **Backup** | Copias de seguridad de la base de datos y la configuración, el espejo de medios, copias automáticas, restauración. | Admin | [Backup](./BACKUP.md) |
| **Estado** | Estado de los servicios, espacio en disco, reinicios de servicios, direcciones permitidas y bloqueadas. | Admin | Este capítulo §3 |

Las fuentes Line-In se gestionan en **Panel → Line Inputs** (vea
[Line-In](./LINE_IN.md)); los idiomas de la interfaz se tratan en
[Idiomas](./I18N.md).

---

## 2. General

Ajustes → **General**.

La página está dividida en **secciones plegadas** (desde el 08/10/2026):
el nombre y la descripción de la emisora quedan arriba, debajo
*Station*, *Styling*, *Playout* y *Automation*, después *Live Text
Info*, *TuneIn Settings* y *Dangerous Options*.  Un clic en un título
abre la sección; una sección con un error de validación tras **Guardar**
se abre sola.

### Arriba de la página

| Campo | Notas |
|---|---|
| **Nombre de emisora** | Visible en todas partes - título de página, metadatos del stream, página de radio. |
| **Descripción de emisora** | Texto libre, usado en los feeds de podcast y en la página de radio. |

### Station

| Campo | Notas |
|---|---|
| **Idioma por defecto** | Idioma de la interfaz para usuarios nuevos y la pantalla de inicio de sesión, e idioma de todos los widgets (fechas, días de la semana, botones; desde el 25/10/2026). Cada usuario conserva su propio idioma de Mi Perfil. |
| **Zona horaria de la emisora** | Solo se muestra como información.  La zona horaria de la emisora se fija en `config/libretime.conf` (`general.timezone`); cada usuario puede elegir una zona horaria de visualización en Mi Perfil. |
| **La semana comienza el** | Primer día de la semana en el calendario y en los widgets (Weekly Schedule, Multi-View Schedule). |
| **Public RASTATIME API** | *Enabled* permite que widgets integrados en otros sitios web lean los datos de la parrilla. Necesario para los widgets de parrilla integrables. |
| **¿Mostrar el botón de inicio de sesión en la página de radio?** | Muestra un botón de inicio de sesión en la página de radio pública. |
| **¿Desactivar la página de radio pública y redirigir al inicio de sesión?** | Quien visita la dirección de la emisora llega directamente al inicio de sesión. |

### Styling

| Campo | Notas |
|---|---|
| **Logo de emisora** | Imagen arriba a la izquierda de cada página. Hasta 1 MB, JPG / PNG / GIF / WebP; **Quitar** lo elimina. |
| **Imagen de fondo de la página de inicio** | La foto detrás de la página de inicio pública (`/`). JPG, PNG o WebP hasta 5 MB; recomendado 1920 px de ancho y 1 MB o menos. Guardada como archivo bajo `landing/` en la ubicación de la mediateca (el espejo de copia nocturno la incluye); **Quitar** vuelve a la imagen integrada. Surte efecto en la siguiente carga de la página de inicio (el navegador guarda la imagen una semana, una nueva subida recibe una nueva dirección). Desde 2026-10-07. |
| **Favicon de emisora** | Imagen en la pestaña del navegador. Hasta 200 KB, PNG / JPG / GIF / ICO. Renderizado como URI data:. |
| **Color principal** | El color de acento de toda la interfaz, la página de radio y los widgets — enlaces, resaltados, filas seleccionadas, la entrada de menú activa, barras de progreso y de almacenamiento, barras de desplazamiento, flechas de sección, el botón de reproducción y el volumen del reproductor, pestañas, botones y resaltados de los widgets, el gráfico de la página de error. Introduzca `#rrggbb` o use el selector junto al campo; **Restablecer el valor predeterminado** recupera el naranja (`#ff5d1a`). Surte efecto en la siguiente carga de página. Elija un color que destaque sobre el fondo gris oscuro; el texto sobre él cambia solo entre blanco y negro. Los colores de señalización (errores, avisos, los colores de los programas en el calendario) y la barra de llenado de los programas en el calendario (siempre naranja) no cambian. |

### Playout

| Campo | Notas |
|---|---|
| **Default Track Crossfade Duration (s)** | El crossfade entre dos pistas consecutivas **del mismo programa**: la pista saliente se desvanece mientras la entrante sube durante estos segundos (1 segundo es típico; 0 = las pistas se siguen sin solapamiento; hasta 10 segundos para transiciones suaves). La parrilla coloca las filas consecutivas con exactamente este solapamiento. |
| **Default Show Crossfade Duration (s)** | La transición **en el límite de un programa** (desde el 2026-09-27): el programa anterior se desvanece durante estos segundos mientras la primera pista del nuevo empieza de inmediato a volumen completo — un programa que abre con un jingle o una identificación se oye desde su primer golpe. La misma forma y el mismo valor rigen cada cambio entre **entradas** (pista ↔ webstream ↔ Line-In): la fuente entrante está a volumen completo al instante, la saliente se desvanece por debajo; 0 = cambio seco. Un webstream o Line-In programado en ambos programas sigue sonando sin corte. Valor inicial 1 s. La cadena de audio aplica ambos valores unos segundos después de guardar (reinicio planificado en un momento tranquilo o en un límite de pista); «Aplicar ahora» en Ajustes → Máquina local lo fuerza. |
| *Crossfade por tipo de pista* | Ajustes → Tipos de pista → *Crossfade Duration (s)* (desde el 2026-09-29) sustituye el valor por defecto para todas las pistas de ese tipo; vacío = valor por defecto. Entre dos pistas se aplica el **menor** de los dos valores: un tipo con 0 siempre se une a tope - el tipo *Jingles* incluido empieza con 0, porque los elementos cortos, ajustados al segundo, no deben acortarse con un crossfade de duración musical. En un cambio entre una pista y un flujo web o Line-In se aplica el menor entre el valor de la pista y la Default Show Crossfade Duration. Un cambio de los valores por defecto o de un tipo de pista recalcula automáticamente las filas de todos los programas futuros; las filas ya iniciadas nunca se tocan. |
| *Sin fundido por tipo de pista* | Ajustes → Tipos de pista → *No Fade during Crossover* (desde 2026-09-30) es el preajuste del tipo para el campo *Crossover* del editor de pista: cada pista del tipo ajustada a *As the track type* conserva su nivel completo mientras la pista vecina se funde de entrada o de salida - el solapamiento se mantiene tal como indica la duración de crossfade del tipo. Pensado para jingles o IDs que deben cortar sobre el final de una canción. Una pista concreta puede seguir ajustándose de otra forma en el editor de pista; una pista excluida del crossover no tiene solapamiento en el que mantener su nivel. Un cambio llega al playout con el siguiente envío de la programación; no se vuelven a maquetar filas porque el solapamiento no cambia. |
| *Enviar metadatos por tipo de pista* | Ajustes → Tipos de pista → *Forward Metadata to the Stream* (desde 2026-10-14) es el ajuste previo del tipo para el campo *Metadatos del stream* del editor de pista: sin marcar, cada pista del tipo con *Como el tipo de pista* suena sin artista / título en el stream y los reproductores muestran «Nombre de la emisora - Nombre del programa» (jingles, identificaciones, promos). Una pista puede anularlo en su editor. |
| **Track Type Upload Default** | El tipo de pista asignado a las subidas nuevas que no fijan uno. Influye en los filtros de bloques inteligentes. |
| **Trim overbooked shows after autoloading?** | Recorta el contenido de un programa llenado por autoloading que dura más que el programa. |
| *Propietario de las importaciones* | No hay ajuste: los archivos que recoge el escaneo en segundo plano de la carpeta de importación local pertenecen a la primera cuenta de administrador (`admin`); los importados con **Scan Now**, al operador que hizo clic. |

### Automation

| Campo | Notas | Capítulo |
|---|---|---|
| **Intro / Outro Autoloading Playlist** | Suena al principio / al final de cada programa con autoloading. | [Listas de autoloading](./AUTOLOADING_PLAYLISTS.md) |
| **Song-Request Pool (smart blocks)** | Los bloques inteligentes cuyas pistas pueden pedir los oyentes. | [Peticiones de canciones](./SONG_REQUESTS.md) |
| **Traffic-Alert Smart Block** | El bloque para avisos de tráfico. | [Avisos de tráfico](./TRAFFIC_ALERTS.md) |
| **Show-Shift Filler Playlist** | Rellena el hueco cuando se desplaza un programa. | [Inicio retrasado](./DELAYED_START.md) |
| **Overwrite Podcast Episode Metatags** | Fija artista, título y álbum de los episodios descargados a partir del feed del podcast. | [Biblioteca](./LIBRARY.md) |
| **Generate a smartblock and a playlist upon creation of a new podcast** | Crea un bloque inteligente y una lista correspondientes para cada nueva suscripción a un podcast. | [Biblioteca](./LIBRARY.md) |

### Live Text Info

Sección plegable bajo las Preferencias generales (desde el 2026-09-28). La
línea «now playing» como archivo de texto para otros sistemas (web,
pantallas, agregadores): una línea UTF-8, siempre reemplazada, escrita por
el playout en cada cambio de pista, webstream, entrada de línea o DJ.

| Campo | Notas |
|---|---|
| **¿Escribir la línea «now playing» en un archivo de texto?** | Interruptor principal. |
| **Formato del texto en vivo** | Las mismas tres variantes que el Stream Label (Artist - Title / Show - Artist - Title / Station name - Show name) con los mismos respaldos: una fuente en vivo sin intérprete ni título muestra *Station name - Show name*, el silencio muestra el texto Off Air. Independiente del Stream Label. |
| **Publicar en la web** | El archivo se sirve en `http://<host>/live/now-playing.txt` (archivo estático, sin inicio de sesión, independiente del interruptor Public API). Accesible desde Internet en cuanto lo sea el servidor web, como los widgets. |
| **Escribir también en un archivo** | Ruta absoluta opcional (este equipo o un recurso compartido de red). |
| **Subir a un servidor FTP** | En cada cambio el archivo se sube por FTP, FTPS (TLS explícito) o SFTP a la ruta remota; credenciales propias, separadas de la importación FTP. SFTP necesita un `curl` con libssh2 (el que trae Git para Windows; el curl integrado de Windows no puede). Los fallos se registran; el siguiente cambio lo reintenta. |

La línea la construye el motor de audio a partir de los metadatos que
realmente envía al stream, incluidos títulos de DJ y de webstream. Un
ajuste modificado se aplica en el siguiente cambio, sin reinicio.

### TuneIn Settings

Sección plegable bajo las Preferencias generales. Desde el 2026-09-28 el
playout envía por sí mismo la información «now playing» a TuneIn; antes
solo se notificaban los inicios de archivo y la visualización
desaparecía a los cinco minutos.

| Campo | Notas |
|---|---|
| **Push metadata to your station on TuneIn?** (enviar metadatos a TuneIn) | Interruptor principal. Activado, el playout envía título e intérprete en cada inicio de pista, el nombre del programa al iniciar un webstream o una entrada de línea, y repite la última actualización cada cuatro minutos (TuneIn borra una visualización que lleva cinco minutos en silencio). Guardar con el interruptor activado comprueba las credenciales con TuneIn y rechaza las no válidas. |
| **Station ID**, **Partner Id**, **Partner Key** | De su cuenta de socio de TuneIn (AIR API). La clave no aparece en ningún registro. |

Un ajuste modificado se aplica en el siguiente envío; sin reinicio. Un DJ
en directo (Master / Show Source) no se anuncia; la última pista permanece
en la visualización hasta el siguiente elemento programado.

### Dangerous Options

Plegadas por defecto; ambos botones piden confirmación y son solo para
administradores.

| Botón | Efecto |
|---|---|
| **Delete All Tracks in Library** | Elimina cada pista de la biblioteca y de las parrillas futuras (upstream). |
| **Clear Calendar** (desde 2026-10-14) | Elimina cada programa que **aún no ha empezado**, con su contenido, y termina todas las repeticiones. El programa en antena y todo el pasado se conservan, el historial de emisión mantiene sus nombres de programa. Un programa sin instancias restantes se borra. La confirmación indica cuántas instancias y programas se retiraron. |

> **Bajo el capó.** Los valores son filas de la tabla `cc_pref`
> (clave / valor).  Los valores por usuario (idioma, zona horaria,
> diseños de tabla) son filas `cc_pref` ligadas al usuario.  La
> configuración de servicio que no puede vivir en la base de datos
> (acceso a la base, rutas, zona horaria de la emisora, clave API) está
> en `config/libretime.conf`.

---

## 3. Estado

Ajustes → **Estado**.  De arriba abajo:

| Sección | Contenido |
|---|---|
| **RASTATIME Version** | La versión instalada. |
| **Componentes** | Bibliotecas PDO y PostgreSQL, configuración de la base de datos y de RabbitMQ, y los servicios de Windows RASTATIME-PLAYOUT, -WORKER, -API, -ANALYZER, -ICECAST y -APACHE con su estado. Un servicio mostrado como detenido es la señal para revisarlo (`Get-Service RASTATIME-*` en PowerShell, o el runbook [`CRASH_RECOVERY`](../../operator/CRASH_RECOVERY.md)). |
| **Espacio en disco** | Espacio libre y usado del almacenamiento. |
| **Reinicios de servicios** | Un botón **Restart** por servicio (Analyzer, API, Apache, Icecast, Playout, Worker), con lo que hace el servicio y cuándo ayuda un reinicio, más **Restart All Services** (la interfaz no está accesible unos 10 segundos). |
| **Direcciones permitidas** | Direcciones y redes que ningún freno de inicio de sesión bloquea nunca. |
| **Direcciones bloqueadas** | Cada dirección o usuario bloqueado ahora por nivel (inicio de sesión web, conexión de DJ, cortafuegos) con **Unblock** y **Allow**. |

Las dos listas de direcciones se describen en
[Usuarios y roles](./USERS_AND_ROLES.md) §8.

Lo que cuesta un reinicio:

| Servicio | Efecto de un reinicio |
|---|---|
| **Playout** | El controlador de la parrilla se reinicia; no durante un programa en directo.  El motor de audio (Liquidsoap) es un servicio propio (RASTATIME-LIQUIDSOAP) y sigue reproduciendo lo que tiene en cola. |
| **Icecast** | Se desconectan todos los oyentes y todas las fuentes; las salidas se reconectan en segundos, los oyentes tienen que volver a conectarse. Solo en una ventana tranquila. |
| **Apache** | La interfaz web no está accesible unos segundos. |
| **API**, **Worker**, **Analyzer** | El trabajo en segundo plano se detiene brevemente; sin efecto en el stream. |

> **Consejo de operador.** Reinicie solo el servicio que falla.  La
> secuencia completa está en
> [`RESTART_ORDER`](../../operator/RESTART_ORDER.md).

Los **avisos preflight** no son una sección de esta página: aparecen
como banner en cada página.  Un ejemplo: **fallo de descarga de
podcast** (desde el 08/10/2026) - cuando falla una descarga de episodio
automática o manual, un aviso nombra el podcast, el episodio, el número
de intentos, el último intento y el motivo (código HTTP o «API
unreachable»).  Desaparece solo cuando la descarga funciona más tarde o
se elimina el podcast.  Revise el feed y la dirección de descarga del
episodio en Biblioteca → Podcasts.

---

## 4. Preguntas frecuentes

### «Cambié un ajuste pero no pasa nada.»

La mayoría de los ajustes surten efecto de inmediato o con la siguiente
carga de página.  Excepciones:

| Ajuste | Surte efecto |
|---|---|
| Crossfades, streams, tarjeta de sonido | Cuando la cadena de audio se reinicia - planificado automáticamente en un momento tranquilo; **Aplicar ahora** en Ajustes → Máquina local lo fuerza. |
| Color principal, logo, favicon | Con la siguiente carga de página (F5). |
| Su propio idioma | Con la siguiente carga de página; la pantalla de inicio de sesión usa el idioma por defecto. |
| Live Text Info, TuneIn | En el siguiente cambio de pista o de fuente. |

### «¿Hay un menú de herramientas, un visor de registros o una consola de base de datos?»

No.  Los scripts de mantenimiento están en la máquina de la emisora en
`infra\scripts` (por ejemplo
`infra\scripts\maintenance\rescan-playability.py`) y se describen en la
documentación del operador.  Los registros están en
`C:\RASTATIME\logs`.

### «¿Cómo hago copia o restauro los ajustes?»

Ajustes → **Backup** guarda la base de datos (con cada fila `cc_pref`) y
la configuración; para restaurar vea [Backup](./BACKUP.md).
`config/libretime.conf` contiene contraseñas - nunca lo ponga tal cual
en un control de versiones.

### «¿Qué configuraciones puede abrir un Program Manager?»

*Mi Perfil*, *Show Templates* y *Auto DJ*.  Todo lo demás en Ajustes
pertenece a los Admins.  Vea [Usuarios y roles](./USERS_AND_ROLES.md) §1-§2.

---

## 5. Motor de playout (Liquidsoap)

> **Configuración a nivel de servicio**, no una configuración UI.  El
> servicio NSSM RASTATIME-PLAYOUT puede llevar
> `RASTATIME_PLAYOUT_ENGINE=liquidsoap` en su entorno; es el único valor
> aceptado.  Solo operador; no expuesto en la UI web.

Desde el 2026-09-10 Liquidsoap es el **único** motor de playout.  El
motor mpv anterior (con sus streamers FFmpeg para las salidas Icecast)
y el plan VLC nunca terminado se eliminaron del código después de que
Liquidsoap llevara en producción cada tipo de elemento de la parrilla
(archivos, webstreams, entradas de línea, grabación, fuentes DJ) desde
el 2026-05-28.

Lo que Liquidsoap provee:

- **Grabación** capturada desde el bus de audio interno (post-switch,
  post-crossfade, post-amplify) — bit-idéntica a lo que escuchan los
  oyentes.  Formato y bitrate siguen Ajustes → Máquina local → Show
  Recording (por defecto MP3 320 kbps).
- **Experiencia del oyente**: los puntos de montaje Icecast permanecen
  abiertos a través de cambios de pista/programa — sin reconexión, sin
  reinicio de contadores.
- **Enrutamiento de fuentes DJ** nativo vía `input.harbor` +
  `switch(...)` de Liquidsoap — los clientes DJ Master / Show se
  conectan directamente al harbor gestionado por Liquidsoap (puerto 8001
  por defecto, vea [Streams](./STREAMS.md)).

**Si el servicio se niega a arrancar** con

```
CRITICAL __main__: RASTATIME_PLAYOUT_ENGINE='mpv' is not supported - Liquidsoap is the only playout engine since 2026-09-10 ...
```

el entorno del servicio aún nombra el motor eliminado: establezca
`RASTATIME_PLAYOUT_ENGINE=liquidsoap` (o elimine la variable) en el
entorno NSSM de `RASTATIME-PLAYOUT` y arranque el servicio de nuevo.
`RASTATIME_MPV_PATH` / `RASTATIME_MPV_LOG_LEVEL` se ignoran y pueden
eliminarse.

**El arranque del motor es visible en el log de playout:**

```
INFO __main__: Playout engine: Liquidsoap (telnet target 127.0.0.1:1234).
```

---

## A dónde ir después

* Siga el enlace de la tabla del §1 al capítulo dedicado de una página
  de Ajustes.
* [Usuarios y roles](./USERS_AND_ROLES.md) — quién puede abrir qué
  página.
* [`docs/operator/INSTALL.md`](../../operator/INSTALL.md) — los ajustes
  hechos durante la instalación.
