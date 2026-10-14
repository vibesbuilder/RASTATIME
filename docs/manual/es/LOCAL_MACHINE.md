# Máquina local

> **Dónde está usted en el manual.** Este capítulo cubre
> la página Configuración → **Máquina local**, que posee
> cada aspecto vinculado a la *máquina del operador
> misma* — salida de tarjeta de sonido, dispositivos de
> entrada line-in, formato de importación y carpeta de
> importación local. Para los
> streams salientes del lado de red, vea
> [Streams](./STREAMS.md). Para el tipo de item de
> biblioteca que *referencia* una entrada de tarjeta de
> sonido, vea [Line-In](./LINE_IN.md).

La página **Máquina local** es donde informa a RASTATIME
sobre los recursos físicos en la máquina del operador:
qué salida de altavoz reproducir, qué dispositivos cuentan
como candidatos line-in, en qué formato entran los archivos
sin pérdida en la biblioteca, y qué carpeta el analyzer debe
vigilar para pistas importadas.

La página reemplaza la página "Soundcard" del LibreTime
original y añade la función carpeta de importación. La URL
legacy todavía funciona; solo el título de la página y el
slug cambian.

---

## 1. La página

Configuración → **Máquina local**.

Secciones independientes: Tarjeta de sonido (salida +
entrada), Formato de importación, Carpeta de importación local,
y después importación FTP, ubicación de la biblioteca de medios y
carpetas de grabación.

---

## 2. Tarjeta de sonido — Dispositivos de salida

La lista muestra cada dispositivo de salida de audio que
la máquina del operador expone.

### Salida por defecto (el "monitor")

El dispositivo seleccionado es la salida **monitor /
cue**:

- El botón **Escuchar** del Panel reproduce sobre él.
- El botón **Vista previa** de la Biblioteca reproduce
  sobre él.
- La vista previa del show-builder también reproduce
  sobre él.

> **Lo que NO es.** La salida por defecto *no* es el
> stream público. Los oyentes no oyen lo que se reproduce
> aquí.

### Por qué elegir un dispositivo específico

- **Emisoras de operador único** con un solo conjunto de
  altavoces — deje por defecto.
- **Emisoras de dos monitores** con un altavoz "air-check"
  y un altavoz "interno" — elija aquí el altavoz interno.
- **Emisoras solo-auriculares** — elija el dispositivo de
  auriculares.

### Pseudo-dispositivo "(Por defecto del sistema)"

La primera entrada es siempre **(Por defecto del
sistema)**. Esto sigue lo que el sistema Windows / Linux
ha marcado como salida de audio por defecto.

> **Cómo funciona bajo el capó.** Los dispositivos se
> enumeran vía `audio.soundcard.windows_manager` (WASAPI
> en Windows, portaudio en Linux). El dispositivo
> seleccionado se persiste en `cc_pref` como
> `default_output_device_id`. Vea ARCHITECTURE §9.

### Aplicar un cambio — «Aplicar ahora»

> **Desde el 16/09/2026 esto ocurre por sí solo.** Tras guardar, la
> reproducción detecta el dispositivo cambiado en su siguiente
> actualización de la programación (en menos de dos minutos) y reinicia
> la cadena de audio en el siguiente momento tranquilo, o, con una
> programación 24/7, entre dos pistas de archivo. Los oyentes siguen
> conectados a través de los montajes de reserva. Lo mismo vale para la
> grabación 24/7, las duraciones de crossfade (pistas y programas) y las
> salidas de emisión.
> **Aplicar ahora** sigue siendo la forma de forzarlo de inmediato.

Guardar almacena el dispositivo; **todavía no** mueve el
monitor local. El motor de emisión compila el dispositivo
elegido en su script de Liquidsoap al arrancar el servicio, y
Liquidsoap lee ese script solo en su *propio* arranque.
Aplicar un cambio requiere por tanto reiniciar ambos
servicios, en ese orden.

En lugar de reiniciar en silencio al guardar — lo que cortaría
la emisión pública sin avisar — la página ofrece un botón
deliberado bajo el selector:

**Aplicar ahora (reinicia la cadena de audio)** — reinicia
RASTATIME-PLAYOUT (que regenera el script con el nuevo
dispositivo) y después RASTATIME-LIQUIDSOAP (que lo carga).

Encima del botón, la página indica **qué salida está impulsando
realmente el monitor**, leída del script de Liquidsoap generado y no
del ajuste guardado. Si ambos difieren — el cambio aún no se ha
aplicado, o el dispositivo no pudo abrirse — la línea lo señala en
ámbar. Un valor guardado no prueba que esté en uso.


> **Impacto en antena.** El segundo reinicio corta las
> conexiones de fuente de Icecast durante unos segundos; los
> oyentes perciben un breve silencio. Hágalo entre programas.
> El botón pide confirmación.

> **Cómo se identifica el dispositivo.** PortAudio enumera el
> mismo punto final una vez por API anfitriona de Windows (MME,
> DirectSound, WASAPI, WDM-KS), y cuál de esas copias funciona
> realmente depende del dispositivo. Por eso RASTATIME prueba los
> candidatos al arrancar — mediante la API **bloqueante** de
> PortAudio, la que usa el propio Liquidsoap — y toma el primero
> que se abre de verdad. Medido a 44,1 kHz en la máquina del
> estudio: MME y DirectSound funcionan con unos auriculares USB;
> WASAPI funciona cuando el formato de Windows del punto final
> coincide (véase la nota siguiente), y WDM-KS no admite la API
> bloqueante en absoluto. Si ningún candidato se
> abre, RASTATIME mantiene el punto final por defecto del sistema
> y registra cada motivo de fallo en el registro de emisión.

> **El dispositivo se escribe en el script por su nombre, no por
> su número.** PortAudio numera sus dispositivos en el orden de
> enumeración, y en una máquina donde los puntos finales aparecen
> tarde tras un reinicio o van y vienen (auriculares USB, audio
> HDMI), esos números se desplazan. Desde el 2026-09-05 el script
> nombra por tanto el punto final (`device_name="…"`); Liquidsoap
> busca el nombre cuando *él* arranca, de modo que un número que
> cambió entre los dos arranques de servicio ya no puede enviar el
> monitor a la toma equivocada. El nombre solo se usa cuando la
> entrada que selecciona se sabe que reproduce (MME o WASAPI,
> abierta en la misma prueba de arriba); si no, RASTATIME vuelve al
> número y lo explica en el registro de emisión. La línea «activo»
> de arriba muestra cuál está en uso.

> **El formato de Windows del dispositivo debe ser 44,1 kHz.**
> Liquidsoap funciona a 44,1 kHz, y WASAPI en modo compartido exige
> exactamente la frecuencia de mezcla configurada del punto final. Un
> dispositivo cuyo formato predeterminado de Windows está en 48 kHz es
> rechazado por todas las API anfitrionas y parece muerto — medido en
> el Tascam US-16x08, inutilizable hasta que su formato se puso en
> 44,1 kHz (Configuración de sonido → la salida → Avanzado → formato
> predeterminado). El registro de emisión señala esta corrección al
> ver una frecuencia rechazada. Una reinstalación del controlador puede
> restablecer el formato; la línea «activa» de arriba muestra entonces
> la discrepancia. Salida y captura Line-In en la misma interfaz
> funcionan a la vez.

### Reinicios automáticos y avisos de salud

Dos situaciones reinician el motor de audio sin el botón, y tres
avisos del panel lo vigilan (desde el 2026-09-05; la salvaguarda y
el tercer aviso desde el 2026-09-07):

- **Tras un reinicio de la máquina.** Ambos servicios arrancan en
  paralelo, y el motor puede cargar el script anterior antes de que
  la emisión haya generado el nuevo. Si la emisión detecta que su
  generación cambió el script en los primeros diez minutos tras el
  arranque, reinicia ella misma RASTATIME-LIQUIDSOAP. Tan pronto no
  hay nada en antena. Los cambios posteriores siguen necesitando el
  botón o el orden manual: primero la emisión, luego Liquidsoap.
- **Reinicio planificado.** La versión de Windows de Liquidsoap
  pierde memoria lentamente mientras funciona, así que la emisión lo
  reinicia a propósito. Cuándo: dentro de una ventana que se abre a
  las 04:00 (ajuste de máquina `RASTATIME_LIQUIDSOAP_NIGHTLY_RESTART`,
  `HH:MM` u `off`) en cuanto el motor tiene más de N días
  (`RASTATIME_LIQUIDSOAP_RESTART_EVERY_DAYS`, 1 por defecto, `0` =
  desactivado) u ocupa más de `RASTATIME_LIQUIDSOAP_RESTART_AT_MB`
  (1536 por defecto); y a cualquier hora por encima de
  `RASTATIME_LIQUIDSOAP_RESTART_HARD_MB` (3072 por defecto). Cómo
  (desde el 2026-09-09): en un momento tranquilo sin nada en antena o,
  con programa 24/7, entre dos pistas de la lista en curso, de modo
  que el hueco de unos dos segundos sustituye a un fundido en lugar de
  cortar una pista. Un webstream o line-in a cualquiera de los lados
  del límite hace esperar al siguiente. Desde el 2026-10-02 la pista que
  sigue al reinicio entra en su audio los pocos segundos que duró el
  reinicio, para que el programa conserve sus horarios en lugar de
  terminar con ese retraso. Desde el 2026-09-09 las
  fuentes DJ comunican ellas mismas sus conexiones y desconexiones,
  así que la emisión ya no consulta al motor cada cinco segundos; esa
  consulta era la causa principal del crecimiento. Si la memoria se
  mantiene estable durante una semana,
  `RASTATIME_LIQUIDSOAP_RESTART_EVERY_DAYS` puede subirse (7 a 30).
- **Respaldo standby para los oyentes.** Un segundo Liquidsoap
  diminuto (servicio RASTATIME-STANDBY, script `standby.liq` generado
  por la emisión con los mismos codificadores) emite silencio en una
  copia `-standby` de cada punto de montaje público, e `icecast.xml`
  señala esa copia como respaldo de cada punto público. Durante los
  dos segundos de un reinicio Icecast traslada a los oyentes al punto
  standby y los devuelve; nadie se desconecta. Instálelo una vez como
  administrador con `backend/playout/config/nssm-install-standby.ps1`
  después de que la emisión haya generado `standby.liq`, y reinicie
  Icecast una vez para que lea los puntos de respaldo. Ajuste
  `RASTATIME_STANDBY_AUDIO` a un archivo de audio si prefiere una cama
  sonora de emisora en lugar de silencio. Si renombra o añade una salida
  de flujo, el lado standby la sigue por sí solo (reinicie
  RASTATIME-STANDBY cuando el registro de la emisión lo pida), pero los
  bloques de respaldo de Icecast no: añada un bloque correspondiente
  para el nuevo punto de montaje en `icecast.xml` y reinicie Icecast. La
  emisión avisa en su registro, en cada arranque, de los puntos públicos
  sin respaldo.
- **Por nombre o nada.** Justo antes de cada reinicio automático la
  emisión vuelve a leer la lista de tarjetas de sonido y direcciona
  el Main Output por el *nombre* del dispositivo. Si en ese momento
  no es posible (la pantalla del estudio duerme y su punto final
  HD-Audio ha desaparecido, el dispositivo fue renombrado, o solo
  coincide una entrada DirectSound/WDM-KS), el reinicio automático
  se omite y el motor en marcha sigue reproduciendo; el registro de
  la emisión indica el motivo. Reinicie manualmente cuando el
  dispositivo vuelva. Antecedente: el 2026-09-06 y el 2026-09-07 el
  reinicio de las 04:01 usó un índice de dispositivo tomado con la
  pantalla dormida; el motor nuevo abrió el punto final equivocado,
  murió a los dos segundos y fue reiniciado en bucle hasta la mañana.
- **Aviso de memoria.** El banner del panel muestra *Liquidsoap usa
  N MB* cuando la memoria del motor supera 2048 MB (ajuste de
  máquina `RASTATIME_LIQUIDSOAP_MEMORY_WARN_MB`). Reinicie la
  emisión y después Liquidsoap en un momento tranquilo. Desde el 15/09/2026 el registro de la emisión anota además cada
  15 minutos la memoria del motor con su crecimiento desde el
  arranque; busque `Liquidsoap memory` en `playout-stdout.log` para
  ver la tendencia.
- **Aviso de Main Output.** El banner muestra *Main Output:
  Liquidsoap reproduce en … en lugar de …* cuando el motor no
  mantiene ninguna sesión de audio en el dispositivo de salida
  elegido aunque lleve un rato funcionando. El monitor está entonces
  en la toma equivocada; reinicie la emisión y después Liquidsoap.
- **El Main Output permanece abierto.** Desde el 14/09/2026 el motor
  abre el Main Output una sola vez al arrancar y ya no lo cierra
  mientras funciona. El pequeño búfer delante del dispositivo se
  vaciaba antes unas dos veces al día; el motor volvía a abrir entonces
  el dispositivo con una lista de dispositivos desactualizada y se
  detenía o reproducía en otro dispositivo. Ahora un breve silencio
  cubre ese momento y el búfer ajusta la velocidad de reproducción de
  forma inaudible para mantenerse lleno. Si alguna vez sospecha de ese
  ajuste, ponga la configuración de la máquina
  `RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT_ADAPTIVE` en `false` y reinicie
  la emisión y después Liquidsoap; la salida sigue abierta con un
  búfer fijo.
- **Aviso de motor parado.** El banner muestra *Liquidsoap no está
  en marcha* o *Liquidsoap se reinicia sin parar (bucle de fallos)*
  cuando no existe ningún proceso del motor o aparece uno nuevo en
  cada exploración. Lea la rebanada más reciente
  `logs/liquidsoap-stdout-*.log` (normalmente el dispositivo
  Main Output), corrija la causa y reinicie la emisión y después
  Liquidsoap.

---

## 3. Tarjeta de sonido — Dispositivos de entrada

La lista muestra cada dispositivo de entrada de audio. La
casilla de verificación controla cuáles son **candidatos**
para uso como Line-Ins nombrados.

### Cuáles habilitar

| Dispositivo | ¿Marcar? | Por qué |
|---|---|---|
| **Micrófono de estudio** | Sí | La razón por la que la mayoría de las emisoras tienen un line-in. |
| **Salida de mezclador** | Sí | El mix de estudio completo como fuente única. |
| **Micrófono incorporado** | Solo si se usa | Desmarcar lo suprime del menú desplegable de creación Line-In. |
| **Micrófono de webcam** | No (normalmente) | Baja calidad, a menudo seleccionado por accidente. |
| **Jack line-in trasero** (si no se usa) | No | Misma prevención de accidente. |

Marcar / desmarcar **no desactiva** el dispositivo a nivel
OS — Windows lo sigue viendo.

### Del dispositivo de entrada al Line-In nombrado

Para usar un dispositivo como fuente de planificación, cree
un Line-In nombrado en la biblioteca bajo **Line Inputs → +
Nuevo** — desde el 17/09/2026 ese diálogo es el único editor
completo (nombre, dispositivo, canales); la
antigua sección Line-In Sources de esta página ya no existe.
Vea [Line-In](./LINE_IN.md).

---

## 4. Salida por defecto para cue / monitor

El menú desplegable bajo la lista de dispositivos de
salida re-expone el por defecto en forma de fila única.

---

## 5. Formato de importación

*(Desde el 2026-10-14.)*  Una casilla: **Convertir el audio sin
pérdida (WAV, FLAC, ...) a MP3 de 320 kbps al importar** —
**activada** por defecto.  Se aplica a todas las vías por las que una
pista entra en la biblioteca: subida del navegador, carpeta de
importación local, importación FTP y el comando de importación masiva.
Pulse el botón **Guardar** de la sección; la siguiente importación
sigue el nuevo valor, no hace falta reiniciar nada.

Lo que hace la importación con cada archivo:

| Audio dentro del archivo | Qué ocurre |
|---|---|
| MP3, MP2, MP1, AAC en M4A / MP4, OGG Vorbis, Opus | Se importa tal cual — nunca se recodifica. |
| AAC en bruto (`.aac`) | Siempre se reempaqueta en un `.m4a`, **sin** recodificar, esté la casilla activada o no. Un archivo AAC en bruto no tiene índice, así que su duración solo puede estimarse (unos 2 s de más en los archivos comprobados), y no puede llevar etiquetas. |
| Sin pérdida: WAV, FLAC, AU, Apple Lossless (ALAC) en M4A | Casilla **activada**: se convierte a MP3 de 320 kbps antes de entrar en la biblioteca; el original sin pérdida **no se conserva**.  Casilla **desactivada**: se importa tal cual. |

- **Cuenta el audio, no la extensión.**  Un `.m4a` con Apple Lossless
  se convierte; un `.wav` con datos MP3 no.
- **Etiquetas y carátula se conservan.**  Título, artista, álbum,
  género, año, número de pista, compositor, copyright, sello, ISRC,
  BPM, idioma, comentario y la fecha **Expiry** se escriben en el MP3,
  y una carátula JPEG o PNG incrustada se mantiene.  El archivo
  conserva su nombre con la nueva extensión (`Interview.wav` pasa a
  ser `Interview.mp3`); un archivo sin etiqueta de título muestra ese
  nuevo nombre como título, como cualquier subida sin etiquetas.
- **Frecuencia de muestreo y canales.**  32, 44,1 y 48 kHz se quedan
  como están; las demás frecuencias (por ejemplo 96 kHz) pasan a
  44,1 kHz.  Más de dos canales se mezclan a estéreo.
- **Medido tras la conversión.**  Duración, puntos de cue, ReplayGain
  y sonoridad se toman del archivo que acaba en la biblioteca.
- **Una conversión fallida nunca cuesta la importación**: entonces se
  importa el archivo original sin cambios.
- La conversión se ejecuta con prioridad baja, para que un lote grande
  no quite potencia de cálculo al playout; una pista convertida
  simplemente aparece un poco más tarde en la biblioteca.
- **Los episodios de podcast no se convierten** — se descargan
  directamente en la biblioteca sin pasar por el análisis de
  importación.

> **Por qué funciona así.**  Los streams tienen pérdida de todos
> modos, y un FLAC o un WAV ocupa entre tres y cuatro veces y media el
> espacio de un MP3 de 320 kbps.  El resto de la biblioteca es MP3, y
> el MP3 lleva la fecha **Expiry** de forma fiable; en un M4A muchas
> herramientas la pierden.  El audio con pérdida (MP3, AAC, Ogg
> Vorbis, Opus) no se toca, porque recodificar un formato con pérdida en
> otro solo cuesta calidad.  Vea ARCHITECTURE §23.57.

> **Pistas importadas antes del 2026-10-14.**  Los archivos sin
> pérdida que ya estaban en la biblioteca los convierte una vez un
> técnico con el comando `convert_lossless` (primero una prueba en
> seco; una pista en antena o programada en las próximas seis horas
> se omite, y no se convierte nada mientras la biblioteca de medios se
> traslada).  La pista conserva su id, su lugar en playlists y
> programas y su Cue In; la sonoridad se mide de nuevo en el MP3.

> **Bajo el capó.**  El ajuste es la clave `cc_pref`
> `convert_lossless_to_mp3` (ausente = activada).  La aplicación web
> la envía con cada mensaje de importación al analyzer
> (`options.convert_lossless`); su paso `convert_format` se ejecuta
> justo después de leer las etiquetas.  Una pista convertida guarda el
> md5 de su original en `cc_files.source_md5`, para que la importación
> masiva siga reconociendo el mismo WAV o FLAC como ya importado.

---

## 6. Carpeta de importación local

La Carpeta de importación local es un directorio en la
máquina del operador que el analyzer vigila para nuevos
archivos. Todo lo que se suelta en la carpeta se importa
automáticamente a la biblioteca en el próximo ciclo de
poll del analyzer (por defecto cada 60 s).

### Configurar la carpeta

| Campo | Notas |
|---|---|
| **Ruta de la carpeta** | Una ruta absoluta en la máquina del operador. Debe existir y ser legible por el servicio RASTATIME-ANALYZER. Por defecto: `C:\rastatime\import\`. Dejar vacío para deshabilitar. |
| **Último escaneo** | Cuándo el analyzer corrió un escaneo por última vez. |

El botón **Escanear ahora** dispara un escaneo inmediato
sin esperar el poll de 60 s.

### Cómo se procesan los archivos

El escáner se ejecuta cada 5 minutos (e inmediatamente con **Scan
Now**).  Para cada archivo situado directamente en la carpeta:

1. **Los archivos no de audio se omiten** y se dejan en su sitio —
   el escáner solo toma archivos de audio (`mp3`, `wav`, `m4a`,
   `mp4`, `flac`, `ogg`, `oga`, `aac`, `opus`, `mp2`, `mp1`, `au`;
   desde el 2026-10-14 exactamente la lista que acepta la subida del
   navegador).  La línea de estado los cuenta como «non-audio files
   left alone».
2. **Los archivos aún sin reposo esperan (desde el 17/09/2026).**
   Un archivo modificado en los últimos 60 segundos puede estar
   todavía escribiéndose (copia lenta, subida FTP); la línea de
   estado lo marca como «still being copied» y una pasada posterior
   lo
   recoge.
3. Cada archivo de audio en reposo pasa al **circuito estándar de
   subida**: se crea una entrada de biblioteca, el archivo se
   **mueve** (no se copia) a la zona `organize` de la biblioteca, y
   el analizador continúa — lectura de metadatos, conversión según el
   **Formato de importación** (sección 5), comprobación de
   reproducibilidad, lugar definitivo en la biblioteca.  Desde
   entonces se comporta exactamente como un archivo subido por la
   interfaz web.
4. **Si la entrega falla, el archivo se mueve a la subcarpeta
   `_failed`** de la carpeta de importación (desde el 2026-10-14;
   antes se borraba).  Allí conserva su ruta relativa
   (`Album/Song.wav` pasa a ser `_failed/Album/Song.wav`; si ese
   nombre está ocupado, se añade un número: `Song (2).wav`).  El
   escáner nunca mira dentro de `_failed`, así que un archivo roto no
   se reintenta en cada pasada — y un archivo rechazado nunca se
   borra.  Si incluso el traslado falla, el archivo se queda donde
   está y la siguiente pasada lo intenta de nuevo.

La carpeta se vacía por tanto de archivos de audio tras cada pasada —
movidos a la biblioteca si hay éxito, a `_failed` si hay fallo.  Los
archivos no de audio permanecen.  La línea de estado indica cuántos
archivos fueron a `_failed` («2 failed (moved to _failed)»).

### Subcarpetas y lotes grandes (desde 2026-10-08)

Las subcarpetas se **recorren**: cada archivo de audio de la carpeta de
importación y de cualquier subcarpeta se importa, carpeta por carpeta
en orden de ruta; una subcarpeta que los traslados dejan vacía se
elimina.  La subcarpeta `_failed` es la excepción: nunca se recorre ni
se elimina.  La estructura de carpetas no pasa a la biblioteca (que
organiza los archivos por sus metadatos): etiquete los archivos antes
de copiarlos.

Un escaneo tampoco entrega nada mientras **300 o más archivos** sigan
en cola en el analizador (procesa alrededor de un archivo por segundo);
la línea de estado muestra esa cola.  Así la biblioteca no acumula
filas que esperan tanto que la limpieza horaria las marca como
fallidas.

Un escaneo entrega como máximo **300 archivos** y se detiene tras
**20 segundos**; el resto espera a la siguiente pasada (cada 5
minutos o **Scan Now**), y la línea de estado indica cuántos esperan.
Así el escaneo se mantiene dentro del límite de tiempo de PHP - un
escaneo interrumpido a mitad de un traslado dejaba antes medio
archivo.  El analizador procesa después la cola archivo a archivo; en
esta máquina un MP3 de cuatro minutos tarda unos 1.1 s (prueba
con 50 archivos, 2026-10-08): cuente con unas 3.000 pistas por hora de
principio a fin y con unas siete horas para 20.000 pistas.  Coloque la carpeta de
importación en la misma unidad que la mediateca (el traslado es
entonces instantáneo y atómico), ajuste antes *Track Type Upload
Default* (el propietario no tiene ajuste: las importaciones en segundo
plano pertenecen al primer administrador, las de Scan Now a usted), y
copie en lotes de unos miles.

### Propiedad

Con **Scan Now**, los archivos importados pertenecen al operador que
pulsó el botón.  Los archivos recogidos por la pasada en segundo
plano pertenecen a la primera cuenta de administrador.

> **Bajo el capó.**  El escáner es la `LocalImportScanTask` del
> gestor de tareas del frontend PHP legacy: se ejecuta con las
> peticiones web normales, como mucho cada 300 s, y actualiza las
> claves `cc_pref` `local_import_last_run` y
> `local_import_last_status` (la línea de estado de esta página).
> Vea ARCHITECTURE §23.12 y, para la carpeta `_failed` y la lista de
> extensiones común, §23.57.

### Importar desde un servidor FTP

Bajo la carpeta de importación hay una segunda fuente de importación
(desde el 17/09/2026): RASTATIME recoge cada 5 minutos (o
inmediatamente con **Fetch now**) los archivos de audio de un
servidor FTP, FTPS o SFTP y los hace pasar por la carpeta de
importación de arriba — que por tanto debe estar configurada.
Active la casilla, rellene servidor, puerto (vacío = valor por
defecto del protocolo), cuenta y la carpeta remota **absoluta**, y
pulse **Save FTP import**.

- **Semántica de buzón.**  Tras una descarga verificada, el archivo
  remoto se borra — la cuenta necesita permiso de borrado.  Si el
  borrado falla, el archivo se importa igualmente y el estado
  avisa, porque el siguiente ciclo traería un duplicado.
- **Las subidas en curso son seguras.**  Un archivo solo se recoge
  cuando su tamaño lleva al menos un minuto sin cambiar entre dos
  comprobaciones, y el tamaño se verifica de nuevo tras la
  descarga.  Hasta entonces el estado lo cuenta como «settling».
- **Los archivos no de audio permanecen en el servidor.**  Solo se
  recogen las extensiones de audio de la carpeta de importación.  Una
  entrada remota llamada `_failed` no se toca.
- **Prefiera FTPS o SFTP** — el FTP en claro transmite la
  contraseña sin cifrar.  La contraseña se guarda en la base de
  datos de ajustes como las demás contraseñas de servicios, para
  que la recogida pueda conectarse sin supervisión; la página no la
  muestra nunca más.
- Cada ciclo inicia descargas nuevas durante un minuto como máximo;
  lo demás lo recoge el ciclo siguiente («left for the next run» en
  el estado).

---

## 7. Ubicación de la biblioteca de medios

Desde el 16/09/2026 la carpeta que contiene la biblioteca de medios
(pistas importadas, carátulas, imágenes de programas) es un ajuste de
esta página y ya no una línea de `libretime.conf`. El archivo de
configuración solo aporta el valor inicial; en cuanto haya movido la
biblioteca una vez, manda el ajuste.

La sección muestra la **ubicación actual**, de dónde procede ese valor
(el ajuste o el archivo de configuración), el número de archivos y el
tamaño de la biblioteca. Para moverla:

1. Escriba la **nueva ubicación**: una ruta absoluta en un disco local
   de esta máquina, por ejemplo `D:\stor`. La carpeta se crea si hace
   falta. No se admiten rutas de red.
2. Pulse **Comprobar**. RASTATIME confirma que puede escribir allí y
   que el disco tiene espacio libre suficiente (la biblioteca más un
   diez por ciento).
3. Pulse **Mover biblioteca** y confirme. Una barra de progreso sigue
   la copia.

Qué ocurre durante el traslado:

- La emisión, la programación, las grabaciones y el monitor local
  siguen funcionando; nada se emite directamente desde la carpeta de la
  biblioteca, la reproducción usa su caché.
- Las importaciones se pausan: las subidas, el rastreo de la carpeta de
  importación local, las descargas de podcasts y las subidas de imágenes
  se rechazan con un breve mensaje hasta que termina el traslado.
- RASTATIME copia la biblioteca con robocopy, comprueba después que cada
  archivo ha llegado con el tamaño correcto y que cada pista de la base
  de datos se encuentra en el nuevo lugar. Solo entonces cambia el
  ajuste. La aplicación web y la API lo siguen al instante; la
  reproducción, en su siguiente actualización de la programación (en
  menos de dos minutos).
- La **copia anterior permanece en el disco**. Bórrela usted mismo
  cuando esté conforme, y solo su contenido, no la carpeta indicada en
  `libretime.conf`, porque la aplicación web comprueba al arrancar que
  esa carpeta existe.

Si el servicio RASTATIME-API se reinicia durante una copia, la sección
muestra el traslado como *interrumpido*. Escriba el mismo destino y
mueva de nuevo: la copia continúa donde se detuvo y omite los archivos
ya copiados. **Cancelar traslado** detiene una copia en curso; lo ya
copiado permanece en el destino y un traslado posterior parte de ahí.

Si la ubicación configurada faltara o fuera de solo lectura (un disco
no montado, una carpeta renombrada), el banner del panel muestra
*Media library location … is missing* hasta que vuelva a estar
disponible.

---

## 8. Carpetas de grabación (relacionadas)

Configuración → Máquina local tiene **dos** carpetas de salida
de grabación:

### Show Recording Folder

Donde [Grabación por programa](./RECORD_PER_SHOW.md) escribe un
archivo por programa marcado «grabar». *(Renombrada desde
«Recording Folder» al añadir la grabación 24/7 — 2026-06-06.)*

Por defecto: `C:\rastatime\recordings\`.

### 24/7 Recording Folder

Donde la [grabación 24/7](./RECORD_PER_HOUR.md) permanente
escribe un archivo por hora de reloj (más un archivo de marcas
`.cues.json`), independientemente de los programas. La activa,
elige un formato / tasa de bits y fija una ventana de borrado
automático directamente en esta sección. Manténgala
**separada** de la Show Recording Folder para que la limpieza
de retención nunca toque los archivos por programa. La carpeta
se crea al guardar si aún no existe.

Ninguna de las dos carpetas es candidata para la Biblioteca —
las grabaciones se guardan como archivos autónomos para
descarga / archivo.

> **Aplique los cambios reiniciando el servicio de playout.**
> Los ajustes del grabador se integran en el script Liquidsoap
> al arrancar; tras un cambio, reinicie **RASTATIME-PLAYOUT**
> (el diálogo Save lo recuerda). Solo el valor 24/7 **Delete
> after (days)** surte efecto sin reinicio.

---

## 9. Preguntas frecuentes

### "Mi micro USB aparece en Windows, pero no en RASTATIME."

Tres cosas a verificar:
1. El micro está **marcado** en la lista Dispositivos de
   entrada en esta página.
2. El servicio `RASTATIME-API` corre.
3. El driver de audio Windows todavía permite acceso a la
   entrada.

### "La Carpeta de importación local no importa nada."

Orden de diagnóstico:
1. La ruta de la carpeta es correcta y existe.
2. El frontend web corre (`RASTATIME-APACHE`) — el escáner se
   ejecuta con las peticiones web, así que **Último escaneo**
   solo avanza mientras la interfaz ve tráfico.  **Scan Now**
   fuerza una pasada.
3. Un archivo modificado en los últimos 60 segundos cuenta como
   «still being copied» — espere un minuto y escanee de nuevo.
4. «N failed (moved to _failed)» en la línea de estado significa
   que la entrega falló y el archivo está ahora en la subcarpeta
   `_failed` (vea la pregunta siguiente).  Pruebe el archivo en otro
   reproductor y busque el motivo en `logs\legacy.log`; el servicio
   `RASTATIME-ANALYZER` debe correr para terminar la importación.

### "¿Qué hago con los archivos de `_failed`?"

Cada archivo que hay allí no pudo entregarse a la biblioteca.  Busque
su nombre en `logs\legacy.log` para ver el motivo, pruébelo en otro
reproductor, repárelo o vuelva a exportarlo si hace falta y muévalo de
nuevo a la carpeta de importación — a cualquier lugar fuera de
`_failed`; la siguiente pasada lo importa.  Borre lo que ya no
necesite: RASTATIME nunca vacía `_failed` por sí mismo.

### "Importé un archivo WAV o FLAC y la biblioteca muestra un MP3."

Es el ajuste **Formato de importación** (sección 5): los archivos sin
pérdida se convierten a MP3 de 320 kbps al importar, y el original sin
pérdida no se conserva.  Para importar archivos sin pérdida tal cual,
desmarque la casilla y pulse **Guardar** *antes* de importarlos.

### "¿Por qué mover y no copiar en la Carpeta de importación local?"

Un workflow basado en copia deja al operador con dos
copias de cada archivo importado y sin propiedad clara.

### "¿Puede la Carpeta de importación local estar en un recurso compartido de red?"

Sí, con dos advertencias: el recurso debe estar montado
en la ruta que RASTATIME ve (ej. `Z:\import\`). Las rutas
UNC no son *confiables* con servicios lanzados por NSSM
en Windows.

### "¿Puedo tener múltiples Carpetas de importación local?"

No. El poller escanea un directorio configurado.

### "¿Cuál es la diferencia entre la Carpeta de importación local y el botón Subir?"

| | Subir | Carpeta de importación local |
|---|---|---|
| Origen | Lado del navegador | Sistema de archivos del lado del servidor |
| Mejor para | Uno o dos archivos | Lotes de muchos archivos |
| Timeout | El navegador puede timeout | Sin timeout |
| Propiedad | Usuario conectado | Propietario por defecto configurado |

### "¿La selección de dispositivo de salida afecta lo que oyen los oyentes?"

No. El dispositivo de salida en esta página es la salida
**monitor / cue**. Los oyentes oyen la salida
[Streams](./STREAMS.md).

---

## A dónde ir después

* [Line-In](./LINE_IN.md) — transformar un dispositivo
  de entrada marcado en un item de biblioteca
  planificable nombrado.
* [Biblioteca](./LIBRARY.md) → §2 — alternativas a la
  Carpeta de importación local.
* [Streams](./STREAMS.md) — la salida de audio del lado
  del oyente.
* [`docs/operator/DEVICE_MISSING.md`](../../operator/DEVICE_MISSING.md)
  — cuando un dispositivo configurado previamente
  desaparece.
