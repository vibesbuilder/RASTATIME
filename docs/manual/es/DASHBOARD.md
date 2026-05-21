# Panel

> **Dónde está usted en el manual.** El Panel es la
> primera página que los operadores alcanzan después del
> inicio de sesión. Muestra el estado de la emisora a
> primera vista y ofrece las anulaciones manuales que no
> necesitan un viaje al Calendario.

El **Panel** responde tres preguntas en una pantalla:

1. ¿Qué está al aire *ahora*?
2. ¿Qué viene *después*?
3. ¿Los streams públicos están sanos?

Un cuarto panel — los controles **Fuente en vivo** — es
la salida de emergencia del operador para poner la
emisora en vivo sin abrir un cliente de difusión
separado.

---

## 1. El diseño de la página

Panel → por defecto la vista en vivo. La página se
refresca cada 5 segundos (configurable en el menú
desplegable arriba a la derecha — 1 / 5 / 10 / 30 segundos
o Manual).

---

## 2. En reproducción

El panel más grande. Muestra el item de planning actual
más el contexto de lo que alimenta el stream público.

### Campos

| Campo | Significado |
|---|---|
| **♪ Título — Artista** | Metadatos del item en reproducción actual. |
| **Programa** | El programa al que pertenece este item + porcentaje de relleno general del programa. |
| **Fuente** | Qué entrada el source switcher enruta actualmente — vea §3. |
| **Barra de progreso** | Tiempo transcurrido / duración del item. |

> **Por qué el porcentaje de relleno importa.** Un
> programa al 60 % de relleno tiene 40 % de su slot
> vacío. Cuando la pista actual termina, el playout
> alcanza la cola vacía y cae al silencio (o Auto DJ si
> está habilitado).

### Apariencia de anulación Live-DJ

Cuando una fuente Live-DJ está activa, el panel cambia:
sin título de pista (la fuente en vivo es audio abierto),
sin barra de progreso, y un indicador claro "🎙 LIVE".

> **Cómo funciona bajo el capó.** El panel En reproducción
> consume `/api/v2/now-playing` que devuelve el estado
> actual del source switcher más el item de planning
> activo. El endpoint lee de `rastatime_playback_state`
> que es escrito por el motor de playout en cada
> transición pista / fuente. Vea ARCHITECTURE §9.

---

## 3. Estado de fuente

El campo **Fuente** en el panel En reproducción cicla a
través de cinco estados posibles. Saber cuál está al aire
ahora es la diferencia entre "el stream funciona" y "el
stream funciona pero está emitiendo lo equivocado".

| Fuente | Lo que significa | Cuándo preocuparse |
|---|---|---|
| **Scheduler** | Playout reproduce lo que el calendario dice. El estado normal. | Nunca. Este es el objetivo. |
| **Show DJ** | Una fuente en vivo remota ha tomado el programa. | Si no espera que un Show DJ esté en vivo — investigar. |
| **Master DJ** | Fuente en vivo a nivel emisora ha anulado todo. | Master DJ solo debería estar al aire cuando el ingeniero ha tomado intencionalmente el control. |
| **Auto DJ** | Relleno Auto-DJ está al aire. | Si esperaba contenido planificado por el operador — abra el Calendario. |
| **Fallback / Silencio** | Nada está planificado, Auto DJ está apagado. | Casi siempre un problema. Abra el Calendario. |

### Cambiar de fuente manualmente

El cambio de fuente **no** está controlado por el operador
del lado del Panel — es conducido por el motor de playout
en respuesta al calendario, un DJ remoto que se conecta,
o intervención Auto-DJ.

Para **forzar** un cambio:
- **Cancelar programa actual** termina el programa en
  ejecución inmediatamente.
- **Quitar Master DJ del aire** desconecta la fuente
  Master.

---

## 4. Viene después

Los próximos 3-5 items que vienen (configurable bajo
Preferencias generales → Vista anticipada del Panel).

Cada fila muestra hora, nombre del programa y porcentaje
de relleno.

> **Consejo del operador.** Un relleno "0 %" o "—" en un
> programa que comienza pronto es un problema.

---

## 5. Streams

Vista compacta de la misma información que obtiene de
Configuración → [Streams](./STREAMS.md):
N. /mount + insignia de estado + contador de oyentes.

Clic en un stream → abre la página de configuración
Streams con foco en ese stream.

> **Consejo del operador.** Esta vista compacta es lo que
> la mayoría de los operadores observan durante un
> programa.

---

## 6. Panel Fuente en vivo

Dos controles + dos líneas de estado.

### Casilla Master DJ al aire

| Casilla | Efecto |
|---|---|
| **Apagada** (por defecto) | Master DJ está silenciado en el source switcher incluso si está conectado. |
| **Encendida** | Master DJ está al aire si está conectado. Cualquier entrada del source switcher es anulada. |

> **Por qué una casilla y no solo "conectado = al
> aire"?** El modelo LibreTime original era "Master DJ al
> aire cuando esté conectado"; RASTATIME 2026-05-15
> añadió el toggle explícito.

### Líneas de estado Show DJ / Master DJ

Cada línea muestra **No conectado**, **Conectado (en
espera)**, o **Conectado (al aire)**.

### Escuchar el monitor

Reproduce la salida monitor de la
[Máquina local](./LOCAL_MACHINE.md) a través de su
navegador.

### Cancelar programa actual

Termina el programa actualmente en reproducción
**inmediatamente**.

Efectos: `cc_show_instances.ends_at` se establece en
"ahora", el source switcher avanza, si el programa
estaba siendo grabado, la grabación se detiene
graciosamente, un Show DJ conectado a este programa es
expulsado.

> **Consejo del operador.** Use **Cancelar programa
> actual** con moderación — la cancelación es
> irreversible.

---

## 7. Preguntas frecuentes

### "El panel En reproducción dice 'Silencio'. ¿Qué significa?"

El motor de playout corre, ningún programa está actual,
ningún Auto DJ está habilitado, y ningún bucle fallback
está configurado.

Solución: Abrir el Calendario y planificar un programa, o
habilitar [Auto DJ](./AUTO_DJ.md).

### "La Fuente es 'Scheduler' pero no oigo nada."

Tres posibilidades:
1. El item planificado actual es él mismo silencioso.
2. La conexión Icecast está abierta pero la codificación
   es silenciosa.
3. La pestaña del navegador está silenciada.

### "¿Por qué la página a veces retrasa unos segundos detrás de la realidad?"

El endpoint En reproducción se refresca cada 5 segundos.

### "¿Puedo ver el Panel sin iniciar sesión?"

No — el Panel requiere autenticación. Para una página
pública "qué está pasando" no autenticada, use el widget
embed en `/embed/now-playing`.

### "¿Por qué el contador de oyentes cae a cero por un ciclo de refresco?"

Icecast brevemente reinicia el contador de oyentes cuando
la fuente se reconecta.

---

## A dónde ir después

* [Calendario](./CALENDAR.md) — qué puebla "Viene
  después".
* [Streams](./STREAMS.md) — detalle completo sobre cada
  stream de salida.
* [Auto DJ](./AUTO_DJ.md) — qué rellena los huecos.
* [Máquina local](./LOCAL_MACHINE.md) — la salida monitor
  que el botón **Escuchar el monitor** usa.
