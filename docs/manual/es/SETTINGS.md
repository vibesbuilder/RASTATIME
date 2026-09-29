# Configuración

> **Dónde está usted en el manual.** Este capítulo es el
> índice hub-y-radios para el menú Configuración.

El menú Configuración es la superficie de configuración
por-emisora. Visible completamente solo para **Admin** y
**Super Admin**; **Program Manager** ve un subconjunto.
Vea [Usuarios y roles](./USERS_AND_ROLES.md) §5 para la
matriz completa de permisos.

---

## 1. El menú Configuración

| Página | Propósito | Capítulo |
|---|---|---|
| **Preferencias generales** | Nombre de emisora, idioma por defecto, colores por defecto, vista anticipada del panel, propietario de importación por defecto, duración crossfade por defecto, favicon, logo de emisora. | Este capítulo §2 |
| **Máquina local** | Dispositivos de salida/entrada de tarjeta de sonido, carpeta de importación local, carpeta de grabación local. | [Máquina local](./LOCAL_MACHINE.md) |
| **Streams** | Hasta cuatro streams de salida. | [Streams](./STREAMS.md) |
| **Line-In Library** | Entradas de audio en vivo nombradas. | [Line-In](./LINE_IN.md) |
| **Auto DJ** | Rellenador en segundo plano. | [Auto DJ](./AUTO_DJ.md) |
| **Plantillas de programa** | Snapshots de formulario de programa reutilizables. | [Plantillas de programa](./SHOW_TEMPLATES.md) |
| **Gestionar usuarios** | Crear / editar / desactivar usuarios. | [Usuarios y roles](./USERS_AND_ROLES.md) |
| **Localización** | Selección de idioma UI. | [Idiomas](./I18N.md) |
| **Estado del sistema** | Salud en vivo de servicios, widget de reinicio. | Este capítulo §3 |
| **Tools** | Submenú: Consola DB, Visor de logs, Reinicio de caché. | Este capítulo §4 |

---

## 2. Preferencias generales

Configuración → **Preferencias generales**.

### Emisora

| Campo | Notas |
|---|---|
| **Nombre de emisora** | Visible en todas partes — título de página, metadatos ICY, nombre From de email. |
| **Descripción de emisora** | Descripción de texto libre. |
| **Logo de emisora** | Imagen arriba a la izquierda de cada página. Máx 200 KB. |
| **Favicon de emisora** | Imagen en la pestaña del navegador. Máx 200 KB. Renderizado como URI data:. |
| **Color principal** | El color de acento de toda la interfaz y de la página de radio — enlaces, resaltados, filas seleccionadas, la entrada de menú activa, barras de progreso y de almacenamiento, barras de desplazamiento, flechas de sección, el botón de reproducción y el volumen del reproductor. Introduzca `#rrggbb` o use el selector junto al campo; **Restablecer el valor predeterminado** recupera el naranja (`#ff5d1a`). Surte efecto en la siguiente carga de página. Elija un color que destaque sobre el fondo gris oscuro; el texto sobre él cambia solo entre blanco y negro. Los colores de señalización (errores, avisos, los colores de los programas en el calendario) y los acentos propios de los widgets Now Playing / Programa semanal (verde azulado) y Song Request (azul) no cambian. |
| **Zona horaria** | La zona horaria del operador. Almacenada por-programa en `cc_show_days.timezone`. |
| **La semana comienza el** | Lunes / Domingo. |

### Valores por defecto

| Campo | Notas |
|---|---|
| **Idioma por defecto** | Idioma UI para nuevos usuarios + la pantalla de inicio de sesión. |
| **Default Track Crossfade Duration** (duración del crossfade entre pistas) | El crossfade entre dos pistas consecutivas **del mismo programa**: la pista saliente se desvanece mientras la entrante sube durante estos segundos (1 segundo es típico; 0 = las pistas se siguen sin solapamiento; hasta 10 segundos para transiciones suaves). La parrilla coloca las filas consecutivas con exactamente este solapamiento. |
| **Default Show Crossfade Duration** (duración del crossfade entre programas) | La transición **en el límite de un programa** (desde el 2026-09-27): el programa anterior se desvanece durante estos segundos mientras la primera pista del nuevo empieza de inmediato a volumen completo — un programa que abre con un jingle o una identificación se oye desde su primer golpe. La misma forma y el mismo valor rigen cada cambio entre **entradas** (pista ↔ webstream ↔ Line-In): la fuente entrante está a volumen completo al instante, la saliente se desvanece por debajo; 0 = cambio seco. Un webstream o Line-In programado en ambos programas sigue sonando sin corte. Valor inicial 1 s. La cadena de audio aplica ambos valores unos segundos después de guardar (reinicio planificado en un momento tranquilo o en un límite de pista); «Aplicar ahora» en Settings → Local Machine lo fuerza. |
| ~~Crossfade por defecto~~ (antiguo campo único, hasta el 2026-09-27) | El *crossfade de la casa*. Entre pistas consecutivas del mismo programa es la duración del crossfade (1 segundo es típico; 0 = cortes secos). Desde el 2026-09-04 el valor también da forma a cada cambio entre **entradas** (pista ↔ webstream ↔ Line-In): un valor mayor que 0 funde la fuente saliente en la entrante durante esos segundos; **0 significa «ducking»** — la fuente entrante arranca de inmediato a nivel completo y la saliente se desvanece por debajo en 1 s. En ambos casos la cola almacenada de la fuente saliente se oye, no se corta. Surte efecto tras reiniciar la cadena de audio («Aplicar ahora» en Settings → Local Machine). |
| **Tipo de pista por defecto** | Tipo de pista asignado a nuevos uploads. |
| **Propietario de importación por defecto** | Cuenta acreditada como propietario para archivos importados vía la Carpeta de importación local. |
| **Grabación por defecto** | Si marcado, los nuevos programas tienen **Grabar este programa:** pre-marcado. |

### Panel

| Campo | Notas |
|---|---|
| **Vista anticipada** | Cuántos programas próximos el panel "Viene después" muestra. 3-5 es típico. |
| **Intervalo de refresco** | Con qué frecuencia el Panel sondea. 5 s es el por defecto. |

### Info de texto en vivo

Sección plegable bajo las Preferencias generales (desde el 2026-09-28). La
línea «now playing» como archivo de texto para otros sistemas (web,
pantallas, agregadores): una línea UTF-8, siempre reemplazada, escrita por
el playout en cada cambio de pista, webstream, entrada de línea o DJ.

| Campo | Notas |
|---|---|
| **¿Escribir la línea «now playing» en un archivo de texto?** | Interruptor principal. |
| **Formato del texto en vivo** | Las mismas tres variantes que el Stream Label (Artist - Title / Show - Artist - Title / Station name - Show name) con los mismos respaldos: una fuente en vivo sin intérprete ni título muestra *Station name - Show name*, el silencio muestra el texto Off Air. Independiente del Stream Label. |
| **Publicar en la web** | El archivo se sirve en `http://<host>/live/now-playing.txt` (archivo estático, sin inicio de sesión, independiente del interruptor Public API). Accesible desde Internet en cuanto lo sea el servidor web, como los widgets. |
| **Escribir también en un archivo** | Ruta absoluta opcional (este equipo o un recurso compartido de red). |
| **Subir a un servidor FTP** | En cada cambio el archivo se sube por FTP, FTPS (TLS explícito) o SFTP a la ruta remota; credenciales propias, separadas de la importación FTP. SFTP necesita un `curl` con libssh2 (el que trae Git para Windows; el curl integrado de Windows no puede). Los fallos se registran; el siguiente cambio lo reintenta. |

La línea la construye el motor de audio a partir de los metadatos que
realmente envía al stream, incluidos títulos de DJ y de webstream. Un
ajuste modificado se aplica en el siguiente cambio, sin reinicio.

### Ajustes de TuneIn

Sección plegable bajo las Preferencias generales. Desde el 2026-09-28 el
playout envía por sí mismo la información «now playing» a TuneIn; antes
solo se notificaban los inicios de archivo y la visualización
desaparecía a los cinco minutos.

| Campo | Notas |
|---|---|
| **Push metadata to your station on TuneIn?** (enviar metadatos a TuneIn) | Interruptor principal. Activado, el playout envía título e intérprete en cada inicio de pista, el nombre del programa al iniciar un webstream o una entrada de línea, y repite la última actualización cada cuatro minutos (TuneIn borra una visualización que lleva cinco minutos en silencio). Guardar con el interruptor activado comprueba las credenciales con TuneIn y rechaza las no válidas. |
| **Station ID**, **Partner Id**, **Partner Key** | De su cuenta de socio de TuneIn (AIR API). La clave no aparece en ningún registro. |

Un ajuste modificado se aplica en el siguiente envío; sin reinicio. Un DJ
en directo (Master / Show Source) no se anuncia; la última pista permanece
en la visualización hasta el siguiente elemento programado.

### Email (restablecimiento de contraseña)

| Campo | Notas |
|---|---|
| **Servidor SMTP / Puerto** | El servidor de correo saliente de su emisora. |
| **TLS** | Recomendado activado. |
| **Dirección From** | Usada como header From del email. |

> **Cómo funciona bajo el capó.** Las configuraciones se
> escriben en la tabla `cc_pref` como filas
> clave/valor. La mayoría se recargan inmediatamente; los
> ajustes SMTP requieren un reinicio del servicio worker.
> Vea ARCHITECTURE §11.

---

## 3. Estado del sistema

Configuración → **Estado del sistema**.

Vista general de salud de cada componente del que
RASTATIME depende.

### Servicios

PID en vivo + uptime para cada servicio Windows gestionado
por NSSM. Una insignia roja aquí es la señal de verificar
el servicio vía `Get-Service RASTATIME-*` en PowerShell o
el runbook
[`CRASH_RECOVERY`](../../operator/CRASH_RECOVERY.md).

### Conectividad

Verificación en vivo de cada dependencia externa:
**Base de datos (PostgreSQL)** — tiempo de respuesta,
**Conexión source Icecast** — estado de conexión source
del lado del motor de playout, **Carpeta de importación
local** — resultado del escaneo reciente.

### Advertencias preflight

Advertencias persistidas desde la verificación preflight
de inicio. Cosas como "FFmpeg no en PATH" o "puerto
esperado ya en uso".

> **Cómo funciona bajo el capó.** Conducido por el
> endpoint `/api/v2/preflight/warnings` respaldado por la
> tabla `rastatime_preflight_warning`. El `preflight.py`
> de inicio corre ~30 verificaciones.

### Controles de servicio (Admin+ solamente)

Reinicio de un botón para cada servicio Windows.

Efectos varían por servicio:

| Servicio | Efecto de reinicio |
|---|---|
| **API** | ~2 s de inactividad de la API REST. |
| **Worker** | Jobs en segundo plano en pausa (~10 s). |
| **Playout** | **El stream se vuelve silencioso ~10 s.** Use con moderación durante el tiempo de aire. |
| **Analyzer** | Carpeta de importación local en pausa (~5 s). |
| **Icecast** | Todos los oyentes se desconectan. |
| **Apache** | Interfaz web inaccesible ~5 s. |

> **Consejo del operador.** Reinicie solo el servicio que
> realmente está mal-comportándose.

---

## 4. Tools

Configuración → **Tools** → submenú.

| Tool | Propósito |
|---|---|
| **Consola DB** | Interfaz de consulta PostgreSQL de solo lectura. Solo Super Admin. Oculta por defecto; habilitar en `config/libretime.conf` con `[tools] db_console = true`. |
| **Visor de logs** | Tail de las últimas 200 líneas de logs de error. |
| **Reinicio de caché** | Limpiar cachés del lado del servidor. |
| **Re-escanear reproducibilidad de biblioteca** | Ejecutar la verificación de reproducibilidad del analyzer sobre cada pista existente. |

Estos *no* son herramientas diarias.

> **Por qué Consola DB oculta por defecto.** Una consola
> DB de solo lectura puede filtrar credenciales en
> cláusulas WHERE, volcar datos personales vía SELECT.

---

## 5. Preguntas frecuentes

### "Cambié un ajuste pero nada sucede."

| Ajuste | Requiere |
|---|---|
| SMTP | Reinicio del servicio worker |
| Credenciales de stream | Reinicio del servicio playout |
| Dispositivo de tarjeta de sonido | Reinicio del servicio playout |
| Zona horaria | Refresco duro del navegador |
| Idioma por defecto | Cerrar sesión / iniciar sesión |

### "¿Dónde Configuración almacena sus valores?"

Principalmente en `cc_pref` (tabla clave / valor). Los
ajustes por-usuario (idioma, clave API) viven en
`cc_subjs`. La configuración de servicio que no puede
vivir en la BD vive en `config/libretime.conf`.

### "¿Puedo versionar mi Configuración?"

Indirectamente: `config/libretime.conf` es un archivo de
texto. Las filas `cc_pref` no están versionadas. Para
copia de seguridad, use `pg_dump --table=cc_pref`.

### "¿Por qué algunas configuraciones son visibles solo
para Super Admin?"

La Consola DB, la capacidad de crear otros Admins, y el
derecho de ver claves API de otros usuarios están
reservados para Super Admin porque otorgan escalada de
acceso.

---

## 6. Motor de playout (Liquidsoap)

> **Configuración a nivel de servicio**, no una configuración UI.  El
> servicio NSSM RASTATIME-PLAYOUT puede llevar
> `RASTATIME_PLAYOUT_ENGINE=liquidsoap` en su entorno; es el único valor
> aceptado.  Solo operador; no expuesto en la UI web.

Desde el 2026-09-10 Liquidsoap es el **único** motor de playout.  El
motor mpv anterior (con sus streamers FFmpeg para las salidas Icecast)
y el plan VLC nunca terminado se eliminaron del código después de que
Liquidsoap llevara en producción cada tipo de elemento de la parrilla
(archivos, webstreams, entradas de línea, grabación, fuentes DJ) desde
el 2026-05-28.

Lo que Liquidsoap provee:

- **Grabación** capturada desde el bus de audio interno (post-switch,
  post-crossfade, post-amplify) — bit-idéntica a lo que escuchan los
  oyentes.  Bitrate fijo de 320 kbps MP3, calidad de archivo.
- **Experiencia del oyente**: los puntos de montaje Icecast permanecen
  abiertos a través de cambios de pista/programa — sin reconexión, sin
  reinicio de contadores.
- **Enrutamiento de fuentes DJ** nativo vía `input.harbor` +
  `switch(...)` de Liquidsoap — los clientes DJ Master / Show se
  conectan directamente al harbor gestionado por Liquidsoap (puerto 8001
  por defecto, vea [Streams](./STREAMS.md)).

**Si el servicio se niega a arrancar** con

```
CRITICAL __main__: RASTATIME_PLAYOUT_ENGINE='mpv' is not supported - Liquidsoap is the only playout engine since 2026-09-10 ...
```

el entorno del servicio aún nombra el motor eliminado: establezca
`RASTATIME_PLAYOUT_ENGINE=liquidsoap` (o elimine la variable) en el
entorno NSSM de `RASTATIME-PLAYOUT` y arranque el servicio de nuevo.
`RASTATIME_MPV_PATH` / `RASTATIME_MPV_LOG_LEVEL` se ignoran y pueden
eliminarse.

**El arranque del motor es visible en el log de playout:**

```
INFO __main__: Playout engine: Liquidsoap (telnet target 127.0.0.1:1234).
```

---

## A dónde ir después

* Siga el enlace por-página en la tabla arriba al
  capítulo dedicado para cualquier gran página de
  Configuración.
* [Usuarios y roles](./USERS_AND_ROLES.md) — matriz de
  permisos que guarda cada página de Configuración.
* [`docs/operator/INSTALL.md`](../../operator/INSTALL.md)
  — los ajustes iniciales configurados al momento de la
  instalación.
