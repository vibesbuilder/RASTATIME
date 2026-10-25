# Plantillas de programa

> **Dónde está usted en el manual.** Lea
> [Calendario](./CALENDAR.md) primero si aún no — las
> Plantillas de programa son un acelerador en el formulario
> Nuevo programa / Editar programa del calendario.

Una **Plantilla de programa** es una instantánea guardada
de los valores de los campos del formulario Nuevo
programa. Cuando aplica una plantilla a un nuevo programa,
cada campo capturado se pre-rellena con un clic.

Las plantillas son **a nivel emisora**: cualquier Admin o
Program Manager puede aplicar o editar cualquier plantilla.

---

## 1. Por qué usar plantillas

Sin plantillas, crear un programa musical recurrente
típico toma unos 90 segundos de relleno de formulario.
Con plantillas, esto cae a unos 5 segundos por programa:

1. Nuevo programa → elegir **Plantillas → Mañanas** en el
   desplegable.
2. Establecer la hora de inicio.
3. **Guardar**.

---

## 2. Crear una plantilla

Dos caminos:

### 2.1 Guardar un programa existente como plantilla

Abra el programa en el calendario → **Guardar como
plantilla** en el menú contextual. Un diálogo pregunta:

| Campo | Notas |
|---|---|
| **Nombre de plantilla** | Único. Por defecto el nombre actual del programa. |

Haga clic en **Guardar**. La plantilla se crea desde el
estado actual del formulario de edición del programa.

### 2.2 Guardar el formulario Nuevo programa antes de guardar el programa

Dentro de Nuevo programa → rellene los campos que quiere
capturar → expanda **Plantillas** → haga clic en **Guardar
como plantilla**. Elija un nombre.

---

## 3. Aplicar una plantilla

Al crear un nuevo programa:

1. Nuevo programa → expanda **Plantillas**.
2. Elija una plantilla en el desplegable.
3. Haga clic en **Aplicar**.
4. Las otras secciones del formulario se pre-rellenan.
5. Edite cualquier campo que quiera anular, luego
   **Guardar** normalmente.

La plantilla anula cada campo capturado. Un botón
**Deshacer aplicación** aparece durante diez segundos para
revertir.

### Al aplicar una plantilla en un programa existente

También puede re-aplicar una plantilla a un programa que
ya existe, vía **Aplicar plantilla** en el menú contextual
del calendario.

> **Por qué no auto-propagar ediciones de plantilla?**
> RASTATIME 2026-05-19 eligió un modelo de **sello
> unidireccional**. Editar una plantilla nunca cambia
> programas creados a partir de ella. Razones:
>
> - Previsibilidad: un operador editando una plantilla no
>   tendría idea de cuántos programas existentes
>   cambiarían silenciosamente.
> - Anulaciones por-programa: un operador que editó el
>   color de un programa después de aplicar la plantilla
>   perdería la anulación si la plantilla se re-propagara.
> - Modo de fallo: una edición de plantilla que rompiera
>   un campo rompería cada programa usando esa plantilla.
>
> Si necesita actualizar masivamente programas existentes,
> use **Aplicar plantilla** en cada uno. Vea ARCHITECTURE
> §23.16 para el registro completo de decisión.

### Al aplicar una plantilla en un formulario Editar instancia

No puede. RASTATIME 2026-05-19 suprime la sección
**Plantillas** en el diálogo Editar instancia.

---

## 4. Qué captura una plantilla

| Grupo | Campos |
|---|---|
| **Identidad** | Nombre de programa, URL, género, descripción |
| **Visuales** | Color de fondo, color de texto, referencia a imagen de programa |
| **Duración** | Longitud por defecto |
| **Repeticiones** | Tipo de repetición, días, fecha de fin |
| **Grabación** | Grabación habilitada (sí/no) |
| **Autoloading playlist** | ID de playlist, ID de intro, ID de outro, flag "repetir hasta lleno" |
| **Auth** | Nombres de usuario de presentador (NO la contraseña live-stream) |
| **Fuente Show DJ** | Live-stream por-programa permitido |

### Lo que una plantilla NO captura

| Campo | Razón |
|---|---|
| **Fecha / hora de inicio** | Por-uso. |
| **Contraseña live-stream** | Seguridad. |
| **Descripciones por-instancia** | Específicas de instancia. |

> **Cómo funciona bajo el capó.** Las plantillas viven en
> la tabla `cc_show_template` (`id`, `name UNIQUE`,
> `template_data JSONB`, `created_at`, `updated_at`). El
> servicio PHP `Application_Service_ShowTemplateService`
> posee CRUD vía 5 acciones JSON.

### Imagen de programa almacenada como referencia, no como copia

Si una plantilla captura una imagen de programa, solo se
guarda la ruta al archivo de imagen existente — no una
copia de los bytes de la imagen.

---

## 5. Renombrar o eliminar una plantilla

### 5.1 Desde la página Configuración → Plantillas de programa

Configuración → **Plantillas de programa** abre una lista
de cada plantilla.

| Columna | Acción |
|---|---|
| **Nombre** | Clic para renombrar. El nuevo nombre debe ser único. |
| **Última actualización** | Ordenable. |
| **Usado por** | Conteo de programas usando actualmente esta plantilla. |
| **Editar** | Abrir el JSON de la plantilla en un visor de solo lectura. |
| **Eliminar** | Confirma, luego elimina la plantilla. |

### 5.2 Desde el diálogo Nuevo programa / Editar programa

Expanda **Plantillas** → elija la plantilla → un icono
**Editar** aparece junto al desplegable.

---

## 6. Comportamiento de sobreescritura-en-duplicado

Si guarda una nueva plantilla con un nombre que ya existe,
la interfaz pregunta:

> **Una plantilla llamada "Mañanas" ya existe.
> ¿Sobreescribir?**

| Clic | Efecto |
|---|---|
| **Cancelar** | Descartar la nueva plantilla. |
| **Sobreescribir** | Reemplazar el `template_data` de la plantilla existente. |

---

## 7. Ejemplo trabajado: un programa matinal semanal

Una emisora opera **Mañanas** Lun-Vie 07:00–10:00 con:

- Presentadores: Anna + Ben
- Color de fondo: azul oscuro
- Color de texto: blanco
- Imagen de programa: mananas-logo.png
- Autoloading playlist: "Playlist Mañanas" con intro +
  outro
- Grabación habilitada

**Primera vez:**

1. Crear la ocurrencia del lunes: Nuevo programa, rellenar
   todos los campos, guardar.
2. Abrir el programa del lunes → **Guardar como plantilla**
   → nombrar `Mañanas`.

**Para martes, miércoles, jueves, viernes:**

1. Nuevo programa → Plantillas → **Mañanas** → Aplicar.
2. Establecer fecha de inicio.
3. Guardar.

**O para una definición de programa recurrente
(preferido):**

1. Nuevo programa → Plantillas → **Mañanas** → Aplicar.
2. Establecer fecha de inicio.
3. Marcar **Se repite** → Semanal → Lun, Mar, Mié, Jue,
   Vie.
4. Guardar.

---

## 8. Preguntas frecuentes

### "¿Puedo crear una plantilla que tenga solo los colores, ningún otro campo?"

Sí. Abra un formulario Nuevo programa vacío, rellene solo
color de fondo y texto, luego **Guardar como plantilla**
con un nombre como `Color: Azul oscuro`.

### "¿Puede un DJ guardar / aplicar plantillas?"

No. Las plantillas están en el diálogo del programa, y solo
los Program Managers y los Admins crean y editan programas;
también son ellos quienes guardan, renombran y eliminan las
plantillas, en el diálogo y en la página de resumen
Ajustes → Show Templates.

### "Cambié la lista de presentadores en la plantilla — ¿por qué los programas existentes no han cambiado?"

Por diseño — vea §3. Use **Aplicar plantilla** en cada
programa existente que deba heredar el cambio.

### "¿Puedo exportar una plantilla para usar en otra emisora?"

No vía la interfaz.

### "¿Cuál es el número máximo de plantillas?"

No hay límite estricto.

---

## A dónde ir después

* [Calendario](./CALENDAR.md) — donde se aplican las
  plantillas.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) —
  la razón más común por la que las plantillas son
  útiles.
* [Configuración](./SETTINGS.md) — recorrido de cada
  sub-página de Configuración.
