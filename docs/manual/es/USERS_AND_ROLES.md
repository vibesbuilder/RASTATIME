# Usuarios y roles

> **Dónde está usted en el manual.** Este capítulo es la referencia de
> permisos para el resto del manual: cuando otro capítulo dice «solo
> Program Managers y Admins», la matriz del §2 da el cuadro completo.
> Describe el estado tras la auditoría de roles del 25/10/2026.

RASTATIME conoce cuatro roles.  Cada cuenta tiene exactamente uno, y el
servidor lo comprueba en cada petición - ocultar un botón es solo una
comodidad, el servidor rechaza la acción de todos modos.  Este capítulo
trata:

1. Los cuatro roles.
2. La matriz de permisos.
3. Gestionar usuarios (Ajustes → Usuarios).
4. Su propio perfil (Mi Perfil).
5. Credenciales para conexiones en directo.
6. Acceso a la API.
7. Sesiones y protección contra abusos.
8. Protección del inicio de sesión.
9. Reparto típico de roles y preguntas frecuentes.

---

## 1. Los cuatro roles

| Rol | Usuario típico | En una frase |
|---|---|---|
| **Invitado** | Pantalla de recepción, visitante | Ve el panel y el calendario, no cambia nada. |
| **DJ** | Un locutor | Trabaja con pistas: subida, sus propias listas y bloques inteligentes, llena los programas que presenta. |
| **Program Manager** | Coordinación de la programación | Dirige la programación: todos los programas, todos los contenidos, webstreams, Line-Ins, podcasts, Auto DJ, plantillas de programa, widgets. |
| **Admin** | Técnica de la emisora | Todo, más los ajustes de la emisora y las cuentas de usuario. |

Cada rol incluye todo lo que puede hacer el rol que está por encima de
él en la tabla.

**La cuenta de instalación `admin`** es un Admin como cualquier otro,
pero no se puede eliminar - ni en Ajustes → Usuarios ni a través de la
API.  Los Admins pueden crear otros Admins.

**El antiguo rol Super Admin** (de Airtime) se retiró el 25/10/2026: una
cuenta de ese tipo pasa a ser Admin (migración de base de datos 0073), y
los inicios de sesión externos (LDAP / FreeIPA, autenticación por
cabecera) del grupo super-admin entran como Admins.

> **Bajo el capó.** El rol es la letra única de `cc_subjs.type`
> (G, H, P, A; S está retirado).  Las reglas generales están en
> `application/configs/ACL.php`; las más finas (propietario de un
> archivo, presentador de un programa, Program Manager o superior) se
> comprueban en los controladores.  La auditoría y sus hallazgos:
> `docs/operator/ROLE_AUDIT_2026-10.md`.

---

## 2. La matriz de permisos

✓ = permitido, – = no permitido.  «Propios» significa que el usuario es
propietario del objeto (lo subió o lo creó); «presentados» significa que
el usuario es presentador (host) del programa.

| Área | Invitado | DJ | Program Manager | Admin |
|---|:---:|:---:|:---:|:---:|
| **Cuenta** | | | | |
| Editar el propio perfil (nombre, correo, contraseña, idioma, zona horaria) | ✓ | ✓ | ✓ | ✓ |
| Gestionar otros usuarios (Ajustes → Usuarios) | – | – | – | ✓ |
| **Panel y fuentes en directo** | | | | |
| Ver Now Playing y los programas planificados | ✓ | ✓ | ✓ | ✓ |
| Ver el estado de Auto DJ en la cabecera | ✓ | ✓ | ✓ | ✓ |
| Activar o desconectar una fuente en directo (Master / Show) | – | durante un programa presentado | ✓ | ✓ |
| Cancelar el programa en curso | – | – | ✓ | ✓ |
| **Calendario** | | | | |
| Ver el calendario | ✓ | ✓ | ✓ | ✓ |
| Crear, editar, mover, redimensionar, eliminar, cancelar programas | – | – | ✓ | ✓ |
| Vaciar el contenido de un programa, teasers, plantillas en el diálogo del programa | – | – | ✓ | ✓ |
| Planificar contenido en un programa | – | programas presentados | ✓ | ✓ |
| **Biblioteca** | | | | |
| Ver la biblioteca (pistas, listas, bloques inteligentes, lista de podcasts) | – | ✓ | ✓ | ✓ |
| Subir pistas | – | ✓ | ✓ | ✓ |
| Editar metadatos y puntos de cue, eliminar pistas | – | propios | ✓ | ✓ |
| Cambiar el propietario de una pista | – | – | – | ✓ |
| Crear listas y bloques inteligentes | – | ✓ | ✓ | ✓ |
| Editar, mezclar, eliminar listas y bloques inteligentes | – | propios | ✓ | ✓ |
| Ver, usar y editar webstreams y Line-Ins | – | – | ✓ | ✓ |
| Suscribirse a podcasts, editarlos, eliminarlos; episodios | – | – | ✓ | ✓ |
| Publicar en el podcast de la emisora (Mi Podcast) | – | – | ✓ | ✓ |
| **Estadísticas** | | | | |
| Estadísticas de oyentes | – | ✓ | ✓ | ✓ |
| Historial de reproducción: ver | – | programas presentados | ✓ | ✓ |
| Historial de reproducción: añadir, editar, eliminar entradas | – | programas presentados | ✓ | ✓ |
| Plantillas de historial | – | – | – | ✓ |
| **Widgets** | | | | |
| Páginas Widgets (códigos de integración, ajustes de los widgets) | – | – | ✓ | ✓ |
| **Ajustes** | | | | |
| Auto DJ | – | – | ✓ | ✓ |
| Página Show Templates | – | – | ✓ | ✓ |
| Idioma predeterminado de la emisora (diálogo del primer inicio) | – | – | ✓ | ✓ |
| General, Usuarios, Tipos de pista, Streams, Máquina local, Importar / Exportar, Backup, Estado | – | – | – | ✓ |

Lo que cada rol ve de forma distinta:

- **Los invitados** reciben el panel y el calendario.  La biblioteca
  muestra «No tienes permiso para ver la biblioteca.»; el menú
  **Nuevo**, **Upload** y el menú **Widgets** no se ofrecen.
- **Los DJ** ven todas las pistas, listas y bloques inteligentes de la
  emisora, pero solo cambian los suyos.  Planifican en los programas que
  presentan - cualquier pista, lista o bloque inteligente, también los
  de otros.  Los webstreams y los Line-Ins están ocultos para ellos
  (pestañas de la biblioteca, menú **Nuevo**); un DJ no puede añadirlos
  a listas ni a programas.  En el historial de reproducción, un DJ
  obtiene el *Show Summary* de sus propios programas y puede añadir,
  editar y eliminar entradas allí.  La lista de podcasts es de solo
  lectura para ellos, y el menú **Widgets** no se les ofrece.
- **Los Program Managers** dirigen la programación, usan las páginas
  **Widgets** y abren tres páginas de ajustes: **Auto DJ**, **Show
  Templates** y Mi Perfil.  Las plantillas de programa se guardan y
  aplican en el diálogo del programa y se renombran o eliminan en
  Ajustes → Show Templates.
- **Los Admins** gestionan además la emisora: ajustes, streams, tarjeta
  de sonido, usuarios, tipos de pista, copia de seguridad, importar /
  exportar, estado del sistema.

El diálogo de idioma y zona horaria del primer inicio fija para cada uno
**su propio** idioma y zona horaria; el idioma predeterminado de toda la
emisora solo cambia si lo confirma un Program Manager o un Admin.

---

## 3. Gestionar usuarios

Ajustes → **Usuarios** (Admins).

### Crear y editar un usuario

**Nuevo** abre el diálogo de usuario; un clic en una fila abre el mismo
diálogo para ese usuario.

| Campo | Notas |
|---|---|
| **Nombre de usuario** | El nombre de inicio de sesión. |
| **Contraseña** / **Verificar contraseña** | Obligatoria para un usuario nuevo.  Al editar, deje el texto de relleno para conservar la contraseña. |
| **Nombre**, **Apellido** | Se muestran en las listas de usuarios y como presentador del programa. |
| **Correo electrónico** | Dirección de contacto. |
| **Teléfono móvil**, **Skype**, **Jabber** | Campos de contacto opcionales. |
| **Tipo de usuario** | Invitado, DJ, Program Manager o Admin. |

La fila de la cuenta `admin` no tiene icono de eliminar.

### Eliminar un usuario

El icono de eliminar en la lista de usuarios borra la cuenta.  Las
pistas de las que el usuario era propietario se **entregan** al primer
Admin - siguen en la biblioteca.  No puede eliminar su propia cuenta, y
la cuenta `admin` no se puede eliminar.

No existe un estado «desactivado»: para quitarle el acceso a alguien,
elimine la cuenta o asigne una contraseña nueva; para dejar solo acceso
de lectura, cambie el tipo a Invitado.

### Usuarios en Importar / Exportar

Ajustes → Importar / Exportar incluye los usuarios como `users.csv` -
sin contraseñas; al importar, solo se asigna una contraseña a las
cuentas nuevas.  Vea [Importar / Exportar](./IMPORT_EXPORT.md).

---

## 4. Su propio perfil

Ajustes → **Mi Perfil** - para todos los roles, invitados incluidos.

Allí cambia su nombre y apellido, su correo, su contraseña, los campos
de contacto, su **idioma de la interfaz** y su **zona horaria**.  El
nombre de usuario es fijo.  La página guarda siempre la cuenta con la
que ha iniciado sesión; las demás cuentas las edita un Admin en
Ajustes → Usuarios.

---

## 5. Credenciales para conexiones en directo

Un DJ que emite en directo (BUTT, Mixxx, …) se conecta a la entrada en
directo de la emisora y se identifica con una de estas credenciales:

| Credencial | Se acepta cuando |
|---|---|
| El nombre de usuario y la contraseña RASTATIME del propio DJ | El DJ presenta el programa en antena, y el programa usa la *RASTATIME Authentication* (diálogo del programa → *Live Stream Input*). |
| La credencial propia del programa (*Usar la autenticación personalizada* en la misma sección) | Ese programa está en antena. |
| La credencial de la fuente Master (Ajustes → Streams) | Siempre; tiene prioridad sobre el programa en curso. |

La contraseña personalizada de un programa solo se muestra en el
diálogo del programa a Program Managers y Admins.  Los puertos y los
puntos de montaje figuran en el capítulo [Streams](./STREAMS.md).

---

## 6. Acceso a la API

**No hay claves API personales**.

- **Los servicios** (playout, analyzer, scripts en la máquina de la
  emisora) usan la clave API de la emisora de `config/libretime.conf`
  (`Authorization: Api-Key …`).  Trátela como una contraseña.
- **Las personas** pueden usar la API REST v2 (`/api/v2/`) con su propio
  nombre de usuario y contraseña; obtienen los permisos de su rol.
- Algunos puntos de acceso internos (dispositivos Line-In, tarjeta de
  sonido, avisos preflight, estado de los streams, la comprobación de
  credenciales de DJ) solo responden a la propia máquina de la emisora o
  a quien llama con la clave API.

---

## 7. Sesiones y protección contra abusos

- **Sesión.** Un inicio de sesión dura hasta que se cierra el navegador
  o hasta que la sesión lleva un rato sin ver ninguna petición (PHP
  `session.gc_maxlifetime`, 24 minutos en la máquina del estudio).  Una
  pestaña de RASTATIME abierta mantiene viva su sesión con sus
  actualizaciones en segundo plano.  Es posible iniciar sesión desde
  varios navegadores a la vez.
- **Cookie.** La cookie de sesión es `Secure`, `HttpOnly` y
  `SameSite=Lax`: otros sitios web no pueden usar su sesión para
  peticiones en segundo plano, y los scripts de la página no pueden
  leerla.
- **Token de petición.** Cada cambio hecho desde la interfaz lleva un
  token ligado a su sesión.  El servidor lo compara; una petición sin el
  token se registra (`CSRF monitor` en `logs/legacy.log`) y, cuando la
  comprobación pase a ser estricta, se rechaza.  Una pestaña que lleve
  abierta más de una semana puede necesitar recargarse (F5) antes de
  guardar.

---

## 8. Protección del inicio de sesión (desde el 06/10/2026)

La página de inicio de sesión frena los fallos repetidos - una
necesidad, ya que la interfaz web es accesible desde Internet.

| Ámbito | Regla | Efecto |
|---|---|---|
| Por dirección de origen | 10 inicios fallidos en 15 minutos | la dirección espera 15 minutos; cada intento en ese tiempo recibe «Too many failed login attempts. Please try again in N minute(s).» (HTTP 429), no se comprueba ninguna contraseña |
| Por nombre de usuario | 20 inicios fallidos en 60 minutos | el nombre espera 5 minutos - corto a propósito, para que quien ataque el nombre de un administrador desde muchas direcciones no pueda bloquearlo para siempre |
| Conexión de DJ (harbor) | 5 inicios rechazados desde una dirección en 10 minutos | la dirección se rechaza 15 minutos sin consultar a la aplicación web |

Un inicio de sesión correcto pone a cero los contadores de su dirección
y de su nombre.  Los umbrales están en `constants.php`
(`RASTATIME_LOGIN_*`) y en el playout (`RejectThrottle`); los intentos
bloqueados se registran con la dirección (`logs/legacy.log`,
`logs/playout-stdout.log`).

**Ver y levantar bloqueos.**  Ajustes → Estado → *Blocked addresses*
lista cada nivel (inicio de sesión web por dirección y por usuario,
conexión de DJ, vigilante del cortafuegos) con el número de fallos y los
minutos restantes; un botón **Unblock** borra la entrada en todos los
niveles - para el DJ que llama porque tenía guardada una contraseña
equivocada en su programa.  La misma lista está disponible en
PowerShell: `infra\scripts\rt-blocks.ps1` (`-Unblock <dirección>` o
`-Unblock user:<login>`).  Un DJ que se conecta **antes** de que empiece
el programa se rechaza pero nunca se cuenta: solo cuenta una contraseña
equivocada.  Los escáneres de Internet persistentes se bloquean 24 horas
en el cortafuegos de Windows mediante una tarea vigilante (cada
5 minutos; 50 peticiones rechazadas en 60 minutos, 3 rutas típicas de
escáner o 5 contraseñas de DJ equivocadas) y aparecen en la misma lista.
Una respuesta «sin sesión» (401) nunca cuenta: es lo que recibe una
pestaña con la sesión caducada en sus consultas de fondo, y desde el
07/10/2026 una pestaña así deja de consultar a la primera.

**Direcciones permitidas (desde el 08/10/2026).**  Junto a **Unblock**,
cada dirección bloqueada tiene **Allow**: se desbloquea en todos los
niveles y se añade a la lista *Allowed addresses* de debajo, donde
también puede introducir a mano una dirección o una red en notación CIDR
(`203.0.113.0/24`) y eliminar entradas.  Una dirección permitida nunca
la frena el inicio de sesión web, nunca la limita la conexión de DJ y
nunca la bloquea el vigilante del cortafuegos; las direcciones de la red
del estudio están exentas de todos modos.  Mantenga la lista corta -
desactiva todos los frenos para esa dirección - y prefiera una red para
una conexión doméstica cuya dirección cambia con el proveedor.  La lista
se guarda en la base de datos y se copia en `config\allowlist.txt` para
el playout y el vigilante.

> **Si usted mismo queda bloqueado:** espere los minutos indicados, o
> pida ayuda a un compañero desde otra dirección.  En caso de urgencia,
> los contadores están en las tablas `cc_login_attempts` (por dirección)
> y `cc_subjs.login_attempts` (por usuario).

---

## 9. Reparto típico de roles y preguntas frecuentes

### Reparto típico

| Emisora | Cuentas |
|---|---|
| Una persona | la cuenta `admin` (Admin); opcionalmente un Invitado para una pantalla en el vestíbulo |
| Radio comunitaria | `admin` y una cuenta Admin personal para el responsable técnico, un Program Manager por área de programación, una cuenta de DJ por locutor, opcionalmente un Invitado |
| Emisora más grande | además uno o dos Admins para la operación técnica |

Una cuenta por persona real: las cuentas compartidas impiden saber quién
cambió qué.

### «Un DJ no encuentra ningún webstream ni ningún Line-In.»

Es intencionado: los DJ solo trabajan con pistas.  Un Program Manager
añade el webstream o el Line-In al programa o a una lista.

### «Un DJ no puede cambiar el horario ni la descripción de su programa.»

Los programas los crean y editan los Program Managers y los Admins.  Los
DJ llenan los programas que presentan y pueden activar y desconectar su
fuente en directo mientras dura su programa.

### «Alguien necesita los derechos de DJ y de Program Manager.»

Asígnele el rol Program Manager - incluye todo lo que puede hacer un DJ.

### «¿Puede un usuario tener dos roles?»

No, exactamente uno por cuenta.

### «Se ha perdido la contraseña de un Admin.»

Otro Admin asigna una nueva en Ajustes → Usuarios - un motivo para
mantener dos cuentas Admin.  Si ningún Admin puede iniciar sesión, hay
que restablecer la contraseña en la base de datos (tabla `cc_subjs`,
columna `pass`, MD5 de la contraseña nueva) - vea
[`docs/operator/CRASH_RECOVERY.md`](../../operator/CRASH_RECOVERY.md).

---

## Adónde ir después

* [Ajustes](./SETTINGS.md) - cada página de ajustes.
* [Panel](./DASHBOARD.md) - fuentes en directo y el programa en curso.
* [Importar / Exportar](./IMPORT_EXPORT.md) - los usuarios como `users.csv`.
* [Streams](./STREAMS.md) - puertos para conexiones en directo y la credencial Master.
