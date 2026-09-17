# Webstreams

> **Dónde está usted en el manual.** Los Webstreams son un
> tipo de item de biblioteca junto a pistas, smart blocks,
> playlists y line-ins. Vea [Biblioteca](./LIBRARY.md)
> para el recorrido general.

Un **Webstream** es una URL apuntando a otra fuente de
audio HTTP — típicamente un stream Icecast o Shoutcast
operado por otra persona. Cuando se planifica en un
programa, el motor de playout se conecta a la URL y emite
su contenido durante la duración configurada.

Los Webstreams son la forma más simple de sindicar
contenido externo: un boletín de noticias por hora
relevado de la BBC, un feed meteorológico local, un
servicio de música automatizado.

---

## 1. La entrada de biblioteca Webstream

Biblioteca → chip de filtro **Webstream** (naranja).

Cada webstream tiene:

| Columna | Significado |
|---|---|
| **Título** | Nombre de visualización. |
| **URL** | La URL fuente HTTP(S). |
| **Longitud** | Duración por defecto cuando planificado. Formato `01h 05m 05s` desde 2026-05-19. |

La Longitud es el *único* parámetro sensible al tiempo —
un webstream "se reproduce para siempre" desde la
perspectiva de la fuente remota; la Longitud en RASTATIME
le dice al playout cuándo desconectarse.

---

## 2. Crear un Webstream

Biblioteca → **+ Nuevo** → **Webstream**.

| Campo | Notas |
|---|---|
| **Nombre** | Requerido. |
| **URL fuente** | Requerida. La URL HTTP(S) del stream de audio. URL de stream directo, no una página de aterrizaje de reproductor. |
| **Longitud por defecto** | Requerida. Formato `HHh MMm SSs`. Vea §3 para el detalle de precisión de segundos. |
| **Descripción** | Texto libre, opcional. |
| **Tipo MIME** | Detectar automáticamente por defecto. |

> **Consejo del operador.** Pruebe la URL en un navegador
> o con `curl -I` antes de guardar.

> **Cómo funciona bajo el capó.** Los webstreams viven en
> `cc_webstream` (id, name, description, url, length,
> creator_id, mtime). Cuando se planifica, una fila
> `cc_schedule` referencia el webstream vía `stream_id`.
> En tiempo de reproducción, el motor de playout abre una
> fuente HTTP vía libVLC. Vea ARCHITECTURE §10.

---

## 3. Longitud por defecto con precisión de segundos (Sección 23.17)

Antes de 2026-05-19, el campo Longitud por defecto
aceptaba solo horas y minutos ("01h 05m"). Desde
2026-05-19, el formulario acepta una **tercera componente
de segundos opcional**:

```
   01h 05m 05s    ← 1 hora 5 minutos 5 segundos
   01h 05m        ← 1 hora 5 minutos
        05m       ← 5 minutos
            45s   ← 45 segundos (un ID de emisora de 45 s vía webstream)
```

> **Por qué esto importa.** Stings cortos, IDs de emisora
> y jingles servidos vía URL webstream debían
> previamente redondearse a un minuto. Un jingle de 30 s
> planificado como "1 minuto" reproducía el jingle
> seguido de 30 s de silencio.

> **Cómo funciona bajo el capó.** Tres puntos calientes
> en `application/models/Webstream.php`. Vea
> ARCHITECTURE §23.17 + commit fae0fc5.

---

## 4. Planificar un Webstream

Igual que cualquier item de biblioteca.

### Qué se reproduce cuando el slot comienza

**Ruta del motor Liquidsoap (default de producción desde 2026-05-29):**

1. Pypo envía tres comandos telnet a Liquidsoap:
   - `webstream.url <URL>` — establece la URL HTTP en la
     fuente dedicada `input.http`.
   - `var.set webstream.gain = <factor>` — establece el
     factor de amplificación por stream (conversión
     dB → lineal en Pypo).
   - `webstream.start` — pide a la fuente que se conecte.
2. La fuente `input.http` de Liquidsoap abre la conexión
   HTTP y bufferiza unos segundos de audio (puente de reloj de
   5 s, búfer de flujo de hasta 10 s). Desde el 2026-09-04 esto
   ocurre ya **10 s antes del slot** («precalentamiento») con la
   *puerta* del bus cerrada, así que el búfer está lleno al inicio
   del slot. Al final del slot Pypo cierra la puerta: el bus funde
   el webstream bajo el siguiente elemento durante la duración de
   crossfade por defecto (Settings → General; 0 = «ducking») y
   luego envía `webstream.stop` — el siguiente elemento arranca a
   su hora.
3. Al inicio del slot Pypo abre la puerta; el bus-switch enruta
   el audio a la fuente webstream en un frame — los oyentes escuchan
   el stream.
4. A la duración configurada, Pypo envía `webstream.stop`;
   el switch vuelve a scheduled (silencio o la siguiente
   pista).

**Bloqueos del servidor de flujo (desde el 2026-09-06):** algunos
servidores dejan de emitir a mitad de flujo sin cerrar la conexión —
Liquidsoap no lo nota por sí solo, y el slot quedaría en silencio
hasta su fin. Un vigilante controla ahora cada webstream en antena:
si la fuente deja de producir audio unos segundos, la emisión la
reconecta (un stop + start limpio). Una conexión nueva vuelve a
antena en unos segundos, y el stop limpio libera la plaza de oyente
en el servidor, para que su límite de conexiones no se llene de
conexiones muertas. Un servidor que rechaza nuevas conexiones sigue
produciendo silencio hasta que acepta una. Desde el 2026-09-07 el
vigilante funciona dentro del propio motor de audio: un contador de
fotogramas comprueba la fuente cada dos segundos y reconecta tras dos
comprobaciones mudas, sin ningún tráfico de sondeo entre la emisión y
el motor (la versión de Windows de Liquidsoap pierde memoria con cada
sondeo de ese tipo). El sondeo anterior desde la emisión se retiró el
2026-09-15 tras una semana tranquila. Desde el 2026-09-08 cada slot de
webstream, y cada reconexión, abre una conexión completamente nueva con
su propio búfer en lugar de reutilizar una entrada permanente: en la
versión de Windows una entrada reutilizada tardaba a veces un minuto o
más en reconectar, y un slot podía empezar con unos segundos del flujo
anterior todavía en el búfer. Ambas cosas han desaparecido; un slot
empieza con su propio flujo, y el precalentamiento diez segundos antes
del slot da tiempo a la nueva conexión para llenarse. Una conexión
descartada que vuelve por sí sola tras una caída se cierra de nuevo en
pocos segundos, para que el servidor de flujo nunca mantenga ocupada
una plaza de oyente con una conexión que nadie escucha.

**Comportamiento de grabación (nuevo desde Phase E,
2026-05-29):**
Los webstreams planificados ahora se incluyen en el
archivo de grabación `.mp3` por show — el audio fluye por
el bus interno de Liquidsoap al que `output.file` está
conectado, y se captura junto con las pistas regulares del
mismo show. Antes de Phase E, los shows solo-webstream
tenían grabaciones silenciosas.

**Latencia inicial del show:** con el precalentamiento (desde
el 2026-09-04) un slot webstream arranca sin hueco — el flujo se
conectó y almacenó 10 s antes. El **mismo** flujo en el programa
siguiente simplemente continúa (solo se traspasa la contabilidad,
sin corte). Solo un webstream *distinto* justo después de otro
webstream (una única fuente de flujo) necesita aún ~5 s de búfer. Los reproductores del lado del oyente añaden su
propio buffer de ~10 s, así que el retraso efectivo percibido por
el oyente final está dominado por el buffer del lado del
reproductor.

### Qué pasa si la URL es inalcanzable

`input.http` reintenta la conexión cada **2 segundos**
(`poll_delay`) con un **timeout de 10 segundos** por
intento (`timeout`). Mientras corren los reintentos,
`source.is_ready` permanece en false y el bus-switch
vuelve a scheduled (silencio). Los reintentos continúan
durante toda la duración del slot planificado.

El log de Liquidsoap captura cada intento de conexión
fallido:

```
[input.http:3] Connection refused: <url>
[input.http:3] Connecting to <url> ...
```

Síntoma visible para el operador: el show reproduce
silencio durante toda su duración. Sin popup de
advertencia en el dashboard; revisa el log de Liquidsoap
— desde el 18/09/2026 la rebanada más reciente
`C:/rastatime/logs/liquidsoap-stdout-*.log` — si un
webstream planificado quedó en silencio.

---

## 5. Editar o eliminar un Webstream

| Acción | Efecto |
|---|---|
| **Editar** | Abrir el diálogo. Los guardados se propagan a *todos* los usos planificados futuros. |
| **Eliminar** | Retirar el webstream. Todas las filas `cc_playlistcontents` y `cc_schedule` se retiran (CASCADE). |

---

## 6. Ganancia de stream (ganancia de entrada por-stream)

Los webstreams de fuentes terceras a menudo son más
fuertes o más débiles que el resto de su biblioteca. Para
normalizar:

Editar el webstream → **Ganancia de entrada (dB)**.

| Configuración | Efecto |
|---|---|
| `0.0` (por defecto) | Sin cambio de ganancia. |
| `+3.0` | Aumento de 3 dB. |
| `-6.0` | Atenuación de 6 dB. |

> **Cómo funciona bajo el capó.** Migración 0048 añadió
> `cc_webstream.input_gain_db` (FLOAT). El motor de
> playout lee esto al abrir la fuente y aplica un filtro
> FFmpeg `volume=<dB>dB`. Vea ARCHITECTURE §10.4.

---

## 7. Webstreams en autoloading playlists

Un webstream puede ser todo el body de una autoloading
playlist.

Limitaciones:
- Un webstream dentro de un body **Repetir hasta lleno**
  produce intentos de conexión cortos repetidos. Evite.
- Smart blocks dentro de una playlist con webstream no
  obtienen el tratamiento de reserva de outro de la misma
  manera.

---

## 8. Preguntas frecuentes

### "¿Por qué mi webstream se corta después de unos segundos?"

Probablemente la **Longitud por defecto** está
configurada muy corta.

### "¿Puedo planificar el mismo webstream en dos programas simultáneamente?"

No. Hay un motor de playout y un mezclador de salida.

### "¿Por qué el webstream suena mal / con glitches?"

Causas comunes: URL intermitente, codec no decodificable,
latencia de red excede el buffer, pérdida de paquetes en
la red.

### "¿Puedo grabar el contenido de un webstream con Record-per-Show?"

Sí. El grabador toca la salida al aire. Vea
[Grabación por programa](./RECORD_PER_SHOW.md).

### "¿Cómo autenticar a una fuente protegida por contraseña?"

Credenciales en línea en la URL:

```
   http://user:password@stream.example.com/private
```

### "¿Puedo usar una URL HLS (.m3u8)?"

Sí — libVLC maneja HLS.

### "¿Puedo usar una URL YouTube Live?"

No directamente. Solución: usar `yt-dlp` para resolver la
URL del stream actual y actualizar la fila de la
biblioteca por cron. No soportado oficialmente.

---

## A dónde ir después

* [Biblioteca](./LIBRARY.md) — recorrido general.
* [Calendario](./CALENDAR.md) — planificar items de
  biblioteca.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) —
  webstreams como contenido autoloaded.
* [Streams](./STREAMS.md) — el lado *saliente*; los
  webstreams aquí son el lado *entrante*.
