# Publicación: equipo de redacción, episodios, participantes

> **Dónde está en el manual.** Ajustes → **Equipo de redacción**;
> Calendario → formulario del programa, sección **Publicación**;
> Calendario → clic derecho en una emisión → **Episodio...**;
> Estadísticas → **Participantes** (en la interfaz en inglés: Settings →
> Editorial Team, Publishing, Episode..., Analytics → Participants).
> Lea primero [Calendario](./CALENDAR.md) y
> [Grabación por programa](./RECORD_PER_SHOW.md): el audio de un
> episodio es la grabación del programa.
>
> **Qué prepara esta función.** Publicar cada episodio en
> [cba.media](https://cba.media) (el archivo de las radios libres de
> Austria) sin subirlo a mano, y el recuento anual de las personas que
> hacen la programación.

Desde el 2026-11-03, RASTATIME guarda los datos que necesita un
episodio publicado: quién hace un programa, los valores predeterminados
de su pódcast en cba.media y, por episodio, un título, un teaser, una
descripción y una imagen opcional.  Los mismos datos alimentan la vista
**Participantes** para la estadística anual.

**Todavía no se sube nada.**  El envío de los episodios a cba.media - a
mano desde el calendario y automáticamente después de la grabación -
llega en las próximas etapas; este capítulo crecerá con ellas.

Un *episodio* es una emisión de un programa en el calendario: el
«Matinal» del próximo lunes es un episodio, el del lunes siguiente es
el siguiente.

---

## 1. Perfiles del equipo de redacción

**Ajustes → Equipo de redacción** lista las personas detrás de los
programas.

| Campo | Significado |
|---|---|
| **Nombre** | Tal como debe aparecer en cba.media y en la estadística. |
| **Correo electrónico (opcional)** | Para su propia referencia. |
| **Usuario (opcional)** | Vincula el perfil con una cuenta de RASTATIME. Un perfil no necesita cuenta: la mayoría de los redactores nunca inicia sesión. |
| **Activo** | Solo los perfiles activos se ofrecen en el formulario del programa.  Un perfil desactivado sigue en los programas a los que ya pertenece. |

**Editar** carga el perfil en el formulario sobre la tabla;
**Eliminar** quita el perfil del equipo de cada programa tras una
confirmación.  La columna **Programas** cuenta los programas de un
perfil.

Los Program Managers y los Admins abren esta página.

---

## 2. Valores del programa: sección «Publicación»

Edite un programa (calendario → clic derecho → **Editar programa**, o
un programa nuevo) y abra la sección **Publicación**, entre **Who** y
**Style**.  Los valores valen para cada episodio del programa mientras
un episodio no fije los suyos.

| Campo | Significado |
|---|---|
| **Equipo de redacción** | Marque los perfiles de las personas detrás del programa. Se envían a cba.media como redactores y aparecen en la vista Participantes. |
| **Participantes** | Cuántas personas participan normalmente en un episodio (0-999). Cuenta en Estadísticas → Participantes. |
| **ID del pódcast en CBA** | El número del pódcast (serie) en cba.media al que pertenecen los episodios. |
| **Licencia** | Licencia predeterminada de los episodios: Todos los derechos reservados, CC BY-NC-ND, CC BY-ND, CC BY-NC, CC BY-SA, CC BY, CC0, Dominio público. |
| **ID del tema en CBA** | El número del tema (categoría) en cba.media. |
| **Idiomas** | Hasta tres códigos de idioma, p. ej. `de, en`. |
| **Etiquetas** | Etiquetas para cba.media, separadas por comas. |
| **Teaser predeterminado** | Se usa en cada episodio sin teaser propio. |
| **Contiene música protegida (AKM)** | Los episodios suelen contener música protegida por derechos de autor. |

La sección no aparece en **Editar emisión**: pertenece al programa
completo.  Los datos de un solo episodio se editan en el diálogo
**Episodio...** (§3).

> **¿De dónde salen los números de CBA?**  Abra el pódcast o el tema
> en cba.media; el número aparece en su dirección o en su página.  La
> próxima etapa ofrecerá una lista para elegir.

---

## 3. Datos del episodio: «Episodio...»

Clic derecho en una emisión del calendario → **Episodio...**.  La
entrada está disponible antes y después de la emisión - la imagen se
puede añadir después - para Admins, Program Managers y los
presentadores del programa.

| Campo | Significado |
|---|---|
| **Título** | Vacío: el nombre del programa y la fecha, en gris como sugerencia. |
| **Teaser** | Un breve resumen. Vacío: el teaser predeterminado del programa. |
| **Descripción** | El texto del episodio: el mismo campo que la **descripción de instancia** del formulario del programa. |
| **Participantes** | Solo si este episodio difiere del programa, p. ej. con invitados. El valor del programa aparece en gris. |
| **Imagen del episodio** | Opcional, JPG o PNG de hasta 10 MB. Elegir un archivo lo sube enseguida; **Quitar imagen** lo borra. Sin imagen, cba.media muestra la del pódcast. |
| **Licencia de la imagen** / **Pie de imagen** | Licencia y crédito de la imagen (p. ej. quién la fotografió). |

La columna derecha muestra además lo que el episodio toma del programa
(equipo de redacción, ID del pódcast en CBA, licencia), y la línea
superior indica si el episodio ya se emitió y si su grabación está en
la biblioteca.

**Guardar** almacena los campos de texto; la imagen se guarda en cuanto
se elige.  Las imágenes de episodio están en la carpeta de la
biblioteca bajo `imported/episode-images/<emisión>/` y forman parte del
espejo de medios de la [Copia de seguridad](./BACKUP.md).

> **Planifique cerca de la emisión.**  Cuando cambia el patrón de
> repetición de un programa, el calendario vuelve a crear sus emisiones
> futuras, y sus datos de episodio se pierden con ellas.  Introduzca
> títulos e imágenes para las próximas semanas, no con meses de
> antelación.

---

## 4. Vista de participantes

**Estadísticas → Participantes** cuenta los participantes por programa
y año (hora de la estación): las cifras de la estadística anual.

* **Año**: el año en curso muestra el recuento hasta hoy.
* **Solo programas sin valor**: los programas que se emitieron pero aún
  no tienen *Participantes*.  Revise esta lista una vez; ponga `0` en
  los programas automatizados o retransmitidos.
* **Descargar CSV**: la tabla y los totales como archivo de hoja de
  cálculo.

Cuentan los episodios **emitidos** en el año (terminados, no
eliminados).  Las retransmisiones del antiguo tipo LibreTime quedan
fuera; los programas configurados como [repetición de otro
programa](./CALENDAR.md) aparecen con la marca **Repetición**: ponga su
valor en `0` si sus personas ya cuentan en el original.

| Columna / total | Significado |
|---|---|
| **Episodios emitidos** | Episodios del programa en el año. |
| **Participantes** | El valor del programa; el total suma los valores de todos los programas. |
| **Episodios con valor propio** | Episodios cuyo diálogo fija otro número. |
| **Participaciones** | Los participantes de cada episodio sumados (un episodio con valor propio cuenta con ese valor). |
| **Perfiles de redacción** (total) | Perfiles distintos en los equipos de los programas emitidos: cada persona una vez. |
| **Programas sin valor** (total) | En naranja mientras haya alguno. |

Una persona en varios programas cuenta una vez por programa en
**Participantes**; el total de perfiles cuenta a cada persona una sola
vez.

Los Program Managers y los Admins abren esta página.

---

## 5. Preguntas frecuentes

### «Marqué perfiles, pero no aparecen en la vista.»

La vista solo lista los programas **emitidos** en el año elegido.  Un
programa nuevo aparece en cuanto termina su primer episodio.

### «La sección Publicación falta o está en gris.»

Falta en **Editar emisión**: la sección pertenece al programa completo;
para un episodio use **Episodio...**.  Está en gris si usted no es
Program Manager ni Admin.

### «Falta Episodio... en el menú.»

La entrada aparece para Admins, Program Managers y los presentadores
del programa, y no en las emisiones de retransmisión del antiguo tipo
LibreTime.

---

## Adónde ir después

* [Calendario](./CALENDAR.md): el formulario del programa y el menú
  contextual.
* [Grabación por programa](./RECORD_PER_SHOW.md): la grabación que se
  convierte en el audio del episodio.
* [Analytics](./ANALYTICS.md): las demás páginas de estadísticas.
* [Configuración](./SETTINGS.md): cada página del menú de ajustes.
