# Usuarios y roles

> **Dónde está usted en el manual.** Este capítulo es la
> referencia de permisos para cada función del resto del
> manual.

RASTATIME tiene cinco roles de usuario y un único sistema
de permisos. Cada acción — abrir una página, arrastrar
una pista, guardar un programa, reiniciar un servicio —
es verificada del lado del servidor contra el rol del
usuario.

Este capítulo cubre:

1. Los cinco roles + qué puede hacer cada uno.
2. Gestionar usuarios.
3. La matriz completa de permisos.
4. Gestión de claves API.
5. Asignación de rol best-practice.

---

## 1. Los cinco roles

| Rol | Símbolo | Usuario típico | Resumen de una línea |
|---|---|---|---|
| **Invitado** | G | Pantalla de recepción / lobby | Panel de solo lectura. |
| **DJ** | H | Cada presentador individual | Sus propios programas + sus propios archivos solamente. |
| **Program Manager** | P | Coordinador de programa | Todo calendario + biblioteca, sin configuración de emisora. |
| **Admin** | A | Admin técnico de emisora | Todo excepto crear otros Admins. |
| **Super Admin** | S | Propietario de la emisora | Todo incluyendo crear Admins. |

Un usuario tiene exactamente **un** rol.

### Por qué basado en roles y no en capacidades?

Basado en roles es el modelo más simple que cubre el 99 %
de las necesidades de las emisoras. Basado en capacidades
(toggles granulares por función) es flexible pero crea
exponencialmente más configuraciones a probar.

> **Cómo funciona bajo el capó.** Los roles viven en
> `cc_subjs.type` como un solo carácter (G / H / P / A /
> S). Las verificaciones de permisos suceden en
> `application/configs/ACL.php` vía Zend_Acl. Vea
> ARCHITECTURE §11.

---

## 2. Capacidades por rol

### Invitado (G)

El rol más pequeño. Usado para pantallas de solo lectura
en áreas públicas.

Puede: iniciar sesión, ver Panel En reproducción + Viene
después, ver el calendario público (solo lectura).

No puede: acceder a Biblioteca, Configuración o cualquier
menú administrativo.

### DJ (H)

Cuenta por-presentador. El rol que la mayoría de los
usuarios tienen.

Puede: todo lo que Invitado puede, más subir pistas
(propias), crear smart blocks y playlists, planificar sus
*propios* items en sus *propios* programas, editar
programas donde es presentador.

No puede: crear programas (los Program Managers deben
crear; el DJ rellena), ver / usar pistas / blocks /
playlists de otros DJs, cambiar configuración a nivel
emisora, reiniciar servicios.

### Program Manager (P)

El propietario del planning.

Puede: todo lo que DJ puede, más crear / editar /
eliminar *cualquier* programa, ver / usar pistas /
blocks / playlists de *cualquier* DJ, usar Plantillas de
programa, usar Auto DJ, gestionar entradas de biblioteca
Webstreams, alternar Master DJ al aire / fuera del aire.

No puede: gestionar Line-Ins (Admin solamente), gestionar
Streams, gestionar Usuarios, reiniciar servicios.

### Admin (A)

Acceso completo a nivel emisora excepto crear otros
Admins.

Puede: todo lo que Program Manager puede, más gestionar
Line-Ins, gestionar Streams, gestionar Usuarios (crear /
editar / desactivar DJs y Program Managers), configurar
Preferencias generales, configurar Máquina local,
configurar valores por defecto Auto DJ, restablecer
contraseñas, leer página Estado del sistema, reiniciar
servicios.

No puede: promover usuario a Admin (Super Admin
solamente), degradar otro Admin.

### Super Admin (S)

Rol máximo. Reservado para el propietario de la emisora /
admin técnico.

Puede: todo lo que Admin puede, más crear nuevos Admins,
degradar Admins a roles inferiores, ver clave API de
cualquier usuario.

Por diseño, hay **exactamente un** Super Admin por
emisora.

---

## 3. Gestionar usuarios

Configuración → **Gestionar usuarios** (solo Admin / Super
Admin).

### Crear un nuevo usuario

Gestionar usuarios → **+ Nuevo**.

| Campo | Notas |
|---|---|
| **Nombre de usuario** | Minúsculas, sin espacios, 3-32 caracteres. No se puede cambiar una vez establecido. |
| **Nombre / Apellido** | Nombre de visualización. |
| **Email** | Usado para restablecimiento de contraseña. |
| **Contraseña** | Mín 8 caracteres. |
| **Rol** | Uno de los cinco roles. Por defecto DJ. |
| **Móvil** | Opcional. |
| **Skype** | Opcional. Campo legacy. |
| **Activo** | Por defecto activado. |

### Editar un usuario

Fila → **Editar**. Todos los campos excepto nombre de
usuario son editables.

Para cambiar el rol de un usuario:
- Bajar un rol (Admin → PM, PM → DJ) está permitido para
  Admin y superior.
- Promoción a Admin es **Super Admin solamente**.
- Degradar un Super Admin: solo el Super Admin mismo
  puede hacerlo.

### Restablecer una contraseña

Fila → **Restablecer contraseña**.

| Opción | Efecto |
|---|---|
| **Enviar email** | Si SMTP está configurado, enviar un enlace de un solo uso válido por 24 horas. |
| **Establecer contraseña** | Establecer una contraseña temporal. |

### Desactivar un usuario

Fila → **Desactivar**. El usuario ya no puede iniciar
sesión pero su actividad histórica se preserva.

Para eliminar un usuario permanentemente, **Eliminar**.
Su contenido se reasigna al **propietario fallback por
defecto** configurado.

> **Consejo del operador.** Prefiera **Desactivar** sobre
> **Eliminar**.

---

## 4. Claves API

Cada usuario puede generar una clave API para acceso por
script a la API REST.

### Generar su propia clave API

Menú de usuario (arriba a la derecha) → **Mi perfil** →
sección **Clave API**.

Las claves API tienen los mismos permisos que el usuario.

### Generar clave API de otro usuario

Gestionar usuarios → fila de usuario → **Clave API** →
Generar. Admin / Super Admin solamente.

> **Cómo funciona bajo el capó.** Las claves API son
> strings aleatorias de 32 bytes almacenadas en
> `cc_subjs.api_key` (hasheadas). Autenticación vía el
> header `Authorization: Api-Key <key>`. Vea
> ARCHITECTURE §11.

> **Consejo del operador.** Trate las claves API como
> contraseñas.

---

## 5. La matriz de permisos

| Acción | G | H | P | A | S |
|---|:---:|:---:|:---:|:---:|:---:|
| **Panel** | | | | | |
| Ver En reproducción | ✓ | ✓ | ✓ | ✓ | ✓ |
| Ver contadores de oyentes | | ✓ | ✓ | ✓ | ✓ |
| Alternar Master DJ al aire / fuera | | | ✓ | ✓ | ✓ |
| Cancelar programa actual | | ✓¹ | ✓ | ✓ | ✓ |
| Escuchar el monitor | | ✓ | ✓ | ✓ | ✓ |
| **Calendario** | | | | | |
| Ver calendario | ✓ | ✓ | ✓ | ✓ | ✓ |
| Crear programa | | | ✓ | ✓ | ✓ |
| Editar su propio programa | | ✓ | ✓ | ✓ | ✓ |
| Editar cualquier programa | | | ✓ | ✓ | ✓ |
| Eliminar su propio programa | | ✓ | ✓ | ✓ | ✓ |
| Eliminar cualquier programa | | | ✓ | ✓ | ✓ |
| Aplicar / guardar Plantilla | | | ✓ | ✓ | ✓ |
| **Biblioteca** | | | | | |
| Ver sus propios archivos | | ✓ | ✓ | ✓ | ✓ |
| Ver todos los archivos | | | ✓ | ✓ | ✓ |
| Subir pista | | ✓ | ✓ | ✓ | ✓ |
| Crear / editar sus propias playlists, blocks | | ✓ | ✓ | ✓ | ✓ |
| Crear / editar cualquier playlist, block | | | ✓ | ✓ | ✓ |
| Crear / editar webstream | | ✓² | ✓ | ✓ | ✓ |
| Crear / editar Line-In | | | | ✓ | ✓ |
| Eliminar sus propios archivos | | ✓ | ✓ | ✓ | ✓ |
| Eliminar cualquier archivo | | | ✓ | ✓ | ✓ |
| **Streams** | | | | | |
| Ver estado stream | | ✓ | ✓ | ✓ | ✓ |
| Editar config stream | | | | ✓ | ✓ |
| **Máquina local** | | | | | |
| Ver config tarjeta de sonido | | | | ✓ | ✓ |
| Editar config tarjeta de sonido | | | | ✓ | ✓ |
| Establecer Carpeta de importación local | | | | ✓ | ✓ |
| **Auto DJ** | | | | | |
| Habilitar / deshabilitar | | | ✓ | ✓ | ✓ |
| Editar valores por defecto | | | | ✓ | ✓ |
| **Configuración** | | | | | |
| Preferencias generales | | | | ✓ | ✓ |
| Localización | | | | ✓ | ✓ |
| Página Plantillas de programa | | | ✓ | ✓ | ✓ |
| Gestión de usuarios | | | | ✓ | ✓ |
| Crear Admin | | | | | ✓ |
| **Sistema** | | | | | |
| Ver Estado del sistema | | | | ✓ | ✓ |
| Reiniciar servicio | | | | ✓ | ✓ |
| Acceder Consola DB | | | | | ✓ |
| **API** | | | | | |
| Generar su propia clave API | | ✓ | ✓ | ✓ | ✓ |
| Ver / generar clave API de cualquier usuario | | | | ✓ | ✓³ |

Notas:
- ¹ — Solo su programa actualmente al aire.
- ² — Por DJ; no puede editar webstreams de otros DJs.
- ³ — Incluyendo los de otros Admins.

---

## 6. Asignación de rol recomendada

### Emisora operador solo (1 persona)

- `admin` — Super Admin.
- (Opcional) `recepcion` — Invitado.

### Pequeña emisora comunitaria (3-10 contribuyentes)

- `admin` — Super Admin.
- `pm1` — Program Manager.
- `anna`, `ben`, `carla`, … — DJ (uno por presentador).
- (Opcional) `ingeniero` — Admin.
- (Opcional) `recepcion` — Invitado.

### Emisora mediana / comercial (10-50 contribuyentes)

- `owner` — Super Admin.
- `engineer1` — Admin.
- `pm1`, `pm2` — Program Manager.
- Cuentas DJ por presentador.
- `script` — DJ (cuenta de servicio para scripts).
- `recepcion` — Invitado.

Para todos los tamaños: **un Super Admin por emisora** es
el sweet spot.

---

## 7. Preguntas frecuentes

### "Estoy bloqueado como Super Admin. ¿Cómo recuperar?"

Acceso directo a la base de datos es la única
recuperación. Vea
[`docs/operator/CRASH_RECOVERY.md`](../../operator/CRASH_RECOVERY.md)
§5.

### "¿Puede un usuario tener dos roles?"

No. Un rol por usuario.

### "¿Pueden dos usuarios compartir una cuenta?"

Técnicamente sí, pero fuertemente desaconsejado.

### "¿Cuánto dura una sesión?"

Por defecto 8 horas.

### "¿Puedo iniciar sesión desde dos navegadores
simultáneamente?"

Sí.

### "¿La API soporta OAuth / SSO?"

No actualmente.

### "¿Puede un DJ ver las grabaciones de otro DJ?"

No. Las grabaciones heredan el propietario del programa.

---

## A dónde ir después

* [Configuración](./SETTINGS.md) — recorrido de cada
  sub-página de Configuración.
* [Panel](./DASHBOARD.md) — la página más usada del
  operador.
* [`docs/operator/CRASH_RECOVERY.md`](../../operator/CRASH_RECOVERY.md)
  — recuperación de bloqueo Super Admin.
