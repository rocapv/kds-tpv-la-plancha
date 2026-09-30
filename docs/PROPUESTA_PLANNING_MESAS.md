# Planning de mesas: el día entero de un vistazo

Estado: **construido el 30/09/2026** (`reservas.html` → Planning, `js/planning.js`). Decisión del
móvil: se desplaza en horizontal con la columna de la mesa fija. Lo único que tocó el servidor fue
un `mesa_id` opcional en el alta de la sala, para que el hueco pulsado reserve esa mesa. Las reservas ya funcionan (`reservas.html` enseña la agenda
del día como una lista, ordenada por hora). Esto es otra manera de mirar lo mismo: **una fila por
mesa y el día entero en horizontal**, para ver de golpe qué mesa está libre a las nueve y media y
cuál lleva tres turnos encadenados.

La lista contesta «¿qué toca ahora?». El planning contesta «¿dónde meto a estos seis del jueves?».

---

## La pantalla

Una tabla con tres columnas:

| Mesa | Comensales | El día |
|---|---|---|
| `C1` | 4 | una barra por reserva, colocada en su hora |
| `C2` | 4 | … |
| `M3` | 6 | … |

- **Mesa**: el código de siempre (`C1`…`C6`, `M1`…`M4`, `A1`…`A3`), agrupado por zona con un
  encabezado, como en el TPV.
- **Comensales**: las plazas de la mesa. Al lado, en tenue, cuántos hay sentados ahora si está
  ocupada, porque es el dato que se pregunta a la vez.
- **El día**: la franja horaria dibujada a escala. Cada reserva es **una barra** que empieza en su
  hora y dura `reserva_duracion_min` (noventa minutos por defecto, el mismo número que ya usa el
  control de solapes, para que lo que se ve sea exactamente lo que el servidor impide).

## Qué se ve en cada barra

Dentro de la barra, si cabe: **hora, nombre y comensales** (`21:30 · Ana · 4`). Si no cabe, solo la
hora, y el resto al pasar por encima o al tocarla.

El color dice el estado, y son los mismos que ya usa la agenda para no aprender dos idiomas:

| estado | barra |
|---|---|
| `pendiente` | contorno ámbar, relleno hueco: reservada pero sin confirmar |
| `confirmada` | ámbar sólido |
| `sentada` | verde |
| `no_show` | gris tachada; se sigue viendo, porque explica por qué la mesa estuvo vacía |
| `anulada` | no se dibuja, salvo que se marque «ver anuladas» |

Dos marcas más, que son las que hacen útil la pantalla en servicio:

- **una línea vertical en la hora actual**, para situarse sin pensar;
- **sombreado en las horas fuera de `reserva_horario`**, para que no se intente encajar a nadie a
  las seis de la tarde.

Y un detalle que sí importa: la barra de una reserva **con pedido adelantado** lleva una marca
(un punto, o el borde izquierdo más grueso), porque esa mesa tiene trabajo en cocina antes de la
hora y eso cambia cómo se planifica el turno.

## Qué se puede hacer desde ahí

- **Pulsar una barra** abre la misma reserva de siempre, con sus botones (confirmar, sentar,
  soltar a cocina, no vino, anular, cambiar de mesa).
- **Arrastrar una barra a otra fila** es cambiarla de mesa: es la operación que más se hace y aquí
  se ve si cabe antes de soltarla. Ya existe el endpoint (`PATCH /api/reservas/{id}/mesa`), que
  comprueba plazas y solape, así que arrastrar no puede colar nada que la lista no dejaría.
- **Pulsar un hueco vacío** abre el alta con esa mesa y esa hora ya puestas.

Con el teclado tiene que hacerse lo mismo: seleccionar una barra y moverla con las flechas. Una
pantalla que solo funcione arrastrando deja fuera a quien no puede arrastrar, y el proyecto ya mide
accesibilidad en `deploy/qa_gui.py`.

## Cómo se alimenta

**No hace falta API nueva.** `GET /api/reservas?fecha=…` ya devuelve la agenda del día con mesa,
hora, comensales, estado y líneas adelantadas, y la configuración (duración, horario) viene en la
misma respuesta. Falta solo la lista de mesas con sus plazas, que es `GET /api/mesas`, y que la
pantalla dibuje.

Se refresca con el mismo WebSocket que ya escucha `reservas.html`: cuando alguien confirma, sienta
o mueve una reserva, el planning se repinta solo.

## Lo que hay que tener en cuenta

- **El día no cabe entero a escala en un móvil.** A 1280 px van bien las horas de servicio (dos
  tramos de tres horas); en el móvil del camarero hay que poder desplazar en horizontal, o enseñar
  un solo turno cada vez. Decidirlo antes de dibujar nada.
- **Las mesas son trece, pero el planning crece con el local.** Con filas fijas de altura y barras
  posicionadas en porcentaje, la tabla aguanta tanto trece mesas como cuarenta.
- **Lo que se ve tiene que ser lo que se impide.** Si algún día la duración deja de ser fija (una
  comida de empresa ocupa más que un café), la barra tendrá que pintar la duración real de esa
  reserva, no la del ajuste, y el solape tendrá que mirar lo mismo. Mientras la duración sea única,
  dibujarla del ajuste es correcto.
- **Es una vista, no otra fuente de verdad**: los estados, los solapes y los cambios de mesa los
  sigue decidiendo el servidor.

## Dónde encaja

Como pestaña dentro de `reservas.html` («Lista» / «Planning»), no como pantalla aparte: es la misma
información y el mismo permiso (camarero o encargado). Así se llega igual desde el menú y no hay
dos sitios donde buscar lo mismo.
