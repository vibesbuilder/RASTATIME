# Inicio diferido de programa (Delayed Show Start)

> **Dónde está usted en el manual.** Este es un capítulo de
> **Operación de difusión diaria**, compañero de
> [Calendario](./CALENDAR.md). Lea primero el capítulo Calendario —
> el único interruptor que añade esta función vive en la sección
> **Cuándo** del formulario Nuevo / Editar programa, justo debajo de
> **Se repite**.

Normalmente cada programa empieza exactamente en su slot del
calendario, y un programa que tiene **más contenido planificado del
que cabe en su slot** simplemente ve su última pista cortada al final
del slot (la punta roja sólida en la
[barra de relleno del calendario](./CALENDAR.md#1-la-página-calendario)).
El programa siguiente sigue empezando a tiempo.

El **inicio diferido** cambia eso para los programas que usted opta a
ello. Cuando el programa *anterior* al suyo se sobrepasa, un programa
inscrito **se desliza más tarde** para que el programa anterior pueda
terminar, en lugar de cortar el programa anterior. Usted marca una
casilla por programa; una tarea en segundo plano hace el resto, unos
minutos antes de salir al aire.

> **Esto es opt-in y solo hacia adelante.** Un programa solo se
> desliza si **su propia** casilla está marcada. El deslizamiento
> nunca se deshace automáticamente — vea §6. Si cambia de opinión,
> desmarque la casilla (los futuros sobrepasos dejan de deslizarlo) o
> arrastre la instancia de vuelta en el calendario.

---

## 1. La visión general

```
   Slot:    │ Prog. A (slot 1h) │ Prog. B (slot 1h) │ Prog. C │
            08:00            09:00              10:00    11:00

   A está sobrepasado — su contenido llega en realidad hasta 09:10.

   Sin inicio diferido (B sin marcar):
            │ Prog. A …✂ corte │ Prog. B          │ Prog. C │
            08:00         09:00                 10:00
            La última pista de A se recorta a las 09:00; B empieza a tiempo.

   Con inicio diferido (B marcado):
            │ Prog. A ………………… │ Prog. B       │ Prog. C │
            08:00          09:10           10:00    11:00
            A se emite entero hasta 09:10. B conserva su FIN (10:00) y
            mueve su INICIO a 09:10, así B dura 50 min en vez de 60 y su
            propia última pista puede recortarse. C sigue empezando a las 10:00.
```

Dos reglas conforman toda la función:

1. **El programa que se sobrepasa se emite entero.** El fin del slot
   del programa A se estira hasta donde su contenido termina realmente
   (09:10), así el playout ya no recorta la última pista de A.
2. **El programa siguiente inscrito conserva su FIN fijo y mueve su
   INICIO.** El programa B ahora va de 09:10 → 10:00 en vez de
   09:00 → 10:00. Sus items planificados se mueven con él; lo que ya no
   cabe antes de las 10:00 se corta al final (el mismo compromiso
   aceptado de cualquier programa sobrepasado).

Un programa **sin** la casilla es una parada dura: siempre empieza a
tiempo, y el programa anterior se recorta en su inicio (la regla 1 no
se aplica a través de una frontera no inscrita).

---

## 2. Activarlo

Abra **Nuevo programa** o **Editar programa** y despliegue la sección
**Cuándo**. Justo debajo de **Se repite** está:

```
   Cuándo
   ─────────────────────────────
   Inicio  [2026-06-15] [08:00]
   …
   Se repite                      [ ]
   ¿Permitir inicio diferido?     [x]   ◀── marque para que ESTE programa se deslice
```

Marque **«¿Permitir inicio diferido?»** en cualquier programa al que se le permita empezar tarde cuando el
programa precedente se sobrepasó.
Déjela sin marcar en los programas que deben empezar exactamente a
tiempo (las noticias en punto, un feed de la red, un enlace en vivo a
hora fija) — esos se convierten en las anclas que detienen un
deslizamiento (§4).

Para un programa **recurrente** la casilla forma parte de la
definición del programa, así que se aplica a cada episodio. Cuando un
sobrepaso real desplaza un episodio, solo **ese** episodio cambia (se
convierte en una anulación por-ocurrencia); los demás episodios
conservan su slot normal.

> **Cómo funciona bajo el capó.** La marca se almacena en el nuevo
> booleano `cc_show.allow_delayed_start` (migración legacy 0056). No
> tiene accesor Propel — el formulario lo lee y escribe vía SQL en
> bruto, el mismo patrón que las columnas de song-request. Nada más
> del programa cambia cuando la marca; la casilla solo importa a la
> tarea en segundo plano de §6.

### La playlist de relleno (Settings → General)

Desde el 27/09/2026 existe un segundo ajuste opcional para toda la
emisora: **Settings → General → Show-Shift Filler Playlist**.  Elija
una de sus playlists — idealmente música de duraciones variadas — y
el inicio diferido deja de cortar temas del programa: los temas que
ya no caben se sustituyen por temas de relleno.  El §3 explica
exactamente qué ocurre.  Deje *(ninguna — cortar el último tema)*
para conservar el comportamiento básico.

---

## 3. Qué ocurre cuando un programa se sobrepasa

Cuando la tarea en segundo plano ve que el contenido planificado del
programa A termina **después** del slot de A, y el programa siguiente
B tiene **¿Permitir inicio diferido?** marcado:

| | Antes | Después |
|---|---|---|
| **Fin de A** | 09:00 (slot) | 09:10 (extendido al fin del contenido) |
| **Inicio de B** | 09:00 | 09:10 (= fin del contenido de A) |
| **Fin de B** | 10:00 | **10:00 (sin cambios)** |
| **Items de B** | 09:00 … | desplazados +10 min |

Así A emite cada pista que tenía planificada, y B empieza justo cuando
A termina realmente. Como el **fin de B se mantiene fijo**, B es
efectivamente diez minutos más corto, y si B ya estaba lleno su última
pista se recorta a las 10:00 — exactamente lo que le habría pasado a A
sin la función. El corte simplemente se traslada al programa que optó
por absorberlo.

> **¿Por qué mantener fijo el fin de B?** Para que un sobrepaso no
> pueda propagarse sin límite al resto del día. B cede sus primeros
> diez minutos pero aun así entrega a lo que siga a las 10:00. Esta fue
> una elección deliberada frente a «empujar también el fin de B» (que
> desplazaría cada programa posterior). Vea ARCHITECTURE §23.24.

### Relleno en lugar de corte (desde el 27/09/2026)

Con una playlist de relleno configurada, el programa desplazado B ya
no se recorta sin más.  Una vez que B se ha movido al final del
contenido de A, la tarea mira qué sobresale ahora del final de B y
hace tres cosas:

1. **El outro se queda en su sitio.**  Si B termina con su playlist
   de outro — el *Select Outro Playlist* propio del programa, o el
   valor por defecto de la emisora en Settings → General —, esos temas
   de outro quedan fijados al final de B y nunca se tocan.  Se
   sustituyen los temas *anteriores* al outro, es decir el penúltimo
   (o varios).  (Que las últimas filas sean realmente el outro se
   comprueba contra los temas de la playlist, nunca se supone: un
   programa rellenado a mano sin outro simplemente no tiene cola
   protegida.)
2. **Todo tema que ya no cabe se va** — uno o varios, desde el final
   del cuerpo de B hacia atrás — hasta que el resto cabe antes del
   outro (o antes del final de B si no hay outro).
3. **El hueco se rellena desde la playlist de relleno** con la
   combinación de temas cuya duración total cubre el hueco con el
   menor exceso.  El *último* relleno se corta al final del hueco.
   Así el aire nunca queda en silencio y el único tema que se acorta
   es un relleno — nunca uno de B.  Vale incluso cuando el hueco es
   más corto que el relleno más corto: suena el más corto y se corta.

El cambio ocurre en la misma transacción de base de datos que el
desplazamiento: o se aplica todo, o nada.  El playout, el Dashboard,
los widgets y el historial ven el resultado como filas normales de la
parrilla.  Solo el programa desplazado B se trata así; el final del
programa A sigue recortándose ante un ancla no habilitada (§4).

> **Ejemplo.**  B va de 10:00 a 11:00, termina con un jingle de outro
> de 30 segundos, y A se sobrepasa cuatro minutos.  B empieza ahora a
> las 10:04.  Su último tema musical terminaría a las 11:03:30 — se
> va.  El cuerpo restante termina a las 10:59:10; el hueco hasta el
> outro (que debe empezar a las 10:59:30) es de 20 segundos: suena el
> relleno más corto y se funde a las 10:59:30, el outro suena entero y
> lo que sigue empieza a las 11:00 en punto.

---

## 4. La cascada y el ancla

Un gran sobrepaso puede alcanzar más allá de un solo programa. El
retraso **se propaga hacia adelante** a través de programas inscritos
consecutivos:

```
   Slot:  │ A (sobrepasado → 09:40) │  B  │      C      │ D │
          08:00                  09:00 09:30         10:30

   El contenido de A llega hasta 09:40.

   • B (09:00–09:30, marcado)  enterrado por completo (09:40 > 09:30)
                               → VACIADO, slot dejado como «omitido»
   • C (09:30–10:30, marcado)  enterrado en parte (09:40 < 10:30)
                               → DESLIZADO a 09:40, conserva su fin 10:30;
                                 la propagación SE DETIENE aquí
   • D (10:30, …)              sin afectar → empieza a tiempo a las 10:30
```

Un **programa sin la casilla** habría detenido la propagación en su
propio inicio: es un **ancla** dura que siempre empieza a tiempo, y el
contenido que se sobrepasa delante de ella se recorta en el inicio del
ancla.

Dos cosas pueden ocurrirle a cada programa inscrito que el sobrepaso
alcanza:

- **Enterrado en parte → se desliza.** Si al programa todavía le queda
  tiempo tras el sobrepaso (el sobrepaso termina antes del propio fin
  del programa), se desliza hasta el fin del sobrepaso, conserva su
  fin, y la propagación **se detiene ahí** — ese programa absorbe el
  resto.
- **Enterrado por completo → se vacía.** Si el sobrepaso cubre todo el
  slot del programa, el programa no puede emitir en absoluto. Su
  contenido se vacía y el slot vacío se deja en el calendario como un
  **marcador «omitido»** (§5). La propagación continúa al siguiente
  programa.

La propagación siempre termina en el **primer programa sin la casilla**
— el **ancla dura**. El ancla empieza exactamente a tiempo; el
contenido que se sobrepasa delante de ella se recorta en el inicio del
ancla. Así controla hasta dónde puede viajar un retraso simplemente
dejando la casilla sin marcar en el siguiente programa a hora fija.

> **Consejo del operador.** Coloque un ancla sin marcar en cada punto
> del día que no debe moverse — las noticias en punto, un feed
> sindicado, el inicio del programa matinal. Todo lo que hay entre dos
> anclas puede deslizarse; nada cruza un ancla.

---

## 5. Un programa enterrado por completo: el slot omitido

Cuando un programa queda enteramente enterrado por un sobrepaso
anterior, se **vacía, no se elimina**:

- sus items planificados se retiran (la barra de relleno del slot baja
  a 0 %),
- el slot vacío **permanece en el calendario** para que pueda ver que
  el programa fue omitido en lugar de desaparecer en silencio,
- de un programa recurrente solo se vacía **ese único episodio**; la
  serie queda intacta.

El programa anterior simplemente suena durante el tiempo de aire del
slot omitido. El marcador está ahí para que usted lo note después —
p. ej. para disculparse al aire, o para ajustar el programa
sobrepasado la próxima vez.

> **Cómo funciona bajo el capó.** Vaciar una instancia enterrada
> refleja la acción **Vaciar planning** para una instancia: sus filas
> `cc_schedule` se eliminan, `time_filled` se pone a cero, la instancia
> se marca `modified_instance` — la marca « ocurrencia eliminada » del
> upstream, adecuada para un slot que nunca sale al aire — más
> `delayed_start_from` (desde el 27/09/2026, véase abajo), y
> `cc_files.is_scheduled` se retira para toda pista que ya no esté
> planificada en ningún sitio.

---

## 6. Cuándo — y con qué frecuencia — ocurre el desplazamiento

El desplazamiento lo hace una tarea en segundo plano, **no** en el
momento en que usted guarda un programa:

- Una tarea (`ShowShiftTask`) se ejecuta cada **2 minutos**.
- Solo actúa sobre sobrepasos cuyo programa afectado empieza en los
  próximos **15 minutos** (el *lead*). Los programas lejanos en el
  futuro, que usted aún puede estar editando, se dejan intactos hasta
  que se acercan.
- Trabaja a partir del **contenido planificado** (`cc_schedule`), así
  que se aplica por igual a programas que usted rellenó a mano y a
  programas que rellenó una autoloading playlist.

La tarea es **idempotente y solo hacia adelante**:

- Ejecutarla de nuevo no cambia nada una vez que un programa ya está
  asentado en el fin del sobrepaso — nunca arrastra un programa más
  allá en sondeos repetidos.
- Un deslizamiento **nunca se deshace automáticamente.** Si más tarde
  recorta el programa sobrepasado para que ya no se sobrepase, el
  programa que ya se deslizó se queda donde está hasta que usted lo
  mueva de vuelta (arrastrándolo en el calendario) o el slot se
  regenere. Este comportamiento «solo hacia adelante» se eligió para
  mantener la función simple y predecible; no hay estado oculto que
  recuerde el slot original de cada programa.

> **El historial de playout se mantiene correcto automáticamente.** El
> desplazamiento ocurre *antes* del aire, y el historial de playout
> registra lo que **realmente** sonó y cuándo (hora de reloj), no las
> horas de slot planificadas. Así un programa que se emitió tarde queda
> registrado en su hora de aire real sin contabilidad adicional.

> **Cómo funciona bajo el capó.**
> `Application_Service_ShowShiftService::applyDelayedStarts()`
> selecciona las instancias sobrepasadas que no son ocurrencias
> eliminadas (`modified_instance`) ni ya desplazadas
> (`delayed_start_from`), cuyo fin de slot cae dentro de la ventana de
> lead, y luego recorre
> cada una hacia adelante: vaciando los programas marcados enterrados
> por completo, deslizando el primer programa marcado enterrado en
> parte (inicio → fin del contenido, fin fijo, items desplazados vía
> `SchedulerService::updateScheduleStartTime`, marcado con
> `delayed_start_from` = el inicio de slot del que se movió), y
> deteniéndose en la primera ancla sin marcar.
>
> **Por qué un marcador propio (27/09/2026).**  El primer ensayo en
> directo mostró que el marcador de junio — `modified_instance`, la
> bandera « esta ocurrencia fue eliminada » del upstream — ocultaba el
> programa desplazado al panel, al live-info, a todos los widgets, al
> calendario, al show builder y a la comprobación de solapamiento,
> mientras el playout lo emitía.  La migración 0058 añadió
> `cc_show_instances.delayed_start_from`; un programa desplazado ahora
> sigue visible en todas partes a su nueva hora.  Guardar el slot
> original (y no solo una bandera) permite además al regenerador de
> repeticiones encontrar la ocurrencia movida al editar el programa,
> en lugar de crear un duplicado a la hora de la serie.
> El propio fin del programa sobrepasado se extiende hasta donde se
> asentó su contenido. El intervalo y el lead son anulables con
> `RASTATIME_SHOW_SHIFT_INTERVAL_SECONDS` (por defecto 120) y
> `RASTATIME_SHOW_SHIFT_LEAD_SECONDS` (por defecto 900). Vea
> ARCHITECTURE §23.24.

---

## 7. Cosas que conviene saber

**Los programas sin el interruptor terminan a su predecesor en el
límite (desde 2026-11-06).**  El playout toma «Allow delayed start» al
pie de la letra: antes de un programa que *no* lo permite, lo que aún
suena se termina al inicio del programa.  Los últimos segundos de la
pista que acaba se funden en 0,3 s para que el nuevo programa empiece
exactamente en su fila; un exceso de hasta 0,3 s se deja como está.
Antes de este cambio un predecesor podía invadir unos 4,5 s el programa
siguiente.  Los programas *con* el interruptor conservan el traspaso
suave descrito arriba.


- **Un programa que movió a mano no es por sí mismo un origen de
  deslizamiento.** Un programa ya desplazado por la tarea
  (`delayed_start_from` puesto) nunca se trata como la *fuente* de una
  nueva propagación, y una ocurrencia eliminada (`modified_instance`)
  se omite por completo — mientras que un programa que simplemente
  arrastró en el calendario es una instancia normal que aún puede
  deslizarse, vaciarse o (si se sobrepasa) provocar él mismo una
  propagación. Así el mecanismo se mantiene idempotente sin luchar
  contra sus ediciones manuales, en consonancia con
  cómo otras pasadas automáticas dejan en paz las instancias editadas a
  mano.
- **En cada paso solo importa la casilla del programa siguiente.** Que
  el propio programa A esté marcado es irrelevante para que el
  sobrepaso de A empuje a B — lo que importa es la casilla de B. (La
  casilla de A solo importa cuando el programa *anterior* a A se
  sobrepasa sobre A.)
- **Un hueco absorbe un sobrepaso gratis.** Si hay tiempo vacío tras el
  programa sobrepasado, su contenido simplemente suena dentro del
  hueco; ningún programa siguiente necesita moverse, y nada cambia.
- **El autoloading puede crear el exceso (desde el 26/10/2026).**  Un
  episodio más largo que su slot se coloca entero si el programa
  siguiente tiene la casilla marcada - la casilla basta para que esos
  episodios suenen completos.  Delante de un programa sin la casilla se
  corta al final (hasta 5 s siempre, más solo con «Allow last track to
  exceed time limit» en su smart block); vea
  [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) §4.

---

## 8. Lista de verificación del operador

Para dejar que un bloque del horario se deslice cuando un programa se
sobrepasa:

1. **Marque «¿Permitir inicio diferido?»** en cada programa que pueda
   empezar tarde — en la sección **Cuándo** de su formulario Nuevo /
   Editar programa.
2. **Déjela sin marcar** en cada programa a hora fija que deba empezar
   en punto (noticias, feeds, enlaces en vivo). Esas son sus anclas.
3. Eso es todo. Unos minutos antes del aire, un sobrepaso delante de un
   programa marcado lo desliza automáticamente; el corte recae en el
   programa marcado en lugar del sobrepasado, y nada cruza un ancla sin
   marcar.

No hay nada que configurar más allá de la casilla por programa.

---

## 9. Preguntas frecuentes

### «Marqué la casilla pero mi programa igual empezó a tiempo.»

Entonces el programa de delante no se sobrepasó (su contenido cabía en
su slot), o había un hueco que absorbió el sobrepaso, o el sobrepaso
fue más corto que un segundo. La casilla solo hace algo cuando el
programa anterior realmente se pasa de su slot **dentro** del suyo.

### «Mi programa se deslizó más tarde y su última pista se cortó.»

Eso es el diseño: el programa deslizado conserva su **fin** fijo, así
que es más corto y recorta su cola — el corte se traslada del programa
sobrepasado al que optó por absorberlo. Planifique un poco menos de
contenido, o acepte el recorte.

### «Un programa entero fue omitido — su slot está vacío.»

Quedó enterrado por completo por un sobrepaso anterior y fue
**vaciado** a un marcador de slot omitido (§5). El programa anterior
sonó durante su tiempo de aire. Ajuste el programa sobrepasado, o
coloque un ancla sin marcar antes para que el sobrepaso se recorte
antes de alcanzar ese programa.

### «Acorté el programa sobrepasado pero el siguiente sigue tarde.»

Los deslizamientos son solo hacia adelante (§6) — no se revierten
automáticamente. Arrastre el programa deslizado de vuelta a su slot en
el calendario, o espere a que el slot se regenere.

### «¿Hasta dónde puede empujar un sobrepaso el horario?»

Hasta el primer programa **sin** la casilla. Todo lo que hay entre dos
anclas sin marcar puede deslizarse; nada cruza un ancla. Coloque anclas
para acotar la propagación.

### «¿Un programa tardío estropea el historial de playout / lo que suena ahora?»

No. El desplazamiento ocurre antes del aire y el historial registra las
horas de aire reales, así que un programa tardío se reporta a la hora a
la que realmente sonó.

---

## A dónde ir después

* [Calendario](./CALENDAR.md) — el formulario de programa, la sección
  **Cuándo**, la barra de relleno cuya punta roja marca un programa
  sobrepasado.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) — una forma
  habitual en que un programa acaba sobrepasado (una dramaturgia que
  rellena ligeramente de más).
* [Plantillas de programa](./SHOW_TEMPLATES.md) — integre «Permitir
  inicio diferido» en una plantilla para que toda una clase de
  programas se inscriba de una vez.
