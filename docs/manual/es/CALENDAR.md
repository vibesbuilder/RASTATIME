# Calendario

> **Dónde está usted en el manual.** Este es uno de los
> capítulos de **Operación de difusión diaria**. Lea
> [Biblioteca](./LIBRARY.md) primero si aún no.

El **Calendario** es donde usted planifica qué sale al
aire. Cada slot de tiempo de aire es:

- Un **programa** que usted ha puesto en el calendario, o
- Tiempo de aire que el [Auto DJ](./AUTO_DJ.md) rellena
  (si está habilitado), o
- El fallback configurado / silencio.

---

## 1. La página Calendario

Calendario → abre la vista semanal por defecto.

### Cambiar de vista

| Botón | Lo que ve |
|---|---|
| **Día** | Un día, filas de horas. Mejor para planificación "qué pasa hoy". |
| **Semana** | Siete días, por defecto. Mejor para planificación de programa semanal. |
| **Mes** | Una cuadrícula mensual. Mejor para vista general "¿está llena la semana de X?". |

Los botones de flecha avanzan por el rango visible. El
botón **Hoy** vuelve al período actual.

Un programa que pasa de la medianoche aparece en dos partes en las
vistas de día y de semana, una en cada día. Ambas partes muestran
el horario completo del programa (p. ej. *23:08 - 0:08*), no la
porción que cae en ese día.

### Qué significan los colores

Cada programa lleva su propio color de fondo y color de
texto (establecidos en el formulario de edición del
programa). Use esto para distinguir programas recurrentes
de puntuales, resaltar programas por género, o marcar
programación especial.

### La barra de relleno por programa

Dentro de cada bloque de programa hay una barra horizontal
delgada en la parte inferior. Muestra el **nivel de
relleno**.

| Barra | Significado |
|---|---|
| (vacía) | 0 % planificado |
| Media llena | ~50 % planificado |
| Llena | 100 % — cada segundo tiene contenido |
| Punta roja sólida | Sobre 100 % — items habrían sobrepasado el slot y fueron recortados |

> **Consejo del operador.** La barra de relleno se
> actualiza automáticamente cada 60 segundos, por lo que
> cuando una
> [Autoloading Playlist](./AUTOLOADING_PLAYLISTS.md)
> construye un programa en segundo plano, puede ver la
> barra moverse de vacía a llena sin recargar la página.
> Antes de 2026-05-20 tenía que recargar manualmente;
> corregido en commit 9484db6.

> **Cómo funciona bajo el capó.** El porcentaje de la
> barra es `cc_show_instances.time_filled / (ends_at −
> starts_at)` × 100, obtenido vía el endpoint JSON
> `/Schedule/event-feed`. La actualización de 60 s es
> `setInterval(refetchEvents, 60_000)` en
> `full-calendar-functions.js`, protegida por
> `$cal.is(":visible")`.

> Desde 2026-10-06 `time_filled` es la longitud dispuesta (del inicio
> del programa al final de la última fila, solapamientos de crossfade
> incluidos): un programa que la barra muestra lleno lo está de verdad.

---

## 2. Crear un programa

Dos rutas:

### 2.1 Desde la cuadrícula del calendario

Haga clic en cualquier celda vacía del calendario.

### 2.2 Desde la barra de herramientas

Calendario → **+ Nuevo programa** arriba a la derecha de
la página.

### El formulario Nuevo programa

El formulario se divide en secciones plegables. **Qué** y
**Cuándo** son obligatorios.

| Sección | Propósito |
|---|---|
| **Plantillas** | Pre-rellenar el formulario desde una [Plantilla de programa](./SHOW_TEMPLATES.md) guardada. |
| **Qué** | Nombre, URL, género, descripción, presentadores, colores, imagen del programa. |
| **Cuándo** | Fecha / hora de inicio, duración, fecha de fin, repeticiones, **¿Permitir inicio diferido?** (dejar que este programa empiece tarde cuando el anterior se sobrepasó — vea [Inicio diferido de programa](./DELAYED_START.md)). |
| **Entrada Live Stream** | Permitir a presentadores remotos tomar el programa vía Show DJ. |
| **Grabación** | Marcar para grabar la salida al aire del programa. Vea [Grabación por programa](./RECORD_PER_SHOW.md). |
| **Own production** (producción propia) | Marcar en las producciones propias de la emisora: los minutos emitidos del programa cuentan en Analytics → [Informe anual](./ANALYTICS.md) (desde 2026-11-03). |
| **Autoloading Playlist** | Adjuntar una playlist para rellenar cada instancia automáticamente. |
| **Quién** | Presentadores adicionales. |
| **Archivo** | Equipo de redacción, participantes, cuenta de CBA, valores de cba.media y archivo automático del programa (no en Editar emisión). Véase [Archivo](./ARCHIVING.md). Desde el 2026-11-03. |
| **Estilo** | Color de fondo, color de texto, imagen de programa. |

### Por qué el formulario rechaza su guardado

| Error | Causa |
|---|---|
| "Cannot schedule overlapping shows." | Otro programa ya ocupa parte del slot. |
| "Start time must be in the future." | Programas puntuales deben empezar al menos 1 minuto desde ahora. |
| "End time must be after start time." | Auto-explicativo. |
| "You are not allowed to schedule show *X*." | Intentó planificar contenido en un programa del que no es presentador. Los DJ planifican en los programas que presentan; los Program Managers y los Admins en todos. |

---

## 3. Editar un programa existente

Haga clic en el programa → menú contextual → elija una
acción.

### Menú de acción

| Acción | Efecto | Disponible cuando |
|---|---|---|
| **Planificar pistas** | Abrir el show-builder. | Siempre |
| **Aplicar plantilla** | Aplicar una [Plantilla de programa](./SHOW_TEMPLATES.md). | Programas futuros solamente |
| **Guardar como plantilla** | Guardar la configuración actual como nueva plantilla. | Siempre |
| **Ver** | Vista de solo lectura de los metadatos + programación del programa. *Start* y *Length* de cada fila son la fila de programación tal como queda colocada (Length = cue-out menos cue-in, como en el show builder; desde el 2026-10-23); los totales de abajo son la longitud colocada del contenido (con puntos de cue y solapes de crossfade) frente a la duración del programa. | Siempre |
| **Teasers** | Los jingles que anuncian este programa: cambiar tipos, desvincular, vincular más; véase [Automatización de teasers](./TEASERS.md). Desde 2026-10-16. | Admin / PM |
| **Archivar en línea** | Título, teaser, descripción, imagen y participantes de este episodio, antes o después de emitirse, y «Archivar en línea ahora» en cba.media; véase [Archivo](./ARCHIVING.md). Desde el 2026-11-03 (primero llamado *Episodio...*). | Admin / PM / presentadores del programa (archivar: Admin / PM) |
| **Editar programa** | Editar la definición de programa. | Programas futuros o actuales |
| **Editar instancia** | Editar solo esta ocurrencia de un programa recurrente. | Programas recurrentes solamente |
| **Cancelar programa** | Terminar el programa *ahora*. | Programa actual solamente |
| **Eliminar programa** | Retirar todo el programa + todas sus instancias. | Programas futuros solamente |
| **Eliminar esta instancia** | Retirar solo esta ocurrencia. | Programas recurrentes, futuros solamente |
| **Vaciar planning** | Borrar el contenido planificado pero mantener el slot vacío. | Programas futuros solamente |

> **Por qué "Editar programa" vs "Editar instancia".** Un
> programa semanal es una *definición* con muchas
> *instancias*. Editar la definición cambia cada instancia
> futura. Editar una sola instancia crea una anulación
> por-ocurrencia.

### Lo que "Editar instancia" no puede hacer

- No puede aplicar una Plantilla de programa. RASTATIME
  2026-05-19 suprime la sección Plantillas en el
  formulario Editar instancia.
- No puede cambiar el inicio/fin de la instancia fuera
  del patrón de repetición del programa padre.

---

### Lo que «Editar instancia» puede cambiar desde 2026-11-03: la carga automática

La sección **Autoloading Playlist** del formulario de instancia es
editable.  **Use the show's autoloading settings** (marcado por
defecto) mantiene el episodio con la lista, intro, outro y repetición
del programa.  Desmárquelo y los campos de abajo se aplican solo a este
episodio: otra lista, ninguna carga automática, otra intro u outro.
**Repeat of show** sigue siendo un ajuste del programa.

La regla **«solo antes del relleno»**: la construcción de la carga
automática se ejecuta una hora antes del inicio, aproximadamente.  Una
vez relleno el episodio, la sección muestra una nota y ya no se puede
cambiar; vacíe el episodio en el Show Builder y se rellena de nuevo con
los ajustes actuales.

---

## 4. Programas recurrentes

Un programa recurrente es una definición con muchas
instancias materializadas eagerly hasta un horizonte
configurable (~3 meses por defecto).

### Crear un programa recurrente

En la sección **Cuándo**, marque **Se repite**. Tres
sub-campos aparecen:

| Campo | Significado |
|---|---|
| **Tipo de repetición** | Semanal / Quincenal / Trisemanal / Mensual. |
| **Seleccionar meses** (desde 2026-10-14) | Solo en repetición mensual: marque los meses en que se emite el programa, los doce por defecto. Desmarque julio y agosto para una pausa de verano, o conserve un mes de cada tres para un programa trimestral. Se combina con *Repeat By* (día del mes / día de la semana). Desmarcar un mes en un programa existente elimina sus instancias futuras de ese mes. |
| **Días** | Qué días de la semana. |
| **Fecha de fin** | Opcional. |

### Editar un programa recurrente

- **Editar programa** cambia la definición: cada instancia
  futura toma el cambio.
- **Editar instancia** crea una anulación
  por-ocurrencia.
- **Eliminar esta instancia** retira solo esa ocurrencia.
- **Eliminar programa** retira toda la serie.
- **Deshacer tras eliminar** (desde 2026-10-28): una eliminación
  desde el menú del calendario no llega al servidor de inmediato.
  El programa desaparece del calendario y un aviso al pie de la
  página cuenta diez segundos hacia atrás con el enlace
  **Deshacer**. Un clic lo devuelve intacto; si la cuenta llega a
  cero, la eliminación se ejecuta como antes. Cerrar la página
  dentro de esos diez segundos envía la eliminación de todos
  modos. *Cancelar programa* para el programa en antena no se
  retrasa y actúa al instante, como siempre.

> **Cómo funciona bajo el capó.** Programas recurrentes
> escriben una fila `cc_show` + una fila `cc_show_days`
> por día de repetición + filas `cc_show_instances` para
> cada ocurrencia materializada.

---

### Repetición de otro programa (desde 2026-10-18)

Muchos programas se emiten una vez y se repiten una vez, otro día o
en otra semana.  Abra el formulario **Edit Show** de la repetición,
sección **Repetición** (justo encima de Autoloading Playlist), y
elija el original en **Repetición
del programa**.  Desde entonces cada instancia de la repetición se
rellena automáticamente:

- **Qué programas ofrece la lista** *(desde 2026-10-27)*: todo
  programa que aún está por venir o en antena, y un programa ya
  emitido (en los últimos 60 días) solo si su última instancia se
  puede repetir completa: solo pistas, o su grabación está importada.
  Un programa en directo pasado sin grabación no se ofrece: elija el
  original antes de que se emita.  Una fuente ya guardada sigue
  seleccionable.
- **Cuándo**: poco antes de que empiece la repetición (alrededor de
  una hora, la misma antelación que la carga automática), no al final
  del original; así se trasladan las correcciones hechas al original
  tras su emisión.
- **Qué**: el contenido de la **última instancia terminada** del
  original: archivos y retransmisiones en su orden con los puntos de
  cue y fundidos emitidos, jingles incluidos.  La lista de carga
  automática rellena después el tiempo restante.
- **Entradas en vivo y webstreams** *(desde 2026-10-20, webstreams desde
  2026-10-21)*: si el original se graba y
  **Copiar las grabaciones de programas a la biblioteca** está activo
  (Ajustes → Máquina local → Show Recording), cada fila line-in o webstream del
  original se sustituye por el fragmento correspondiente de su
  grabación: los puntos cue de entrada y salida son los desplazamientos
  de la fila respecto al inicio del programa, así que la repetición
  reproduce exactamente lo que salió en directo entre las pistas.  Un
  original sin filas (programa puramente en vivo) se repite solo desde
  la grabación.  El relleno espera a que se importe la grabación, pero
  no más allá de cinco minutos antes del inicio de la repetición; sin
  grabación, un webstream se copia como fila en vivo y un line-in queda
  fuera, como antes.  La grabación
  está protegida contra el borrado mientras una repetición pendiente la
  necesite.
- **Si el original aún no se ha emitido** (primera semana, instancia
  cancelada): la repetición se deja a su lista de carga automática.
- **Duración**: una repetición más corta se corta al final como
  cualquier programa sobrecargado; una más larga la completa su lista
  de carga automática.
- **Cadenas** permitidas (C repite B, B repite A); un bucle se
  rechaza al guardar.  «Repetición del programa» no se puede combinar
  con **Link**.
- **Borrar una pista** que emitió el original se rechaza mientras una
  repetición la espera («todavía se necesita para la repetición ...
  del ...»).  Un archivo desaparecido del disco fuera de RASTATIME se
  omite y se cuenta.

En el calendario una repetición lleva un **icono de repetición**
(dos flechas, desde 2026-10-21) en lugar de la marca roja «vacío» o
«parcialmente lleno», como el reloj de un programa con carga
automática: se rellena sola; al pasar el ratón sobre el icono aparece
el nombre del original.

**View Show** en una repetición rellenada dice «Repetición del
programa A del <fecha> a las <hora>» y, si se omitieron filas,
cuántas.  Una instancia que ya tiene contenido (rellenada a mano)
nunca se sobrescribe.  Los programas en vivo grabados aún no se
pueden repetir así (etapa 2, véase BACKLOG).

## 5. Arrastrar y soltar

### 5.1 Mover un programa

Haga clic y arrastre cualquier bloque de programa futuro a
una hora / día diferente. El programa se ajusta al intervalo de
cuadrícula elegido en el desplegable arriba a la izquierda de la
cuadrícula horaria (1, 5, 10, 15, 30 o 60 minutos; 10 minutos
mientras no elija otro, guardado por usuario).

### 5.2 Redimensionar un programa

Pase sobre el borde inferior de un programa; el cursor se
convierte en una doble flecha. Arrastre hacia abajo para
alargar, hacia arriba para acortar.

### Lo que no puede arrastrarse

- Programas pasados.
- El programa actualmente al aire (use **Cancelar
  programa** en su lugar).
- Cualquier programa, a menos que sea Program Manager o
  Admin (los DJ no mueven ni redimensionan programas).

---

## 6. El menú contextual del calendario

Clic derecho en cualquier programa:

| Grupo | Items |
|---|---|
| Contenido | Planificar pistas, Vaciar planning |
| Edición | Editar programa, Editar instancia, Aplicar plantilla, Guardar como plantilla |
| Ciclo de vida | Cancelar programa, Eliminar programa, Eliminar esta instancia |
| Info | Ver programa, Ver archivo grabado |

---

## 7. La línea de ahora

Una línea roja delgada cruza el calendario a la hora
actual. La línea se actualiza cada minuto.

> **Consejo del operador.** Si está depurando "por qué el
> programa equivocado está reproduciendo ahora" — alinee la
> línea de ahora contra el calendario.

---

## 8. Operaciones masivas

Calendario → menú desplegable **Acciones masivas**:

| Acción | Efecto |
|---|---|
| **Aplicar plantilla a programas seleccionados** | Marque múltiples programas futuros. |
| **Eliminar programas seleccionados** | Eliminar cada programa seleccionado. |

---

## 9. Preguntas frecuentes

### "Planifiqué un programa pero nada se reproduce a la hora de inicio."

Tres posibilidades:
1. El programa está vacío (barra de relleno muestra 0 %).
2. El programa tiene una autoloading playlist vacía.
3. El servicio **RASTATIME-PLAYOUT** no está corriendo.

### "¿Puede un programa contener otro programa?"

No. Los programas son planos.

### "¿Pueden dos programas solaparse si son diferentes DJs?"

No. La regla de "no solapamiento" es a nivel emisora
porque solo hay una salida.

### "¿Cuál es la duración máxima de programa?"

Técnicamente 24 horas. Operativamente debería dividir
cualquier cosa de más de unas pocas horas en múltiples
programas.

### "¿Qué pasa la noche del cambio de hora?"

Los programas se definen en hora local y se quedan en su hora local:
un programa a las 08:00 se emite a las 08:00 antes y después del
cambio.  Un programa que cruza el cambio termina a su hora local de
fin: «22:00 durante 8 horas» termina a las 06:00 la noche de otoño
(nueve horas reales, la carga automática rellena la hora extra) y a las
06:00 la noche de primavera (siete horas reales).  No hay hueco ni
solapamiento con el programa siguiente.  Dentro de la hora de
transición (02:00–03:00): un programa cuya hora de fin no existe en
primavera termina una hora más tarde; un programa que cae por completo
en la hora saltada conserva su duración; una hora de fin que ocurre dos
veces en otoño se toma en su primera aparición.  Desde 2026-10-16;
antes, un programa que cruzaba el cambio terminaba una hora antes
(otoño) o una hora después (primavera).

### "¿Puedo importar / exportar el calendario como ICS?"

Sí — export ICS de solo lectura en
`/Calendar/ics/format/ics`. Import no está soportado.

---

## A dónde ir después

* [Plantillas de programa](./SHOW_TEMPLATES.md) — dejar
  de escribir la misma configuración cada semana.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) —
  dejar que los programas se rellenen solos.
* [Auto DJ](./AUTO_DJ.md) — dejar que el sistema rellene
  los huecos de calendario.
* [Grabación por programa](./RECORD_PER_SHOW.md) —
  capturar lo que estuvo al aire en un archivo.
