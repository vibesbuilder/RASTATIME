# Copia de seguridad

> **Dónde está en el manual.** Este capítulo cubre la página
> Settings → **Backup**: copias de seguridad de la base de datos y de
> la configuración con un clic, en una carpeta de su elección, y su
> descarga a través del navegador.  Restaurar una copia es un
> procedimiento deliberado fuera de línea, documentado para
> administradores en `docs/operator/BACKUP.md` — no es un botón.

Todo lo que RASTATIME sabe — programas, parrilla, metadatos de la
biblioteca, usuarios, ajustes — vive en la base de datos PostgreSQL;
las contraseñas y puertos de los servicios viven en unos pocos
archivos de configuración.  La página **Backup** escribe ambos en un
único ZIP autocontenido por ejecución.

La biblioteca de medios (los archivos de audio en sí) nunca se
comprime — ocupa muchos gigabytes.  Active en su lugar **Include
media library** y se replicará en el lado del servidor junto a los
ZIP; vea la sección 3.

## 1. La carpeta de copias

Introduzca una ruta absoluta en un disco local, por ejemplo
`D:\rastatime-backups`, y pulse **Check** y **Save settings**.

- La carpeta se crea si no existe.
- No debe estar dentro de la biblioteca de medios.
- Idealmente está en un **disco distinto** al de la base de datos,
  para que un disco averiado no se lleve ambos.
- Las rutas de red no están soportadas.

## 2. Copiar ahora

**Back up now** inicia la copia en el servidor e informa bajo los
botones; unos segundos después el nuevo archivo aparece bajo
**Existing backups**.  Cada copia es un ZIP con el nombre de su hora
de creación:

```
rastatime-backup-2026-09-16T1830.zip
    db.dump          la base de datos completa (pg_dump, formato custom)
    config/…         cada archivo de configuración (libretime.conf, …)
    manifest.json    qué contiene, cuándo se creó, con qué pg_dump
```

Una copia fallida (por ejemplo porque PostgreSQL no responde) **no**
deja ningún ZIP a medio escribir; el mensaje bajo los botones indica
el motivo.  Una copia interrumpida por un reinicio de servicio se
muestra como interrumpida — simplemente ejecútela de nuevo.

## 3. Incluir la biblioteca de medios

Marque **Include media library** y pulse **Save settings**.  Desde
entonces cada ejecución sincroniza además la biblioteca en la
subcarpeta `media` junto a los ZIP:

- **Incremental.**  Solo se copian los archivos nuevos o modificados;
  los archivos borrados de la biblioteca desaparecen también del
  espejo.  El espejo es siempre la biblioteca *actual*, no un
  historial.
- **Verificado.**  Tras cada ejecución, cada archivo de la biblioteca
  se comprueba contra el espejo (existencia y tamaño); una diferencia
  hace fallar la copia.
- **Primera ejecución.**  Copia todo y puede tardar — la barra de
  progreso muestra el avance.  **Cancel** detiene el espejo (el ZIP de
  la base ya está completo en ese momento); la siguiente ejecución
  simplemente continúa donde se detuvo.

El espejo nunca viaja por el navegador.  Para restaurar los medios,
copie el contenido de `media` de vuelta a la raíz de la biblioteca
mostrada en [Máquina local](./LOCAL_MACHINE.md).

## 4. Copias existentes

La tabla lista cada copia de la carpeta, la más reciente primero, con
tamaño y hora de creación.  **Download** guarda el ZIP a través del
navegador — útil para conservar una copia fuera de la máquina.  Los
archivos en disco quedan intactos; borre las antiguas a mano cuando ya
no las necesite.

## 5. Restaurar

Restaurar reemplaza la base de datos en servicio y por eso es un
procedimiento deliberado y documentado fuera de línea — servicios
parados, base restaurada con `pg_restore`, servicios arrancados.  Siga
`docs/operator/BACKUP.md`, sección 7.  El `db.dump` del ZIP es
exactamente lo que `pg_restore` espera.

## 6. Buenas prácticas

- Haga copia antes de todo lo que odiaría rehacer: borrados masivos,
  grandes cambios de parrilla, actualizaciones de versión.
- Descargue de vez en cuando una copia a otra máquina — una copia en
  el mismo ordenador no sobrevive a ese ordenador.
- Los archivos de configuración del ZIP contienen contraseñas de
  servicios.  Trate las copias descargadas como las contraseñas que
  contienen.
