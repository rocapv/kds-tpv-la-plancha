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
3. ~~Contraseña larga obligatoria para los escalafones con gestión; el PIN, solo para la barra.~~
   **Aparcado el 30/09 por decisión de RocaPV**: esto no es una cantina de verdad, es un proyecto
   de clase, y los PIN de cuatro cifras (`1111`, `3333`, `9999`) son los que se usan para
   enseñarlo. No se toca. El mecanismo ya está hecho por si algún día hiciera falta —
   `POST /api/login` acepta número de empleado con contraseña además del PIN—, lo que no se hace
   es exigirlo. Ojo si alguna vez esto sirviera a clientes reales: entonces sí, y antes el punto 1.

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

## QA completo del sitio (30/09/2026)

Pasada entera contra una instancia de usar y tirar (BD aparte, `127.0.0.1:8191`, copia del repo:
nada de esto tocó producción). Resultado final: 196 pruebas de `pytest`, `qa.py`, `qa_gui.py` en los
dos temas y los tres tamaños, `qa_cliente.py`, `qa_sinred.py` y `qa_ritmo.py`, **sin fallos**. Lo
que destapó, ya arreglado:

- ~~**La simulación de la demo se paraba en seco a los 2½ minutos.**~~ Lo peor de la tanda, porque
  la demo es lo que ve el tribunal: a los 2:30 dejaban de entrar pedidos, no se cocinaba y no se
  cobraba nada más (medido: 25 pedidos, **0 cobrados**, cola clavada en 25 durante cuatro minutos).
  Al añadir el paso «cocina → mesa» nadie actualizó `simulacion.py`: una comanda con todo en
  «lista» sigue saliendo en la pantalla de cocina —espera en el pase— pero avanzarla da 409, así
  que el bot cogía siempre la más antigua (justo la ya lista), se comía el 409 en cada vuelta y no
  avanzaba **ninguna**; la cocina no se vaciaba, la sala se frenaba por atasco y todo se detenía.
  Y **ningún bot recogía del pase**, que es el paso nuevo. Tres arreglos: `trabajo_de_cocina()`
  descarta lo que ya está listo, el bot de sala vacía el pase con `entregar_pedido` antes de sentar
  a nadie, y cada comanda de la tacada va en su propio `try` (un 409 tumbaba las demás). Vuelto a
  medir: **82 pedidos, 63 cobrados**, cola entre 4 y 10. Dos pruebas nuevas en `test_ritmo_bots.py`,
  comprobadas contra la lógica vieja para ver que fallan.
- El fallo lo delató `qa_ritmo.py`, pero su mensaje apuntaba a otro sitio («la cola crece sin
  parar»): esa comprobación compara la media de la segunda mitad con la de la primera, y una cola
  **clavada** en el techo también la dispara. Y los errores de los bots se guardaban en
  `ficha["ultimo"]`, que `qa_ritmo.py` no imprime: hubo que preguntar a `GET /api/simulacion` para
  ver el 409. Merece la pena que el informe saque el `ultimo` de cada bot cuando algo falla.

- ~~**El punto verde mentía.**~~ Es lo único que mira la camarera para saber si lo que apunta llega
  a cocina, y con la red cortada seguía verde **más de 60 s** (medido). Dos causas juntas: el
  «ping» de `comun.js` no esperaba respuesta y el `/ws` del servidor se lo comía sin contestar, así
  que el estado solo cambiaba si el navegador lanzaba `onclose`… y cuando se cae el wifi de la sala
  el TCP se queda colgado **sin cerrarse**. Ahora el servidor contesta `pong`, el cliente cierra el
  socket a mano si pasan 15 s sin oír nada, y además escucha el aviso `offline` del navegador.
  Vuelto a medir: se entera **al instante**. De paso, cada reconexión dejaba un `setInterval` vivo
  apuntando a un socket muerto; una tableta de todo el turno acababa con decenas.
- Cuidado al probar esto: `set_offline()` de Playwright **no cierra un socket ya abierto** ni corta
  su tráfico, así que una prueba que solo lo llame puede pasar sin comprobar nada. Los dos caminos
  se midieron por separado, porque el rápido tapa al otro: con el aviso `offline` puesto salta a
  **0 s**; anulando ese aviso y tirando el «ping» antes de que salga —que es el wifi asociado pero
  sin enlace de arriba— lo caza el latido a los **15 s**.

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
| 3 · Cuenta y pago desde la app | **Hecho** (`f837b44`): `/api/publico/visita/pagar` y `26_pago_app.sql`. Lo suyo o la mesa entera; de quién es el dinero lo dice el token, no el cuerpo; el método lo pone el servidor (`app`, que el arqueo no suma al efectivo); reintentar con la misma clave devuelve el mismo recibo. 16 pruebas |
| Visión por CCTV | **Sin construir, y bloqueada por lo de arriba** (ver nota). Sin reconocimiento facial y sin medir a nadie por su nombre: lo exige la ley. DPIA y cartel antes de la primera cámara |

**Reparto de trabajo (30/09, decisión de RocaPV): la visión por CCTV y el estudio de vídeo se
llevan en otro chat.** Y no son dos temas separados, por eso van juntos: la visión por cámara no se
puede construir a ciegas —hace falta metraje de gente comiendo en una mesa para tener con qué
probarla— y ese metraje es justo lo que produce el estudio de vídeo. Así que **la CCTV depende de
que el estudio sepa generar vídeo realista de gente comiendo**, y hasta entonces no hay nada que
programar aquí. Quien trabaje en este chat: no empieces ninguna de las dos, y no las cuentes como
pendientes propias.

Dos decisiones pendientes de RocaPV: qué son las pantallas de mesa (ESP32 con panel LED o
tableta; el QR ya lo dibuja el servidor, así que valen las dos) y si el pago de la app se queda en
simulacro o algún día cobra de verdad.

Sobre lo segundo, ahora que la ruta existe conviene dejarlo escrito sin adornos: **el pago desde
la app apunta el cobro, pero no mueve dinero.** Contabiliza igual que un cobro en barra —la cuenta
queda saldada y el pedido se cierra—, y eso es exactamente lo que hace falta para el proyecto y
para una demo. Si algún día tiene que cobrar de verdad, la pasarela entra en un solo sitio: entre
la comprobación del saldo y la llamada a `_registrar_pago()`, que es la que da el hecho por bueno.
Hasta que cobre de verdad, el método `app` en el arqueo hay que leerlo como «se lo llevó el
teléfono», no como dinero en la caja.

## Tres tareas encadenadas (29/09/2026)

1. **Grupo en la mesa** — **hecho** (`f6e66d8`): `23_comensales.sql`, popup con la rejilla del
   tamaño real de la mesa, lo que pide cada móvil nace a su nombre. Repartir es opcional.
2. **Cuenta comensal a comensal** — **hecho** (`21d1e77`, `6365440`): cada uno lo suyo o dividir,
   tickets individuales, `25_pago_comensal.sql`.
3. **Factura a petición** — **hecho** (`47f62ca`): `27_factura_a_peticion.sql` y `facturacion.py`,
   que es donde viven la numeración, el plazo y la regla de **o una por cabeza, o una de todos**.
   La pide el cliente desde la mesa (`/api/publico/visita/factura`), la de un cobro suelto la
   emite la sala (`/api/pagos/{id}/factura`) y quien lo deje puesto en su perfil la recibe con el
   propio pago. 23 pruebas.

Diseño de las tres en `PROPUESTA_GRUPOS_Y_FACTURACION.md`.

### Lo que la factura NO hace, dicho antes de que alguien lo suponga

- **No hay rectificativa.** Si una factura sale mal, hoy no hay manera de anularla desde la
  aplicación: habría que emitir una rectificativa (serie propia, referencia a la original) y eso
  no está construido. Mientras no exista, el freno está en su sitio: un cobro con factura ya no se
  puede borrar, así que nadie deja un número de la serie sin operación detrás.
- **No se envía por correo.** La factura se ve y se descarga en la pantalla del cliente; lo que la
  app dice cuando ya no puede emitirla es el teléfono y el correo del local, y el envío lo hace
  una persona. Mandarla desde el servidor pide un SMTP y un registro de envíos que no hay.
- **El IVA es uno para toda la carta** (`ajustes.iva_pct`). Con carta de comida y bebida alcohólica
  al 21 % esto no valdría: el tipo tendría que ir por producto. Queda escrito porque es el cambio
  que más cuesta descubrir tarde.

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

- La corrección que traía `PROPUESTA_GRUPOS_Y_FACTURACION.md` —«al cerrar el día ya no se puede»
  vale como política de caja, no como norma absoluta— está **aplicada** en `47f62ca`: con la caja
  cerrada la app deja de emitir pero contesta a quién pedirla, el encargado la sigue emitiendo y
  el documento lleva las dos fechas. Lo que queda de ahí es la **rectificativa**, que es la única
  salida cuando una factura ya emitida está mal.

## Estudio de vídeo (`estudio_video/`) — se lleva en otro chat

Desde el 30/09 esto **no se toca desde aquí** (decisión de RocaPV). Se queda apuntado porque la
visión por CCTV cuelga de ello, no para que nadie de este chat lo coja.

- **Primera tirada de generación de imagen** (casting de los nueve retratos + un clip de prueba):
  sin hacer. `esperar_gpu.py` la lanza solo cuando hay 5.200 MiB libres dos lecturas seguidas; el
  29/09 la tarjeta la ocupaba el modelo de Graphify en LM Studio. Hasta entonces, las cifras de
  calidad y tiempo del `README` son estimaciones.
- La zona de recogida no tiene mostrador en el plano (se arregla en `plano.html`); falta publicar
  los vídeos terminados en `home.pr1.es`.
- (Resuelto el 30/09: el sitio de pruebas `:8093` ya tiene `reservas.html` y `pantalla.html`. Le
  faltaban por no haberse republicado, no por nada del código; entraron solas al pasar
  `publicar.sh` por los dos docroots. Comprobado en el disco de Raspa, no supuesto.)

