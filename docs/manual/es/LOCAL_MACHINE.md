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
> estudio: MME y DirectSound funcionan con unos auriculares USB,
> mientras que WASAPI rechaza 44,1 kHz y WDM-KS no admite la API
> bloqueante en absoluto. El resultado se escribe en el script
> como `device_id=` con un comentario. Si ningún candidato se
> abre, RASTATIME mantiene el punto final por defecto del sistema
> y registra cada motivo de fallo en el registro de emisión.

> **No todo dispositivo de salida sirve.** Un dispositivo que
> Windows ofrece como salida no es automáticamente utilizable
> aquí: Liquidsoap maneja PortAudio por su API bloqueante, y
> algunos puntos finales la rechazan. Medido en la máquina del
> estudio, **la salida del Tascam US-16x08 es rechazada por todas
> las API anfitrionas** y por tanto no puede servir de monitor
> local: el ajuste recurre al valor por defecto del sistema y lo
> indica en el registro. La misma interfaz sí funciona como
> fuente de captura Line-In; solo la dirección de salida no está
> disponible.

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

## 6. Carpetas de grabación (relacionadas)

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

## 7. Preguntas frecuentes

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
