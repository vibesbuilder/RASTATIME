# Widgets públicos integrables

> **Dónde está usted en el manual.** Este capítulo cubre
> los widgets listos-para-usar que un sitio web externo
> (su página de inicio pública de la emisora, un sitio
> socio, una pantalla informativa) puede integrar mediante
> un simple `<iframe>`. Los widgets extraen los datos en
> vivo de RASTATIME y no requieren inicio de sesión —
> están diseñados para ser visibles públicamente.

RASTATIME entrega una pequeña familia de widgets HTML que
los sitios externos pueden integrar para mostrar lo que
está al aire, lo que viene a continuación, el programa
semanal, etc. Cada widget es una URL de iframe autónoma
que usted inserta en el HTML de su página de inicio.

Este capítulo es la referencia del operador: qué widgets
existen, qué parámetros URL aceptan y cómo integrarlos en
un sitio externo.

---

## 1. La familia de widgets

| Widget | URL | Propósito |
|---|---|---|
| **Now Playing — Show** | `/embed/now-playing-show` | Widget de texto de dos líneas. Nombre del programa actual + duración restante; nombre del próximo programa + horas de inicio-fin. |
| **Now Playing — Track** | `/embed/now-playing-track` | Widget de texto de dos líneas. Pista actual "Artista - Título" + duración restante; próxima pista + horas de inicio-fin. |
| **Next Shows** | `/embed/next-shows` | Widget de lista. Título del programa + lista cronológica de las próximas instancias de un programa recurrente. |
| **Latest Shows** | `/embed/latest-shows` | Widget de lista. Título del programa + lista crono-inversa de las últimas instancias pasadas de un programa recurrente. |
| **On Air Today** | `/embed/on-air-today` | Widget de cuadrícula diaria. Banda de cabecera + programa actual + próximos del día, cada línea "HH:MM – HH:MM   Nombre (enlace)". |
| **Weekly Schedule** | `/embed/weekly-program` | Widget de pestañas de siete días. Cabecera con ◀ / ▶ navegación semanal + etiqueta de rango de fechas; pestañas de día; lista de filas por pestaña con HH:MM – HH:MM + nombre del programa (enlace). Imagen de fondo opcional vía `?bg=URL`. |
| **Multi-View Schedule** | `/embed/multi-view-schedule` | Widget calendario basado en FullCalendar 6 (alojado localmente). Vistas Day / 2-Day / Week conmutables vía botones in-widget o `?view=`. Slots de programa coloreados desde `cc_show.background_color`. Clic → modal con descripción + botón URL. Auto-scroll a la línea now. |
| **Track History** | `/embed/track-history` | Registro de reproducción de pistas (últimos 7 días). Date-picker HTML5 + time-picker + botón Now + dropdown pagesize (10/20/50/100). Filas "HH:MM - HH:MM Artista - Título"; clic → modal con contexto de programa + enlace URL. Botón Load-more con tope duro a 1000 filas. |
| **Stream Player** | `/embed/player` | Botón de escucha en directo con líneas now-playing / next y control de volumen. Layouts tarjeta y barra inferior a ancho completo. Elige el primer stream decodificable por el navegador y cae al siguiente si uno falla. |

Más widgets están planificados (vea [BACKLOG.md](../../../BACKLOG.md)).

---

## 2. Widget Now Playing — Show

iframe listo para usar:

```html
<iframe src="https://su-emisora.example/embed/now-playing-show"
        width="100%" height="50" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Lo que muestra

Dos líneas, cada una con un nombre a la izquierda y una
hora a la derecha:

```
Mañanas                                                   -25:14
Music Hour                                          10:00 - 11:30
```

- **Línea 1**: nombre del programa actual + cuenta atrás hasta el fin (`-MM:SS` o `-H:MM:SS`)
- **Línea 2**: nombre del próximo programa + su ventana `HH:MM - HH:MM`

La cuenta atrás se actualiza cada segundo del lado del
cliente, así que la pantalla se ve fluida. Los datos
subyacentes se refrescan cada 60 segundos (configurable
— vea §7).

### Parámetros URL

| Parámetro | Valores | Por defecto | Efecto |
|---|---|---|---|
| `theme` | `auto`, `dark`, `light` | `auto` | Color del texto. `auto` sigue el `prefers-color-scheme` del navegador. Fondo siempre transparente. |
| `cache` | entero segundos, 10–3600 | `60` | TTL del caché HTTP del lado del servidor. Más bajo = datos más frescos + más hits backend. |
| `overflow` | `ellipsis`, `marquee` | `ellipsis` | Qué hacer con nombres de programa / pista más anchos que el widget de 340 px. `ellipsis` trunca con `…`; `marquee` desplaza el texto a la izquierda durante 24 s. |
| `timezone` | cualquier zona horaria estándar (`Europe/Madrid`) | predeterminado de la emisora | Todas las horas renderizadas en esta zona. |

> **Nota.** El cuerpo del widget está limitado a **340 px de
> ancho** para encajar en diseños de barra lateral típicos de
> los sitios de emisoras.  Establezca el ancho del iframe en
> 340 en el HTML de integración para un ajuste perfecto.
> (Los widgets Next-Shows / Latest-Shows están limitados a
> 300 px — sirven a un caso de uso de barra lateral más
> estrecho.)

---

## 3. Widget Now Playing — Track

iframe listo para usar:

```html
<iframe src="https://su-emisora.example/embed/now-playing-track"
        width="100%" height="50" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Lo que muestra

El mismo diseño de dos líneas que el widget show, pero
para pistas:

```
The Beatles - Hey Jude                                    -02:14
Pink Floyd - Comfortably Numb                       16:00 - 17:30
```

- **Línea 1**: pista actual `Artista - Título` + cuenta atrás hasta el fin
- **Línea 2**: próxima pista `Artista - Título` + su ventana `HH:MM - HH:MM`

Si una pista no tiene metadatos de artista, solo se
muestra el título (y viceversa). Si ninguno está
disponible, la línea muestra "No track playing" / "No
upcoming track" en estilo atenuado.

### Parámetros URL

Igual que el widget show — vea §2.

---

## 4. Widgets Next-Shows / Latest-Shows

Widgets hermanos que listan múltiples instancias **de un solo
programa recurrente** en lugar del envoltorio "qué está sonando
ahora" de los dos widgets Now-Playing.  Útil para una página de
detalle de programa en su sitio: integre el widget en la barra
lateral y los oyentes verán los próximos cuatro episodios (o
los últimos tres, según el widget integrado).

iframe listo para usar (next shows):

```html
<iframe src="https://su-emisora.example/embed/next-shows?show_id=42"
        width="300" height="140" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

iframe listo para usar (latest shows):

```html
<iframe src="https://su-emisora.example/embed/latest-shows?show_id=42"
        width="300" height="120" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Lo que muestra

```
Mañanas
mar 21 may                                  06:00 - 08:00
mié 22 may                                  06:00 - 08:00
jue 23 may                                  06:00 - 08:00
vie 24 may                                  06:00 - 08:00
```

- **Línea de título**: nombre del programa desde `cc_show.name`
- **Líneas de lista**: una línea por instancia, `Día DD Mes`
  a la izquierda, `HH:MM - HH:MM` a la derecha

La lista se refresca cada `cache` segundos (vea §7).  Cuando
la línea superior de un widget Next-Shows se desliza al pasado
(el programa ha empezado), se dispara un refresh anticipado en
~1 s para que la línea desaparezca sin esperar el TTL del caché.

### Parámetros URL

| Parámetro | Valores | Por defecto | Efecto |
|---|---|---|---|
| `show_id` | entero (cc_show.id) | — | Identifica el programa. Estable frente a renombres y a cambios de instancia recurrente — cada instancia de un programa recurrente comparte este id. **Recomendado sobre `show`.** |
| `show` | cadena (cc_show.name) | — | Fallback cuando `show_id` está ausente.  Coincidencia exacta sensible a mayúsculas/minúsculas — **coincide con todos los programas que comparten el nombre**, así una emisora con un programa "BBC News" por día de semana puede listarlos todos con un solo embed `?show=BBC%20News`.  `show_id` gana cuando ambos están definidos. |
| `limit` | entero 1..20 | 4 (next), 3 (latest) | Cuántas instancias listar. |
| `theme` | `auto`, `dark`, `light` | `auto` | Igual que los widgets de dos líneas — vea §2. |
| `cache` | entero segundos 10..3600 | `60` | Igual que los widgets de dos líneas — vea §7. |
| `overflow` | `ellipsis`, `marquee` | `ellipsis` | Comportamiento del título del programa cuando es más ancho que 300 px. |
| `timezone` | cualquier zona estándar | predeterminado de la emisora | Todas las horas renderizadas en esta zona. |

> **Consejo.** Elija el programa desde el menú desplegable de
> la página de Configuración (sección siguiente) en lugar de
> teclear el id a mano — la página muestra una vista previa
> en vivo y copia un snippet de iframe listo para usar con
> el id ya rellenado.

### Instancias modificadas / canceladas

Las instancias individuales que el operador movió o canceló
(`cc_show_instances.modified_instance = TRUE`) se filtran de
la lista, coincidiendo con la convención que
`Application_Model_Show::getNextShows` usa en el panel
interno.  Un episodio pospuesto no deja por tanto una línea
fantasma en el widget público.

---

## 5. Widget On-Air-Today

Widget compacto de cuadrícula diaria que lista el programa
de hoy — desde el programa actualmente al aire hasta los
siguientes programas, tope a medianoche de la emisora para
que el widget nunca se derrame al programa de mañana.

iframe listo para usar:

```html
<iframe src="https://su-emisora.example/embed/on-air-today"
        width="340" height="250" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Lo que muestra

```
On Air Today                       ← banda de cabecera
────────────────────────────────
16:00 - 16:30    Newslink           ← línea actual (negrita)
16:30 - 17:00    Pages of History (EN)
17:00 - 17:30    L'Info Chez-Vous
17:30 - 04:00    Pages d'histoire
18:30 - 19:00    Choices (EN)
19:00 - 19:30    L'Info chez vous (FR)
```

- **Cabecera**: "On Air Today" (o "On Air *<fecha>*" cuando
  un día específico está fijado vía `?day`)
- **Líneas**: `HH:MM - HH:MM` a la izquierda, nombre del
  programa a la derecha.  La línea actualmente al aire se
  renderiza en **negrita** para que el operador (y el
  oyente) vea de un vistazo qué línea está en vivo.
- **Enlaces**: un programa con una **Programa → Editar →
  URL** configurada renderiza su nombre como enlace
  cliqueable que abre en una nueva pestaña (`target="_blank"
  rel="noopener noreferrer"`).  Los programas sin URL
  renderizan como texto plano.

La lista se refresca cada `cache` segundos (vea §7).  Cuando
la hora de fin de la línea actual pasa, se dispara un
refresh anticipado en ~1 s para que el resaltado en negrita
migre a la línea siguiente sin esperar el TTL del caché.

### Parámetros URL

| Parámetro | Valores | Por defecto | Efecto |
|---|---|---|---|
| `limit` | entero 1..20 | `6` | Total de líneas (current + próximas).  Por defecto = 1 current + 5 próximas. |
| `day` | `YYYY-MM-DD` | hoy | Fija un día específico (en la zona horaria resuelta) para renderizar vistas históricas o futuras.  Cuando se omite o iguala a hoy, el widget filtra los programas ya emitidos; para cualquier otro día lista todos los programas cuyo inicio cae en la ventana de 24 h. |
| `theme` | `auto`, `dark`, `light` | `auto` | Igual que los otros widgets — vea §2. |
| `cache` | entero segundos 10..3600 | `60` | Igual que los otros widgets — vea §7. |
| `overflow` | `ellipsis`, `marquee` | `ellipsis` | Comportamiento de nombres de programa más anchos que 340 px. |
| `link` | `underline`, `plain` | `plain` | Renderizado de enlaces para nombres de programa: `plain` (por defecto) quita el subrayado para que los nombres se fundan con el texto en negrita de las filas; `underline` reactiva la affordance estándar de hipervínculo.  Con `plain` la affordance sólo sobrevive vía el cursor puntero al hover. |
| `timezone` | cualquier zona IANA | predeterminado de la emisora | Define "hoy" y renderiza todas las horas en esta zona. |

> **Límite del día.** "Hoy" es el día calendario de la
> emisora — 00:00 a 24:00 en la zona horaria de la emisora
> (o en `?timezone` cuando se sobrescribe).  Un programa
> que comenzó ayer 23:30 y aún está al aire a las 14:00 hoy
> cuenta como la línea actual.  Un programa que comienza
> mañana 00:30 **no** se lista aunque el `limit` lo
> permitiría — el tope es duro.

### Instancias modificadas / canceladas

Misma convención que los widgets Next-Shows / Latest-Shows
— las filas con `cc_show_instances.modified_instance = TRUE`
se filtran para que una instancia pospuesta / cancelada no
deje una línea fantasma en el widget público.

### Página de configuración

**Configuración → Widgets → On Air Today** aloja:

- Una sola etiqueta de estado vacío configurable (por
  defecto `No shows on air today`, fallback al inglés por
  defecto cuando está vacío).
- Una vista previa iframe en vivo sobre fondo oscuro.
- El código `<iframe>` de integración listo-para-usar con
  la URL absoluta de la emisora pre-rellenada.

Sin selector de programa — el widget extrae automáticamente
del programa en vivo para toda la jornada de la emisora.

---

## 6. Widget Weekly Schedule

Un widget de pestañas de 7 días — el reemplazo modernizado
del embed jQuery + Handlebars heredado.  Cabecera compacta
con navegación ◀ / ▶, pestañas día-de-semana, y lista de
filas por día.

iframe listo para usar:

```html
<iframe src="https://su-emisora.example/embed/weekly-program"
        width="400" height="560" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Lo que muestra

```
◀  21 May – 27 May 2026                ▶            ← banda de cabecera
MON  TUE  WED  THU  FRI  SAT  SUN                   ← pestañas
 21   22   23   24   25   26   27                      (hoy circulado)
─────────────────────────────────────────────────
06:00 - 08:00    Mañanas                            ← lista de filas
08:00 - 10:00    Newslink                              (por pestaña activa)
...
```

- **Banda de cabecera**: ◀ botón → semana anterior, etiqueta
  de rango semanal centrada (p.ej. "21 May – 27 May 2026"),
  ▶ botón → semana siguiente.  Hacer clic actualiza el
  parámetro `week_offset` de la URL iframe en su sitio vía
  `history.pushState` y recarga.
- **Pestañas día**: 7 pestañas (Lun … Dom en la locale del
  visitante).  La pestaña de hoy está decorada con un anillo
  pill sutil alrededor del número del día.
- **Lista de filas**: por pestaña, una fila por programa.
  Hora a la izquierda, nombre a la derecha.  Los nombres
  enlazados a una `cc_show.url` renderizan como enlaces
  que abren en una nueva pestaña.

### Parámetros URL

| Parámetro | Valores | Por defecto | Efecto |
|---|---|---|---|
| `week_offset` | entero -2..4 | `0` | Fija la ventana a ±N semanas del bloque rodante de 7 días de hoy.  Cap ajustado (-2 / +4) porque los casos de uso homepage pública rara vez necesitan un rango más amplio; los botones ◀ / ▶ se desactivan en el límite. |
| `theme` | `auto`, `dark`, `light` | `auto` | Igual que los otros widgets — vea §2. |
| `cache` | entero segundos 10..3600 | `60` | Igual que los otros widgets — vea §8. |
| `overflow` | `ellipsis`, `marquee` | `ellipsis` | Comportamiento de nombres de programa más anchos que 400 px. |
| `link` | `underline`, `plain` | `plain` | Renderizado de enlaces de nombres de programa (vea On-Air-Today §5). |
| `bg` | URL de una imagen | ninguna | Imagen de fondo opcional (cover-posicionada) en lugar del relleno transparente por defecto. |
| `bgcolor` | color hex, p.ej. `#222222` | ninguna | Color de fondo opcional como cadena hex (3, 6 u 8 caracteres con alpha — p.ej. `#fff`, `#112233`, `#11223388`).  Renderiza detrás de `?bg` cuando ambos están definidos.  Valores no-hex se rechazan por razones de seguridad. |
| `timezone` | cualquier zona IANA | predeterminado de la emisora | Todas las horas renderizadas en esta zona. |

> **Pestaña de hoy + estado activo.**  La pestaña día-de-
> semana correspondiente a la fecha de hoy se rellena con
> el color de acento (por defecto LibreTime teal
> `#459B8F`) para que el operador vea de un vistazo dónde
> está en la semana.  La pestaña del panel actualmente
> activo recibe un subrayado de color de acento.  El
> hover sobre una pestaña o los botones ◀ / ▶ enciende
> el mismo color de acento con alpha baja — pista de
> interactividad sutil.

> **Auto-scroll al programa actualmente al aire.**  Cuando
> la pestaña activa es hoy, el widget desplaza el programa
> que se está emitiendo ahora al centro del viewport del
> panel — para que el visitante aterrice directamente en
> "lo que suena ahora" en lugar de tener que desplazarse
> por la programación de la madrugada.  El programa en
> curso también se marca con un borde izquierdo color
> acento para que el visitante lo identifique tras el
> desplazamiento.  Sin efecto cuando hoy tiene un hueco
> de programación o cuando otro día está activo.

> **Ancho.** El widget Weekly Schedule mide **670 px de ancho**
> (ampliado desde 400 px el 2026-05-25 a petición del operador —
> todas las fuentes, paddings y la max-height del panel-día se
> escalaron proporcionalmente; el iframe en el snippet de
> embebido recomendado es `width="670" height="670"`).  Ajuste
> el iframe a estos valores en el HTML de embebido para un
> encaje preciso.

### Instancias modificadas / canceladas

Misma convención que los otros widgets —
`modified_instance = TRUE` se filtran.

### Página de configuración

**Configuración → Widgets → Weekly Schedule** aloja la
personalización de la etiqueta de estado vacío ("No shows
scheduled on this day" por defecto), un iframe de vista
previa en vivo sobre fondo oscuro, y el código `<iframe>`
de integración listo-para-usar.

---

## 7. Widget Multi-View Schedule

Widget calendario basado en **FullCalendar 6.1.10** (integrado
localmente, sin dependencia de CDN).  Tres vistas conmutables:
**Day**, **2-Day**, **Week**.  Layout time-grid con slots de
programa coloreados, línea now-indicator, auto-scroll al
programa actualmente al aire, y modal de apertura al clic con
descripción + enlace URL.

iframe listo para usar:

```html
<iframe src="https://su-emisora.example/embed/multi-view-schedule"
        width="100%" height="600" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Lo que muestra

- **Banda de cabecera**: ◀ / ▶ navegación, etiqueta de rango
  de fechas centrada, botón **Today** (vuelve a ahora y
  re-dispara el auto-scroll), conmutador de vista
  (DAY / 2-DAY / WEEK).
- **Time-grid**: 24h, slots 15 min, etiquetas horarias
  60 min.  Línea now-indicator en color de acento.
- **Slots de programa**: desde `cc_show_instances` JOIN
  `cc_show`.  Color de fondo desde el `background_color`
  configurado (Calendario → Programa → Editar → Estilo).
  El programa actualmente al aire recibe un anillo de
  acento.
- **Clic**: abre un modal con nombre, rango horario,
  descripción y enlace click-through a la URL del
  programa (si está configurada).

### Parámetros URL

| Parámetro | Valores | Por defecto | Efecto |
|---|---|---|---|
| `view` | `day`, `2day`, `week` | `day` | Vista inicial.  El visitante puede cambiar vía botones in-widget. |
| `theme` | `auto`, `dark`, `light` | `auto` | Igual que los otros widgets — vea §2. |
| `clock` | `24`, `12`, `auto` | `24` | Formato hora-del-día en eje horario, slots de programa y modal.  `24` fuerza estilo `17:00` independiente de la locale; `12` fuerza `5 PM`; `auto` deja que FullCalendar elija según locale. |
| `cache` | entero segundos 10..3600 | `300` (5 min) | TTL caché HTTP del servidor para el feed JSON.  Por defecto más alto que los otros widgets. |
| `bg` | URL de una imagen | ninguna | Igual que el widget Weekly Schedule — vea §6. |
| `bgcolor` | color hex | ninguna | Igual que el widget Weekly Schedule — vea §6. |
| `timezone` | cualquier zona IANA | predeterminado de la emisora | Todas las horas renderizadas en esta zona. |

### Página de configuración

**Configuración → Widgets → Multi-View Schedule** aloja la
etiqueta de estado vacío, un iframe de vista previa en vivo
sobre fondo oscuro, y snippets de código de integración
listos-para-usar para las tres vistas por defecto.

### Rendimiento

- **FullCalendar alojado localmente** bajo
  `/js/libs/fullcalendar/` (~282 KB JS + ~26 KB locales).
  Sin round-trip CDN, sin dependencia de red externa.
- **CSS empaquetado en el JS** por FullCalendar 6 — sin
  carga de hoja de estilos separada.
- **Lazy event-fetch**: FullCalendar obtiene solo los
  eventos del rango actualmente visible.

---

## 8. Widget Track History

Registro de reproducción de pistas — el visitante elige un
día de los últimos 7, selecciona un tamaño de página (10 /
20 / 50 / 100), y el widget muestra las pistas reproducidas
en orden cronológico inverso.  Clic en una fila → modal con
metadatos + contexto de programa + enlace URL.

iframe listo para usar (~500 px de alto):

```html
<iframe src="https://su-emisora.example/embed/track-history"
        width="100%" height="500" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Parámetros URL

| Parámetro | Valores | Por defecto | Efecto |
|---|---|---|---|
| `date` | `YYYY-MM-DD` | hoy | Día a cargar.  Limitado a `[hoy - 6 días, hoy]`. |
| `time` | `HH:MM` (24h) | ahora (hoy) / 23:59 (día pasado) | Cota superior de hora.  Pistas finalizadas ANTES de este punto, más recientes primero. |
| `pagesize` | `10`, `20`, `50`, `100` | `10` | Pistas por página. |
| `exclude_short` | `0`, `1` | Preferencia (por defecto `1`) | Ocultar pistas más cortas que `min_sec` segundos (jingles / station IDs). |
| `min_sec` | entero 1..3600 | Preferencia (por defecto `60`) | Umbral en segundos para el filtro exclude-short. |
| `theme` | `auto`, `dark`, `light` | `auto` | Igual que los otros widgets. |
| `cache` | entero segundos 10..3600 | `60` | TTL caché HTTP. |
| `bg`, `bgcolor` | URL / hex | ninguna | Igual que los otros widgets. |
| `timezone` | cualquier zona IANA | predeterminado de la emisora | Todas las horas en esta zona. |

**Formato de fila**: `HH:MM - HH:MM Artista - Título` — hora inicio + fin a la izquierda, luego artista / título en **negrita**.

La página **Configuración → Widgets → Track History** aloja además la casilla **Exclude short tracks** + el campo de umbral en segundos (estilo Auto-Expiry — el campo segundos aparece solo cuando la casilla está marcada).

Fuente: `cc_playout_history` LEFT JOIN `cc_files` LEFT JOIN
`cc_show_instances` → `cc_show` con fallback en
`cc_playout_history_metadata`.  Seis tipos de filas:

1. **Reproducciones de archivo programadas** (`file_id IS
   NOT NULL`) — título / artista desde `cc_files`.
2. **Items webstream programados** (`file_id IS NULL`) —
   escritas por `insertPlayedItem()` para items con
   `stream_id`.  Bloque sintético con
   `title = cc_webstream.description` (fallback a
   `name` si description está vacío) y
   `artist = cc_webstream.name`.
3. **Items line-in programados** (`file_id IS NULL`,
   **solo RASTATIME**, requiere migración 0047
   `cc_schedule.linein_id`) — escritas por
   `insertPlayedItem()` para items con `linein_id`
   (el operador arrastró una line-in de la Library a un
   programa, p.ej. "Jabra-Mikro").  Bloque sintético con
   `title = rastatime_linein.description` (texto
   libre, fallback al nombre corto si description
   vacío) y `artist = rastatime_linein.name` (etiqueta
   corta).  `linein_id` se lee vía SQL bruto porque las
   clases ORM Propel se generaron antes de la migración
   RastaTime.
4. **Pistas webstream** (`file_id IS NULL`) — escritas
   por `insertWebstreamMetadata()` por cada metadata
   ICY entrante.
5. **Sesiones Live-Show** (`file_id IS NULL`) — nuevo
   2026-05-23.  Escritas por `ensureLiveShowLogged()`
   como side-effect en `/api/live-info(-v2)`.  Detecta
   show-instances con `time_filled = '00:00:00'`.
   Artist = "Live Show".
6. **Cambios manuales de fuente Dashboard** (`file_id IS
   NULL`) — escritas por `insertLineInLog()` al
   alternar Master/Show Source.  Artist = "Master
   Source" / "Show Source".

Etiqueta para tipos 5+6 configurable bajo Configuración
→ Widgets → Track History → "Line-Input label".  El tipo
3 usa en su lugar el `name` por-line-in de
`rastatime_linein`, que el operador configura en la
Line-In Library.

En el modal: encima de la línea del nombre de programa
está ahora la etiqueta **"Played in the show:"**.  Para
entradas webstream sin enlace de instancia el bloque
de contexto se oculta.

**Configuración → Widgets → Track History** aloja la
etiqueta de estado vacío, vista previa en vivo, y dos
snippets listos-para-usar (pagesize 10 + 50).

---

## Widget Stream Player (`/embed/player`)

> Reconstruido el 18/09/2026 en el estilo de las olas — el
> reproductor jQuery de 2015 desapareció.  Las URL de inserción
> antiguas siguen funcionando sin cambios.

Botón de escucha en directo para la página pública.  Reproduce los
streams habilitados en **Settings → Streams**: el widget prefiere
streams móviles en pantallas pequeñas, conserva solo los formatos
decodificables por el navegador del visitante y cae automáticamente
al siguiente stream si uno falla.  Las líneas now-playing, programa
y **Next** se refrescan por el endpoint de datos de los widgets; un
host Icecast configurado como localhost se reescribe al host de la
página para oyentes remotos.

Dos layouts:

* **card** (por defecto) — panel compacto, con control de volumen
  (recordado por navegador).
* **bar** — barra de 56 px a ancho completo, pensada fija al pie de
  la página (la portada de la emisora la usa).

Parámetros de URL (todos opcionales):

| Parámetro | Valores | Significado |
|---|---|---|
| `title` | texto | Texto de cabecera; sin él, la cabecera se oculta. |
| `theme` | `auto` / `dark` / `light` | El mismo theming de todos los widgets. |
| `layout` | `card` / `bar` | Layout; el antiguo `style=premium` sigue mapeando a `bar`. |
| `stream` | `auto` / nombre | Fijar un stream configurado en lugar de la elección automática. |
| `cache` | `10`..`3600` | Caché del poll de metadatos en segundos. |

Los códigos de inserción con vista previa están en **Settings →
Widgets → Player**.  Los textos de estado vacío se comparten con
los widgets Now-Playing (sección 9).

---

## 9. Personalizar las etiquetas de estado vacío

Cuando no hay programa o pista actual / próxima, el widget
muestra un breve texto placeholder.  Los operadores pueden
personalizar los cuatro placeholders sin tocar el código bajo:

**Configuración → Widgets → Current Show/Track**

| Etiqueta de configuración | Valor por defecto |
|---|---|
| No show on air: | `No show on air` |
| No upcoming show: | `No upcoming show` |
| No track playing: | `No track playing` |
| No upcoming track: | `No upcoming track` |

Las ediciones se persisten en `cc_pref` y son recogidas por
el widget dentro de un TTL de caché (por defecto 60 segundos).
Deje un campo vacío para volver al inglés por defecto mostrado
en su placeholder.

La misma página de configuración aloja también:

- una **vista previa en vivo** de ambos widgets lado a lado;
- el **código de integración `<iframe>` listo-para-usar** para
  cada widget con la URL absoluta de la emisora pre-rellenada.

Los widgets Next-Shows / Latest-Shows tienen su propia página
de etiquetas en:

**Configuración → Widgets → Next/Latest Shows**

| Etiqueta de configuración | Valor por defecto |
|---|---|
| No upcoming shows: | `No upcoming shows` |
| No past shows: | `No past shows` |

Esta página también aloja un **menú desplegable de selección
de programa** que controla los iframes de vista previa y los
snippets de código de integración — elija el programa,
pulse Guardar, y copie el bloque `<iframe ...>` generado con
`show_id` ya integrado en la URL.

---

## 10. El parámetro `cache` — ¿qué TTL?

El servidor almacena en caché los datos subyacentes
durante `cache` segundos antes de regenerarlos. El polling
JS dentro del iframe coincide con esta cadencia, por lo
que bajo alta carga cada visitante alcanza el **caché del
navegador** en lugar de su backend.

Valores recomendados:

| `cache=` | Cuándo |
|---|---|
| `30` | Pantalla de alta precisión, ej. pantalla del lobby. ~2 hits backend/min por navegador. |
| `60` (por defecto) | Página de inicio pública con tráfico moderado. Buen equilibrio entre frescura y carga. |
| `120`–`300` | Integración de muy alto tráfico. Cambie hasta 5 min de obsolescencia por un orden de magnitud menos hits backend. |
| `> 600` | No recomendado — el programa / pista mostrada a menudo ya ha terminado cuando el navegador vuelve a consultar. |

> **Consejo del operador.** El widget compensa los datos
> obsoletos: cuando pasa la hora de fin del item actual
> (calculada del lado del cliente desde los timestamps
> absolutos en el payload), el JS dispara una consulta
> inmediata sin esperar el próximo intervalo. Así una
> integración `cache=300` cambia a la próxima pista en
> ~1 s — la obsolescencia solo afecta a la primera
> visualización después de una pausa inactiva larga.

> **Cómo funciona bajo el capó.** Ambos endpoints de
> widget establecen `Cache-Control: public,
> max-age=<cache>`. Apache sirve el HTML del iframe; el
> JS dentro del iframe consulta `/embed/now-playing-data`
> (mismo TTL de caché). El endpoint JSON extrae de
> `Application_Model_Schedule::GetPlayOrderRange()` — la
> misma fuente que `/api/live-info` — pero recortado a
> ~1-2 kB de payload.

---

## Carátulas (`?art=`)

> Añadido el 18/09/2026.

Tres widgets pueden mostrar la carátula del tema del que hablan: el
**Stream Player** (ambos layouts), las filas del **Track History** y
el widget **Now Playing — Track**.

| Widget | Por defecto | Desactivar / activar |
|---|---|---|
| Stream Player | **activado** | `?art=off` |
| Track History | **activado** | `?art=off` |
| Now Playing — Track | **desactivado** | `?art=on` |

Now Playing está *desactivado* a propósito: ese widget está
documentado con `height="50"`, así que las carátulas son opt-in para
que ninguna inserción existente cambie sola. Con `?art=on` la caja
crece a unos 48 px — dé al iframe `height="56"` o más.

Dos cosas que conviene saber:

* **Solo los temas que realmente tienen carátula muestran una.** El
  resto mantiene su aspecto de texto — una fila de Track History sin
  carátula conserva un hueco vacío para que las columnas sigan
  alineadas, y el reproductor simplemente oculta la imagen. Los
  webstreams y Line-Ins nunca tienen carátula.
* **Las carátulas necesitan la API pública.** Vienen del mismo
  endpoint que usa el widget Song Request, sujeto a Settings →
  Preferences → *Public API*. Con el interruptor apagado los widgets
  siguen funcionando, solo que sin imágenes.

Si las carátulas aparecen pocas veces, la causa casi siempre es la
biblioteca y no el widget: solo los archivos cuya carátula se
importó tienen una.

---

## 11. Temas

Tres modos, controlados vía el parámetro `theme`:

| `theme=` | Efecto |
|---|---|
| `auto` (por defecto) | Texto claro en páginas de integración oscuras, texto oscuro en claras. Detectado vía la media query `prefers-color-scheme` del navegador. |
| `dark` | Fuerza texto claro. |
| `light` | Fuerza texto oscuro. |

El fondo del widget es **siempre transparente**.

---

## 12. Autenticación

Ninguna. Los widgets Now-Playing son intencionalmente
públicos.

No exponen: contadores de oyentes, estado de fuente del
stream, nombres de operadores, estado de grabación, IDs
internos.

---

## 13. Integración cross-origin

Los iframes funcionan cross-origin de forma nativa —
ninguna configuración adicional necesaria.

---

## 14. Resolución de problemas

### "El widget muestra 'No show on air' pero un programa está corriendo"

- Verifique vía el [Panel](./DASHBOARD.md).
- El caché del servidor puede tener datos obsoletos.
  Espere hasta `cache` segundos.

### "El widget no muestra nada (iframe vacío)"

- Verifique que la URL sea accesible desde el contexto
  del navegador de la página integradora.
- Verifique la consola del navegador.

### "El fondo del widget es blanco pero quiero oscuro"

Añada `?theme=dark` a la URL.

### "La cuenta atrás muestra -00:00 y se queda ahí"

La hora de fin del item actual ha pasado pero el widget
no ha recogido aún los nuevos datos. Auto-recupera en
~1 s. Si persiste, el motor de playout puede estar
detenido — verifique `Get-Service RASTATIME-PLAYOUT`.

### "El widget On-Air-Today está vacío aunque hay programas programados"

- Verifique que *hoy* en la zona horaria de la emisora aún
  tiene programas próximos: ya de noche el widget queda
  legítimamente vacío hasta que la próxima medianoche de
  la emisora pase.  Para mirar hacia adelante, fije un
  día específico vía `?day=YYYY-MM-DD`.
- Confirme que los programas realmente estén programados
  en el Calendario — las instancias canceladas
  (`modified_instance = TRUE`) se filtran by-design.
- Si la URL del iframe contiene `?timezone=...`, eso
  sobrescribe la zona horaria de la emisora para el cálculo
  de "hoy".  Un embed `?timezone=Asia/Tokyo` mostrará el
  hoy de Tokio, que puede ya ser mañana en la emisora.

### "El widget Next / Latest Shows muestra el placeholder vacío"

- Verifique que la URL del iframe contenga `?show_id=N`
  (preferido) o `?show=Nombre`.  La página de Configuración
  (§5) genera el snippet con el id ya integrado — cópielo
  desde ahí en lugar de armar la URL a mano.
- Confirme que el programa realmente tenga instancias
  futuras en el Calendario (para Next Shows) o haya salido
  al aire al menos una vez (para Latest Shows).  Un
  programa nuevecito sin episodios emitidos muestra el
  placeholder vacío en el widget Latest hasta que termine
  el primer episodio.
- Las filas `modified_instance = TRUE` se filtran by-design
  (coincide con el panel interno).  Un programa cuya
  única instancia próxima fue movida o cancelada muestra
  vacío hasta que se genere una nueva instancia.

---

## A dónde ir después

* [Panel](./DASHBOARD.md) — la versión interna de los
  mismos datos.
* [Streams](./STREAMS.md) — los streams de audio
  subyacentes.
* [BACKLOG.md](../../../BACKLOG.md) — próximas olas de
  widgets.
