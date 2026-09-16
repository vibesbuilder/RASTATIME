# Grabación 24/7 (Record-per-Hour)

> **Dónde está en el manual.** Esta es la función de
> **Grabación 24/7** para toda la estación, configurada en
> [Configuración → Máquina local](./LOCAL_MACHINE.md). Es la
> compañera permanente de la [Grabación por
> programa](./RECORD_PER_SHOW.md).

La **Grabación 24/7** graba de forma continua todo lo que sale
al aire — las 24 horas, independientemente de los programas — y
lo divide en **un archivo por hora de reloj**. Captura los
huecos que la grabación por programa se pierde (relleno de
Auto-DJ, silencios entre programas, contenido no planificado,
emergencias), lo que la hace la herramienta adecuada para
**archivos de cumplimiento, escucha diferida / recuperación y
copia de seguridad de emergencia**.

Como el grabador por programa, es una **toma de salida**
paralela sobre el bus de audio interno de Liquidsoap: no cambia
nada de cómo se planifica o reproduce la estación — solo
escucha el audio al aire y lo escribe en el disco.

---

## 1. Grabación 24/7 vs. por programa

Los dos grabadores son independientes y pueden funcionar a la
vez, en **carpetas separadas**.

| | Por programa | 24/7 |
|---|---|---|
| **Alcance** | Un archivo por programa marcado «grabar» | Un archivo por hora de reloj, siempre activo |
| **Captura** | Solo mientras un programa grabado está al aire | Todo, 24/7 (incl. huecos, relleno, emergencias) |
| **Configurado** | Por programa (Calendario) | Una vez (Configuración → Máquina local) |
| **Nombre de archivo** | `<YYYY-MM-DD HH-MM> - <programa>.mp3` | `<YYYY-MM-DD HH>-00.<ext>` |
| **Calidad** | MP3 320 kbps fijo | Formato + tasa de bits a elección (predet. 192 kbps MP3) |
| **Archivos de marcas** | No | Sí (`.cues.json` por hora) |

> **¿Por qué dos grabadores?** El modo por programa da un
> archivo limpio, titulado por programa, para los programas que
> le importan. El modo 24/7 da un archivo ininterrumpido de
> toda la emisión para cumplimiento y escucha diferida. Muchas
> estaciones usan ambos.

---

## 2. Cómo funciona

Un segundo bloque `output.file` de Liquidsoap toma el mismo bus
de audio interno que alimenta las salidas Icecast públicas, y
rota a un archivo nuevo en cada cambio de hora:

```liquidsoap
output.file(
  id="recording_hourly",
  reopen_when=rec247_reopen,   # verdadero cuando cambia la hora de reloj
  fallible=true,
  %ffmpeg(format="mp3", %audio(codec="libmp3lame", b="192k")),
  {rec247_path()},             # <carpeta>/<YYYY-MM-DD>/<YYYY-MM-DD HH>-00.mp3
  bus,
)
```

El bloque se renderiza en el script Liquidsoap en ejecución
**solo cuando activa la función**; de lo contrario es un
comentario sin efecto y el flujo en directo queda intacto.

> **Escrita por Liquidsoap.** Como la grabación por programa,
> la 24/7 la provee `output.file` de Liquidsoap en el bus
> interno (Liquidsoap es el único motor de playout desde el
> 2026-09-10).

---

## 3. Activar la grabación 24/7

**Configuración → Máquina local → «24/7 Recording Folder»** (la
sección justo encima de «Show Recording Folder»):

| Campo | Significado |
|---|---|
| **Enable** | Interruptor principal. Se requiere una carpeta si está activado. |
| **Folder path** | Ruta absoluta en esta máquina — creada al guardar si no existe. Dentro o fuera del árbol del proyecto (p. ej. `C:\rastatime\recordings-247` o `D:\rec247`). Manténgala **separada** de la Show Recording Folder. |
| **Format** | MP3 / AAC / OGG (Vorbis) / Opus. Predet. **MP3**. |
| **Bitrate** | 96–320 kbps. Predet. **192** (calidad de archivo, ~la mitad del disco de 320). |
| **Delete after (days)** | Ventana de limpieza automática. `0` = conservar para siempre. |

Pulse **Save**, luego **reinicie el servicio de playout** para
aplicar (véase [§5](#5-aplicar-los-cambios)). La línea de estado
se lo recuerda.

> **Bajo el capó.** Save guarda las claves cc_pref
> `local_247_recording_{enabled,folder,format,bitrate,retention_days}`.
> Al arrancar el playout se leen y se renderizan en
> `rastatime.liq`; el demonio de limpieza y el escritor de
> marcas también las leen.

---

## 4. Dónde viven las grabaciones

```
   <carpeta>\<YYYY-MM-DD>\<YYYY-MM-DD HH>-00.<ext>
   <carpeta>\<YYYY-MM-DD>\<YYYY-MM-DD HH>-00.cues.json
```

Ejemplo (carpeta `C:\rastatime\recordings-247`, MP3):

```
   C:\rastatime\recordings-247\2026-06-05\2026-06-05 14-00.mp3
   C:\rastatime\recordings-247\2026-06-05\2026-06-05 14-00.cues.json
```

Las horas son el **reloj local del ordenador del estudio**,
para que el nombre del archivo coincida con lo que estaba al
aire. Los archivos rotan en la hora en punto; la transición es
sin cortes (ningún hueco audible entre horas).

### 4.1 Archivos de marcas (cue sidecars)

Junto a cada archivo de audio horario hay un **archivo de
marcas** JSON que señala lo que ocurrió durante esa hora, para
que un futuro reproductor de recuperación salte directo a un
programa o pista:

```json
{
  "version": 1,
  "recording": "2026-06-05 14-00.mp3",
  "hour_start": "2026-06-05T14:00:00",
  "audio_start": "2026-06-05T14:00:00",
  "audio_start_offset": 0.0,
  "marks": [
    {"t": 0.0,   "kind": "show",  "event": "start", "name": "Tarde"},
    {"t": 0.0,   "kind": "track", "event": "start", "show": "Tarde",
                 "title": "Song A", "artist": "Artist A"},
    {"t": 183.4, "kind": "track", "event": "end"},
    {"t": 600.0, "kind": "webstream", "event": "start", "show": "Noticias"}
  ]
}
```

`t` es el desplazamiento **en segundos desde el inicio de la
hora**. `kind` es `track` / `show` / `webstream` / `linein`;
`event` es `start` / `end`. Los límites de programa se deducen
de un cambio de programa, así que cubren todo programa con
contenido. Una pista que cruza el cambio de hora tiene su
`start` en el archivo de marcas de la hora anterior y su `end`
en el nuevo.

Desde el 16/09/2026 el archivo de marcas anota también cuándo se
creó el archivo de audio de la hora: `audio_start` (hora local) y
`audio_start_offset` (segundos después de `hour_start`). Una hora
completa tiene desplazamiento 0; la primera hora parcial tras un
reinicio - cada día tras el reinicio de las 04:00 - empieza más
tarde, y un reproductor se sitúa entonces en
`t - audio_start_offset` dentro de ese archivo.

---

## 5. Aplicar los cambios

> **Desde el 16/09/2026 no hace falta ningún reinicio manual.** La
> reproducción detecta un cambio guardado en su siguiente actualización
> de la programación (en menos de dos minutos), vuelve a generar el
> script y reinicia Liquidsoap en el siguiente momento tranquilo, o, con
> una programación 24/7, entre dos pistas de archivo. Los oyentes siguen
> conectados a través de los montajes de reserva; la primera hora tras
> el reinicio es un archivo parcial (véase `audio_start` en §4.1); un
> reinicio dentro de una hora continúa en un segundo archivo de esa hora
> (`… HH-00.2.mp3`, el archivo de marcas lista las partes), solo faltan
> los pocos segundos del reinicio. Los
> pasos siguientes siguen siendo la vía manual.

Los ajustes 24/7 se leen al arrancar el playout y se integran
en el script Liquidsoap. Tras guardar un cambio (Enable,
carpeta, formato, tasa de bits), **reinicie el servicio de
playout** para que regenere el script:

- Reinicie el servicio de Windows **RASTATIME-PLAYOUT**
  (regenera `rastatime.liq` y reinicia **RASTATIME-LIQUIDSOAP**).
- Elija un momento de baja audiencia — el reinicio causa una
  breve (~5 s) reconexión del flujo.

La excepción es el valor **Delete after (days)**: el demonio de
limpieza lo relee en cada ciclo, así que un cambio solo de la
retención surte efecto en menos de una hora sin reinicio.

> **Reversión.** Desmarque Enable, guarde y reinicie — el
> bloque grabador ya no se renderiza y el flujo se comporta
> exactamente como antes. Los archivos ya grabados permanecen
> en el disco.

---

## 6. Limpieza automática (retención)

Cuando **Delete after (days)** es mayor que 0, un demonio dentro
del servicio de playout purga carpetas diarias enteras en
cuanto alcanzan esa antigüedad. Funciona aproximadamente una
vez por hora.

Solo toca carpetas diarias con nombre `YYYY-MM-DD` **dentro de
la carpeta 24/7** — su Show Recording Folder y cualquier otro
archivo nunca se ven afectados. `0` desactiva la limpieza
(conservar para siempre).

---

## 7. La exclusión del antivirus es OBLIGATORIA

> ⚠️ La misma advertencia que en [Grabación por programa §3.5](./RECORD_PER_SHOW.md)
> — y aquí importa aún más, porque el grabador 24/7 escribe **de
> forma continua**.

Los antivirus en tiempo real (Bitdefender, Windows Defender, …)
analizan cada escritura en el archivo en crecimiento y pueden
bloquear el codificador lo bastante como para perder audio.
**Añada la carpeta 24/7 a la lista de exclusiones de su
antivirus** antes de activar el grabador.

Si un archivo horario sale corto mientras todo lo demás va
bien, las causas habituales son el análisis antivirus o una
máquina sobrecargada (el «catch-up de latencia» de Liquidsoap
bajo alta carga de CPU/disco puede perder audio de grabación).
El primer archivo tras activar es siempre una hora parcial —
eso es lo esperado.

---

## 8. Planificar el espacio en disco

La grabación 24/7 nunca se detiene; dimensione el disco para el
día entero × la ventana de retención:

| Tasa de bits | 1 hora | 1 día | 1 semana |
|---|---|---|---|
| 128 kbps | ~58 MB | ~1,4 GB | ~9,5 GB |
| 192 kbps *(predet.)* | ~86 MB | ~2,1 GB | ~14 GB |
| 320 kbps | ~145 MB | ~3,4 GB | ~24 GB |

Con **Delete after (days)** definido, la huella está acotada:
aproximadamente `tamaño de un día × días de retención`. Los
archivos de marcas son diminutos (unos pocos KB por hora).

---

## 9. Preguntas frecuentes

### «¿Por qué el primer archivo es más corto que una hora?»

El grabador arranca cuando activa + reinicia, normalmente a
mitad de hora — así que el primer archivo cubre solo el resto
de esa hora. Cada archivo siguiente es una hora de reloj
completa.

### «Una hora salió unos minutos corta, ¿es un fallo?»

Casi siempre carga externa, no el grabador: un análisis
antivirus (véase [§7](#7-la-exclusión-del-antivirus-es-obligatoria))
o una máquina sobrecargada que hace que Liquidsoap pierda audio
durante el catch-up de latencia. Una diferencia de 1–3 segundos
es la alineación normal de tramas MP3.

### «¿Puedo grabar en 24/7 y por programa a la vez?»

Sí. Son tomas `output.file` independientes sobre el mismo bus,
escribiendo en carpetas separadas. Ambas funcionan juntas sin
coordinación adicional.

### «¿Captura DJ en directo / webstream / line-in?»

Sí — toma el bus al aire, así que se graba lo que oyen los
oyentes, sea cual sea la fuente. (Las marcas para una toma de
control de DJ-harbor en directo son una limitación conocida de
v1 — el audio se graba igual, el segmento en directo solo puede
no tener su propia marca.)

### «¿Puedo cambiar el formato / tasa de bits más tarde?»

Sí — cámbielo en Configuración y reinicie el servicio de
playout. Los archivos existentes conservan su formato original;
las horas nuevas usan el nuevo ajuste.

---

## A dónde ir después

* [Grabación por programa](./RECORD_PER_SHOW.md) — el grabador
  compañero por programa.
* [Configuración → Máquina local](./LOCAL_MACHINE.md) — donde
  configura ambos grabadores.
* [Streams](./STREAMS.md) — la salida al aire que ambos
  grabadores toman.
* [`docs/operator/BACKUP.md`](../../operator/BACKUP.md) —
  política de retención / copia fuera de la máquina.
