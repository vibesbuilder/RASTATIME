# Archivo: productores, episodios, archivo en línea, participantes

> **Dónde está en el manual.** Ajustes → **Archivo** (productores,
> cuentas de CBA); Calendario → formulario del programa,
> sección **Archivo**; Calendario → clic derecho en una emisión →
> **Archivar en línea**; Estadísticas → **Participantes** y
> **Estado del archivo** (en la interfaz en inglés: Settings →
> Archiving, Archiving, Archive Online, Analytics → People Involved y
> Archive Status).  Lea primero
> [Calendario](./CALENDAR.md) y
> [Grabación por programa](./RECORD_PER_SHOW.md): el audio de un
> episodio archivado es la grabación del programa.
>
> **Qué hace esta función.** Archiva los episodios de sus programas en
> [cba.media](https://cba.media) (el archivo de las radios libres de
> Austria) sin subirlos a mano, y cuenta a las personas que hacen la
> programación para la estadística anual.
>
> **Por qué «Archivo».** En RASTATIME, «publicar» se refiere al pódcast
> de la emisora (My Podcast).  Llevar un episodio a cba.media se llama
> por eso *archivar en línea*, para no confundir ambas cosas.

Un *episodio* es una emisión de un programa en el calendario: el
«Matinal» del próximo lunes es un episodio, el del lunes siguiente es
el siguiente.

**Estado de las etapas.**

| Etapa | Qué | Estado |
|---|---|---|
| 1 | Productor, valores del programa, datos del episodio, participantes | desde el 2026-11-03 |
| 2 | Archivar un episodio en línea a mano desde el calendario | desde el 2026-11-03 |
| 3 | Archivar cada episodio automáticamente tras la grabación | desde el 2026-11-03 |

---

## 1. Productores

**Ajustes → Archivo** lista en su parte superior, **Productores**,
quién hace los programas: una persona o un equipo cada uno.  Cada
programa elige un productor (§3).  (Hasta el 2026-11-04 *Equipos de
redacción*; cba.media los llama *redacción*.)

| Campo | Significado |
|---|---|
| **Nombre** | Tal como debe aparecer en cba.media (como redacción) y en la estadística. |
| **Correo electrónico (opcional)** | Para su propia referencia. |
| **Usuario (opcional)** | Vincula el productor con una cuenta de RASTATIME, p. ej. la de la persona responsable. Un productor no necesita cuenta. |
| **Activo** | Solo los productores activos se ofrecen en el formulario del programa.  Un productor desactivado sigue en los programas que ya lo tienen. |

**Editar** carga el productor en el formulario sobre la tabla;
**Eliminar** lo quita de cada programa tras una confirmación.  La
columna **Programas** cuenta los programas de un productor.

Los Program Managers y los Admins abren esta página; los Program
Managers solo ven esta parte.

---

## 2. Cuentas de CBA

Cada programa se archiva con un usuario de cba.media: los episodios
aparecen con su nombre.  La parte inferior de **Ajustes → Archivo**,
**Cuentas de CBA**, guarda estos usuarios; solo los Admins la ven.

| Campo | Significado |
|---|---|
| **Nombre de la cuenta** | Su nombre para la cuenta, p. ej. la persona o la emisora. |
| **Usuario de CBA** | El nombre de usuario en cba.media. |
| **Contraseña de aplicación** | Se crea en cba.media en el perfil del usuario (*contraseña de aplicación* de WordPress, no la contraseña de acceso). RASTATIME la guarda y nunca vuelve a mostrarla; un campo vacío conserva la guardada. |

* **Probar la conexión** pregunta a cba.media, con los datos guardados,
  quién es el usuario y si puede subir archivos (roles admin, author,
  podcaster, stationmanager, channelmanager).  No se sube nada.
* **Eliminar** quita la cuenta; los programas que la usan se quedan sin
  cuenta hasta que elija otra.
* **Límite de subida**: la subida comparte la línea de internet con los
  streams de los oyentes, así que RASTATIME envía como máximo a esta
  velocidad (por defecto 4 Mbit/s: una hora de audio a 320 kbit/s tarda
  unos cinco minutos).
* **Archivo automático**: cuántos minutos después del final de un
  episodio lo suben los programas con *Archivar automáticamente* (§3)
  (por defecto 30): tiempo para completar el episodio o marcar *No
  archivar este episodio automáticamente*.

---

## 3. Valores del programa: sección «Archivo»

Edite un programa (calendario → clic derecho → **Editar programa**, o
un programa nuevo) y abra la sección **Archivo**, entre **Who** y
**Style**: como las demás secciones, aparece plegada; haga clic en su
título.  Los valores valen para cada episodio del programa mientras un
episodio no fije los suyos.

| Campo | Significado |
|---|---|
| **Productor** | Quién hace el programa: una persona o un equipo, elegido de la lista (uno por programa, §1). El nombre se envía a cba.media como redacción y aparece en Estadísticas → Participantes. |
| **Cuenta de CBA** | El usuario de CBA con el que se archivan los episodios (§2). |
| **Visibilidad en cba.media** | *Público* (listado), *No listado* (accesible solo por su dirección) o *Privado* (visible solo para el usuario de CBA). |
| **ID del pódcast en CBA** | El número del pódcast (serie) en cba.media al que pertenecen los episodios. Sin él, cba.media mantiene la entrada privada. |
| **Licencia** | Licencia de los episodios. El icono de ayuda muestra qué licencia responde a las preguntas del formulario web de la CBA (véase abajo). |
| **Tema de CBA** | El tema (categoría) en cba.media, elegido de la lista que RASTATIME obtiene una vez al día. Antes de la primera obtención, el campo admite el número. |
| **Idiomas** | Hasta tres códigos de idioma que conoce la CBA, p. ej. `de, en`. |
| **Etiquetas** | Etiquetas para cba.media, separadas por comas. |
| **Teaser predeterminado** | Se usa en cada episodio sin teaser propio. |
| **Contiene música protegida** | Los episodios suelen contener música protegida (AKM); cba.media restringe entonces la descarga. |
| **Archivar automáticamente** | Archivar cada episodio nuevo en cba.media por sí solo (§5, *Automáticamente*). Necesita cuenta de CBA, tema, idioma y licencia; junto a la casilla: desde cuándo está activado. Si el programa no tiene descripción, una nota bajo la casilla indica que un episodio sin la suya recibe entonces el nombre del programa como texto. |

**¿Qué licencia?**  El formulario web de la CBA hace tres preguntas; la
licencia las responde:

| Licencia | ¿Citar al autor? | ¿Uso comercial? | ¿Adaptaciones? |
|---|---|---|---|
| CC BY | sí | sí | sí |
| CC BY-NC | sí | no | sí |
| CC BY-ND | sí | sí | no |
| CC BY-NC-ND | sí | no | no |
| CC0 | no | sí | sí |

*Todos los derechos reservados* no permite nada de ello sin preguntar;
*CC Sampling+* permite reutilizar fragmentos, la obra completa solo sin
fines comerciales; *Dominio público* no conserva ningún derecho.

El número de participantes ya no está en esta sección (desde el
2026-11-04): se encuentra en la sección **What**, debajo de **Producción
propia**, como **Presentadores** (Hosts involved, 0-999; *Número de
participantes* hasta el 2026-11-07), y aparece en cuanto se marca
**Producción propia**; cuenta en Estadísticas → Participantes (§6).

En **Editar emisión** la sección se muestra **de solo lectura** con los
valores del programa (desde el 2026-11-04; antes no aparecía): pertenece
al programa completo.  Los datos de un solo episodio se editan en
**Archivar en línea** (§4).

> **¿De dónde sale el número del pódcast?**  Abra el pódcast en
> cba.media; el número aparece en su dirección o en su página (la CBA
> solo muestra los pódcasts de una emisora a usuarios con sesión
> iniciada).

---

## 4. Datos del episodio: «Archivar en línea»

Clic derecho en una emisión del calendario → **Archivar en línea**
(hasta el 2026-11-03 *Episodio...*).  La entrada está disponible antes
y después de la emisión - la imagen se puede añadir después - para
Admins, Program Managers y los presentadores del programa.

| Campo | Significado |
|---|---|
| **Título** | Vacío: el nombre del programa y la fecha, en gris como sugerencia. |
| **Teaser** | Un breve resumen. Vacío: el teaser predeterminado del programa. |
| **Descripción** | El texto del episodio, en cba.media el texto de la entrada. Vacío: la descripción del programa o, si no tiene, el nombre del programa (en gris). Es el único lugar para editarla (Editar emisión ya no la muestra). |
| **Invitados** (Guests involved) | Los invitados de este episodio (0-999), contados además de los presentadores del programa (desde el 2026-11-07; antes el campo se llamaba *Participantes* y sustituía el valor del programa). Vacío significa sin invitados; la línea bajo el campo muestra los presentadores del programa. |
| **Fecha de producción** | La exige cba.media. Vacía: el día de la emisión. Indíquela si el episodio se produjo antes. |
| **No archivar este episodio automáticamente** | Para pruebas, episodios cancelados o problemas de derechos. Se aplica con el archivo automático (§5); archivar a mano sigue siendo posible. |
| **Imagen del episodio** | Opcional, JPG o PNG de hasta 10 MB. Elegir un archivo lo sube enseguida; **Quitar imagen** lo borra. Sin imagen, cba.media muestra la del pódcast. |
| **Licencia de la imagen** / **Pie de imagen** | Licencia y crédito de la imagen (p. ej. quién la fotografió), pie de hasta 500 caracteres. |

La columna derecha muestra lo que el episodio toma del programa (productor,
cuenta de CBA, pódcast, licencia, visibilidad); la línea
superior indica si el episodio ya se emitió y si su grabación está en
la biblioteca.

**Guardar** almacena los campos de texto; la imagen se guarda en cuanto
se elige.  Las imágenes de episodio están en la carpeta de la
biblioteca bajo `imported/episode-images/<emisión>/` y forman parte del
espejo de medios de la [Copia de seguridad](./BACKUP.md).

> **Planifique cerca de la emisión.**  Cuando cambia el patrón de
> repetición de un programa, el calendario vuelve a crear sus emisiones
> futuras, y sus datos de episodio se pierden con ellas.  (**Editar
> emisión** de un solo episodio los conserva.)  Introduzca títulos e
> imágenes para las próximas semanas, no con meses de antelación.

---

## 5. Archivar en línea

El bloque inferior de **Archivar en línea** - **Archivo en línea
(cba.media)** - muestra el estado del episodio en cba.media.  Los Admins
y los Program Managers archivan desde aquí; los presentadores ven el
estado.

1. Complete lo que el bloque lista en *Antes de poder archivar este
   episodio*: normalmente la cuenta de CBA, el tema, el idioma y la
   licencia del programa.  No hace falta una descripción: si no la
   tienen ni el episodio ni el programa, el nombre del programa se
   convierte en el texto de la entrada.
2. Pulse **Archivar en línea ahora** y elija el audio:
   * **La grabación de este episodio**: la copia que
     [Grabación por programa](./RECORD_PER_SHOW.md) puso en la
     biblioteca;
   * **Un archivo de la biblioteca**: búsqueda por título o autor, p. ej.
     el archivo preproducido sin jingles (solo MP3, OGG y Opus; la CBA no
     acepta M4A).
3. **Iniciar carga**.  El servicio en segundo plano (RASTATIME-WORKER)
   recoge la tarea en unos 15 segundos; el bloque muestra el progreso y
   después el enlace a la entrada.

El título, el teaser, la descripción, la imagen y los valores del
programa se leen al empezar la subida.  **Los cambios después de la
subida se hacen en cba.media**: la interfaz de la CBA no permite
modificar ni sustituir una entrada.

| Estado | Significado, qué hacer |
|---|---|
| *Esperando la subida* | En cola; el worker la inicia en breve. |
| *Subiendo a cba.media: n %* | En curso, limitada al límite de subida (§2). |
| *Archivado en cba.media como entrada n* | Terminado; el número enlaza la entrada. |
| *Esperando otro intento* | cba.media no estaba disponible u ocupado; RASTATIME vuelve a intentarlo tras 2, 5, 15, 30 minutos ... durante 24 horas como máximo. |
| *La subida falló: motivo* | Faltan datos, o cba.media la rechazó (p. ej. contraseña de aplicación incorrecta, tema desconocido). Corrija la causa y **Archivar en línea ahora** de nuevo. |
| *No está claro si se creó la entrada* | La conexión se cortó durante la subida. La entrada quizá exista: compruébelo en cba.media y luego **Vincular una entrada existente** o vuelva a archivar. RASTATIME nunca repite este caso por sí mismo, para que ningún episodio aparezca dos veces. |

**Vincular una entrada existente** sirve para una entrada que ya está en
cba.media: subida allí a mano o tras una subida *dudosa*.  Escriba su
número (o su dirección con `?p=<número>`) y pulse el botón: RASTATIME
marca el episodio como archivado y no sube nada.  Un campo vacío quita
el vínculo.  El icono de ayuda junto al botón dice lo mismo.

> **Detener el worker** solo pausa las subidas; la emisión no se ve
> afectada.  Una tarea que estaba en curso se comprueba tras el
> reinicio: si no había salido ningún byte, empieza de nuevo; si no,
> termina como *no está claro*.

### Automáticamente

Si en la sección *Archivo* del programa (§3) está marcado **Archivar
automáticamente**, RASTATIME archiva por sí solo cada episodio nuevo,
siempre con la grabación:

1. El episodio termina; [la grabación por programa](./RECORD_PER_SHOW.md)
   deja la grabación en la biblioteca en segundos (el programa debe
   grabar y *Copy Show Recordings into Library* debe estar activado en
   Ajustes → Local Machine).
2. Tras el tiempo de espera (Ajustes → Archivo, 30 minutos por
   defecto), el servicio en segundo plano comprueba el episodio y pone la
   subida en cola, con la visibilidad del programa.
3. Si aún falta algo (la grabación, un tema ...), el episodio
   espera y se vuelve a comprobar cada cinco minutos, hasta 24 horas.
   Después el proceso se da por vencido; el diálogo muestra *El archivo
   automático se dio por vencido* con el motivo.

Nunca se archivan automáticamente:

* los episodios que terminaron **antes** de marcar la casilla - no se
  recupera nada; archive a mano los episodios anteriores;
* las retransmisiones y los programas creados como *Repetición de otro
  programa*;
* los episodios con **No archivar este episodio automáticamente** (§4);
* los episodios ya archivados o vinculados, o cuya subida alguien inició
  a mano - el archivo automático no los toca;
* los episodios cuya grabación cubre menos de la mitad del programa
  (p. ej. una grabación interrumpida).

**Archivar en línea** muestra en el bloque *Archivo en línea* lo que el
archivo automático prevé para el episodio, p. ej. *Se archiva
automáticamente a partir del 2026-11-10 14:30, en cuanto no falte nada
de lo de abajo*.

Cuando una subida automática falla, queda sin aclarar o se abandona, el
aviso en la parte superior de la página nombra el episodio durante siete
días, hasta que se archiva a mano o se vincula su entrada; los Program
Managers y los Admins encuentran allí un enlace a **Estadísticas →
Estado del archivo** (§7).

> **No se detecta:** un programa de sustitución emitido en lugar de un
> programa en directo (no vino el presentador) se archiva como el
> programa.  Active el archivo automático para programas que funcionan
> de forma fiable; si ocurre, borre la entrada en cba.media.

---

## 6. Participantes

**Estadísticas → Participantes** cuenta los participantes por
producción propia y año (hora de la estación): las cifras de la
estadística anual.  Solo cuentan los programas con **Producción propia**
(Editar programa → What).  Un programa al que se le quita la casilla
conserva sus números, pero queda fuera.

Desde el 2026-11-07 el recuento sigue a las personas, no a los episodios:

* Los **Presentadores** (Hosts involved; Editar programa → What, justo
  debajo de **Producción propia**) son las personas que están en cada
  episodio.  Cuentan **una vez por programa y año**, sin importar
  cuántos episodios se emitieron.
* Los **Invitados** (Guests involved; Archivar en línea en el
  calendario) son los invitados de un episodio.  Cuentan **en cada
  episodio** y se suman.
* **Participantes** = presentadores + invitados.

Ejemplo: un programa semanal con 2 presentadores se emitió 40 veces;
tres episodios tuvieron invitados (1, 2 y 1).  Participantes: 2 + 4 = 6.

* **Año**: el año en curso muestra el recuento hasta hoy.
* **Solo programas sin valor**: las producciones propias que se
  emitieron pero aún no tienen *Presentadores*.  Revise esta lista una
  vez; ponga `0` en los programas automatizados o retransmitidos.
* **Descargar CSV**: la tabla y los totales como archivo de hoja de
  cálculo.

Cuentan los episodios **emitidos** en el año (terminados, no
eliminados).  Las retransmisiones del antiguo tipo LibreTime quedan
fuera.  Los programas configurados como [repetición de otro
programa](./CALENDAR.md) aparecen con la marca **Repetición** y no
cuentan nada: sus personas ya se contaron con el original.  Nunca
aparecen en *Programas sin valor*.

| Columna / total | Significado |
|---|---|
| **Producciones propias emitidas** (total) | Producciones propias con al menos un episodio emitido en el año, repeticiones incluidas. |
| **Episodios emitidos** | Episodios del programa en el año. |
| **Presentadores** | Los presentadores del programa, una vez al año; el total suma los presentadores de todos los programas. |
| **Invitados** | Los invitados de todos los episodios emitidos del programa sumados. |
| **Participantes** | Presentadores + invitados; el total es la cifra para la estadística. |
| **Programas sin valor** (total) | Producciones propias (sin repeticiones) sin *Presentadores*; en naranja mientras haya alguno. |

Una persona en varios programas cuenta una vez por programa; un
invitado que vuelve cuenta en cada episodio.  Las cifras son números, no
nombres: RASTATIME no puede saber que dos programas comparten un
presentador.  Los productores no se cuentan.

Los Program Managers y los Admins abren esta página.

---

## 7. Estado del archivo

**Estadísticas → Estado del archivo** (desde el 2026-11-04, en inglés
Analytics → Archive Status) muestra en una sola página si los episodios
llegan a cba.media.  La abren los Program Managers y los Admins; el
aviso enlaza con ella.

* **En curso y en espera** - la subida en curso (la parte enviada,
  actualizada cada pocos segundos) y las que esperan: al servicio en
  segundo plano, o a un nuevo intento tras un problema de conexión (hora
  y motivo).  **Cancelar** detiene una subida en espera.  Una subida en
  curso no se puede cancelar: pertenece al servicio en segundo plano
  hasta que termina.
* **Pendiente (archivo automático)** - los episodios de los programas con
  *Archivar automáticamente* de los próximos 7 días y los ya emitidos que
  aún no están en cola, con su vencimiento:

  | Estado | Significado |
  |---|---|
  | *Aún no emitido: previsto ...* | El episodio aún está por llegar. |
  | *Emitido: previsto ...* | Corre el tiempo de espera (Ajustes → Archivo). |
  | *Previsto: se pone en cola en la próxima comprobación* | No falta nada; el servicio en segundo plano lo pone en cola en cinco minutos. |
  | *En espera, como máximo hasta ...* | Falta algo (columna **Falta**); después el archivo automático se da por vencido. |
  | *No se archiva automáticamente: ...* | *No archivar este episodio automáticamente* está marcado. |

  Antes de la emisión, **Falta** ya indica lo que le falta al programa
  (cuenta de CBA, tema, idioma, licencia): tiempo para completar el
  programa.
* **Problemas (últimos 30 días)** - subidas a mano o automáticas que
  fallaron, quedaron inciertas o se abandonaron, mientras el episodio no
  tenga entrada.  **Archivar de nuevo** vuelve a poner en cola el mismo
  audio (la grabación, si ese archivo ya no existe).  Tras una subida
  *incierta*, la página pregunta primero, porque puede que la entrada
  exista: compruébelo en cba.media y use **Vincular entrada…** (número o
  dirección) si está allí.  La línea desaparece en cuanto el episodio se
  archiva o se vincula.
* **Historial** - cada subida con hora, programa, episodio, quién la
  inició (*Automático* o el login), estado, enlace a la entrada, audio,
  tamaño, duración y nota.  Filtro por año, mes, estado, iniciado por y
  nombre del programa; **Descargar CSV** toma toda la lista filtrada (la
  página muestra las 500 más recientes).

La página se recarga sola cuando una subida empieza o termina.

---

## 8. Preguntas frecuentes

### «Falta Archivar en línea ahora.»

El botón aparece para Admins y Program Managers, y solo mientras el
episodio no esté archivado ni esperando una subida.

### «Probar la conexión dice que se rechazó el usuario o la contraseña.»

Use la *contraseña de aplicación* del perfil en cba.media, no la
contraseña con la que inicia sesión; los espacios que contiene no
importan.  Revise el nombre de usuario.

### «El tema es un campo numérico, no una lista.»

El servicio en segundo plano obtiene la lista de temas una vez al día.
Tras una instalación nueva o antes de que RASTATIME-WORKER se haya
ejecutado, el campo admite el número.

### «¿Comentarios en cba.media?»

La interfaz de subida de la CBA no tiene ajuste para ello; se aplica el
valor predeterminado del usuario de CBA.

### «Elegí un productor, pero el programa no aparece en la vista.»

La vista solo lista los programas **emitidos** en el año elegido.  Un
programa nuevo aparece en cuanto termina su primer episodio.

### «La sección Archivo está en gris.»

En **Editar emisión** es de solo lectura: la sección pertenece al
programa completo; para un episodio use **Archivar en línea**.  También
está en gris si usted no es Program Manager ni Admin.

### «Un episodio no se archivó automáticamente.»

Abra **Archivar en línea**: el bloque *Archivo en línea* indica el
motivo - el interruptor está desactivado, *No archivar automáticamente*
está marcado, el episodio terminó antes de activarlo, espera algo, o el
proceso se dio por vencido y por qué.  Archívelo a mano desde allí.
**Estadísticas → Estado del archivo** (§7) lista todos esos episodios
a la vez.

### «¿Dónde están Equipo de redacción y Cuentas de CBA?»

Desde el 2026-11-03 ambos están en una sola página, **Ajustes →
Archivo**: los productores arriba (hasta el 2026-11-04 *Equipos de
redacción*), las cuentas de CBA con el
límite de subida y el tiempo de espera debajo (solo Admins).

---

## Adónde ir después

* [Calendario](./CALENDAR.md): el formulario del programa y el menú
  contextual.
* [Grabación por programa](./RECORD_PER_SHOW.md): la grabación que se
  convierte en el audio del episodio.
* [Analytics](./ANALYTICS.md): las demás páginas de estadísticas.
* [Configuración](./SETTINGS.md): cada página del menú de ajustes.
