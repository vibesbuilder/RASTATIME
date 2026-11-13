# Auto DJ

> **Dónde está usted en el manual.** Lea
> [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md)
> primero — Auto DJ es el contrapunto a nivel emisora de
> la autoloading playlist por-programa. §8 de ese capítulo
> tiene la comparación lado a lado.

**Auto DJ** es el rellenador en segundo plano que mantiene
la emisora al aire durante el tiempo no planificado por el
operador. Funciona en dos pasos complementarios, ambos
totalmente automáticos una vez habilitados:

1. **Pre-pass** — si la próxima hora del calendario
   contiene cualquier hueco mayor de 60 segundos, crea un
   nuevo programa en el primer hueco encontrado, nombrado
   según sus valores por defecto, con la playlist Auto-DJ
   autoloaded.
2. **Fill-pass** (opcional) — si cualquier programa
   próximo termina más de 5 s corto de su slot después de
   su construcción, completa la cola con la playlist
   Auto-DJ; un pequeño hueco restante en el que no cabe nada
   puede cerrarlo una pista de reserva (desde 2026-11-13, §4).

Resultado: mientras Auto DJ esté habilitado y apunte a una
playlist sana, su emisora nunca cae en silencio.

---

## 1. Por qué existe Auto DJ

Antes de 2026-05-21, el fallback para "no hay programa
planificado ahora" era un archivo de bucle configurado
(silencio por defecto). Esto cubría "nunca un programa",
pero un calendario con 80 % de cobertura y 20 % de huecos
todavía reproducía silencio en los huecos.

Los dos patrones que el operador encontraba repetidamente:

- El programa del lunes por la mañana termina a las 10:00
  pero el próximo programa comienza a las 14:00. El hueco
  de cuatro horas reproducía silencio fallback.
- La autoplaylist de un programa de 60 minutos solo
  rellenaba 55 minutos; los últimos 5 minutos eran
  silencio.

Auto DJ cubre ambos con la misma playlist configurada.

---

## 2. Habilitar Auto DJ

Configuración → **Auto DJ**.

### Campos requeridos

| Campo | Notas |
|---|---|
| **Habilitado** | Interruptor maestro. |
| **Playlist por defecto** | La playlist que Auto DJ usa. Requerida cuando **Habilitado** está activado. |

### Forma de playlist recomendada

Use una playlist que contenga exactamente **un smart
block** con:

- Tipo: **Dinámico**.
- Criterios: un filtro generoso que coincida con varios
  cientos de pistas. "Tipo de pista = Música" es una
  buena base.
- **Limitar a: Tiempo restante en el programa**. Esto es
  crítico.
- Ordenar: **Aleatorio**.

### Campos opcionales

| Campo | Qué hace Auto DJ con él |
|---|---|
| **Nombre de programa** | Usado como nombre del programa auto-creado. Por defecto `Auto DJ`. |
| **URL / Género / Descripción** | Copiado a los metadatos de cada programa auto-creado. |
| **Color de fondo / texto** | Usado para colorear los programas auto-creados en el calendario. |
| **Logo de programa** | Logo por defecto. Almacenado como blob base64 en `cc_pref`. Límite de subida 2 MB. |
| **Rellenar automáticamente cualquier programa** | Si activado, habilita el segundo paso (fill-pass). |

> **Cómo funciona bajo el capó.** Configuración vive en
> la tabla `cc_pref` como simples filas clave/valor.
> Vea ARCHITECTURE §23.20.

---

## 3. El pre-pass — relleno de huecos

Cada 60 segundos, Auto DJ escanea la próxima hora en
busca de huecos de calendario. Un **hueco** es cualquier
rango contiguo donde ningún programa está planificado.

Para el **primer** hueco mayor de 60 segundos cuyo inicio
está dentro de la próxima hora:

1. Crear una nueva fila `cc_show` con los valores por
   defecto configurados.
2. Insertar una fila `cc_show_days` con la zona horaria
   local del operador y horas redondeadas (inicio
   redondeado HACIA ARRIBA al próximo minuto, fin
   redondeado HACIA ABAJO al minuto anterior).
3. Insertar una fila `cc_show_instances` para el mismo
   rango.
4. Adjuntar la playlist Auto-DJ configurada como
   autoloading.

El nuevo programa luego es tomado por el **mismo** ciclo
de poll en el bucle body y construido.

### Por qué solo un programa por ciclo?

El pre-pass crea **un** programa por ciclo de 60 s,
incluso si existen múltiples huecos. Es intencional:

- Después de que un programa se crea, el próximo hueco
  se mueve.
- Un operador que reorganiza activamente el calendario no
  debería ver diez programas Auto-DJ materializarse más
  rápido de lo que puede reaccionar.

### Las horas de programa se redondean al minuto

Los programas creados por Auto-DJ siempre comienzan en un
límite de minuto. Esto es para evitar el error "Cannot
schedule overlapping shows" que ocurría cuando el operador
abría un programa Auto-DJ con un inicio 14:00:30.

---

## 4. El fill-pass — completar programas incompletos

Opcional, opt-in vía **Rellenar automáticamente cualquier
programa incompleto después de la construcción de
autoplaylist**.

Cada 60 s ciclos, después del pre-pass + las
construcciones body de autoplaylist normales, el fill-pass
recorre cada programa próximo cuya cola terminó más de 5
segundos corta de su slot. Para cada uno, agrega la
playlist Auto-DJ al final.

**Nunca antes del llenado propio del programa (desde el
26/10/2026).**  Un programa con playlist de autoloading se omite
hasta que su construcción se haya ejecutado, y una repetición
(«Repeat of show») hasta que tenga su copia - mientras la copia aún
pueda llegar (hasta 5 minutos antes del inicio).  Los programas de
song requests y traffic alerts, que se llenan paso a paso justo a
tiempo, nunca se completan.  Antes, el fill-pass podía alcanzar un
programa un momento antes que su autoloading y llenarlo con la
playlist de Auto DJ (26/10/2026, «Vinyl Hour»: llenado a las
15:00:00, el autoloading lo encontró lleno a las 15:01:30).

### Por qué 5 segundos y no un umbral más estricto?

La reserva de outro deja intencionalmente hasta 5 s de
juego para que la auto-construcción no se desborde.

### El fill-pass deja en paz un programa que está editando (desde 2026-11-07)

Mientras arrastra pistas a un programa en el calendario o en el show
builder, ese programa es suyo: cada acción de planificación bloquea
primero el episodio del programa, y el fill-pass no espera a ese
bloqueo.  Omite el programa en este ciclo, escribe una línea
informativa en el registro («is being edited right now - left alone
until the next pass») y vuelve a mirar un minuto después.  Una vez
guardada su edición, si al programa le siguen faltando más de 5
segundos, el fill-pass lo completa como antes.  Antes de este cambio
ambos corrían a la vez y podían chocar en la base de datos
(interbloqueo) - el perdedor era aleatorio, así que una colocación del
operador podía fallar con un mensaje de error.

### El fill-pass nunca modifica la definición del programa

El fill-pass solo inserta **items de planning** en el
episodio existente.

### La pista de reserva para pequeños huecos restantes (desde 2026-11-13)

El fill-pass solo añade pistas que caben; nunca sobrerreserva.
Cuando la playlist Auto-DJ no tiene nada lo bastante corto para el
resto de un episodio, el final del programa queda en silencio
(2026-11-11: un episodio de podcast dejó 30,8 s libres, la pista
musical más corta que podía sonar duraba 40 s - 31 s de silencio y
una alerta de aire muerto).

**Ajustes → Auto DJ → Buffer Track** cierra esos huecos:

| Campo | Significado |
|---|---|
| **Buffer Playlist** | Una playlist de pistas largas, producidas para poder desvanecerse en cualquier momento (una cama musical, una pieza ambiental, de varios minutos cada una). **— No buffer track —** desactiva la función. Bajo el campo la página muestra cuántas pistas reproducibles tiene la playlist y la más larga, o un aviso cuando ninguna es lo bastante larga. |
| **Maximum Gap (s)** | La pista de reserva llena huecos de más de 5 s y como máximo esta duración (6-600 s, por defecto 60). Los huecos mayores siguen siendo cosa de la playlist Auto-DJ. |
| **At the End of the Show** | **Cut**: la pista de reserva termina al final del programa con el fundido de programa de Ajustes → General. **Fade Out**: se desvanece durante la **Fade Out Duration** (0,5-3 s) y termina al final del programa. |

Cómo funciona:

1. Tras la playlist Auto-DJ, el fill-pass vuelve a medir el resto
   del episodio. ¿Es de más de 5 s y como máximo el hueco máximo?
2. Toma una pista reproducible de la playlist de reserva más larga
   que el hueco + 5 s - primero la que lleva más tiempo sin sonar,
   así las pistas se turnan - y la añade tras el último elemento,
   también tras un outro fijo o un webstream.
3. Es el único elemento al que se permite pasar del final del
   programa. El playout la corta exactamente al final del programa o
   la desvanece hasta ese momento; el programa siguiente empieza a su
   hora. Un programa siguiente con **Allow delayed start** no se
   desplaza por ella.
4. El episodio cuenta como exactamente lleno: el calendario lo
   muestra lleno, el pie del show builder indica 00:00 y la fila de
   reserva lleva la nota *(Auto DJ buffer track, ends with the show)*
   en lugar del color de sobrerreserva.

Límites y notas:

- Como todo el fill-pass, solo actúa antes de que empiece el
  episodio (hasta una hora antes). Un hueco que surge durante la
  emisión no queda cubierto.
- Los **programas vinculados** no reciben pista de reserva: un cambio
  en un programa vinculado llega a cada uno de sus episodios.
- El desvanecimiento se aplica cuando el programa siguiente empieza
  con una pista. Antes de un webstream, una entrada de línea o
  silencio, la pista de reserva termina al final del programa sin
  desvanecimiento propio.
- Una fila cuenta como pista de reserva cuando su archivo está en la
  playlist de reserva y pasa del final de su programa. Reserve esas
  pistas para este fin.
- Una repetición (**Repeat of show**) no copia la pista de reserva de
  su origen; recibe la suya si la necesita.
- El artista y el título de la pista de reserva llegan a los
  metadatos del stream y al Live Text como cualquier pista; etiquétela
  de forma neutra o ponga su **Stream Metadata** en *Do not forward*
  (Library → Edit Metadata).
- Si se borra la playlist de reserva, o ninguna de sus pistas
  reproducibles dura más que el hueco máximo + 5 s, el panel muestra
  el aviso *Auto DJ: ...* (y sale una alerta si las alertas están
  activadas).

---

## 5. Programas creados por Auto-DJ en el calendario

Los programas creados por Auto-DJ se ven como cualquier
otro programa, con la pista visual del color de fondo
configurado.

| Acción | ¿Permitida en programas Auto-DJ? |
|---|---|
| **Ver** | Sí |
| **Editar programa** | Sí — pero tenga en cuenta que la edición sucede en el programa auto-creado, no en los valores por defecto Auto-DJ. |
| **Planificar pistas** | Sí |
| **Cancelar programa** | Sí (solo programa actual). |
| **Eliminar programa** | Sí. Después de eliminar, el hueco reaparece y Auto DJ puede re-rellenarlo. |

> **Consejo del operador.** Si quiere **prevenir** que
> Auto DJ re-rellene un hueco (ej. quiere 30 minutos de
> silencio para un homenaje), cree un programa vacío
> puntual explícito sin autoloading playlist sobre ese
> hueco.

---

## 6. Deshabilitar Auto DJ

Configuración → Auto DJ → desmarcar **Habilitado** →
**Guardar**.

Efectos:
- El pre-pass deja de crear nuevos programas. Programas
  Auto-DJ ya creados permanecen.
- El fill-pass deja de completar programas incompletos.

---

## 7. Preguntas frecuentes

### "Auto DJ no está creando programas."

Verifique en este orden:
1. **Habilitado** está marcado y **Guardar** clickeado.
2. **Playlist por defecto** está establecida en una
   playlist no vacía.
3. La ventana de próxima hora contiene un hueco > 60 s.
4. El servicio **RASTATIME-WORKER** corre.
5. Los smart blocks de la playlist configurada devuelven
   al menos una pista coincidente.

### "Auto DJ creó 17 programas diminutos sobre un hueco largo."

Esta fue una regresión en v4 (Sección 23.20). Corregida
desde RASTATIME 2026-05-21.

### "Los programas Auto-DJ muestran zona horaria incorrecta en el diálogo de edición."

Esta fue una regresión en v5 (Sección 23.20). Corregida
el 2026-05-21.

### "¿Puede Auto DJ usar diferentes playlists para diferentes momentos del día?"

No directamente. La playlist Auto-DJ es una sola elección
a nivel emisora.

### "¿Auto DJ honra el fill-pass por-programa diferentemente?"

No — el fill-pass es a nivel emisora.

---

## 8. Perfil Auto-DJ recomendado para nuevas emisoras

| Configuración | Valor |
|---|---|
| **Habilitado** | Apagado (configure todo lo demás primero, luego habilite) |
| **Playlist por defecto** | Una playlist llamada "Auto DJ" conteniendo un smart block: tipo Dinámico, criterios "Tipo de pista = Música", límite "Tiempo restante en el programa", ordenar Aleatorio |
| **Nombre de programa** | `Auto DJ` |
| **Color de fondo** | `222222` (gris oscuro) |
| **Color de texto** | `ffffff` |
| **Rellenar automáticamente** | Apagado (habilitar más tarde) |

---

## A dónde ir después

* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) —
  el contrapunto por-programa.
* [Biblioteca](./LIBRARY.md) → Smart Blocks — primitiva
  más útil para la playlist Auto-DJ.
* [Calendario](./CALENDAR.md) — donde aparecen los
  programas Auto-DJ.
