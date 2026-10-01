# Autoloading Playlists

> **Dónde está usted en el manual.** Lea
> [Biblioteca](./LIBRARY.md) y [Calendario](./CALENDAR.md)
> primero — las autoloading playlists conectan un item de
> biblioteca (la playlist) con un item de calendario (el
> programa). La función distinta [Auto DJ](./AUTO_DJ.md)
> *no* es lo mismo; vea §8.

Una **autoloading playlist** es una playlist de biblioteca
*adjunta a una definición de programa* para que cada
instancia del programa se rellene desde esa playlist
automáticamente.

Esta es la herramienta ahorradora de trabajo más poderosa
en RASTATIME para emisoras con programación regular. Una
"Mañanas" con una autoloading playlist de smart blocks
necesita cero atención semanal: edite los criterios del
smart block una vez por temporada, y el programa se
rellena cada día de semana.

---

## 1. Lo básico

Un programa con autoloading playlist se construye **una
vez por instancia** por el constructor de autoplaylist en
segundo plano. La construcción típicamente sucede 60
segundos antes del inicio de la instancia.

La secuencia de construcción para cada instancia:

1. (Opcional) **Playlist intro** añadida al principio.
2. Items de la **playlist body** añadidos en orden; smart
   blocks se expanden aquí.
3. (Opcional) **Playlist outro** añadida al final.
4. Si el slot todavía tiene más de 5 s de cola no
   planificada y **Repetir hasta lleno** está habilitado,
   el body se repite hasta llenar.
5. Los segundos restantes pasado el slot outro son
   recortados.

---

## 2. Adjuntar una autoloading playlist a un programa

Abra el programa en el calendario → **Editar programa** →
expanda **Autoloading Playlist**.

| Campo | Qué hace |
|---|---|
| **¿Añadir Autoloading Playlist?** | Interruptor maestro. |
| **Playlist intro** | Añadida al principio. Opcional. Se reproduce exactamente una vez. |
| **Playlist principal** | El contenido body. Requerido si el interruptor maestro está activado. Smart blocks en esta playlist se expanden al momento de build usando los segundos restantes del slot como límite si está configurado. |
| **Playlist outro** | Añadida al final. Opcional. Se reproduce exactamente una vez. |
| **Repetir hasta lleno** | Si activado, los items de la playlist principal se repiten (smart blocks re-evaluados en cada ciclo) mientras eso añada filas (estrictamente en orden, parando en el primer tema que no cabe). |

Guarde el programa.

---

## 3. La cadencia de construcción de 60 segundos

El constructor de autoplaylist corre cada 60 segundos.
Para cada instancia próxima de un programa con autoloading
playlist:

- Si la instancia comienza en **menos de ~60 s** y no ha
  sido construida aún, construir ahora.
- Si no, dejarla para el próximo ciclo.

Esto significa que la construcción es *siempre* una
construcción del estado **actual** de la playlist.

> **Cómo funciona bajo el capó.** El constructor es el
> método estático
> `AutoPlaylistManager.buildAutoPlaylist()`, invocado por
> el `SchedulePollJob` del worker job runner cada 60 s.
> Vea ARCHITECTURE §17.

---

## 4. Cómo se llena el slot (desde 2026-10-01)

El builder llena un programa en tres pasos, siempre contra el
tiempo que **realmente** queda libre en el slot:

1. La **playlist intro** va al principio, exactamente una vez.
2. La **playlist outro** va al final, exactamente una vez — se
   coloca de verdad, así que su duración se conoce con exactitud
   (la inserción de prueba con medición de las versiones anteriores
   desaparece, y con ella el margen de 5 segundos).
3. La **playlist autoloading** llena el espacio entre ambas.

Cada lista se toma **estrictamente en su orden** y se detiene en
el primer tema que ya no cabe antes del final del programa
(decisión del operador, «variante a»): nunca se coloca nada más
allá del final, así que después no hay nada que recortar. Una
intro u outro más larga que el slot se recorta igual (los temas
que no caben se omiten; el registro indica cuántos).

«Realmente libre» es el tiempo maquetado: desde 2026-09-29 las
filas se solapan por su crossfade (valor de la casa 3 s, o el del
tipo de pista), y la suma de las duraciones ya no dice dónde
termina la última fila. El builder maqueta las filas con la misma
regla de pares que el scheduler; un programa de 60 minutos con
quince temas musicales ya **no** termina 42 segundos antes.

Un smart block con *Limitar a: tiempo restante del programa*
recibe ese tiempo maquetado como presupuesto — aumentado con el
solapamiento que generará su propia selección; el builder lo
intenta varias veces y conserva el mejor ajuste. Tras el llenado,
una pasada de relleno tira de los bloques «tiempo restante» de la
playlist contra el hueco que queda, hasta que la última fila
termine a menos de **4 segundos** del final del programa o ya no
quepa nada. En los ensayos del 2026-10-01 el hueco fue de 0–3 s
en la mayoría de los casos y de unos 6 s en el peor (el solucionador
del bloque es aleatorio; el pool decide lo posible), nunca una
sobrerreserva.

> **Bajo el capó.** `AutoPlaylistManager::fillInstance()` expande
> las playlists por sí mismo (`expandPlaylist`), planifica con
> `chainEnd()` — la regla de pares de `Scheduler::calculateCrossfades`
> — e inserta solo las filas que caben mediante
> `Scheduler::scheduleFilesAfter()`. La línea de registro
> «show_instance_id=N filled - intro a, outro b, auto c (+d top-up)
> rows, x s free at the end» resume cada build; `ap_fill_test.php`
> (C:\Temp\optd) ensaya un llenado en una instancia temporal.

---

## 5. Elegir la playlist correcta para autoloading

### Lo que funciona bien

- **Playlists solo-smart-block** con *Limitar a: Tiempo
  restante en el programa*. El patrón más común.
- **Intro + smart block + outro** para programas con un
  intro de ID de emisora y un outro de ID de emisora.
- **Playlists estáticas para programas cortos** de menos
  de 5 minutos.

### Lo que no funciona bien

- **Mezclar pistas estáticas y smart blocks "repetir
  hasta lleno"** — los smart blocks seguirán añadiendo
  pistas incluso después de que las pistas estáticas
  habrían llenado el slot.
- **Webstreams o line-ins en el body** cuando **Repetir
  hasta lleno** está activado.
- **Playlists muy largas** (1000+ items).

---

## 6. Comportamiento Repetir-hasta-lleno

Cuando **Repetir hasta lleno** está marcado:

- Los items de la playlist principal se insertan, smart
  blocks expandidos, y la playlist se repite mientras eso
  añada filas — estrictamente en orden, parando en el primer
  tema que no cabe.
- El ciclo re-evalúa smart blocks en cada iteración.
- Las playlists solo-pista también se repiten.

Cuando no marcado:

- La playlist principal se reproduce una vez.
- Una cola que deje el body la llenan sus smart blocks de
  «tiempo restante» (la pasada de relleno corre igualmente);
  sin tal bloque queda en silencio.

> **Consejo del operador.** Siempre marque **Repetir
> hasta lleno** para un body smart-block. Sin esto, un
> programa de 60 min con un smart block "Limitar a 10
> pistas" reproduce ~40 min de música y 20 min de
> silencio antes del outro.

---

## 7. Retirar una autoloading playlist

Editar programa → expandir **Autoloading Playlist** →
desmarcar **¿Añadir Autoloading Playlist?** → Guardar.

Las instancias futuras ya no se auto-construirán. Las
instancias ya construidas mantienen su contenido
construido.

---

## 8. Autoloading Playlists vs Auto DJ

| | Autoloading Playlist | Auto DJ |
|---|---|---|
| **Dónde adjunto** | Formulario de edición de un programa específico | Configuración → Auto DJ (nivel emisora) |
| **Cuándo rellena** | Por instancia de programa, 60 s antes del inicio | (a) Crea nuevos programas en huecos. (b) Completa programas incompletos. |
| **Con qué rellena** | La playlist configurada (cualquier estructura) | Una playlist Auto-DJ configurada |
| **Afecta a qué programas** | Solo al programa al que está adjunto | Todos los programas + crea nuevos |
| **Necesita un presentador?** | No | No |
| **Deshabilitado por defecto** | Sí | Sí |

Use autoloading playlists para **programación regular**
(la Mañanas siempre usa la Playlist Mañanas). Use Auto DJ
para **tiempo de aire no planificado**.

---

## 9. Preguntas frecuentes

### "Adjunté una playlist pero el programa quedó vacío."

Tres posibilidades:
1. La instancia ya comenzó.
2. La instancia ya fue rellenada manualmente.
3. El worker job runner no está corriendo.

### "¿Cómo veo si la auto-construcción corrió para una instancia específica?"

Abra el programa en el calendario; la barra de relleno
del calendario debería ser > 0 %.

### "¿La playlist intro puede contener un smart block?"

Sí, pero la intro se coloca primero, contra todo el slot
libre, y la outro justo después.

### "¿Por qué la auto-construcción elige a veces la misma pista dos veces?"

Si la playlist body usa **Repetir hasta lleno** con una
playlist estática, las mismas pistas se repiten. Use un
smart block **Dinámico** o "Ordenar: Aleatorio".

### "¿Puedo tener dos autoloading playlists en un programa?"

No. El modelo es **intro + body + outro**.

---

## A dónde ir después

* [Auto DJ](./AUTO_DJ.md) — la automatización a nivel
  emisora que complementa el autoloading por-programa.
* [Plantillas de programa](./SHOW_TEMPLATES.md) — capturar
  el adjunto de autoloading-playlist como parte de una
  plantilla.
* [Biblioteca](./LIBRARY.md) → §3 Smart Blocks — la
  primitiva body-playlist más poderosa.
