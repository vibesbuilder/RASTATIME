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
| **Autoloading Playlist** | Adjuntar una playlist para rellenar cada instancia automáticamente. |
| **Quién** | Presentadores adicionales. |
| **Estilo** | Color de fondo, color de texto, imagen de programa. |

### Por qué el formulario rechaza su guardado

| Error | Causa |
|---|---|
| "Cannot schedule overlapping shows." | Otro programa ya ocupa parte del slot. |
| "Start time must be in the future." | Programas puntuales deben empezar al menos 1 minuto desde ahora. |
| "End time must be after start time." | Auto-explicativo. |
| "You are not allowed to schedule show *X*." | Eligió otro DJ como presentador pero usted no es Admin. |

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
| **Ver** | Vista de solo lectura. | Siempre |
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
| **Días** | Qué días de la semana. |
| **Fecha de fin** | Opcional. |

### Editar un programa recurrente

- **Editar programa** cambia la definición: cada instancia
  futura toma el cambio.
- **Editar instancia** crea una anulación
  por-ocurrencia.
- **Eliminar esta instancia** retira solo esa ocurrencia.
- **Eliminar programa** retira toda la serie.

> **Cómo funciona bajo el capó.** Programas recurrentes
> escriben una fila `cc_show` + una fila `cc_show_days`
> por día de repetición + filas `cc_show_instances` para
> cada ocurrencia materializada.

---

## 5. Arrastrar y soltar

### 5.1 Mover un programa

Haga clic y arrastre cualquier bloque de programa futuro a
una hora / día diferente. El snap es de 15 minutos por
defecto.

### 5.2 Redimensionar un programa

Pase sobre el borde inferior de un programa; el cursor se
convierte en una doble flecha. Arrastre hacia abajo para
alargar, hacia arriba para acortar.

### Lo que no puede arrastrarse

- Programas pasados.
- El programa actualmente al aire (use **Cancelar
  programa** en su lugar).
- Programas que no posee (a menos que sea Program Manager
  o Admin).

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
