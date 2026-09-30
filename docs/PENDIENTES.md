# Mejoras pendientes

De las diez propuestas el 21/09/2026 están hechas **las diez**: la **7** (carta editable), la
**4** (dividir cuenta y pago mixto), la **1** (sesiones con token y roles), la **2** (HTTPS), la
**8** (alérgenos en TPV y cocina), la **9** (pantalla de recogida), la **6** (copias
incrementales con restauración probada), la **10** (pruebas automáticas y despliegue), la **5**
(arqueo de caja y cierre Z) y la **3** (modo sin red en el TPV).

No queda ninguna pendiente de aquella lista. Lo que se vaya viendo a partir de ahora se apunta
aquí abajo.

## Apuntado al cerrar la mejora 3

- **El certificado tiene que estar confiado en la tableta.** Sin instalarlo, el navegador se
  niega a registrar `sw.js` («An SSL certificate error occurred») y el TPV pierde la mitad del
  modo sin red: aguanta un corte con la pantalla abierta, pero no una recarga. Lo comprueba
  `deploy/qa_sinred.py`, que arranca el navegador haciendo de cuenta que ya está confiado.
- **Empezar el turno exige red**: el PIN lo valida el servidor. Una sesión ya abierta aguanta el
  corte, pero quien llega con la tableta recién arrancada y sin wifi no puede entrar.
- Sin red el TPV enseña la carta y las mesas **de la última vez que hubo servidor**. Si el
  encargado cambia un precio mientras una tableta está caída, esa tableta apunta el precio viejo;
  al reenviar manda el producto, y **el precio lo pone el servidor**.

## Abierto por internet (22/09/2026)

`home.pr1.es` sirve el TPV a todo el mundo, y el PIN sigue siendo de cuatro cifras **sin límite
de intentos**. En el primer minuto de exposición los registros ya recogieron sondas automáticas
pidiendo `/api/.env`, `/api/config` y `/api/settings`. Pendiente, por orden:

1. Freno al `POST /api/login`: espera creciente y bloqueo temporal por IP. **Sigue pendiente**, y
   ahora se puede calibrar con datos: el registro del punto 2 dice cuántos fallos hace de verdad
   el personal antes de acertar.
2. ~~Registro de intentos fallidos~~ — **hecho el 30/09**: `24_intentos_login.sql` (`empleado_intentos`,
   se guardan 30 días), `app/intentos.py`, `GET /api/seguridad/intentos` y la pestaña «Intentos de
   entrada» en `usuarios.html`: fallos por dirección, si vienen de la red del local o de internet,
   y quién entró después desde esa IP. Se apunta cada entrada, buena o mala, **nunca lo tecleado**.
3. Contraseña larga obligatoria para los escalafones con gestión; el PIN, solo para la barra.

## Rediseño de la interfaz (23/09/2026)

Hecho y medido (ver `deploy/_qa/gui/`). Lo que quedó apuntado de esa tanda, **resuelto el 30/09**:

- ~~Color de categoría en línea~~: `tpv.js` solo pasa `--c` y la hoja de estilos pone borde y
  tinte, con el texto del tema. Probado con una categoría `#ffff66` en noche y en día.
- ~~Pasada a 1024×600~~: `qa_gui.py` tiene el tamaño `tableta_barata` (táctil; `--tamanos` para
  elegir). Destapó que la barra se parte en dos filas y el pie del ticket del TPV quedaba fuera
  de la vista; `comun.js` mide ahora la barra real (`--barra-alto`). Informe en
  `deploy/_qa/gui/1024_oscuro/`.
- ~~Sale de la misma pasada: `cliente.html` se desborda en el móvil por la cabecera
  `barra-cliente`~~. Medido honesto (sin `is_mobile`, que reescala y lo disimula) eran 78 px de
  más: 484 px de contenido en 390. No era solo feo —el navegador ensancha el viewport para que
  quepa y **toda la página se desplaza**, así que el botón «Pedir» dejaba de estar donde se veía
  y el dedo caía en el plato de al lado. `flex-wrap` en la cabecera, los tres botones juntos en
  `.acciones` para que bajen de línea a la vez, y el `top: 60px` escrito a mano de las categorías
  sustituido por `--alto-barra`, que mide `cliente.js`. Cero desborde en las cuatro pantallas
  públicas, y sin zonas de toque ni contrastes por debajo del mínimo en los dos temas.

## Encargo del 29/09/2026: la app del cliente y la visión por cámara

RocaPV describió cinco cosas nuevas, especificadas en `PROPUESTA_APP_CLIENTE.md` y
`PROPUESTA_VISION_CCTV.md`. Estado al cerrar el día:

| Bloque | Estado |
|---|---|
| 4 · Reservas con pedido adelantado | **Hecho** (`7dd56bb`): `19_reservas.sql`, agenda `reservas.html`, reserva desde el móvil, 16 pruebas |
| — · Carta instalable y cuentas de cliente | **Hecho** (`e6bc059`, `d4c815d`) |
| 1 · QR de mesa rotativo (5-50 s, un solo uso) | **Hecho** (`4c8e047`, `e91fbf0`): `21_mesa_qr.sql`, `pantalla.html`, 17 pruebas |
| 2 · Pedido directo con filtro | **Hecho** (`b756858`): lo absurdo se para con el motivo escrito y sala corrige la cantidad, 14 pruebas |
| — · Paso cocina → mesa | **Hecho** (`89209e1`): cocina llega a «lista», la entrega la confirma sala desde el pase |
| 3 · Cuenta y pago desde la app | **Pendiente.** El cliente ya ve sus platos en cola (`/api/publico/visita/comanda`); falta saldar la cuenta desde el móvil, entera o a trozos. Depende de la tarea 2 de abajo |
| Visión por CCTV | **Sin construir.** Sin reconocimiento facial y sin medir a nadie por su nombre: lo exige la ley. DPIA y cartel antes de la primera cámara |

Dos decisiones pendientes de RocaPV: qué son las pantallas de mesa (ESP32 con panel LED o
tableta; el QR ya lo dibuja el servidor, así que valen las dos) y si el pago de la app se queda en
simulacro o algún día cobra de verdad.

## Tres tareas encadenadas (29/09/2026)

1. **Grupo en la mesa** — **hecho** (`f6e66d8`): `23_comensales.sql`, popup con la rejilla del
   tamaño real de la mesa, lo que pide cada móvil nace a su nombre. Repartir es opcional.
2. **Cuenta comensal a comensal** — **hecho** (`21d1e77`, `6365440`): cada uno lo suyo o dividir,
   tickets individuales, `25_pago_comensal.sql`.
3. **Factura a petición** — en curso (30/09): desde la app o al camarero.

Diseño de las tres en `PROPUESTA_GRUPOS_Y_FACTURACION.md`.

## Planning de mesas (30/09/2026)

**Hecho**: pestaña «Planning» en `reservas.html` (`js/planning.js`), según
`PROPUESTA_PLANNING_MESAS.md`. Una fila por mesa agrupada por zona, el día a escala con las horas
fuera de horario sombreadas y la línea de «ahora»; colores de estado de la agenda y marca de
pedido adelantado. Tocar abre la reserva con sus botones; arrastrar a otra fila la cambia de mesa
(la fila se pinta verde o roja antes de soltar, con la misma regla que el servidor); ↑/↓ hace lo
mismo con teclado; un hueco vacío abre el alta con esa mesa y esa hora. En el móvil se desplaza en
horizontal con la mesa fija. Lo único que tocó el servidor: `mesa_id` opcional en el alta de la
sala (internet lo ignora) y `sentados` en `/api/mesas`. 6 pruebas en `test_planning.py`.

- Queda por probar **con el dedo en una tableta de verdad**: el arrastre táctil está escrito con
  eventos de puntero y `touch-action: pan-x`, pero solo se ha probado con ratón en Chromium.
- Si la duración de las reservas deja de ser única, la barra y el solape tienen que pasar a mirar
  la de cada reserva (lo avisa la propuesta).

## Pendiente de construir

- Al construir la factura (tarea 3), recordar la corrección que trae
  `PROPUESTA_GRUPOS_Y_FACTURACION.md`: lo de «al cerrar el día ya no se puede emitir» vale como
  política de caja, pero no como norma absoluta, porque el reglamento de facturación obliga a
  expedirla cuando el cliente la pide.

## Estudio de vídeo (`estudio_video/`)

- **Primera tirada de generación de imagen** (casting de los nueve retratos + un clip de prueba):
  sin hacer. `esperar_gpu.py` la lanza solo cuando hay 5.200 MiB libres dos lecturas seguidas; el
  29/09 la tarjeta la ocupaba el modelo de Graphify en LM Studio. Hasta entonces, las cifras de
  calidad y tiempo del `README` son estimaciones.
- La zona de recogida no tiene mostrador en el plano (se arregla en `plano.html`); el sitio de
  pruebas `:8093` no tiene `reservas.html` ni `pantalla.html` (republicar con `publicar.sh`);
  falta publicar los vídeos terminados en `home.pr1.es`.

