# Widgets públicos integrables

> **Dónde está usted en el manual.** Este capítulo cubre
> los widgets listos-para-usar que un sitio web externo
> (su página de inicio pública de la emisora, un sitio
> socio, una pantalla informativa) puede integrar mediante
> un simple `<iframe>`. Los widgets extraen los datos en
> vivo de RASTATIME y no requieren inicio de sesión —
> están diseñados para ser visibles públicamente.

RASTATIME entrega una pequeña familia de widgets HTML que
los sitios externos pueden integrar para mostrar lo que
está al aire, lo que viene a continuación, el programa
semanal, etc. Cada widget es una URL de iframe autónoma
que usted inserta en el HTML de su página de inicio.

Este capítulo es la referencia del operador: qué widgets
existen, qué parámetros URL aceptan y cómo integrarlos en
un sitio externo.

---

## 1. La familia de widgets

| Widget | URL | Propósito |
|---|---|---|
| **Now Playing — Show** | `/embed/now-playing-show` | Widget de texto de dos líneas. Nombre del programa actual + duración restante; nombre del próximo programa + horas de inicio-fin. |
| **Now Playing — Track** | `/embed/now-playing-track` | Widget de texto de dos líneas. Pista actual "Artista - Título" + duración restante; próxima pista + horas de inicio-fin. |
| **Weekly Program** | `/embed/weekly-program` | (Existente) Vista de cuadrícula de calendario de siete días del programa. |
| **Audio Player** | `/embed/player` | (Existente) Reproductor de audio HTML5 integrado para el stream público. |

Más widgets están planificados (vea [BACKLOG.md](../../../BACKLOG.md)).

---

## 2. Widget Now Playing — Show

iframe listo para usar:

```html
<iframe src="https://su-emisora.example/embed/now-playing-show"
        width="100%" height="50" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Lo que muestra

Dos líneas, cada una con un nombre a la izquierda y una
hora a la derecha:

```
Mañanas                                                   -25:14
Music Hour                                          10:00 - 11:30
```

- **Línea 1**: nombre del programa actual + cuenta atrás hasta el fin (`-MM:SS` o `-H:MM:SS`)
- **Línea 2**: nombre del próximo programa + su ventana `HH:MM - HH:MM`

La cuenta atrás se actualiza cada segundo del lado del
cliente, así que la pantalla se ve fluida. Los datos
subyacentes se refrescan cada 60 segundos (configurable
— vea §4).

### Parámetros URL

| Parámetro | Valores | Por defecto | Efecto |
|---|---|---|---|
| `theme` | `auto`, `dark`, `light` | `auto` | Color del texto. `auto` sigue el `prefers-color-scheme` del navegador. Fondo siempre transparente. |
| `cache` | entero segundos, 10–3600 | `60` | TTL del caché HTTP del lado del servidor. Más bajo = datos más frescos + más hits backend. |
| `overflow` | `ellipsis`, `marquee` | `ellipsis` | Qué hacer con nombres de programa / pista más anchos que el widget de 300 px. `ellipsis` trunca con `…`; `marquee` desplaza el texto a la izquierda durante 24 s. |
| `timezone` | cualquier zona horaria estándar (`Europe/Madrid`) | predeterminado de la emisora | Todas las horas renderizadas en esta zona. |

> **Nota.** El cuerpo del widget está limitado a **300 px de
> ancho** para encajar en diseños de barra lateral típicos de
> los sitios de emisoras.  Establezca el ancho del iframe en
> 300 en el HTML de integración para un ajuste perfecto.

---

## 3. Widget Now Playing — Track

iframe listo para usar:

```html
<iframe src="https://su-emisora.example/embed/now-playing-track"
        width="100%" height="50" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Lo que muestra

El mismo diseño de dos líneas que el widget show, pero
para pistas:

```
The Beatles - Hey Jude                                    -02:14
Pink Floyd - Comfortably Numb                       16:00 - 17:30
```

- **Línea 1**: pista actual `Artista - Título` + cuenta atrás hasta el fin
- **Línea 2**: próxima pista `Artista - Título` + su ventana `HH:MM - HH:MM`

Si una pista no tiene metadatos de artista, solo se
muestra el título (y viceversa). Si ninguno está
disponible, la línea muestra "No track playing" / "No
upcoming track" en estilo atenuado.

### Parámetros URL

Igual que el widget show — vea §2.

---

## 4. Personalizar las etiquetas de estado vacío

Cuando no hay programa o pista actual / próxima, el widget
muestra un breve texto placeholder.  Los operadores pueden
personalizar los cuatro placeholders sin tocar el código bajo:

**Configuración → Widgets → Current Show/Track**

| Campo | Texto por defecto |
|---|---|
| Etiqueta cuando ningún programa está al aire | `No show on air` |
| Etiqueta cuando no hay próximo programa | `No upcoming show` |
| Etiqueta cuando no se reproduce ninguna pista | `No track playing` |
| Etiqueta cuando no hay próxima pista | `No upcoming track` |

Las ediciones se persisten en `cc_pref` y son recogidas por
el widget dentro de un TTL de caché (por defecto 60 segundos).
Deje un campo vacío para volver al inglés por defecto mostrado
en su placeholder.

La misma página de configuración aloja también:

- una **vista previa en vivo** de ambos widgets lado a lado;
- el **código de integración `<iframe>` listo-para-usar** para
  cada widget con la URL absoluta de la emisora pre-rellenada.

---

## 5. El parámetro `cache` — ¿qué TTL?

El servidor almacena en caché los datos subyacentes
durante `cache` segundos antes de regenerarlos. El polling
JS dentro del iframe coincide con esta cadencia, por lo
que bajo alta carga cada visitante alcanza el **caché del
navegador** en lugar de su backend.

Valores recomendados:

| `cache=` | Cuándo |
|---|---|
| `30` | Pantalla de alta precisión, ej. pantalla del lobby. ~2 hits backend/min por navegador. |
| `60` (por defecto) | Página de inicio pública con tráfico moderado. Buen equilibrio entre frescura y carga. |
| `120`–`300` | Integración de muy alto tráfico. Cambie hasta 5 min de obsolescencia por un orden de magnitud menos hits backend. |
| `> 600` | No recomendado — el programa / pista mostrada a menudo ya ha terminado cuando el navegador vuelve a consultar. |

> **Consejo del operador.** El widget compensa los datos
> obsoletos: cuando pasa la hora de fin del item actual
> (calculada del lado del cliente desde los timestamps
> absolutos en el payload), el JS dispara una consulta
> inmediata sin esperar el próximo intervalo. Así una
> integración `cache=300` cambia a la próxima pista en
> ~1 s — la obsolescencia solo afecta a la primera
> visualización después de una pausa inactiva larga.

> **Cómo funciona bajo el capó.** Ambos endpoints de
> widget establecen `Cache-Control: public,
> max-age=<cache>`. Apache sirve el HTML del iframe; el
> JS dentro del iframe consulta `/embed/now-playing-data`
> (mismo TTL de caché). El endpoint JSON extrae de
> `Application_Model_Schedule::GetPlayOrderRange()` — la
> misma fuente que `/api/live-info` — pero recortado a
> ~1-2 kB de payload.

---

## 6. Temas

Tres modos, controlados vía el parámetro `theme`:

| `theme=` | Efecto |
|---|---|
| `auto` (por defecto) | Texto claro en páginas de integración oscuras, texto oscuro en claras. Detectado vía la media query `prefers-color-scheme` del navegador. |
| `dark` | Fuerza texto claro. |
| `light` | Fuerza texto oscuro. |

El fondo del widget es **siempre transparente**.

---

## 7. Autenticación

Ninguna. Los widgets Now-Playing son intencionalmente
públicos.

No exponen: contadores de oyentes, estado de fuente del
stream, nombres de operadores, estado de grabación, IDs
internos.

---

## 8. Integración cross-origin

Los iframes funcionan cross-origin de forma nativa —
ninguna configuración adicional necesaria.

---

## 9. Resolución de problemas

### "El widget muestra 'No show on air' pero un programa está corriendo"

- Verifique vía el [Panel](./DASHBOARD.md).
- El caché del servidor puede tener datos obsoletos.
  Espere hasta `cache` segundos.

### "El widget no muestra nada (iframe vacío)"

- Verifique que la URL sea accesible desde el contexto
  del navegador de la página integradora.
- Verifique la consola del navegador.

### "El fondo del widget es blanco pero quiero oscuro"

Añada `?theme=dark` a la URL.

### "La cuenta atrás muestra -00:00 y se queda ahí"

La hora de fin del item actual ha pasado pero el widget
no ha recogido aún los nuevos datos. Auto-recupera en
~1 s. Si persiste, el motor de playout puede estar
detenido — verifique `Get-Service RASTATIME-PLAYOUT`.

---

## A dónde ir después

* [Panel](./DASHBOARD.md) — la versión interna de los
  mismos datos.
* [Streams](./STREAMS.md) — los streams de audio
  subyacentes.
* [BACKLOG.md](../../../BACKLOG.md) — próximas olas de
  widgets.
