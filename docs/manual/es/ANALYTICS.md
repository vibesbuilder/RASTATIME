# Analytics

> **Dónde está usted en el manual.** Este es un capítulo de
> **Salida e infraestructura**, un acompañante de
> [Streams](./STREAMS.md). Streams cubre la *configuración* de sus
> salidas y su supervisión en vivo; este capítulo cubre el
> **espejo retrovisor** — qué salió realmente al aire y cuántas
> personas escuchaban mientras tanto.

El menú **Analytics** de la barra de navegación agrupa ocho
páginas:

| Página | Pregunta que responde |
|---|---|
| **Playout History** | ¿Qué emitió realmente la emisora, minuto a minuto? |
| **History Templates** | ¿Qué columnas debe registrar y exportar el registro de emisión? |
| **Listener Stats** | ¿Cuántos oyentes estaban conectados a cada flujo, a lo largo del tiempo? |
| **Show Listener Stats** | ¿Qué audiencia logró cada *programa*? |
| **People Involved** (Participantes) | ¿Cuántas personas hicieron las producciones propias de la emisora en un año? Véase § 6 y [Archivo](./ARCHIVING.md) § 6 (desde el 2026-11-03, entrada de menú propia desde el 2026-11-04). |
| **Programme Minutes** (Minutos de programa) | ¿Cuántos minutos de producciones propias salieron al aire en un año? Un año cada vez, CSV. Véase § 5 (desde el 2026-11-03; hasta el 2026-11-04 parte del «Yearly Report», el informe anual). |
| **Music by Country** (Música por país) | ¿De dónde viene la música emitida (cuota musical)? Un año cada vez, CSV. Véase § 7 (desde el 2026-11-08). |
| **Archive Status** (estado del archivo) | ¿Llegó cada episodio a cba.media? Subidas en curso y en espera, lo que tiene por delante el archivo automático, problemas, historial, CSV. Véase [Archivo](./ARCHIVING.md) § 7 (desde el 2026-11-04). |

Las dos primeras existen para la **rendición de cuentas** —
informes de derechos de autor, registros para el regulador,
llamadas del tipo «¿qué canción sonó a las 14:32?». Las dos
últimas existen para **decisiones de programación** — qué franjas
y programas atraen realmente audiencia.

---

## 1. Playout History

**Analytics → Playout History** muestra todo lo que el motor de
emisión envió realmente al aire, sin importar cómo llegó a la
parrilla (programa del calendario, Auto DJ, override manual, DJ en
vivo).

Arriba, un **selector de rango de fecha/hora** con **Filter
History** limita cada vista a una ventana — por defecto, el día
actual.

Debajo, tres pestañas (los DJ solo ven la tercera, con los programas
que presentan; allí añaden, editan y eliminan entradas - los Program
Managers y los Admins editan todas las entradas):

* **Log Sheet** — el registro bruto de emisión, una fila por
  elemento reproducido, con su hora de inicio / fin y las columnas
  de metadatos que define su plantilla activa (véase §2). Esta es
  la vista que se exporta para las sociedades de gestión de
  derechos.
* **File Summary** — la misma ventana agregada **por pista**:
  cuántas veces sonó cada archivo en el período. Ordenable por
  cualquier columna.
* **Show Summary** — la misma ventana agrupada **por instancia de
  programa**. Despliegue un programa para ver qué sonó dentro.

> **Consejo para el operador.** El Log Sheet registra lo que
> reprodujo el *motor*. Un DJ en vivo hablando sobre el flujo no
> deja filas aquí — solo se registra la reproducción de archivos y
> webstreams.

> **Cómo funciona por dentro.** El servicio de playout escribe una
> fila por elemento emitido en `cc_playout_history` (más
> `cc_playout_history_metadata`) en el momento en que el elemento
> comienza. Las tres pestañas son vistas DataTables sobre
> `/playouthistory/{playout-history-feed,file-history-feed,show-history-feed}`,
> todas filtradas en el servidor según el rango elegido.

> **Una pista borrada conserva su historial (desde 2026-10-08).** Cada
> fila de archivo lleva título, creador, duración, compositor y
> copyright del momento de la emisión. Borrar la pista de la biblioteca
> solo vacía la referencia al archivo; la fila se queda y se muestra a
> partir de esos valores - igual que las filas de webstream y line-in.
> La pestaña *File Summary* cuenta las pistas que aún existen. Antes,
> LibreTime borraba las filas junto con la pista.

---

## 2. History Templates

**Analytics → History Templates** controla **qué columnas de
metadatos** registran y muestran el Log Sheet y el File Summary.
Existen dos tipos de plantilla — **Log Sheet Template** y **File
Summary Template** — y exactamente una de cada tipo es la
plantilla predeterminada activa.

Añada campos por nombre y tipo (cadena / entero / fecha …),
ordénelos y pulse **Set Default Template**. Las filas nuevas del
historial registran los campos de la plantilla activa *en el
momento de la emisión*; cambiar de plantilla no reescribe las
filas antiguas.

> **Consejo para el operador.** Configure su plantilla **una vez,
> antes** de necesitar su primer informe de derechos, y luego no
> la toque. Los campos de serie (artista, título, fecha/hora de
> emisión) satisfacen la mayoría de las obligaciones de reporte.

---

## 3. Listener Stats

**Analytics → Listener Stats** grafica el número de **oyentes
conectados simultáneamente por punto de montaje** en el rango
elegido, una línea de color por montaje (p. ej. `rastatime`,
`rastatime-aac`). Use el mismo selector de fecha/hora que en
Playout History; las casillas de la leyenda muestran u ocultan
cada montaje.

Las cifras provienen de su servidor de streaming, por lo que
cuentan oyentes *directos* del flujo. Los oyentes detrás de un
relay, CDN o agregador aparecen como **una sola** conexión.

> **Cómo funciona por dentro.** El servicio de playout consulta
> cada **120 segundos** el `/admin/stats.xml` de cada servidor
> Icecast configurado, con las credenciales de administrador de la
> configuración de ese flujo, y guarda un punto de datos por
> montaje en `cc_listener_count`. Solo se consultan los flujos
> cuyo **Admin Password** está definido en **Settings → Streams**;
> los flujos sin contraseña se omiten con una advertencia en
> `logs/playout.log`.
> *(Restaurado en Windows en RASTATIME 2026-08-30 — en versiones
> anteriores este gráfico quedaba vacío porque no corría ningún
> colector.)*

**Stream Data Collection Status** (el recuadro a la derecha, desde el
26/10/2026): una línea por flujo activo con su punto de montaje.
**OK** significa que la última consulta funcionó.  Si no, la línea
indica la causa y desde cuándo: Icecast rechaza el usuario/contraseña
de admin (compruébelos en **Settings → Streams**), no está accesible,
no responde a tiempo, envía una página de estadísticas ilegible o
responde con otro error.  Con la primera consulta correcta tras el
problema la línea vuelve sola a OK - antes del 26/10/2026 un error se
quedaba para siempre y decía siempre «comprobar usuario/contraseña de
admin».  Un flujo sin Admin Password indica que no se recogen
estadísticas para él.

**¿Gráfico vacío?** En orden de probabilidad:

1. El servicio **RASTATIME-PLAYOUT** no está en ejecución (él
   aloja el colector).
2. El **Admin Password** del flujo en **Settings → Streams** está
   vacío o es incorrecto — busque en `logs/playout.log` una
   advertencia de omisión o un HTTP 401.
3. Está mirando un rango anterior al inicio de la recolección —
   los datos solo se acumulan desde la primera pasada del
   colector.

---

## 4. Show Listener Stats

**Analytics → Show Listener Stats** pliega los mismos datos de
audiencia **por instancia de programa**: para cada programa del
rango elegido obtiene el número **medio** y el **máximo** de
oyentes simultáneos durante su emisión.

Esta es la página para decisiones de programación — compare las
cifras de un programa a lo largo de semanas, o dos programas en la
misma franja.

> **Las cifras de programa necesitan datos de programa.** Un
> programa emitido antes del inicio de la recolección (o con el
> playout detenido) muestra ceros — la agregación solo puede
> plegar los puntos de datos que existan en `cc_listener_count`
> para la ventana horaria del programa.

## 5. Minutos de programa (desde 2026-11-03)

Las cifras del informe anual a las autoridades están en dos páginas,
cada una con un selector de año (hora de la emisora; el año en curso
hasta hoy): **Analytics → Programme Minutes** (Minutos de programa, esta
sección) y **Analytics → People Involved** (Participantes, § 6).  Hasta
el 2026-11-04 ambas eran una sola página, el «Yearly Report» (informe
anual).

Marque **Own production** (producción propia) en un programa (Edit Show
→ What; el icono de ayuda junto a la casilla la explica en breve; único
o recurrente; las plantillas y el Import/Export lo llevan como
`own_production`).  La página cuenta los
episodios de los programas marcados emitidos en el año - terminados, no
borrados, sin retransmisión antigua - con su duración **programada**,
redondeada a minutos por programa y mes.  Los programas configurados
como [Repetición de otro programa](./CALENDAR.md) tienen su propia
columna (primeras emisiones frente a repeticiones), porque la mayoría de
las autoridades los declaran por separado.  Los programas sin la casilla
aparecen en gris con sus minutos bajo «otros programas (no contados)»
para ver qué queda fuera.  Una tabla por mes y **Download CSV (minutes)**
(por programa, totales, por mes) completan la sección.

Program Managers y Admins abren esta página.

## 6. Participantes (desde 2026-11-03)

**Analytics → People Involved** (Participantes) cuenta las personas que
hicieron las **producciones propias** de la emisora en un año.  Desde el
2026-11-07: **People involved** (participantes) = los **Hosts
involved** (presentadores; Edit Show → What, debajo de **Own
production**; el campo aparece en cuanto se marca la casilla), contados
**una vez al año**, + los **Guests involved** (invitados) de cada
episodio emitido (Archive Online, «Archivar en línea», en el
calendario), contados **por episodio**.  Solo cuentan los programas con
**Own production**: un programa sin la casilla conserva su número, pero
queda fuera hasta que se vuelva a marcar; los programas de repetición
(*Repeat of*) aparecen en la lista, pero no cuentan nada.
**Only shows without a value** (solo programas sin valor) y **Download
CSV** (descargar CSV) ayudan con el informe anual.  Los detalles están
en [Archivo](./ARCHIVING.md) § 6.

Program Managers y Admins abren esta página.

## 7. Música por país (desde 2026-11-08)

**Analytics → Music by Country** (Música por país) muestra de dónde
viene la música que salió al aire en un año: la cuota musical de la
emisora.  Un año cada vez (hora de la emisora; el año en curso hasta
hoy).

Se cuentan las emisiones de la Playout History (§ 1) de las pistas cuyo
tipo tiene el código `music` (Settings → Track Types); las pistas de
otro tipo o sin tipo no cuentan.  Cada emisión cuenta con el país de su
pista tal como está hoy (Edit Track → **País**, leído de la etiqueta
`Country` al importar; véase [Biblioteca](./LIBRARY.md)), así que
corregir un país corrige también las emisiones pasadas.  Una pista sin
país cuenta como **Sin país**; una combinación como
`Germany/Switzerland` es una fila propia.

La página muestra los minutos de música, las emisiones, el número de
países y la proporción de minutos con país; una tabla por país
(emisiones y minutos con sus proporciones, ordenada por minutos, *Sin
país* al final); una tabla por mes (emisiones, minutos, minutos con
país y su proporción); y las **25 pistas de música más emitidas sin
país**: introduzca su país para completar el informe.  **Descargar
CSV** añade una tabla de los minutos por país y mes.

No se cuentan, porque no están en la Playout History: la música que los
DJ tocan en directo, las entradas de línea y los webstreams, ni las
emisiones de pistas borradas desde entonces.  El historial empieza con
la primera emisión registrada de la instalación; la página lo indica si
empieza más tarde en el año.

Program Managers y Admins abren esta página.
