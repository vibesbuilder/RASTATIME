# My Podcast

> **Dónde está en el manual.** Lea primero [Library](./LIBRARY.md): lo
> que publica en My Podcast es una pista corriente de la biblioteca.
> No confundir con **Podcasts** del menú principal (feeds de *otros*
> podcasts a los que se suscribe y que descarga) ni con el
> [Archivo](./ARCHIVING.md) (episodios en cba.media).

**My Podcast** es el podcast propio de la emisora: un feed RSS de
pistas de su biblioteca al que los oyentes se suscriben en cualquier
aplicación de podcasts.  Publicar una pista la añade al feed; retirarla
(«Unpublish») la quita.  Desde el 2026-11-14 una pista puede llevar
además el **último día en que sigue publicada**; después RASTATIME la
retira por sí mismo.

Publicar está reservado a los Program Managers y Admins (véase
[Usuarios y roles](./USERS_AND_ROLES.md)).

---

## 1. Publicar una pista

1. En **Tracks**, abra el menú contextual de la pista y elija
   **Publish...**.  El diálogo de publicación se abre en su propia
   pestaña.
2. En **Publish to:**, marque **My Podcast**.
3. Opcional: introduzca **Published until:**, el último día en que la
   pista sigue en el podcast (AAAA-MM-DD, o elíjalo en el calendario
   que se abre).  Déjelo vacío para que no tenga fin.  La fecha más
   temprana es hoy.
4. Haga clic en **Publish**.

La pista aparece entonces en **Published on:** en el mismo diálogo,
con su fecha (o *no end date*) al lado.

El título, el autor y la descripción del feed proceden de los
metadatos de la pista: **Edit Metadata...** en el diálogo abre el
editor de pistas.

---

## 2. Cambiar la fecha o retirar

Vuelva a abrir **Publish...** para una pista publicada:

- **Cambiar la fecha:** modifique la fecha junto a *My Podcast* y haga
  clic en **Save date**.  Un campo vacío más **Save date** quita el
  fin: la pista sigue publicada hasta que la retire.  Una fecha pasada
  se rechaza.
- **Retirar:** haga clic en **Unpublish**.  La pista sale del feed de
  inmediato.

---

## 3. Retirada automática («Published until»)

La fecha es **inclusiva**: una pista publicada hasta el 31 de
diciembre sigue en el podcast el 31 de diciembre y se retira **poco
después de medianoche** (zona horaria de la emisora), como muy tarde
unos siete minutos después de las 00:00.

La retirada equivale exactamente a hacer clic en **Unpublish**:

- el episodio sale del **feed**;
- su **enlace de descarga** deja de funcionar: las aplicaciones de
  podcasts ya no pueden obtener el archivo;
- desaparece de la lista de episodios de la página My Podcast.

La pista en sí sigue en la biblioteca.  Para recuperarla, vuelva a
publicarla: cuenta entonces como una publicación nueva y aparece
arriba en las aplicaciones de podcasts.  Las copias que los oyentes ya
descargaron se quedan en sus dispositivos; nadie puede recuperarlas.

Las aplicaciones de podcasts solo obtienen un feed cada pocas horas;
una aplicación puede mostrar un episodio retirado hasta su siguiente
consulta, pero la descarga ya no funciona mientras tanto.

Cada retirada automática queda anotada en el registro legacy
(`StationPodcastExpiryTask: unpublished episode ...`).

---

## 4. La página My Podcast

**My Podcast** en el menú principal muestra a la izquierda los ajustes
del podcast y a la derecha sus episodios.

- **General Fields / iTunes Fields**: nombre, descripción, idioma,
  autor, categoría, etc., tal como los muestran las aplicaciones de
  podcasts.  Haga clic en **Save** después de los cambios.
- **Privacy Settings**: **Public** (cualquiera con la dirección del
  feed) o **Private** (solo con la dirección del feed que lleva la
  clave para compartir).  **Feed URL** y **View Feed** muestran la
  dirección que hay que difundir.
- **Lista de episodios**: cada pista publicada con su fecha
  **Published until** (vacío = sin fin).  Seleccione episodios y haga
  clic en **Unpublish** para quitarlos.

---

## Véase también

- [Library](./LIBRARY.md): las pistas que publica.
- [Archivo](./ARCHIVING.md): poner los episodios en cba.media en su lugar.
- [Usuarios y roles](./USERS_AND_ROLES.md): quién puede publicar.
