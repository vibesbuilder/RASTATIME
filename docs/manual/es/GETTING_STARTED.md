# Primeros pasos

> **Dónde está usted en el manual.** Este capítulo asume
> que RASTATIME ya está instalado y la interfaz web es
> accesible. Si no, recorra primero
> [`docs/operator/INSTALL.md`](../../operator/INSTALL.md).
>
> **Tiempo de lectura.** ~15 minutos para la pista
> operador, ~25 con las notas técnicas.

Este capítulo guía a un operador completamente nuevo a
través del primer inicio de sesión, la primera pantalla
que ve, el rol de cada menú principal, y la secuencia
mínima para poner una pista al aire.

Al final, usted habrá:

1. Iniciado sesión con las credenciales por defecto y
   cambiado su contraseña.
2. Identificado qué rol de usuario tiene y qué le permite.
3. Encontrado la Biblioteca, el Calendario y el Panel.
4. Creado y emitido su primera pista planificada.
5. Verificado que el stream de salida alcanza a los
   oyentes.

---

## 1. Primer inicio de sesión

Abra `http://<station-host>/` en cualquier navegador
moderno (Chrome, Edge, Firefox; Internet Explorer *no*
está soportado).

Las credenciales super-admin por defecto de una
instalación fresca son:

| Campo | Valor |
|---|---|
| Usuario | `admin` |
| Contraseña | `admin` |

> **Cámbielo ahora.** Tan pronto como haya iniciado
> sesión, vaya a **Configuración → Gestionar usuarios**,
> haga clic en `admin`, y establezca una contraseña real.
> RASTATIME no fuerza un cambio de contraseña en el primer
> inicio de sesión. La cuenta por defecto es un vector de
> ataque conocido si el servidor es accesible desde fuera
> de su LAN de estudio.

> **Cómo funciona bajo el capó.** Las credenciales viven
> en `cc_subjs`. Las contraseñas están hasheadas (bcrypt).
> La cookie de sesión es `PHPSESSID`; el almacenamiento de
> sesión Zend está en `C:\rastatime\runtime\sessions\` por
> defecto.

Si no puede iniciar sesión: el runbook
[`CRASH_RECOVERY`](../../operator/CRASH_RECOVERY.md)
cubre el caso de que Apache, mod_fcgid o el servicio API
estén caídos.

---

## 2. La barra superior y qué hace cada elemento

Después del inicio de sesión, aterriza en el **Calendario**
por defecto. La barra de navegación superior contiene cada
otra área de la aplicación:

| Menú | Qué vive ahí |
|---|---|
| **Panel** | Qué está al aire ahora, qué viene después, estado de fuente (scheduler / line-in / master DJ / show DJ), y un panel de anulación manual. Vea [Panel](./DASHBOARD.md). |
| **Calendario** | La cuadrícula de planificación. Crear / editar / eliminar programas. Arrastrar y soltar programas. Vea [Calendario](./CALENDAR.md). |
| **Biblioteca** | Todas sus pistas, smart blocks, playlists, webstreams y line-ins. Buscar y filtrar. Vea [Biblioteca](./LIBRARY.md). |
| **Configuración** | Streams, Máquina local (tarjeta de sonido + carpeta de importación), Auto DJ, Plantillas de programa, Preferencias generales, Gestionar usuarios, Localización. |
| **Ayuda** | Enlaces a este manual, al runbook de instalación y a la documentación original de LibreTime. |
| **Menú de usuario** (arriba a la derecha) | Cerrar sesión, cambiar idioma, ver su propio perfil, su propia clave API (para scripts). |

> **Consejo del operador.** El Calendario es el centro de
> gravedad. Puede hacer casi todo desde el menú contextual
> del Calendario — crear un programa, rellenarlo desde la
> biblioteca, adjuntar una plantilla, abrirlo para editar.

---

## 3. Roles — quién es usted decide qué ve

Cada usuario tiene exactamente un **rol**. El rol se
establece en la página Gestionar usuarios y es lo único
que controla qué le deja hacer la interfaz.

| Rol | Puede ver / hacer |
|---|---|
| **Invitado (G)** | Solo Panel de lectura. Sin Calendario, sin Biblioteca, sin Configuración. Usado para paneles de monitoreo o pantallas de información en recepción. |
| **DJ (H)** | Sus propios programas + sus propios archivos solamente. Puede rellenar sus propios programas, subir sus propias pistas. No puede crear programas. No puede ver archivos de otros DJs. |
| **Program Manager (P)** | Acceso completo al Calendario y Biblioteca. Puede crear y editar programas para cualquier DJ. No puede cambiar configuración a nivel emisora. |
| **Admin (A)** | Todo lo que un Program Manager puede hacer, más configuración a nivel emisora (Streams, Máquina local, Auto DJ, Plantillas de programa, Localización). |
| **Super Admin (S)** | Todo. Más la capacidad de crear y degradar otros Admins. Reservado para el propietario de la emisora / admin técnico. |

> **Por qué funciona así.** ACL basado en roles se aplica
> del lado del servidor en `configs/ACL.php`. Ocultar
> elementos de menú en la interfaz es solo una
> conveniencia — el backend re-verifica cada acción contra
> el rol del usuario. Vea ARCHITECTURE §11 para la matriz
> completa de roles.

[`USERS_AND_ROLES`](./USERS_AND_ROLES.md) cubre la
asignación de roles y la matriz de permisos
recurso-por-recurso.

---

## 4. Los primeros diez minutos: de emisora vacía a pista al aire

Una instalación RASTATIME completamente nueva tiene una
biblioteca vacía, un calendario vacío, e Icecast corriendo
pero sin audio alcanzando su entrada. Esta sección guía el
camino más corto para arreglar los tres.

### 4.1 Confirmar que el stream de salida existe

Configuración → **Streams**.

La instalación por defecto entrega **Stream 1**
configurado con:

| Campo | Por defecto |
|---|---|
| Tipo | Icecast |
| Servidor | `localhost` |
| Puerto | `8000` |
| Mount | `/rastatime` |
| Formato | MP3, 192 kbps, 44,1 kHz, estéreo |

La columna **Conectado** debería mostrar ya una insignia
verde si el servicio playout está corriendo. Si muestra
roja ("Desconectado"), el playout no ha arrancado —
verifique con `Get-Service RASTATIME-PLAYOUT` en
PowerShell.

> **Cómo funciona bajo el capó.** La interfaz web no
> empuja el stream ella misma — el servicio Windows
> **RASTATIME-PLAYOUT** lo hace. Lee la configuración de
> stream desde `cc_pref` al arranque y en cada guardado,
> abre una conexión source Icecast y comienza a publicar
> silencio (o el contenido fallback si está configurado)
> inmediatamente.

Para escuchar, abra en otra pestaña:
`http://<station-host>:8000/rastatime`. Debería oír
silencio o el bucle fallback si está configurado.

### 4.2 Subir una pista

Biblioteca → **Subir**.

Arrastre cualquier archivo MP3, FLAC o WAV al área de
subida. El analyzer ejecuta el archivo a través de
ffprobe (metadatos) y ffmpeg (reproducibilidad —
decodifica todo el archivo a `null` para confirmar que se
reproduce de principio a fin), luego la fila aparece en
la lista de la biblioteca.

> **Consejo del operador.** Si tiene una carpeta de
> música para importar, no las arrastre una por una.
> Establezca la **Carpeta de importación local** bajo
> Configuración → Máquina local a un directorio en el
> servidor; todo lo que se suelta en ese directorio se
> auto-importa en el próximo poll del analyzer (cada 60 s
> por defecto). Vea [Máquina local](./LOCAL_MACHINE.md).

> **Cómo funciona bajo el capó.** Subir escribe a un
> directorio de staging bajo `C:\rastatime\import\`, luego
> encola un job de analyzer. El analyzer analiza
> metadatos (tags ID3 / Vorbis) y verifica
> reproducibilidad vía `ffmpeg -v error -i <file> -f null
> -`; vea ARCHITECTURE §23.14. En éxito, el archivo se
> mueve a la biblioteca de medios en
> `C:\rastatime\media\<owner>\<year>\<month>\` y se
> inserta una fila `cc_files`.

### 4.3 Crear un programa

Calendario → haga clic en cualquier celda vacía en la
próxima hora → **Nuevo programa**.

Complete:

| Campo | Valor sugerido |
|---|---|
| **Nombre** | `Test` |
| **Fecha / hora de inicio** | Ahora + 2 minutos |
| **Duración** | 10 minutos |
| **Género** | dejar vacío |
| **Presentadores** | usted mismo |

Deje todo lo demás en los valores por defecto. Haga clic
en **Guardar**.

El programa aparece en el calendario como un bloque de
color.

> **Cómo funciona bajo el capó.** Guardar el formulario
> escribe una fila en `cc_show` (la definición del
> programa) y al menos una fila en `cc_show_instances`
> (cada ocurrencia).

### 4.4 Rellenar el programa con la pista

Calendario → haga clic en el programa → **Planificar
pistas**.

El show-builder se abre con el programa a la izquierda y
la biblioteca a la derecha. Arrastre su pista subida
desde la biblioteca al programa. Aparece como primer item
planificado.

Haga clic en **Guardar** en la parte superior del
show-builder.

> **Consejo del operador.** También puede hacer clic
> derecho en un programa vacío en el calendario y
> seleccionar **Aplicar plantilla** para rellenarlo desde
> una [Plantilla de programa](./SHOW_TEMPLATES.md)
> reutilizable.

### 4.5 Esperar a que el programa comience

A la hora de inicio del programa:

1. El widget **En reproducción** del Panel cambia de
   "Fallback" (o "Silencio") al título de la pista.
2. El stream Icecast en
   `http://<station-host>:8000/rastatime` comienza a
   reproducir su pista.
3. La barra de relleno del Calendario para el programa
   cambia de gris ("0 %") a color ("100 %" si la pista
   rellena todo el slot, menos si no).

Si algo de eso no sucede, el runbook
[`CRASH_RECOVERY`](../../operator/CRASH_RECOVERY.md)
cubre el camino de diagnóstico.

---

## 5. Operaciones comunes del primer día

Ahora sabe lo suficiente para hacer el trabajo diario.
Aquí donde encontrar cada tarea común en el resto del
manual:

| Quiero… | Vaya a |
|---|---|
| Subir un lote de pistas | [Biblioteca](./LIBRARY.md) |
| Planificar el horario de mañana | [Calendario](./CALENDAR.md) |
| Hacer un programa semanal recurrente | [Calendario](./CALENDAR.md) → Programas recurrentes |
| Usar la misma configuración de programa cada semana | [Plantillas de programa](./SHOW_TEMPLATES.md) |
| Hacer que un programa se rellene solo | [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) |
| Rellenar huecos de calendario automáticamente | [Auto DJ](./AUTO_DJ.md) |
| Poner la emisora en vivo desde un micrófono | [Panel](./DASHBOARD.md) → Fuente en vivo |
| Añadir el stream Icecast externo de un invitado como webstream | [Webstreams](./WEBSTREAMS.md) |
| Añadir el mezclador del estudio como line-in nombrado | [Line-In](./LINE_IN.md) |
| Grabar lo que estuvo al aire hoy | [Grabación por programa](./RECORD_PER_SHOW.md) |
| Añadir un segundo stream de salida (ej. baja tasa móvil) | [Streams](./STREAMS.md) |
| Añadir un nuevo DJ | [Usuarios y roles](./USERS_AND_ROLES.md) |
| Cambiar el idioma de la interfaz | [Idiomas](./I18N.md) |
| Recorrido del menú Configuración | [Configuración](./SETTINGS.md) |

---

## 6. Tres hábitos para evitar dolor más tarde

Estos no son opcionales. Le ahorrarán una larga noche en
algún momento.

1. **Use Plantillas de programa desde el día dos.** Si se
   encuentra escribiendo el mismo nombre / presentadores /
   colores dos veces, guárdelo como plantilla. Los
   presentadores que aprenden esto nunca miran atrás.
   Vea [Plantillas de programa](./SHOW_TEMPLATES.md).

2. **Configure la Carpeta de importación local.** Las
   subidas de arrastre del navegador están bien para uno
   o dos archivos, pero una importación por lotes de 200
   pistas hará timeout al navegador y le frustrará.
   Vea [Máquina local](./LOCAL_MACHINE.md).

3. **Haga una copia de seguridad el día que salga en
   vivo.** RASTATIME entrega un script de backup de un
   comando que captura la base de datos, los medios
   subidos y la configuración. Programe para correr todas
   las noches en la misma máquina, y una vez por semana a
   almacenamiento fuera de máquina.
   Vea [`docs/operator/BACKUP.md`](../../operator/BACKUP.md).

---

## A dónde ir después

* Si solo tiene tiempo para un capítulo más hoy, lea
  [Calendario](./CALENDAR.md) — el calendario es donde
  pasará la mayor parte de su tiempo.
* Para el lector técnico que quiere entender el sistema
  de extremo a extremo, el documento
  [ARCHITECTURE](../../../RASTATIME_ARCHITECTURE_DRAFT_v0.1.md)
  da la imagen completa en una lectura.
* Para un operador que sale en vivo por primera vez,
  también recorra
  [`docs/operator/INSTALL.md`](../../operator/INSTALL.md)
  §6 ("Smoke test") para confirmar que cada servicio está
  sano antes de anunciar la emisora.
