# La app del cliente: mesa por QR, pedido, cuenta y reservas

Estado: **propuesta**, nada de esto está construido todavía. Lo que hay hoy es el flujo público de
`frontend/cliente.html` (carta, alérgenos, destacados y «solicitudes» que un camarero acepta a
mano). Este documento describe lo que falta para que el cliente pida, siga y pague desde su
teléfono, y para que pueda reservar mesa con pedido por adelantado.

Cuatro bloques, en el orden en que conviene construirlos: cada uno se sostiene sobre el anterior.

---

## 1. Vincular al cliente con su mesa: el QR que cambia

En cada mesa hay una **pantalla LED pequeña tras un cristal** que enseña un QR. El QR **cambia
cada 5–50 segundos** hasta que alguien lo lee; al leerlo, esa cuenta queda vinculada a esa mesa
hasta que el cliente se va.

### Por qué rotar y no poner una pegatina

Una pegatina con el QR de la mesa 7 es un cartel permanente: quien la fotografía una vez puede
pedir «desde la mesa 7» meses después, desde la calle y sin estar sentado. Rotar convierte el
código en **un solo uso y con caducidad**: para pedir hay que estar delante del cristal en ese
momento. Que el intervalo sea variable (5–50 s, al azar) evita además que nadie prediga cuándo
sale el siguiente.

### Piezas

**`mesa_pantallas`** — una fila por pantalla física.

| columna | qué es |
|---|---|
| `id` | de la pantalla |
| `mesa_id` | la mesa donde está atornillada |
| `secreto` | clave con la que la pantalla pide códigos (`Authorization: Bearer`) |
| `visto_en` | último latido; si falta más de dos minutos, la sala lo ve en rojo |
| `firmware` | versión que dice la pantalla, para saber a cuál hay que subir |

**`mesa_codigos`** — los códigos que se van emitiendo.

| columna | qué es |
|---|---|
| `codigo` | 12 caracteres al azar, clave primaria |
| `mesa_id`, `pantalla_id` | de dónde salió |
| `emitido_en`, `caduca_en` | vida corta: el intervalo que toque más diez segundos de margen |
| `canjeado_en`, `visita_id` | si alguien lo leyó, cuándo y para qué visita |

**`visitas`** — la estancia de un grupo en una mesa. Es la pieza que falta: hoy la «cuenta» es el
pedido abierto, y eso no basta, porque un grupo puede cambiar de mesa o pedir en dos tandas.

| columna | qué es |
|---|---|
| `id`, `mesa_id` | la visita y dónde se sienta |
| `abierta_en`, `cerrada_en` | cuándo se sentaron y cuándo se fueron |
| `pedido_id` | el pedido al que se cargan las comandas (se crea con la primera) |
| `estado` | `activa`, `cerrada` |

**`visita_dispositivos`** — cada teléfono unido a la visita: `token` (el que guarda el móvil),
`visita_id`, `alias` («Ana»), `unido_en`, `ultimo_visto`. Así una mesa de cuatro pide desde cuatro
teléfonos contra la misma cuenta.

### Cómo va

1. La pantalla pide `POST /api/pantalla/codigo` con su secreto. El servidor guarda un código
   nuevo, lo devuelve junto con **cuántos segundos debe enseñarlo** (al azar entre 5 y 50) y la
   pantalla pinta `https://home.pr1.es/m/<codigo>`.
2. El cliente lo lee y cae en `GET /m/<codigo>` → `POST /api/publico/mesa/canjear`. El servidor
   comprueba que el código existe, no ha caducado y no está canjeado; abre la visita si la mesa no
   tenía una activa, y devuelve un **token de visita** que el móvil guarda.
3. **El código queda quemado** y la pantalla deja de rotar: pasa a enseñar un QR fijo de «únete a
   la mesa» mientras dure la visita, para que los rezagados entren sin volver a jugar a la lotería
   del código.
4. La visita se cierra cuando el camarero marca la mesa como libre, o cuando la cuenta queda
   saldada y pasan los minutos de `ajustes.visita_cierre_min` (diez por defecto). Al cerrarse, los
   tokens dejan de valer y la pantalla vuelve a rotar.

### Lo que hay que tener en cuenta

- **La pantalla no decide nada**: solo enseña lo que le dan. Si le roban el secreto, lo peor que se
  consigue es generar códigos de esa mesa, y por eso el canje exige que el código sea reciente.
- **Reloj**: las pantallas no llevan RTC. Quien mide la caducidad es el servidor.
- **Sin cobertura no hay QR que valga**: hace falta wifi de invitados, o que la carta se pueda
  abrir con datos. Si no hay red, el camarero toma nota como siempre; esto no sustituye a nadie.
- **Accesibilidad**: la pantalla enseña también el código en texto grande, para quien no pueda
  enfocar el QR, y el camarero puede unir una mesa a mano desde el TPV.

---

## 2. Pedir desde la app, y el filtro antes de cocina

Hoy el cliente manda una «solicitud» y un camarero la teclea. Con la visita vinculada, la comanda
puede ir **directa a cocina**, salvo cuando huele mal.

### El filtro

Un pedido pasa solo si cumple todas las reglas; si no, queda **retenido** con el motivo escrito y
aparece en el TPV y en el pase para que alguien decida. Las reglas viven en `ajustes`, se editan
desde la pantalla de ajustes y se comprueban **en el servidor**, nunca en el móvil:

| ajuste | por defecto | para qué |
|---|---|---|
| `cliente_max_unidades_linea` | 10 | las **1111 botellas de agua** se paran aquí |
| `cliente_max_lineas_pedido` | 25 | el carrito absurdo |
| `cliente_max_importe_cent` | 15000 | por encima, lo confirma un camarero |
| `cliente_max_pedidos_hora` | 12 | el que se aburre pulsando |
| `cliente_confirmar_categorias` | (vacío) | categorías que **siempre** pasan por camarero: botellas caras, menús de grupo |

Se mantiene lo que el servidor ya comprueba hoy: producto activo, no agotado, y el precio lo pone
**siempre** el servidor.

El motivo se guarda en la solicitud (`motivo_retencion`) y se enseña tal cual: «11 unidades de
Agua de deshielo: el máximo por línea son 10». El camarero puede **ajustar la cantidad** y
aceptar, aceptar tal cual, o rechazar con un motivo que el cliente ve en su teléfono.

Cocina no hace nada distinto: una comanda aceptada es una comanda como las de siempre.

---

## 3. Seguir el pedido y pagar la cuenta

### Seguir

`GET /api/visita/estado` (con el token de la visita) devuelve, y solo eso:

- las líneas **de esa visita**, con su estado real de cocina: `en cola`, `preparando`, `lista`,
  `servida` — el mismo `lineas_pedido.estado` que ve el KDS, traducido a palabras de cliente;
- el total pedido, lo ya pagado y **el saldo**;
- el tiempo estimado de lo que falta, que ya se calcula para el pase.

Nada de estaciones, ni de qué camarero atiende, ni de otras mesas. El teléfono se entera de los
cambios por el **canal público del WebSocket**, que no lleva datos: solo dice «vuelve a mirar».

### Pagar

La cuenta de la visita es el pedido, y `pagos` ya admite **pagos parciales** (se usan desde el TPV
para dividir cuentas). El cliente puede:

- **pagar lo que lleva** en cualquier momento, entero o en parte;
- **pagar solo lo suyo**, marcando sus líneas, igual que hace el camarero al dividir;
- **dejarlo abierto** y pagar al final, él mismo o llamando al camarero.

Cada pago desde la app entra como `pagos.metodo='app'`, con su `concepto` y el dispositivo que lo
hizo. La mesa no se libera hasta que el saldo es cero.

> **Esto no cobra dinero de verdad.** El proyecto no tiene pasarela: lo que se construye es el
> hueco donde entra (Redsys, Stripe o el datáfono del banco) y el flujo completo en modo
> simulacro, con un aviso visible en pantalla. Cobrar de verdad exige comercio, contrato y
> certificados, y **no se toca sin decirlo**. Un ticket emitido contra un pago simulado no es una
> factura válida: mientras esté en simulacro, el documento sale marcado.

---

## 4. Reservar mesa, y dejar el pedido adelantado

Reserva con **quince minutos de antelación como mínimo** (`ajustes.reserva_antelacion_min`), para
que la sala tenga margen de reaccionar.

**`reservas`**: `id`, `mesa_id` (o `zona`, si da igual la mesa concreta), `hora`, `comensales`,
`nombre`, `telefono`, `token` (el enlace que se le manda al cliente), `estado` (`pendiente`,
`confirmada`, `sentada`, `no_show`, `anulada`), `nota`, `creada_en`.

- **Solapes**: al reservar se comprueba que la mesa no tenga otra reserva dentro de la duración
  estimada (`ajustes.reserva_duracion_min`, noventa por defecto) ni una visita activa a esa hora.
- **Pedido adelantado**: la reserva puede llevar líneas, que quedan **programadas**. Entran en
  cocina solas a la hora de la reserva menos lo que tarde el plato más lento, y el pase las ve
  marcadas con la hora a la que tienen que estar listas. El encargado puede soltarlas antes o
  retenerlas.
- **Al llegar**: el cliente lee el QR de su mesa como todo el mundo; si trae token de reserva, la
  visita se abre ya con la reserva y su pedido adelantado dentro. Si llega tarde, decide la sala:
  el `no_show` es una decisión de negocio, no del programa.
- **Lo que no se hace**: cobrar por adelantado ni pedir tarjeta en garantía. Ni hay pasarela ni
  merece la pena para un local de trece mesas.

---

## Orden y avisos

1. **Bloque 1** (vínculo por QR) es la base: sin visita no hay cuenta del cliente.
2. **Bloque 2** (pedido directo con filtro) es el que quita trabajo a la sala.
3. **Bloque 3** (estado y cuenta) es lo que el cliente nota.
4. **Bloque 4** (reservas) es independiente y cabe en cualquier momento.

Antes de empezar hay que decidir dos cosas que no son de programación:

- **Qué son las pantallas de mesa**: un ESP32 con panel LED generando el QR, o una tableta barata.
  Cambia el firmware, no el servidor.
- **Si el pago va a ser real algún día**, porque eso decide si el bloque 3 se queda en simulacro o
  hay que hablar con un banco.

Y uno de seguridad, ya apuntado en `PENDIENTES.md`: **`home.pr1.es` está abierto a internet**.
Todo lo público de aquí (canje, carta, estado, pagos) queda expuesto a cualquiera, así que va con
límite por IP, y el token de visita solo sirve mientras la visita esté activa.
