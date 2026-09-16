# Máquina local

> **Dónde está usted en el manual.** Este capítulo cubre
> la página Configuración → **Máquina local**, que posee
> cada aspecto vinculado a la *máquina del operador
> misma* — salida de tarjeta de sonido, dispositivos de
> entrada line-in y carpeta de importación local. Para los
> streams salientes del lado de red, vea
> [Streams](./STREAMS.md). Para el tipo de item de
> biblioteca que *referencia* una entrada de tarjeta de
> sonido, vea [Line-In](./LINE_IN.md).

La página **Máquina local** es donde informa a RASTATIME
sobre los recursos físicos en la máquina del operador:
qué salida de altavoz reproducir, qué dispositivos cuentan
como candidatos line-in, y qué carpeta el analyzer debe
vigilar para pistas importadas.

La página reemplaza la página "Soundcard" del LibreTime
original y añade la función carpeta de importación. La URL
legacy todavía funciona; solo el título de la página y el
slug cambian.

---

## 1. La página

Configuración → **Máquina local**.

Tres secciones independientes: Tarjeta de sonido (salida +
entrada), Carpeta de importación local.

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
  del límite hace esperar al siguiente. Desde el 2026-09-09 las
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
  cada exploración. Lea `liquidsoap.log` (normalmente el dispositivo
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
un Line-In nombrado en la sección **Line-In Sources** de
esta misma página (encima de Import Folder desde el
2026-08-31) — ese editor completo también elige los
**canales de entrada** (par estéreo o mono) en interfaces
multicanal. Además existe una creación rápida sencilla en la
biblioteca bajo **Line Inputs → + Nuevo** (canales 1/2 por
defecto). Vea [Line-In](./LINE_IN.md).

---

## 4. Salida por defecto para cue / monitor

El menú desplegable bajo la lista de dispositivos de
salida re-expone el por defecto en forma de fila única.

---

## 5. Carpeta de importación local

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

Para cada nuevo archivo que el analyzer encuentra:

1. El archivo se mueve (no se copia) a un área de staging
   (`C:\rastatime\import\.staging\`).
2. El analyzer ejecuta ffprobe + verificación de
   reproducibilidad ffmpeg.
3. En éxito, el archivo se mueve a
   `C:\rastatime\media\<owner>\<year>\<month>\<filename>`.
4. En fallo duro, el archivo se mueve a
   `C:\rastatime\import\.failed\` con un archivo `.err`
   al lado.
5. En fallo suave, el archivo se importa con una insignia
   de advertencia amarilla.

### Subcarpetas

Las subcarpetas se escanean recursivamente. Los archivos
en subcarpetas se importan, y el **nombre de la
subcarpeta** se convierte en el campo de metadatos
`album` de la pista importada si el propio tag ID3 album
del archivo está vacío.

### Propiedad

Los archivos importados pertenecen al
**propietario-importación-por-defecto** configurado.

> **Cómo funciona bajo el capó.** El poller del Carpeta
> de importación local es uno de los jobs en segundo
> plano del servicio `RASTATIME-WORKER` (el
> `LocalImportJob`). Vea ARCHITECTURE §16.

---

## 6. Ubicación de la biblioteca de medios

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

## 7. Carpetas de grabación (relacionadas)

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

## 8. Preguntas frecuentes

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
2. El servicio `RASTATIME-ANALYZER` corre.
3. El servicio `RASTATIME-WORKER` corre.
4. Verifique **Último escaneo** — si muestra "N archivos
   fallidos", mire en `.failed\`.

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
