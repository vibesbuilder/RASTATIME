# Grabación por programa

> **Dónde está usted en el manual.** Este es un toggle
> por-programa en el formulario de edición de programa
> (vea [Calendario](./CALENDAR.md) §2.3). La función
> reemplaza la casilla original "Record from Line In?" por
> una captura más amplia "grabar todo lo que pasa al aire
> durante el programa". Sección 23.13 en ARCHITECTURE
> cubre las decisiones técnicas.

**Grabación por programa** escribe un archivo de todo lo
que estuvo al aire durante un programa — la música, el
micro en vivo, el relevo de webstream, todo — para
archivo, replay, podcast o uso de cumplimiento.

La grabación es un **tap de salida** paralelo: no cambia
nada sobre cómo el programa está planificado o
reproducido. El grabador simplemente escucha la salida
Icecast pública y la escribe a un archivo durante la
duración del programa.

---

## 1. Por qué funciona así

### Lo que hacía LibreTime original

La función original "Record from Line In?" grababa *solo*
la fuente line-in (una entrada física específica), usando
Liquidsoap. Era útil para "un presentador con un micro en
el estudio" pero rota para todo lo demás.

### Lo que hace RASTATIME

El nuevo modelo graba la **salida completa al aire** — lo
que los oyentes escuchan durante el programa,
independientemente de la fuente.

La implementación es un subproceso FFmpeg independiente
que abre el primer mountpoint Icecast configurado de la
emisora como entrada y lo escribe textualmente a un
archivo:

```
   ffmpeg -i http://localhost:8000/rastatime \
          -c copy \
          -t <duración-programa-segundos> \
          -y C:\rastatime\recordings\<show-id>-<starts-at>.mp3
```

| Propiedad | Valor |
|---|---|
| **Coste CPU** | ~1-2 % de un núcleo en Intel i3-1315U |
| **Calidad** | Idéntica al stream público (típicamente 192 k o 320 k MP3) |
| **Aislamiento de fallos** | Crash del grabador nunca afecta el stream en vivo |
| **Cambios de fuente** | Capturados automáticamente |

> **Por qué no grabar el bus interno de alta calidad?**
> Un codificador separado alimentado por PCM podría
> producir 320 kbps MP3 o FLAC, pero costaría ~10x la
> CPU. ARCHITECTURE §23.13 tiene la tabla de alternativas
> consideradas.

---

## 2. Habilitar Grabación por programa

### 2.1 En un nuevo programa

Calendario → Nuevo programa → expandir **Grabación** →
marcar **Grabar este programa:** → Guardar.

### 2.2 En un programa existente

Calendario → clic en el programa → **Editar programa** →
expandir **Grabación** → marcar → Guardar.

> **Consejo del operador.** Muchas emisoras graban cada
> programa por defecto. La forma más rápida: marque
> **Grabar este programa:** en una plantilla, guarde como
> Plantilla de programa, luego aplique esa plantilla a
> cada programa. Vea
> [Plantillas de programa](./SHOW_TEMPLATES.md).

> **Cómo funciona bajo el capó.** El toggle establece
> `cc_show.record = TRUE`. Al inicio del programa, el
> constructor de planning del motor de playout emite un
> evento `SHOW_RECORD_START`. El handler del grabador en
> `backend/playout/libretime_playout/engine/ffmpeg_recorder.py`
> lanza el subproceso FFmpeg. Vea ARCHITECTURE §23.13.

---

## 3. Dónde vive la grabación

Por defecto, las grabaciones se escriben a:

```
   C:\rastatime\recordings\<show-id>-<starts-at>.mp3
```

Ejemplo:

```
   C:\rastatime\recordings\1234-2026-05-21_14-00-00.mp3
```

El directorio y la plantilla de nombre de archivo se
configuran en `config\libretime.conf` bajo la sección
`[recording]`.

Placeholders disponibles: `{show_id}`, `{show_name}`,
`{starts_at}` (datetime), `{ends_at}` (datetime).

---

## 4. Encontrar y descargar una grabación

### Desde el calendario

Clic en el programa → **Ver archivo grabado** en el menú
contextual. Aparece solo después de que la grabación ha
terminado de escribir.

### Desde el sistema de archivos

Navegue `C:\rastatime\recordings\` directamente.

---

## 5. Planificación del tamaño de archivo

Tamaño aproximado para una grabación de 1 hora:

| Bitrate de stream | Tamaño 1 hora |
|---|---|
| 96 kbps MP3 | ~43 MB |
| 128 kbps MP3 | ~58 MB |
| 192 kbps MP3 | ~86 MB |
| 256 kbps MP3 | ~115 MB |
| 320 kbps MP3 | ~145 MB |

Una emisora que corre 24/7 a 192 kbps con todos los
programas grabados llena alrededor de **2 GB por día** o
**730 GB por año**.

Las grabaciones no se auto-eliminan. Para rotarlas,
configure una tarea programada:

```powershell
# Eliminar grabaciones más viejas que 90 días
Get-ChildItem "C:\rastatime\recordings\" -File |
   Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-90) } |
   Remove-Item
```

Vea [`docs/operator/BACKUP.md`](../../operator/BACKUP.md).

---

## 6. Qué incluyen las grabaciones

| Fuente | ¿Incluido? |
|---|---|
| Pistas planificadas | Sí |
| Webstreams | Sí |
| Line-ins | Sí |
| Show DJ (fuente en vivo remota) | Sí |
| Master DJ | Sí |
| Fallback Auto-DJ | Sí |
| Silencio | Sí (como silencio real en el archivo) |

### Lo que las grabaciones NO incluyen

- Audio pre-fader del estudio.
- Múltiples variantes de stream (solo el **primer
  configurado** se graba).
- Metadatos de stream de salida (actualizaciones ICY).

---

## 7. Usar grabaciones como podcasts / catchup

Un workflow de seguimiento común:

1. Grabaciones escritas a `C:\rastatime\recordings\`.
2. Una tarea programada las copia a un directorio
   accesible por web.
3. Un generador de feed RSS produce un feed de podcast.
4. Los oyentes se suscriben.

RASTATIME no entrega un generador RSS integrado.

---

## 8. Grabación de cumplimiento

Algunas jurisdicciones requieren que las emisoras de
difusión guarden un registro de difusión durante N días.
Grabación por programa con cada programa grabado + una
copia de archivo por-día es suficiente para la mayoría
de las regulaciones, pero:

- Verifique que el **bitrate** sea aceptable para su
  regulador.
- Configure **almacenamiento fuera de máquina** para
  resiliencia.
- Documente la **cadena de custodia**.

---

## 9. Deshabilitar Grabación por programa

Editar programa → expandir **Grabación** → desmarcar
**Grabar este programa:** → Guardar.

Las instancias ya grabadas no se ven afectadas. Las
instancias futuras no inician el subproceso FFmpeg.

---

## 10. Preguntas frecuentes

### "¿Por qué la grabación comienza unos segundos antes del programa?"

El subproceso FFmpeg toma ~1-2 segundos para arrancar. El
grabador inicia ~3 segundos *antes* de `starts_at`.

Para retirar el padding pre-programa:

```
ffmpeg -ss 00:00:03 -i input.mp3 -c copy output.mp3
```

### "¿Por qué la grabación está silenciosa?"

Si toda la grabación está silenciosa, el grabador se
adjuntó al stream pero el stream mismo estaba silencioso
durante el programa.

### "¿Puedo grabar solo parte de un programa?"

No. El toggle es por-programa.

### "¿Pueden dos programas emitiendo simultáneamente en diferentes salidas grabar ambos?"

El grabador solo captura el **primer stream configurado**.

### "¿Grabación por programa captura la fuente Live DJ?"

Sí.

### "¿Por qué el tamaño del archivo de grabación es mayor que duración × bitrate?"

La estructura de frame MP3 tiene unos bytes de sobrecarga
por frame.

### "¿Puedo grabar a un bitrate diferente del stream?"

No (porque `-c copy` salta el re-encoding).

---

## A dónde ir después

* [Streams](./STREAMS.md) — el stream de salida que
  Record-per-Show toca.
* [Calendario](./CALENDAR.md) — donde habilitar /
  deshabilitar por programa.
* [Plantillas de programa](./SHOW_TEMPLATES.md) — sellar
  grabación en cada nuevo programa.
* [`docs/operator/BACKUP.md`](../../operator/BACKUP.md) —
  plantilla de política de retención.
