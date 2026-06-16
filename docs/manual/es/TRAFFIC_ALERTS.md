# Alertas de tráfico

> **Dónde está en el manual.** Lea primero [Biblioteca](./LIBRARY.md)
> → §3 Smart Blocks y
> [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md), e idealmente
> [Peticiones de canciones](./SONG_REQUESTS.md) — las alertas de tráfico
> reutilizan el *mismo* mecanismo de llenado incremental al aire. No se
> introduce ningún nuevo tipo de objeto.

Las **alertas de tráfico** permiten que un MP3 de último momento — un
boletín de tráfico que se le entrega minutos antes de que deba emitirse —
suene dentro del **programa en curso**, de forma automática, en unos diez
minutos, sin que un presentador haga clic en nada y sin interrumpir el
motor de playout.

Toda la función se ensambla a partir de piezas que ya conoce:

- un **smart block** que coincide con sus boletines de tráfico se nombra,
  una sola vez, como la **fuente de tráfico** en los ajustes;
- una **Autoloading Playlist** que contiene ese bloque, colocada en
  algunos puntos de un programa, convierte un programa corriente en un
  **programa con alertas de tráfico**;
- importar un nuevo boletín a la biblioteca es todo lo que hace falta para
  ponerlo al aire en el siguiente espacio de tráfico.

No hay una «cola de alertas» separada ni ningún cambio del lado del
playout. Un programa *se convierte* en un programa con alertas de tráfico
cuando su Autoloading Playlist contiene el bloque de tráfico configurado —
nada más.

---

## 1. La visión general

```
   REDACCIÓN                RASTATIME                       AL AIRE
   ┌──────────┐  importar   ┌────────────────────────┐
   │ tráfico  │────────────▶│ Biblioteca: el archivo  │
   │  .mp3    │             │  coincide ya con el blq  │
   └──────────┘             └───────────┬─────────────┘
                                        │  el programa en curso se llena
                                        │  de forma incremental, al aire
                            ┌───────────▼─────────────┐   ┌──────────┐
                            │ Bloque de alerta en el   │──▶│ Programa │
                            │  SIGUIENTE espacio dram.  │   │ horario  │
                            │  más antiguo, una vez     │   └──────────┘
                            └──────────────────────────┘
```

El mecanismo es el que las Song Requests ya usan (véase
[Peticiones de canciones](./SONG_REQUESTS.md) §5): un programa con alertas
de tráfico se llena **de forma incremental mientras está al aire**, solo un
poco por delante de la cabeza de reproducción. Cada espacio de tráfico del
programa se resuelve poco antes de sonar — de modo que recoge cualquier
boletín que se haya importado entretanto. Por eso, un boletín importado
*durante* el programa suena en el **siguiente** espacio de tráfico; nada
de lo ya planificado se retrasa.

Usted configura la fuente una vez (§2–§3) y coloca el bloque en sus
programas (§4); después la función funciona sin supervisión (§5).

---

## 2. El smart block de tráfico

Un boletín de tráfico no es más que un archivo de audio. El «bloque de
tráfico» es un [smart block](./LIBRARY.md) corriente cuyos criterios
coinciden con esos archivos y con nada más. Configuración típica:

- **Criterios** que seleccionen solo boletines — por ejemplo *Género es
  Tráfico*, o *Carpeta/Ruta contiene `/traffic/`*, lo que sea que los
  aísle limpiamente en su biblioteca.
- **Orden: Más recientes primero** es lo natural, pero el orden de emisión
  no depende de ello — el sistema siempre emite el boletín **más antiguo
  no emitido** primero (el que está más cerca de su plazo; véase §5).
- **Excluir pistas reproducidas recientemente** (opcional, recomendado):
  una vez que un boletín ha sonado, sale del bloque, de modo que un boletín
  obsoleto nunca se vuelve a recoger en un día posterior.
- **Sin un límite de elementos ajustado.** Deje sitio para varios boletines
  de manera que, si llegan dos seguidos, ambos sean candidatos.

> **Consejo.** Mantenga este bloque dedicado al tráfico. No reutilice un
> bloque de música — cada archivo que el bloque coincide se trata como un
> boletín emitible.

---

## 3. Selecciónelo en los ajustes

Abra **Settings → General Preferences** y busque **Bloque inteligente de
alertas de tráfico**. Elija su bloque de tráfico de la lista y guarde.

- La lista contiene cada smart block de su biblioteca.
- **`(ninguno — desactivado)`** es el valor por defecto y desactiva la
  función por completo — un programa que aún contiene el bloque lo
  reproduce entonces una sola vez como un bloque corriente.

Solo **un** bloque puede ser la fuente de tráfico a la vez. Este es el
único interruptor que arma la función.

---

## 4. Construir un programa con alertas de tráfico

Añada el bloque de tráfico a la **Autoloading Playlist** de un programa,
del mismo modo que añadiría cualquier bloque — pero colóquelo en **varios
puntos** a lo largo de la dramaturgia del programa, no solo una vez. Por
ejemplo:

```
   jingle · música · TRÁFICO · música · música · TRÁFICO · música · …
```

Cada entrada `TRÁFICO` es un espacio donde un boletín *puede* irrumpir. Si
ningún boletín está esperando cuando se alcanza el espacio, el espacio no
emite nada y el siguiente elemento simplemente suena — así que los
espacios vacíos no le cuestan nada.

**Lo densamente que los coloque es la forma de cumplir el plazo de diez
minutos** (véase §6). Como regla general, un espacio de tráfico cada cinco
a siete minutos de programación, sin ninguna pista muy larga
inmediatamente antes de uno, mantiene cualquier boletín cómodamente dentro
de su SLA.

El programa necesita la **Autoloading Playlist** activada (es lo que hace
que el programa se llene a sí mismo). Nada más en el programa necesita
ajustes especiales.

---

## 5. Cómo y cuándo se emite un boletín

Cuando un programa con alertas de tráfico está al aire, la tarea de
llenado (cada dos minutos) resuelve su dramaturgia un poco por delante de
la cabeza de reproducción. Cuando alcanza un espacio de tráfico elige
**un** boletín, según estas reglas:

1. **Más antiguo primero (FIFO).** Entre los boletines en espera emite el
   **importado primero** — el que está más cerca de su plazo de diez
   minutos.
2. **Una sola vez.** Un boletín ya planificado en cualquier lugar de este
   programa nunca se vuelve a elegir, de modo que la misma alerta no puede
   sonar dos veces aunque el bloque esté en varios espacios.
3. **Sin relleno.** Si ningún boletín fresco está esperando, el espacio no
   emite **nada** — deliberadamente no hay un fallback de pista aleatoria
   (a diferencia de un hueco de petición). En su lugar suena el siguiente
   elemento de programación.

Así que el flujo de trabajo normal del día a día es simplemente:
**importe el boletín a la biblioteca** (a la carpeta/género con que su
bloque coincide). Dentro de un ciclo de sondeo se convierte en candidato,
y suena en el siguiente espacio de tráfico del programa en curso.

> **Cómo funciona por dentro.** Las alertas de tráfico y las Song Requests
> comparten un mismo motor de llenado incremental. La única diferencia es
> cómo se resuelve un espacio: un hueco de petición extrae las peticiones
> de los oyentes y recurre a una pista aleatoria; un espacio de tráfico
> extrae el boletín más antiguo no emitido y recurre a *nada*. Ambos
> escriben en el horario normal del programa, que el motor de playout
> recoge en su siguiente refresco — no hay ningún cambio en la ruta de
> audio en directo, y el boletín aparece en el historial y en el
> calendario como cualquier pista.

---

## 6. El plazo de diez minutos lo cumple usted

Como un boletín suena en su **espacio dramatúrgico**, lo rápido que suena
depende de cómo construyó el programa — no de que el sistema corte una
pista. RASTATIME **no** salta la pista que se está reproduciendo para sacar
un boletín a toda prisa (ese *salto por plazo* automático es una opción
futura prevista, retenida hasta que la operación en directo demuestre que
realmente hace falta).

Usted cumple la SLA con dos hábitos:

- **Coloque los espacios de tráfico densamente** — no más separados que su
  plazo, de modo que el siguiente espacio esté siempre cerca.
- **Mantenga corta la pista anterior a un espacio.** Una mezcla de quince
  minutos justo antes de un espacio de tráfico puede por sí sola empujar el
  espacio más allá de los diez minutos.

Si su programación realmente no puede garantizar un espacio dentro del
plazo (programas de formato muy largo, por ejemplo), avise a su
responsable de mantenimiento de RASTATIME — el salto por plazo activo
puede entonces construirse y activarse.

---

## 7. Lista de verificación del operador

1. **Una vez:** construya un smart block que coincida solo con sus
   boletines de tráfico (§2).
2. **Una vez:** Settings → General → **Bloque inteligente de alertas de
   tráfico** → selecciónelo (§3).
3. **Por programa:** añada ese bloque en varios puntos de la Autoloading
   Playlist del programa, ≤ su plazo de separación (§4).
4. **Por boletín:** importe el MP3 a la biblioteca de modo que coincida con
   el bloque — suena en el siguiente espacio (§5).
5. **Para pausar la función:** Settings → vuelva a poner el bloque en
   `(ninguno — desactivado)`.

---

## 8. Preguntas frecuentes

### «Importé un boletín pero no sonó.»
Compruebe tres cosas: que el archivo realmente **coincide con el bloque de
tráfico** (abra el bloque y confirme que aparece); que el **bloque está
seleccionado** en los ajustes; y que el **programa en curso contiene el
bloque** en su Autoloading Playlist. Si las tres se cumplen, suena en el
siguiente espacio de tráfico — que puede estar a unos minutos de distancia
según su dramaturgia (§6).

### «El mismo boletín sonó dos veces.»
No debería — un boletín ya planificado en el programa queda excluido de los
espacios posteriores. Si realmente se repitió, las dos emisiones están en
*programas distintos* (los espacios de un programa nuevo lo ven como fresco
hasta que realmente ha sonado; active *Excluir pistas reproducidas
recientemente* en el bloque para evitarlo).

### «Un espacio de tráfico no emitió nada.»
Es lo esperado cuando ningún boletín fresco estaba esperando — un espacio
de tráfico no tiene relleno, así que simplemente suena el siguiente
elemento de programación. Los espacios vacíos son gratis; coloque tantos
como quiera.

### «Llegaron dos boletines a la vez — ¿cuál suena primero?»
El **importado más antiguo** primero, luego el siguiente en el espacio de
tráfico que sigue. Cada espacio emite un boletín, así que deles suficientes
espacios para drenarse.

### «¿Con qué rapidez sonará un boletín?»
En el siguiente espacio de tráfico del programa en curso. Con los espacios
colocados dentro de su plazo de diez minutos y sin una pista demasiado
larga delante de uno, eso queda dentro de la SLA. RASTATIME no interrumpe
la pista actual para hacerlo (§6).

### «¿Puedo desactivarlo?»
Sí — Settings → **Bloque inteligente de alertas de tráfico** →
`(ninguno — desactivado)`. Un programa que aún lleva el bloque lo
reproduce entonces simplemente una sola vez como un bloque corriente.

---

## Adónde ir después

- [Peticiones de canciones](./SONG_REQUESTS.md) — el mismo llenado
  incremental al aire, para las peticiones de los oyentes.
- [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) — cómo un programa se
  llena a sí mismo a partir de playlists y bloques.
- [Biblioteca](./LIBRARY.md) → §3 Smart Blocks — construir el bloque que
  coincide con sus boletines.
