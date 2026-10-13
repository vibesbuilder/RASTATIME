# Importar/Exportar

> **Dónde está en el manual.** Configuración → **Importar/Exportar**
> mueve los objetos del calendario hacia y desde RASTATIME como
> archivos: programas, listas de reproducción, bloques inteligentes,
> webstreams y suscripciones a podcasts. Lea primero
> [Calendario](./CALENDAR.md) y [Plantillas de programa](./SHOW_TEMPLATES.md)
> si el diálogo «Nuevo programa» le resulta nuevo: la importación crea
> los programas exactamente como lo haría ese diálogo.
>
> **Qué reemplaza esta función.** Construir toda una parrilla con el
> diálogo «Nuevo programa», un programa a la vez, y volver a teclearla
> cuando la emisora se traslada a un nuevo RASTATIME.

La página tiene dos mitades. **Exportar** escribe los objetos actuales
como CSV (JSON para los bloques inteligentes). **Importar** recibe esos
archivos de vuelta —un paquete ZIP con todo, o un solo archivo de un
tipo— y muestra siempre primero una **vista previa**: cada fila se
comprueba, usted marca las filas que quiere y solo esas se escriben.
Una fila cuyo horario se solapa con un programa existente nunca se
importa.

Solo los administradores ven la página.

---

## 1. Exportar

1. Marque los tipos que quiera. El número entre paréntesis es cuántas
   filas contendrá la exportación; el nombre de archivo es el que la
   importación espera de vuelta.
2. Pulse **Exportar los tipos seleccionados**.
   * Un tipo produce un único archivo (`shows.csv`, `playlists.csv`,
     `webstreams.csv`, `podcasts.csv` o `blocks.json`).
   * Varios tipos producen un ZIP con todos los archivos, una carpeta
     `logos/` con los logotipos de programa y un `README.txt` que
     explica cada columna.
3. **Descargar paquete de plantilla** da el mismo ZIP con las cabeceras
   de columna, una fila de ejemplo por tipo y el README: la forma más
   rápida de empezar una hoja de cálculo desde cero.

La exportación de programas contiene los programas que aún tienen
emisiones próximas. Cada fila empieza en la **siguiente** emisión del
programa, de modo que un archivo exportado puede importarse de nuevo
sin tocar el pasado.

Los archivos CSV son UTF-8 con `;` como delimitador y se abren
correctamente en Excel o LibreOffice; al importar también se aceptan
`,` y tabulador. Las columnas de interruptor toman `yes`/`no`.

## 2. Importar

1. Elija el archivo: el paquete ZIP o un único archivo CSV/JSON. Deje
   **Tipo** en *detectar desde el archivo* salvo que su archivo tenga
   un nombre inusual.
2. **Nombres existentes**: *omitir* (por defecto) deja intacto un objeto
   cuyo nombre ya existe; *reemplazar* sobrescribe listas, bloques
   inteligentes, webstreams y las opciones de una suscripción a
   podcast. Los programas nunca se reemplazan: un programa que se
   solaparía simplemente falla.
3. Pulse **Vista previa**. La tabla lista cada fila con su estado:
   * **listo**: válida, se creará al importar;
   * **omitido**: ya existe (con *omitir*) o no está seleccionada;
   * **error**: la nota dice por qué (lista desconocida, solapamiento,
     fecha incorrecta…). Corrija el archivo y súbalo de nuevo, o
     importe las demás filas.
4. Desmarque lo que no quiera y pulse **Importar las filas
   seleccionadas**. Las filas se crean en orden de dependencia —
   webstreams, bloques inteligentes, listas, podcasts, programas—, de
   modo que una lista puede referenciar un bloque del mismo paquete y
   un programa una lista del mismo paquete.
5. La tabla de resultado muestra qué se creó, se omitió o falló. El
   calendario y la emisión recogen los nuevos programas en su siguiente
   actualización (unos dos minutos).

Cada fila se comprueba una segunda vez justo antes de escribirse: un
programa que pasó a solaparse mientras usted miraba la vista previa
sigue rechazándose.

## 3. Los archivos

### shows.csv

| Columna | Significado |
|---|---|
| `name`, `url`, `genre`, `description` | como en el diálogo; solo `name` es obligatorio |
| `start_date`, `start_time`, `end_date`, `end_time` | primera emisión; `end_date` puede quedar vacío (mismo día, o día siguiente cuando el fin precede al inicio) |
| `timezone` | nombre IANA como `Europe/Berlin`; vacío = zona horaria de la emisora |
| `allow_delayed_start` | yes/no, véase [Inicio diferido](./DELAYED_START.md) |
| `repeats`, `repeat_type` | `none`, `weekly`, `biweekly`, `every_3_weeks`, `every_4_weeks`, `monthly_date`, `monthly_weekday` |
| `days` | para los tipos semanales: `Mon,Tue,Wed,Thu,Fri,Sat,Sun` (también valen las abreviaturas alemanas); vacío = día de la semana de `start_date` |
| `repeat_end_date`, `no_end` | fecha de la última emisión, o `no_end = yes` |
| `linked`, `record` | yes/no |
| `content`, `content_repeat` | el nombre de una lista usada como **lista de carga automática** del programa, y si se repite hasta llenar el programa; véase [Listas de carga automática](./AUTOLOADING_PLAYLISTS.md). Una lista puede contener pistas, bloques inteligentes, webstreams y entradas de línea, así cada instancia del programa se llena automáticamente. |
| `intro_playlist`, `outro_playlist` | nombres de listas; vacío = valores por defecto de la emisora |
| `rastatime_auth`, `custom_auth`, `custom_username` | autenticación de DJ en directo como en el diálogo |
| `djs` | logins de DJ, separados por comas; solo se pueden asignar usuarios de tipo DJ |
| `background_color`, `text_color` | seis dígitos hexadecimales sin `#` |
| `logo` | nombre de archivo dentro de la carpeta `logos/` del paquete (jpg, png, gif) |

**La contraseña personalizada de directo nunca forma parte del
archivo.** La exportación la omite, y la importación da a un programa
con autenticación personalizada una contraseña aleatoria que nadie
conoce. Defina después la contraseña real en el calendario; la vista
previa y el resultado lo indican en cada fila afectada.

### playlists.csv

`name`, `description` e `items`. `items` lista el contenido en orden,
separado por `|`:

```
file:imported/Example Radio/StationID/Intro.mp3|webstream:BBC World Service|block:Morning Music|linein:Studio A
```

Los archivos se referencian por su ruta bajo la raíz de la biblioteca
(tal como la escribe la exportación), todo lo demás por nombre. Los
puntos de corte y los fundidos vienen del archivo y de los valores por
defecto, como al soltar un elemento en una lista.

### blocks.json

Una lista JSON, un objeto por bloque inteligente: `name`,
`description`, `type` (`dynamic` o `static`), `limit` (`value` y
`modifier`: items, minutes, hours, remaining), `sort`, los interruptores
(`repeat_tracks`, `overflow_tracks`, `only_unplayed`,
`only_with_expiry`, `use_requests`, `exclude_played_lately` con sus
horas, `exclude_artists_played_lately` con sus horas) y `criteria`, una
lista de reglas con `group`, `field`, `modifier`, `value` y `extra`.
Las reglas del mismo grupo se combinan con Y, los grupos con O: el
mismo modelo que el editor de bloques inteligentes.

### webstreams.csv

`name`, `description`, `url`, `length` (`HH:MM:SS`) e `input_gain_db`.
La URL se sondea al importar, como hace el diálogo de webstream.

### podcasts.csv

`url` (el feed), `title`, `auto_ingest`, `auto_expiry_enabled`,
`auto_expiry_days`, `album_override`, `default_track_type` (el código de
Configuración → Tipos de pista). El feed se descarga al importar; los
episodios no se exportan: el feed los entrega de nuevo.

## 4. Consejos

* Exporte primero, incluso en una emisora vacía: el archivo lleva las
  cabeceras exactas y el README.
* Mantenga una hoja de cálculo por emisora y reimpórtela tras los
  cambios; con *omitir* solo se crean las filas nuevas.
* Dos filas del mismo archivo que se solapan entre sí: la primera se
  crea, la segunda falla al importar con el mensaje de solapamiento.
* Logotipos grandes: el límite de subida del servidor se muestra bajo
  el campo de archivo.

## 5. Véase también

* [Calendario](./CALENDAR.md): el diálogo «Nuevo programa» cuyas reglas
  aplica la importación.
* [Plantillas de programa](./SHOW_TEMPLATES.md): reutilizar ajustes
  dentro del diálogo.
* [Listas de carga automática](./AUTOLOADING_PLAYLISTS.md): lo que
  activa la columna `content`.
* [Copia de seguridad](./BACKUP.md): la copia completa de la base de
  datos; Importar/Exportar es su complemento legible y editable.
