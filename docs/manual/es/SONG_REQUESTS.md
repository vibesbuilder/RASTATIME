# Peticiones de canciones (Song Requests)

> **Dónde está en el manual.** Lea primero
> [Biblioteca](./LIBRARY.md) → §3 Smart Blocks y
> [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) — las Song
> Requests se construyen por completo a partir de esas dos primitivas
> más un widget público para los oyentes. No se introduce ningún nuevo
> tipo de objeto «request».

Las **Song Requests** permiten que sus oyentes pidan pistas desde un
widget web público y que esas pistas suenen automáticamente dentro de
un programa normal, sin que un presentador tenga que hacer clic. Toda
la función se ensambla a partir de piezas que ya conoce:

- un **Smart Block** marcado como *Use requests* extrae las pistas que
  los oyentes han pedido realmente;
- una **Autoloading Playlist** que contiene ese bloque convierte un
  programa corriente en un **programa de peticiones** (request show);
- un pequeño **widget de incrustación** en su web pública recoge las
  peticiones.

No hay un interruptor «acepta peticiones» por programa ni una cola de
moderación separada. Un programa *es* un request show cuando su
Autoloading Playlist contiene un bloque *Use requests*; nada más.

---

## 1. La visión general

```
   OYENTE                   RASTATIME                     AL AIRE
   ┌─────────┐   petición   ┌──────────────────────┐
   │ Widget  │─────────────▶│ rastatime_song_request│
   │ (iframe)│   /api/v2    │  status = pending     │
   └─────────┘              │ cc_files.requested=t  │
                            └──────────┬────────────┘
                                       │  el request show se llena
                                       │  ~8 min antes del inicio
                            ┌──────────▼────────────┐   ┌──────────┐
                            │ bloque «Use requests»  │──▶│ Programa │
                            │  extrae los pending,    │   │ horario  │
                            │  más antiguo, 1 c/u     │   └──────────┘
                            └────────────────────────┘
```

Dos mitades independientes se encuentran en el medio:

1. Los **oyentes** abren el widget, ven el catálogo de pistas
   solicitables y envían una petición. La petición se registra y la
   pista se marca como «deseada».
2. Un **request show** —cualquier programa cuya Autoloading Playlist
   contenga un Smart Block *Use requests*— se llena con esas pistas
   deseadas unos minutos antes de salir al aire.

Las dos mitades solo están unidas por el **pool** de peticiones (§2) y
el criterio *Use requests* (§3). Usted configura ambos una vez;
después la función funciona sin supervisión.

---

## 2. El pool de peticiones — qué pueden pedir los oyentes

El **pool** es el catálogo de pistas que un oyente tiene permitido
pedir. Se define mediante uno o más Smart Blocks.

Abra **Settings → General → Song-Request Pool (Smart Blocks)**. El
campo es un desplegable al estilo del selector *Columns* de la
Biblioteca: haga clic en **Smart Blocks**, marque uno o más bloques,
haga clic fuera para cerrar.

```
   Song-Request Pool (smart blocks)   [ Smart Blocks ▾ ]
                                      ┌────────────────────┐
                                      │ ☑ Pool Indie / Alt │
                                      │ ☐ Jingles          │
                                      │ ☑ Catálogo petic.  │
                                      │ …                  │
                                      └────────────────────┘
```

El pool es la **unión** del catálogo de cada bloque marcado: las
pistas que cumplen los criterios de cada bloque (género, álbum, …),
*independientemente* de si ya han sido pedidas. No marque ninguno para
desactivar las peticiones por completo: el widget muestra entonces
«actualmente no disponible».

> **Cómo funciona por dentro.** Una tarea en segundo plano
> (`RequestablePoolSyncTask`, cada 5 min) expande la unión de los
> bloques seleccionados con el filtro de petición *ignorado* y escribe
> `cc_files.requestable = true` para cada miembro, borrándolo en todo
> lo demás. El endpoint público de búsqueda del catálogo filtra por
> ese indicador. Los identificadores de los bloques seleccionados
> residen en la clave cc_pref `requestable_pool_block_ids`.

---

## 3. El Smart Block «Use requests»

Un Smart Block se convierte en **fuente de peticiones** cuando marca
**Use requests** en el diálogo del Smart Block (Library → editar un
Smart Block → criterios avanzados).

Esto cambia lo que el bloque extrae:

| Estado | Qué selecciona el bloque |
|---|---|
| **Use requests OFF** (normal) | Todas las pistas que cumplen sus criterios (género, álbum, …). |
| **Use requests ON** | Solo las pistas que cumplen sus criterios **y** tienen una petición abierta (`cc_files.requested = true`). |

Hay dos órdenes disponibles, relevantes para los bloques de
peticiones:

- **Petición más antigua primero** — cola justa: quien pidió antes
  suena antes.
- **Más pedida primero** — popularidad: la pista con más peticiones
  pendientes suena antes.

> **Consejo para el operador.** El *mismo* bloque suele desempeñar
> ambos papeles: lo selecciona como **pool** en Settings (lo que usa
> su catálogo, ignorando el filtro de petición) *y* lo coloca en la
> playlist de un request show (donde el criterio *Use requests* le hace
> extraer las peticiones reales). Mantenga sus criterios de catálogo
> (p. ej. `genre = Indie or Alternative`) sensatos: limitan **ambas
> cosas**, lo que se puede pedir y lo que se extrae.

---

## 4. Construir un request show

Un request show es simplemente un programa con
[Autoloading Playlist](./AUTOLOADING_PLAYLISTS.md) cuya playlist
contiene al menos un bloque *Use requests*. Usted compone la playlist
como una **dramaturgia**: un orden fijo que el llenado recorre una
vez:

```
   Autoloading Playlist «Hora de peticiones»
   ──────────────────────────────────────────
   1. Smart Block · Use requests · 1 elem.   ◀── petición A
   2. Smart Block · StationID    · 1 elem.
   3. Smart Block · Use requests · 1 elem.   ◀── petición B (¡distinta!)
   4. Smart Block · StationID    · 1 elem.
   5. Smart Block · Use requests · 1 elem.   ◀── petición C (¡distinta!)
   6. Smart Block · Música · Límite «tiempo restante»  ◀── llena el resto
```

Cuando el programa se llena (§5), cada hueco *Use requests* extrae una
petición **distinta**, y el bloque final **«tiempo restante»** llena
el resto con música. Adjunte la playlist a un programa de la forma
habitual (**Editar programa → ¿Añadir Autoloading Playlist?**), y ese
programa es ahora un request show.

> **Puede reutilizar un solo bloque.** Colocar el *mismo* bloque *Use
> requests* en las posiciones 1, 3 y 5 funciona: el llenado resuelve
> cada posición por separado, así que tres colocaciones extraen tres
> peticiones distintas. No necesita tres bloques separados.

> **Por qué un bloque «tiempo restante» final.** Sin un bloque que
> llene el resto, un request show con solo un puñado de peticiones
> dejaría aire muerto tras la última petición. El bloque musical
> «tiempo restante» es la red de seguridad. Póngale **Repetir pistas =
> sí** (o un catálogo suficientemente grande) para que llene todo el
> resto en una pasada; con «repetir desactivado» llena con tanta
> variedad como permita su pool y puede dejar un pequeño hueco que el
> fallback del playout cubre.

---

## 5. Cómo y cuándo se llena un request show

Un request show se llena **una vez, unos minutos antes de empezar**,
no pista a pista mientras suena.

- Una tarea en segundo plano (`RequestShowFillTask`, cada 2 min) busca
  request shows que empiezan en los próximos **8 minutos** (el
  *lead*).
- Llena el programa recorriendo la playlist **posición por posición**,
  resolviendo un hueco cada vez. Tras cada hueco, saca la petición
  extraída del pool, de modo que el **siguiente** hueco *Use requests*
  extraiga otra pista.
- El bloque «tiempo restante» final llena el resto.
- Un programa completamente lleno se deja intacto en pasadas
  posteriores.

Este llenado de una pasada es **seguro frente al aire muerto**: el
programa está completo mucho antes de salir al aire. El compromiso
—elegido deliberadamente— es que una petición que llega *después* del
llenado (menos de ~8 min antes del inicio, o mientras el programa ya
está al aire) cae en el **siguiente** request show, no en el actual.

> **Hueco de petición vacío → pista aleatoria.** Si un hueco *Use
> requests* no tiene ninguna petición pendiente en el momento del
> llenado, **no** deja un hueco. Emite una pista **aleatoria** del
> propio catálogo de ese bloque (su género / criterios, ignorando el
> filtro de petición). Así, un request show sin peticiones emite igual
> una hora normal y acorde al formato; a medida que llegan peticiones,
> reemplazan las elecciones aleatorias hueco por hueco.

> **Cómo funciona por dentro.** `AutoPlaylistManager::`
> `fillRequestShows()` (lead `RASTATIME_REQUEST_FILL_LEAD_SECONDS`,
> por defecto 480) recorre `cc_playlistcontents` en orden, añade cada
> archivo/bloque con `addAutoloadItemToShow()` y ejecuta el paso de
> consumo entre huecos. El constructor de autoplaylist normal
> (§ Autoloading Playlists) omite deliberadamente los request shows
> para que ambos nunca entren en conflicto. Véase ARCHITECTURE §23.23.

---

## 6. El widget para los oyentes

El widget público se encuentra en:

```
   http://<su-emisora>/Embed/song-request
   http://<su-emisora>/Embed/song-request?theme=dark
```

Incrústelo en un `<iframe>` en su web (temas: `light`, `dark`,
`auto`). Muestra una tabla desplazable de cada pista solicitable
—carátula · artista / título · un botón **Request**— sin campo de
búsqueda ni paginación:

```
   ┌──────────────────────────────────────────────┐
   │ [carát.] Robb — Down with It         [Request]│
   │ [carát.] Leyya — Butter              [Request]│
   │          Viech — Steuermann          [Request]│
   │ …                                             │
   └──────────────────────────────────────────────┘
```

Un clic envía la petición y muestra una línea de estado: gracias, «ya
pedida recientemente» o «límite de peticiones alcanzado».

Salvaguardas integradas (sin necesidad de cola de moderación):

| Salvaguarda | Por defecto |
|---|---|
| **Límite de tasa** | 5 peticiones por hora por oyente |
| **Deduplicación** | el mismo oyente no puede volver a pedir la misma pista en menos de 30 min |
| **Restricción al catálogo** | solo las pistas del pool (§2) son listables / solicitables |

> **Las carátulas necesitan la API de terceros.** Las miniaturas de
> carátula proceden del endpoint de ilustración, protegido por
> **Settings → … → Allow 3rd party API**. Desactivado, la tabla se
> muestra solo en texto (artista / título), lo cual es perfectamente
> usable. Las pistas que simplemente no tienen ilustración también
> quedan en texto.

> **Cómo funciona por dentro.** El widget es una página iframe
> autónoma en JS vanilla (`/Embed/song-request`) que habla con dos
> endpoints Django públicos: `GET /api/v2/song-requests/search` (el
> catálogo) y `POST /api/v2/song-requests` (envío). Sin inicio de
> sesión, sin cookie. La IP en bruto del oyente nunca se almacena;
> solo un hash con sal, usado para el límite de tasa y la
> deduplicación.

---

## 7. El ciclo de vida de una petición

Cada petición pasa por cuatro estados:

| Estado | Se establece cuando | Significado |
|---|---|---|
| **pending** | el oyente la envía | esperando en el pool a ser extraída |
| **queued** | el llenado planifica su pista | extraída a un programa; fuera del pool |
| **played** | la pista ha sonado | hecho (conservado para el historial) |
| **expired** | TTL vencido sin emitir | nunca extraída; barrida del pool |

- Cuando una petición se **planifica**, su pista sale del pool
  (`cc_files.requested` borrado) para que el siguiente hueco extraiga
  otra cosa, y la petición pasa a **queued**.
- Una tarea basada en el horario marca **played** una vez que el hueco
  de la pista ha pasado (`RequestPlayedTask`, cada 2 min) —elegido en
  lugar de un hook del lado del playout, para no tocar nunca la ruta
  de emisión en directo.
- Si un **request show se elimina** antes de emitir sus pistas, sus
  peticiones planificadas no se pierden: el mismo barrido las devuelve
  a **pending** (su pista ya no está en ningún planning), para que el
  siguiente request show reintente el deseo.
- El barrido de expiración (`RequestExpiryTask`, cada 10 min) hace
  expirar cualquier petición aún **pending** tras el TTL —por defecto
  **8 horas**, ajustable con `RASTATIME_REQUEST_EXPIRY_HOURS`— y
  recalcula el agregado del pool para que una pista cuya última
  petición expiró salga limpiamente del catálogo.

---

## 8. Lista de verificación del operador

Para poner en marcha las Song Requests desde cero:

1. **Cree un Smart Block de peticiones.** Library → nuevo Smart Block
   → defina sus criterios de catálogo (p. ej. `genre = Indie or
   Alternative`), marque **Use requests**, elija **Orden: Petición más
   antigua primero**, **Límite: 1 elemento**. Guarde.
2. **Selecciónelo como pool.** Settings → General → **Song-Request
   Pool** → marque el bloque. (En 5 min sus pistas se vuelven
   solicitables.)
3. **Componga la playlist de dramaturgia** (§4): su bloque de
   peticiones en varias posiciones, jingles/IDs entre medias, un
   bloque musical **«tiempo restante»** al final (con **Repetir pistas
   = sí**).
4. **Adjúntela a un programa** como Autoloading Playlist (§4).
5. **Incruste el widget** (§6) en su web; opcionalmente active **Allow
   3rd party API** para las carátulas.

Eso es toda la configuración. A partir de ahí, los oyentes piden y el
programa se llena solo ~8 min antes de cada emisión.

---

## 9. Preguntas frecuentes

### «El widget no muestra pistas.»

El pool está vacío. O no hay ningún bloque seleccionado en **Settings
→ Song-Request Pool**, o los criterios del bloque seleccionado no
coinciden con nada, o la sincronización del pool (5 min) aún no se ha
ejecutado. Compruebe que el bloque muestra pistas en la Library;
espere un ciclo de sincronización.

### «Mi request show salió al aire pero no sonó ninguna pista pedida.»

Lo más probable es que no hubiera peticiones *abiertas* en el momento
del llenado (más de ~8 min antes del inicio), así que cada hueco *Use
requests* recurrió a una pista aleatoria del catálogo (§5). Envíe
algunas peticiones y observe el *siguiente* request show. Confirme
también que el bloque de peticiones de la playlist tiene **Use
requests** marcado y que sus criterios coinciden con el género de las
pistas pedidas.

### «Varios huecos de petición sonaron con la misma canción.»

Eso no debería ocurrir: el llenado consume cada petición al
planificarla, de modo que los huecos sucesivos extraen pistas
distintas. Si ve duplicados, la playlist probablemente añade la
playlist *entera* de forma repetida (comportamiento antiguo);
asegúrese de estar en una build con llenado posición por posición
(ARCHITECTURE §23.23).

### «Hay aire muerto al final de un request show.»

El bloque «tiempo restante» final se quedó sin pistas elegibles.
Póngale **Repetir pistas = sí**, amplíe sus criterios de género o
relaje una ventana de «excluir artistas reproducidos recientemente»
para que pueda llenar todo el resto.

### «Llegan peticiones después de empezar el programa, ¿suenan?»

No en ese programa. El llenado es de una sola pasada, ~8 min antes del
inicio (decisión del operador: seguridad frente al aire muerto por
encima de la inserción a mitad de programa). Las peticiones tardías
suenan en el siguiente request show.

### «¿Puedo moderar las peticiones antes de emitirlas?»

Deliberadamente no hay cola de moderación. Las salvaguardas son la
restricción al pool (solo pistas del catálogo), el límite de tasa y la
ventana de deduplicación (§6). Si necesita un control más estricto,
estreche los criterios del bloque del pool.

---

## Adónde ir después

* [Biblioteca](./LIBRARY.md) → §3 Smart Blocks — el criterio *Use
  requests* y los órdenes de clasificación están aquí.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) — la playlist de
  dramaturgia y su bloque «tiempo restante» final.
* [Widgets de incrustación públicos](./WIDGETS.md) — incrustar el
  widget de peticiones junto a los demás widgets públicos.
* [Ajustes](./SETTINGS.md) — el selector Song-Request Pool y el
  interruptor Allow 3rd party API.
