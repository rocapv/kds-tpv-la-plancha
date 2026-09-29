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

1. Freno al `POST /api/login`: espera creciente y bloqueo temporal por IP.
2. Registro de intentos fallidos (quién, desde dónde, cuántos) visible para el encargado.
3. Contraseña larga obligatoria para los escalafones con gestión; el PIN, solo para la barra.

## Rediseño de la interfaz (23/09/2026)

Hecho y medido (ver `deploy/_qa/gui/`). Lo que queda apuntado de esa tanda:

- Los botones de categoría del TPV se pintan con el color de la categoría por estilo **en línea**
  desde `tpv.js`, así que la hoja de estilos no puede gobernarlos. Funciona y el contraste da bien,
  pero el día que una categoría se ponga de un color claro, el texto blanco dejará de leerse. Lo
  suyo es que la carta guarde el color y el CSS decida el texto.
- `qa_gui.py` mide con el navegador a 1280×800 y 390×844. Faltaría una pasada a 1024×600, que es
  la resolución de muchas tabletas de TPV baratas.

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
2. **Cuenta comensal a comensal** — pendiente: cada uno lo suyo o dividir, tickets individuales o
   de la mesa.
3. **Factura a petición** — pendiente: desde la app o al camarero.

Diseño de las tres en `PROPUESTA_GRUPOS_Y_FACTURACION.md`.

## Sin construir

- `PROPUESTA_PLANNING_MESAS.md` — la agenda vista como planning, una fila por
  mesa y el día en horizontal, con una barra por reserva. No necesita API nueva: sale de
  `/api/reservas` y `/api/mesas`. Iría como pestaña de `reservas.html`, no como pantalla aparte.
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

