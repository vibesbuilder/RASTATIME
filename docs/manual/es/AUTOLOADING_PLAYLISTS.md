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
| **Repetir hasta lleno** | Si activado, los items de la playlist principal se repiten (smart blocks re-evaluados en cada ciclo) hasta llenar el slot menos la reserva outro. |

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

## 4. La reserva de outro (Sección 23.19)

Esta es la parte operacionalmente más difícil del
autoloading y merece ser entendida.

### El problema

Suponga que su **Playlist principal** usa un smart block
con *Limitar a: Tiempo restante en el programa*, y tiene
una **Playlist outro** con un ID de emisora de 60 s.

Sin reserva de outro, la expansión del smart block ve
"tiempo restante = 60 minutos" (el programa entero),
elige 60 minutos de pistas, y la inserción de outro
posterior o:

- Falla porque el slot ahora está lleno, o
- Empuja el outro pasado el final del slot, causando un
  sobreexceso de 60 s.

### La solución

Antes de expandir cualquier smart block en la playlist
principal, el constructor:

1. **Trial-inserta** el outro en el slot.
2. Mide su longitud.
3. Anula la inserción de prueba.
4. Restaura cualquier efecto secundario
   `cc_files.is_scheduled`.
5. Le dice al scheduler que **reserve** ese número de
   segundos del slot.

Un smart block con "tiempo restante" ahora ve
*(slot total) − (longitud outro) − (5 s margen)* y elige
el número correcto de pistas.

### El margen de 5 segundos

La reserva está limitada en la longitud outro medida más
un **margen de 5 s** (decisión del operador 2026-05-20,
v8).

> **Por qué 5 s y no más?** Los operadores prefirieron
> alta utilización (más música, menos silencio) sobre una
> reserva sobre-precavida.

### Limpieza post-construcción

Después de que el body se construye y el outro se
inserta, un paso final recorta cualquier item cuyo tiempo
de fin superaría el inicio del outro.

> **Cómo funciona bajo el capó.** La reserva es
> `Application_Model_Scheduler::setReservedSeconds()`. El
> recorte es
> `Application_Model_Scheduler::trimTailExcept($outroStart)`.
> Vea commit ed57399.

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
  blocks expandidos, hasta que el slot esté lleno menos
  la reserva outro.
- El ciclo re-evalúa smart blocks en cada iteración.
- Las playlists solo-pista también se repiten.

Cuando no marcado:

- La playlist principal se reproduce una vez.
- Cualquier cola restante es silencio.

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

Sí, pero los smart blocks dentro de playlists intro /
outro *no* obtienen el tratamiento de reserva de outro.

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
