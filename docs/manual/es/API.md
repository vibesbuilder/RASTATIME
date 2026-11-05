# API

> **Dónde está en el manual.** Este capítulo es para quien quiera
> leer los datos de RASTATIME desde fuera — el sitio web de la
> emisora, un sitio asociado, un script de supervisión — o saber qué
> expone el sistema al público.  Enumera los puntos de acceso públicos,
> explica el interruptor que los habilita y dice para qué sirve la
> clave API y por qué nunca debe salir de la emisora.  Para los widgets
> iframe listos para usar, vea [Widgets públicos integrables](./WIDGETS.md).

RASTATIME tiene dos interfaces HTTP que nacieron en momentos distintos:

| Interfaz | Ruta base | Formato | Usada por |
|---|---|---|---|
| **API REST v2** | `/api/v2/` | JSON, esquema OpenAPI, Swagger UI | El playout, el analizador, las páginas de Configuración, scripts |
| **API legacy** | `/api/<acción>` | JSON (a veces JSONP), imágenes, M3U | Los widgets, el panel, integraciones antiguas |

Ambas responden en la dirección web de la emisora
(`https://<station-host>/…`).  Todo lo siguiente vale para la emisora
en producción; una instalación de desarrollo se comporta igual.

---

## 1. Quién puede leer qué

| Acceso | Qué cubre |
|---|---|
| **Público, sin inicio de sesión** | Los puntos de acceso de solo lectura de la API legacy de la sección 3, mientras **Configuración → General → Public RASTATIME API** esté activado; además `version`, `info`, `now-playing` y la búsqueda / el envío de peticiones de oyentes de la API v2. |
| **Inicio de sesión (sesión o basic auth)** | Navegar por `/api/v2/` en el navegador, el esquema OpenAPI y la Swagger UI.  Una cuenta conectada ve lo que su rol permite (vea [Usuarios y roles](./USERS_AND_ROLES.md)). |
| **Clave API** | Todos los demás puntos de acceso: escritura, estado interno, listas de archivos, ajustes de streams.  Una sola clave para toda la emisora, acceso completo. |

Todo lo que no es público responde `401` o `403` sin credenciales.  No
hay límite de peticiones en los puntos públicos de lectura; solo los de
peticiones de oyentes están limitados por oyente.

---

## 2. El interruptor: Public RASTATIME API

**Configuración → General → Public RASTATIME API** (on / off).

- **On:** los puntos de lectura de la API legacy responden sin clave.
  Es lo que necesitan los widgets — now-playing, programa semanal y
  reproductor leen `live-info`, `track` y `show-logo`.  Apagar el
  interruptor rompe los widgets de su sitio web.
- **Off:** los mismos puntos exigen la clave API.  Solo tiene sentido
  sin widgets y sin un sitio externo que lea la programación.

El interruptor no toca la API v2 y no abre nada que escriba.

---

## 3. Puntos de acceso públicos de lectura (API legacy)

Todos devuelven JSON salvo indicación.  Horas en la zona horaria de la
emisora, salvo que pase `timezone=` (un nombre de la base tz como
`Europe/Berlin`, o `UTC`).

| Punto de acceso | Parámetros | Devuelve |
|---|---|---|
| `/api/live-info-v2` | `days` (por defecto 2), `shows` (por defecto 5), `timezone` | Lo que está al aire: `shows` (anterior / actual / siguiente), `tracks` (anterior / actual / siguiente), `sources` (DJ en vivo, DJ master, automatización), `station`. |
| `/api/live-info` | `type` (`endofday` o intervalo), `limit` (por defecto 5), `timezone` | La forma antigua de los mismos datos: `currentShow`, `nextShow`, `current`, `next`, `previous`, `schedulerTime`. |
| `/api/week-info` | `timezone` | La programación de esta semana y la siguiente, una lista por día (`monday` … `nextsunday`), cada programa con nombre, horas, descripción, imagen, url. |
| `/api/station-metadata` | — | Nombre, descripción, logo, idioma, zona horaria de la emisora y la lista de streams. |
| `/api/shows` | `show_id` (opcional) | Todos los programas, o uno: id, nombre, descripción, género, url, colores, indicador linked. |
| `/api/show-schedules` | `show_id` (obligatorio), `start`, `end` (`YYYY-MM-DD HH:MM:SS`) | Las instancias de un programa en el periodo. |
| `/api/show-tracks` | `instance_id` (obligatorio) | Las filas de una instancia: posición, título, artista, duración, inicio. |
| `/api/item-history-feed` | `start`, `end`, `instance_id` (opcional) | El historial de emisión: qué sonó y cuándo, con título, artista e instancia. |
| `/api/show-history-feed` | `start`, `end`, `user_id` (opcional) | Los programas emitidos en el periodo. |
| `/api/track?id=<id archivo>&return=<tipo>` | `return` = `artwork`, `artwork-32`, `artwork-64`, `artwork-data` | La carátula de una pista (JPG). |
| `/api/show-logo?id=<id programa>` | — | La imagen de un programa. |
| `/api/track-types` | — | Los tipos de pista configurados en la biblioteca. |
| `/api/stream-m3u` | — | Un archivo M3U con los streams de la emisora. |

**Qué expone una pista.**  Los metadatos de pista en `live-info` y
`live-info-v2` se limitan a propósito a los créditos que un oyente
puede ver: título, artista, álbum, año, género, idioma, duración,
número de pista y de disco, compositor, director, letrista, artista
original, sello, copyright, ISRC, bpm, ánimo, las URL de info / compra /
artista, la referencia de carátula y el tipo de pista.  Rutas de
archivo, propietarios, sumas de verificación, comentarios, letras y
detalles de importación nunca se envían.  `/api/shows` omite igualmente
los ids de las playlists de autoloading, intro y outro.

---

## 4. Puntos de acceso públicos de la API v2

| Punto de acceso | Devuelve |
|---|---|
| `GET /api/v2/version` | `{"api_version": "…"}` |
| `GET /api/v2/info` | `{"station_name": "…"}` |
| `GET /api/v2/now-playing` | Lo que está al aire, leído de la parrilla (vea abajo). |
| `GET /api/v2/song-requests/search?q=<texto>` | Pistas que un oyente puede pedir: id, title, artist, album, has_artwork. |
| `POST /api/v2/song-requests` | Envía una petición (`file_id`, `listener_label` opcional).  Limitado por oyente; vea [Song Requests](./SONG_REQUESTS.md). |

**now-playing** responde siempre `200`:

```json
{
  "is_playing": true,
  "now": "2026-11-05T13:07:21+00:00",
  "source": "scheduled",
  "started_at": "2026-11-05T13:07:00+00:00",
  "item": {
    "type": "file", "id": 1304,
    "title": "Example Song", "artist": "Example Artist", "album": "Example Album",
    "genre": "Pop", "year": "2024",
    "length_seconds": 251.438, "has_artwork": true,
    "starts_at": "2026-11-05T13:07:00+00:00",
    "ends_at": "2026-11-05T13:11:11+00:00"
  },
  "show": {"id": 912, "name": "…", "description": "…", "url": "…",
           "genre": "…", "starts_at": "…", "ends_at": "…"},
  "next": {"type": "file", "id": 1305, "title": "…", "…": "…"}
}
```

`type` es `file`, `webstream` o `linein`; `source` es `scheduled`,
`live_dj` o `master_dj`.  Cuando nada de la parrilla está al aire,
`is_playing` es `false`, `item` y `started_at` son `null`, y `show`
sigue nombrando el programa en curso.  Horas en UTC (ISO 8601).

---

## 5. Usar la API con credenciales

**En el navegador.**  Inicie sesión en RASTATIME y abra
`https://<station-host>/api/v2/` para la API navegable y
`https://<station-host>/api/v2/schema/swagger-ui` para la Swagger UI
(el esquema OpenAPI en bruto está en `/api/v2/schema`).  Ambos exigen
la sesión; sin ella responden `403`.

**Desde un script.**  Envíe la clave API de la emisora en la cabecera
`Authorization`:

```
Authorization: Api-Key <key>
```

La clave es el valor `api_key` bajo `[general]` en
`C:\rastatime\config\rastatime.conf`.  La API legacy también la acepta
como `?api_key=<key>`.

> **Nunca entregue la clave a terceros.**  Hay exactamente una clave y
> da acceso completo: pushes de parrilla, listas de archivos,
> contraseñas de streams, configuración.  Un sitio asociado que solo
> necesita la programación usa los puntos públicos de la sección 3 —
> sin clave.  Si necesita más que leer, eso es una petición de un token
> de cliente de solo lectura (vea BACKLOG), no de la clave de la emisora.

---

## 6. Ejemplos

Lo que está al aire (público):

```bash
curl -s "https://<station-host>/api/v2/now-playing"
```

La programación de esta semana en UTC (público):

```bash
curl -s "https://<station-host>/api/week-info?timezone=UTC"
```

Las filas de una instancia de programa (público):

```bash
curl -s "https://<station-host>/api/show-tracks?instance_id=12345"
```

El historial de emisión de un día (público):

```bash
curl -s "https://<station-host>/api/item-history-feed?start=2026-11-05%2000:00:00&end=2026-11-05%2023:59:59"
```

Un punto protegido con la clave (desde la máquina de la emisora):

```bash
curl -s -H "Authorization: Api-Key <key>" "https://<station-host>/api/v2/files?limit=5"
```

---

## 7. Preguntas frecuentes

**¿Puedo publicar la dirección de la API en el sitio de la emisora?**
Sí, para los puntos públicos.  Solo contienen la programación y los
créditos de las pistas.

**¿Por qué `/api/version` responde 401?**  Ese punto legacy no forma
parte del conjunto público; use `/api/v2/version`.

**¿La API indica cuándo un DJ está en vivo?**  `live-info-v2` →
`sources` y `now-playing` → `source`.

**¿Hay límite de peticiones?**  No en los puntos públicos de lectura.
Una página que consulta `live-info-v2` cada pocos segundos por
visitante es aceptable para el sitio de una emisora; un rastreador que
descarga `week-info` (unos 270 KB) en bucle, no — ponga una caché
delante.

> **Cómo funciona bajo el capó.**  Las acciones legacy sin clave están
> en `ApiController::$ignoreAuth`; aun así comprueban el interruptor
> (`Application_Model_Preference::GetAllow3rdPartyApi`).  La lista
> blanca de pistas es `WidgetHelper::PUBLIC_TRACK_FIELDS`
> (`restrictLiveInfo`), la de programas `PUBLIC_SHOW_FIELDS`.  Los
> permisos de la API v2 viven en `rastatime_api/permissions.py`
> (`IsSystemTokenOrUser`: Api-Key o usuario conectado con los permisos
> Django de su rol; `internal_only` para las vistas simples que llama
> el playout).  Las vistas del esquema llevan `IsAuthenticated`.
> `now-playing` lee en `cc_schedule` la fila que cubre *ahora* y
> pregunta al playout en `/source-state` por los indicadores de DJ.
> Vea ARCHITECTURE §23.90 y §23.91.
