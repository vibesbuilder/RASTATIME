# Automatización de teasers

> **Dónde está en el manual.** Biblioteca → editor de pista, campos
> **Teaser para el programa** y **Tipo de teaser**; Biblioteca → Smart
> Blocks, criterios **Teaser: programa**, **Teaser: tipo**, **Teaser:
> encaja con la parrilla**.  Lea primero [Biblioteca](./LIBRARY.md) § 3
> (bloques inteligentes) y
> [Listas de carga automática](./AUTOLOADING_PLAYLISTS.md): la
> automatización es un criterio de bloque inteligente que la carga
> automática emite.
>
> **Qué reemplaza esta función.** Colocar a mano, día tras día, los
> jingles «hoy» y «mañana» de cada programa, antes y después de las
> noticias y en los programas musicales.

Una emisora conoce tres tipos de teasers: un **teaser de programa** que
simplemente anuncia un programa («Around the World - cada jueves a
las 11»), un **teaser del día «hoy»** («Around the World - hoy a
las 11») y un **teaser del día «mañana»**.  Cuál encaja depende del día
en que suena el jingle y del calendario.  Desde 2026-10-16 la biblioteca
sabe qué programa anuncia un jingle y cómo, y un criterio de bloque
inteligente elige los jingles que encajan con el día del programa que
se rellena.

---

## 1. Vincular un jingle con su programa

Abra el jingle en el editor de pista (Biblioteca → lápiz o doble clic) y
establezca

| Campo | Significado |
|---|---|
| **Tipo de teaser** | **Teaser de programa (cualquier día)**, **Teaser del día: «hoy»** o **Teaser del día: «mañana»**.  Elíjalo primero: la lista de programas permanece atenuada hasta que haya un tipo, y un guardado con programas sin tipo se rechaza. |
| **Teaser para los programas** | los programas que anuncia este jingle; marque uno o varios, una casilla por programa como en el pool de peticiones.  La lista contiene cada programa con una emisión próxima, con su siguiente hora (`bbc (Sat 12:00)`) para distinguir programas homónimos; los huecos de noticias de cada hora son programas distintos y un solo jingle «BBC hoy» puede anunciarlos todos.  Nada seleccionado = no es teaser; volver a poner el tipo en *None* vacía la lista. |

Para muchos jingles a la vez, selecciónelos en la biblioteca y use
**Edit** (edición masiva): los mismos dos campos; nada seleccionado
conserva un campo, *None* quita los vínculos, los programas elegidos
sustituyen la lista, y necesitan un tipo en el mismo guardado, porque las
pistas seleccionadas aún pueden no tenerlo.  La columna de biblioteca
**Teaser** (selector de columnas, oculta por defecto) muestra `Nombre
del programa (today)` y se puede buscar, de modo que «Teaser contiene
Worldwide» lista todos los jingles de ese programa.

Un jingle tiene un tipo y anuncia uno o varios programas; encaja en
cuanto encaja uno de sus programas.  Dos jingles pueden, por supuesto,
anunciar el mismo programa con tipos distintos.

## 2. Los criterios de bloque inteligente

| Criterio | Modificadores | Valor | Coincide con |
|---|---|---|---|
| **Teaser: programa** | es / no es | un programa | los jingles que anuncian ese programa (entre otros) |
| **Teaser: tipo** | es / no es | teaser de programa, hoy, mañana | los jingles de ese tipo |
| **Teaser: encaja con la parrilla** | es | el día del programa que se rellena | véase abajo |

**Teaser: encaja con la parrilla** es la automatización.  «El día» es el
día del calendario (zona horaria de la emisora) del *hueco* para el que
se expande el bloque: el inicio del programa para una lista de intro de
carga automática, el final del programa para el outro, la posición
actual para la lista de contenido y, cuando arrastra un bloque a un
programa a mano, el final de la fila tras la que lo suelta.  Con ese
día *D* y el instante *T* del hueco:

* un teaser **«hoy»** encaja cuando su programa tiene una emisión el
  día *D* que empieza después de *T*;
* un teaser **«mañana»** encaja cuando su programa tiene una emisión el
  día *D + 1*;
* un **teaser de programa** encaja cualquier día, salvo que su programa
  haya *terminado por hoy*: tuvo una emisión el día *D* que acabó antes
  de *T* y no tiene otra posterior ese día;
* un jingle nunca encaja con el programa cuya instancia se está
  rellenando: un programa no se anuncia a sí mismo.

Una emisión cancelada o movida se lleva, por tanto, sus teasers del día:
el criterio mira el calendario en el momento del relleno, no una lista
fija.

## 3. Rotación: ningún jingle dos veces en un programa

Combine el criterio con **Exclude tracks played lately** (por ejemplo
3 horas).  Desde 2026-10-16 ese filtro cuenta también las filas
**planificadas**: una pista programada dentro de la ventana, antes o
después del hueco, incluidas las filas que un bloque anterior del mismo
relleno acaba de colocar en el mismo programa, queda excluida aunque
todavía no haya sonado.  Dos bloques de teasers en un programa nunca
sacan el mismo jingle, y un jingle planificado en el programa anterior
no vuelve en el siguiente.  Esto vale para todo bloque inteligente con
el filtro activado, música incluida.

## 4. Recetas

**Bloque de noticias (p. ej. el programa BBC de cada hora).**  Dé al
programa una lista de intro y una de outro de carga automática, cada una
con un bloque inteligente dinámico: *1 elemento*, criterio *Teaser:
encaja con la parrilla es el día del programa que se rellena*, *Exclude
tracks played lately 3 h*.  El hueco debe tener sitio para los jingles:
un programa de 7 minutos con un stream de 7 minutos no lo tiene.

**Programas musicales.**  Sustituya los bloques de teasers del día hechos
a mano en sus listas de carga automática por ese mismo bloque.  Conserve
un segundo bloque *Teaser: tipo es Teaser de programa* para los
programas que aún no tienen teasers del día.

**Un solo programa.**  *Teaser: programa es Worldwide* junto con
*Teaser: encaja con la parrilla* da los jingles de ese programa solo
cuando encajan.

## 5. Importar/Exportar

[Importar/Exportar](./IMPORT_EXPORT.md) lleva los criterios en
`blocks.json`: `teaser_show` por nombre de programa (el primer programa
con ese nombre al importar), `teaser_type` como `show`, `today` o
`tomorrow`, `teaser_fits` con el valor `yes`.  Los vínculos de los
propios jingles son metadatos de los archivos y no forman parte del
paquete.

## 6. Preguntas frecuentes

### «Generate en el editor de bloques inteligentes muestra otros jingles que los que recibe el programa.»

El editor no tiene hueco: toma *ahora* como instante y no excluye ningún
programa.  La elección real ocurre al rellenar el programa.

### «Un programa desapareció de la lista.»

La lista contiene programas con una emisión próxima.  Un jingle
conserva su vínculo con un programa que ya no la tiene; el editor lo
sigue mostrando, el criterio simplemente no encuentra un día que
encaje.

### «No se elige nada.»

Compruebe que los jingles llevan programa y tipo, que el programa
realmente tiene una emisión ese día y que los demás criterios del bloque
(tipo de pista, género) no los excluyen.  Hasta que se hayan ejecutado las
migraciones de base de datos 0069 y 0070, el criterio devuelve un conjunto vacío
y el registro lo dice.

## Véase también

* [Biblioteca](./LIBRARY.md) § 3: criterios de bloques inteligentes,
  límites y filtros de exclusión.
* [Listas de carga automática](./AUTOLOADING_PLAYLISTS.md): listas de
  intro, outro y contenido que llevan los bloques de teasers.
* [Calendario](./CALENDAR.md): las emisiones que lee el criterio.
