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
| **Zona horaria** | La zona horaria del operador. Almacenada por-programa en `cc_show_days.timezone`. |
| **La semana comienza el** | Lunes / Domingo. |

### Valores por defecto

| Campo | Notas |
|---|---|
| **Idioma por defecto** | Idioma UI para nuevos usuarios + la pantalla de inicio de sesión. |
| **Crossfade por defecto** | El *crossfade de la casa*. Entre pistas consecutivas del mismo programa es la duración del crossfade (1 segundo es típico; 0 = cortes secos). Desde el 2026-09-04 el valor también da forma a cada cambio entre **entradas** (pista ↔ webstream ↔ Line-In): un valor mayor que 0 funde la fuente saliente en la entrante durante esos segundos; **0 significa «ducking»** — la fuente entrante arranca de inmediato a nivel completo y la saliente se desvanece por debajo en 1 s. En ambos casos la cola almacenada de la fuente saliente se oye, no se corta. Surte efecto tras reiniciar la cadena de audio («Aplicar ahora» en Settings → Local Machine). |
| **Tipo de pista por defecto** | Tipo de pista asignado a nuevos uploads. |
| **Propietario de importación por defecto** | Cuenta acreditada como propietario para archivos importados vía la Carpeta de importación local. |
| **Grabación por defecto** | Si marcado, los nuevos programas tienen **Grabar este programa:** pre-marcado. |

### Panel

| Campo | Notas |
|---|---|
| **Vista anticipada** | Cuántos programas próximos el panel "Viene después" muestra. 3-5 es típico. |
| **Intervalo de refresco** | Con qué frecuencia el Panel sondea. 5 s es el por defecto. |

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

## 6. Motor de playout (Liquidsoap / mpv / VLC)

> **Configuración a nivel de servicio**, no una
> configuración UI. Configurado vía la variable de
> entorno `RASTATIME_PLAYOUT_ENGINE` en el servicio NSSM
> RASTATIME-PLAYOUT. Solo operador; no expuesto en la
> UI web.

RASTATIME incluye tres motores de reproducción. Solo uno
está activo a la vez.

| Motor | Estado | Fortalezas | Limitaciones |
|---|---|---|---|
| **Liquidsoap** | **Producción** (desde 2026-05-28, Phase-C5) | Transiciones gapless, crossfades nativos, PUTs Icecast persistentes (oyentes permanecen conectados a través de cambios de pista), conmutación de fuentes DJ vía `input.harbor`, grabación por-programa desde el bus interno a 320 kbps MP3 fijo | Webstreams y entradas de línea programados aún no portados (todavía vía mpv en paralelo; Phase-E + Phase-F) |
| **mpv** | **Deprecado** (default histórico) | Probado en batalla, archivos/webstreams/entradas-línea | Sin grabación (FfmpegRecorder eliminado en C5 Teil 2d), sin gapless, reconexión de oyentes en cada pista |
| **VLC** | **Deprecado** (escape de operador) | Fallback si mpv tiene problema de DLL | Como mpv más VLC 3.x se atraganta con Icecast URL-auth en Windows |

**Por qué Liquidsoap es ahora producción** (decisión del
operador 2026-05-28): grabación bit-idéntica a lo que
escuchan los oyentes, sin reconexión entre pistas,
enrutamiento nativo de fuentes DJ.

**Cuándo podría aún necesitar el fallback mpv**:
programa programado 100 % webstream o 100 % entrada de
línea con record=true (la grabación será silenciosa en
Liquidsoap hasta Phase-E / Phase-F).

**Cómo cambiar de motor**: ver
[`docs/operator/LIQUIDSOAP_CUTOVER.md`](../../operator/LIQUIDSOAP_CUTOVER.md).
Versión corta: establecer
`RASTATIME_PLAYOUT_ENGINE=liquidsoap` en el entorno del
servicio NSSM, reiniciar `RASTATIME-PLAYOUT`, luego
`RASTATIME-LIQUIDSOAP`.

El log de playout al arranque muestra:

```
INFO __main__: Local-playback engine: Liquidsoap ...
```

vs. (en el camino deprecado):

```
WARNING __main__: DEPRECATED: RASTATIME_PLAYOUT_ENGINE=mpv is now legacy. ...
INFO __main__: Local-playback engine: mpv (libmpv) [DEPRECATED]
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
