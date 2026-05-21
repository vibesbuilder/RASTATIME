# Line-In

> **Dónde está usted en el manual.** Este capítulo cubre
> el tipo de item de biblioteca **Line-In** — entradas de
> audio en vivo nombradas que puede arrastrar a playlists
> y programas. Para la configuración de tarjeta de sonido
> del lado de la máquina-operador, vea
> [Máquina local](./LOCAL_MACHINE.md). Para el
> procedimiento de emergencia cuando un line-in cae en
> silencio o ruido, vea
> [`docs/operator/LINE_IN_BROKEN.md`](../../operator/LINE_IN_BROKEN.md).

Un **Line-In** es una entrada de audio en vivo nombrada
desde un dispositivo de tarjeta de sonido en la máquina
del operador — un micrófono, una salida de mezclador, un
reproductor CD, una interfaz de audio externa — que
RASTATIME expone como item de biblioteca.

Los Line-Ins son nuevos en RASTATIME (2026-05-12).
Reemplazan el slot "Line In" único codificado que
LibreTime original tenía.

---

## 1. Vista general del concepto

Un Line-In tiene dos capas:

| Capa | Qué es | Dónde vive |
|---|---|---|
| **Dispositivo físico** | La entrada real de tarjeta de sonido — un micrófono USB, un jack line incorporado, una interfaz XLR, etc. Identificado por su ID de dispositivo del lado del OS. | La configuración de tarjeta de sonido de la máquina del operador; vea [Máquina local](./LOCAL_MACHINE.md). |
| **Line-In nombrado** | Una fila de biblioteca que *referencia* un dispositivo físico por ID, más un nombre de visualización y configuración. | Tabla `rastatime_linein`. |

Un solo dispositivo físico puede respaldar **como máximo
un** Line-In a la vez.

---

## 2. La página Line-In Library

Configuración → **Line-In Library** (o haga clic en el
chip Line-In verde en la página Biblioteca principal).

Cada fila es un Line-In nombrado. Las columnas:

| Columna | Significado |
|---|---|
| **Nombre** | El nombre de visualización. |
| **Dispositivo** | El dispositivo de tarjeta de sonido que el Line-In referencia. |
| **Longitud por defecto** | La duración por defecto que una fila Line-In ocupa cuando se arrastra a una playlist o programa. `∞` significa "se reproduce hasta que se le diga que pare". |

La barra de herramientas:

| Botón | Qué hace |
|---|---|
| **+ Nuevo** | Abrir el diálogo nuevo-Line-In. |
| **Editar** | Abrir el diálogo de edición. |
| **Habilitar / Deshabilitar** | Alternar el estado disponible sin eliminar. |
| **Eliminar** | Retirar el Line-In. |

> **Cómo funciona bajo el capó.** Todas las acciones
> mutantes son finos pass-through desde
> `application/controllers/LineinController.php` a la API
> REST Django en `/api/v2/audio/linein[/<id>]`. El
> controlador solo aplica ACL (Admin + Super Admin); el
> lado Python en `backend/api/libretime_api/linein/` posee
> validación y persistencia en `rastatime_linein`. Vea
> ARCHITECTURE §14.

---

## 3. Crear un Line-In

Line-In Library → **+ Nuevo**.

| Campo | Notas |
|---|---|
| **Nombre** | Requerido. Único. La etiqueta visible en todas partes. |
| **Dispositivo** | Requerido. El menú desplegable lista cada dispositivo de entrada que el OS ve ahora. Si su dispositivo falta, vea [Máquina local](./LOCAL_MACHINE.md). |
| **Longitud por defecto** | Requerida. Formato `HHh MMm SSs` (mismo parser que Webstreams). Para "se reproduce hasta que se le diga que pare" use `0h 0m 0s`. |
| **Habilitado** | Por defecto activado. |

### La longitud por defecto importa

- Para un **micrófono** en un estudio normal de solo
  habla, establezca la Longitud por defecto a la longitud
  típica del segmento de habla (5 min es común).
- Para una **salida de mezclador** que conduce todo el
  programa, establézcala a la longitud completa del
  programa (ej. 60 min) o infinito.
- Para un **reproductor CD** u otra fuente cronometrada,
  establézcala a la longitud típica de pista (3 min).

---

## 4. Usar un Line-In en un programa

Dos caminos:

### 4.1 Arrastre directo a un programa

Show-builder → arrastre la fila Line-In del panel
Biblioteca al programa. Un item de planning aparece con
el nombre y la Longitud por defecto del Line-In.

### 4.2 Dentro de una playlist

Editor de playlist → arrastre el Line-In desde la
Biblioteca.

> **Cómo funciona bajo el capó.** Migración 0054
> (2026-05-19) añadió `cc_playlistcontents.linein_id`
> como foreign key nullable a `rastatime_linein`, más una
> restricción CHECK de que exactamente uno de `file_id` /
> `stream_id` / `block_id` / `linein_id` es no-NULL por
> fila. Tipo 3 en `cc_playlistcontents.type` indica una
> fila Line-In. ARCHITECTURE §23.18 cubre la decisión de
> esquema.

### Qué se reproduce cuando el slot del Line-In comienza?

El motor de playout envía un evento `LINEIN_START` al
source switcher, que:

1. Detiene lo que estaba al aire.
2. Abre el dispositivo de entrada de tarjeta de sonido
   configurado.
3. Enruta el audio entrante al stream de salida.

Cuando la duración del slot transcurre, el motor envía un
evento `LINEIN_END` y el source switcher regresa al
planning.

---

## 5. Editar o retirar un Line-In

### Editar

Line-In Library → clic en la fila → **Editar**. Cambie
nombre, dispositivo, longitud por defecto o estado
habilitado. **Guardar**.

- **Cambio de nombre** se propaga a la lista Biblioteca y
  al widget En reproducción en la próxima actualización.
- **Cambio de dispositivo** se propaga a *cada* uso
  futuro.
- **Cambio de longitud por defecto** afecta solo *nuevos*
  usos.
- **Habilitado = apagado** retira el Line-In
  inmediatamente de la biblioteca de arrastre.

### Deshabilitar

Menú contextual de fila → **Deshabilitar**.

### Eliminar

Menú contextual de fila → **Eliminar**. Confirme. El
Line-In se retira *y* cada fila `cc_playlistcontents` y
`cc_schedule` que lo referencia se retira (CASCADE).

> **Consejo del operador.** Prefiera **Deshabilitar**
> sobre **Eliminar** a menos que esté seguro de que nunca
> usará el Line-In de nuevo.

---

## 6. La dependencia del dispositivo físico

Un Line-In referencia un dispositivo de tarjeta de sonido
por **ID del lado del OS**. Ese ID es estable a través de
reinicios mientras:

- El dispositivo permanezca enchufado.
- Ningún otro software de audio haya sido instalado que
  reasigne IDs de dispositivo.

Si el dispositivo desaparece:

- El Line-In sigue en la Biblioteca.
- Su fila en Configuración → Line-In Library muestra una
  insignia de **signo de exclamación rojo** junto a la
  columna dispositivo.
- Cualquier planning que intente reproducir el Line-In lo
  salta con una advertencia "Device not found" en el log
  de playout.
- El fallback (silencio o bucle fallback) se reproduce.

Vea
[`docs/operator/DEVICE_MISSING.md`](../../operator/DEVICE_MISSING.md)
para el runbook de recuperación.

---

## 7. Permisos

Solo los roles **Admin (A)** y **Super Admin (S)** pueden
crear, editar o eliminar Line-Ins.

DJs (H) y Program Managers (P) pueden arrastrar Line-Ins
existentes a sus propias playlists / programas, pero no
pueden crear o modificar las definiciones de Line-In
subyacentes.

---

## 8. Preguntas frecuentes

### "¿Dónde está la configuración 'Show Source' / 'Master Source' / 'Line In' original?"

LibreTime original tenía tres entradas codificadas
configuradas bajo **Configuración → Live Sources**.
RASTATIME mantiene Show Source y Master Source (estas son
entradas DJ remotas sobre Icecast) pero reemplaza el
"Line In" único codificado por la función Line-In
nombrado.

### "¿Pueden dos Line-Ins referenciar el mismo dispositivo físico?"

Sí, pero solo uno tendrá éxito en cualquier momento. La
mayoría de drivers de tarjeta de sonido conceden acceso
exclusivo al primer abridor.

### "¿Puede un Line-In ser el único contenido de la autoloading playlist?"

Sí. Cree una playlist conteniendo exactamente una fila
Line-In con Longitud por defecto = la longitud del
programa (o infinito).

### "¿Se graba el audio del Line-In si Record-per-Show está habilitado?"

Sí. El grabador toca la salida Icecast, que lleva lo que
sea que está actualmente al aire. Vea
[Grabación por programa](./RECORD_PER_SHOW.md).

### "¿Puedo añadir una fuente de audio de red (ej. AES67 / Dante) como Line-In?"

Solo si la fuente se presenta como dispositivo de entrada
de tarjeta de sonido Windows — muchos drivers AES67 /
Dante entregan una tarjeta de sonido virtual.

---

## A dónde ir después

* [Máquina local](./LOCAL_MACHINE.md) — configuración
  física de tarjeta de sonido.
* [Biblioteca](./LIBRARY.md) — los Line-Ins aparecen
  también en la Biblioteca principal.
* [Panel](./DASHBOARD.md) → Estado de fuente — vea qué
  Line-In está actualmente al aire.
* [`docs/operator/LINE_IN_BROKEN.md`](../../operator/LINE_IN_BROKEN.md)
  — procedimiento de emergencia.
* [`docs/operator/DEVICE_MISSING.md`](../../operator/DEVICE_MISSING.md)
  — cuando el dispositivo subyacente desaparece.
