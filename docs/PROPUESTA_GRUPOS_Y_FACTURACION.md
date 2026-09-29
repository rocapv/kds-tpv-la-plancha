# Grupos en la mesa, cuentas individuales y factura a petición

Estado: **propuesta**, sin construir. Se apoya en dos cosas que ya existen: los pagos parciales con
líneas enganchadas a su pago (`lineas_pedido.pago_id`, se usa hoy para dividir cuentas desde el
TPV) y la facturación (`facturas`, con `tipo` simplificada o completa).

Lo que falta es saber **quién es quién dentro de la mesa**.

---

## 1. El grupo: quién se sienta y qué ha pedido cada uno

### El popup

Al pulsar una mesa en el TPV (y en el plano de sala) se abre un **popup que se cierra al pulsar
fuera** —o con `Esc`, que es lo mismo para quien va por teclado— con una **rejilla del tamaño de la
mesa**: una mesa de seis se pinta **2 × 3**, una de cuatro 2 × 2, una de dos 2 × 1. Cada celda es
un sitio, y en la celda va **el nombre del comensal y lo que ha pedido**:

```
┌─────────────────────┬─────────────────────┐
│ Ana                 │ Bruno               │
│ Roca Madre          │ Doble Impacto       │
│ Agua de deshielo    │ Rubia gravedad baja │
│              12,40 €│              15,90 €│
├─────────────────────┼─────────────────────┤
│ Carmen              │ (libre)             │
│ César invernadero   │                     │
│               8,90 €│                     │
├─────────────────────┼─────────────────────┤
│ Dani                │ (libre)             │
│ Regolito especiado  │                     │
│               4,50 €│                     │
└─────────────────────┴─────────────────────┘
```

Un sitio vacío se pulsa para sentar a alguien; el nombre lo pone el camarero («Ana», «el de la
gorra») o lo trae el propio cliente desde su móvil cuando exista el vínculo por QR
(`PROPUESTA_APP_CLIENTE.md`, bloque 1). **El nombre es una etiqueta de servicio, no una ficha de
cliente**: se borra al cerrar la mesa.

### Qué hace falta en la base

| tabla | para qué |
|---|---|
| `comensales` | `id`, `pedido_id`, `sitio` (1..plazas), `nombre`, `creado_en`. Un comensal vive dentro de un pedido; al cobrarse la mesa deja de usarse |
| `lineas_pedido.comensal_id` | columna nueva, opcional: de quién es esa línea. `NULL` = «de la mesa» (la botella de agua que comparten) |

Que sea opcional es importante: hoy se pide sin repartir, y así tiene que seguir funcionando.
Quien no quiera usar los sitios, no los usa, y la mesa se comporta como siempre.

### Cómo se reparte

- Al apuntar una línea en el TPV, si la mesa tiene comensales dados de alta, se pregunta de quién
  es (con un «de la mesa» por defecto y bien a mano: la mayoría de las veces da igual).
- En el popup se puede **arrastrar una línea de un comensal a otro**, que es lo que pasa de verdad
  cuando alguien dice «eso es mío».
- Desde el móvil, cada teléfono unido a la visita pide **para su comensal**, sin tener que decir
  nada: lo que pide Ana es de Ana.

---

## 2. La cuenta: cada uno lo suyo, o dividir

Al ir a cobrar, el mismo popup cambia de cara y pasa a **cliente + cantidad**:

| | |
|---|---|
| Ana | 12,40 € |
| Bruno | 15,90 € |
| Carmen | 8,90 € |
| Dani | 4,50 € |
| **De la mesa** (lo compartido) | 6,00 € |

Y dos maneras de terminar, que no se mezclan:

- **Cada uno lo suyo**: se cobra comensal a comensal. Cada cobro es un `pago` con su `concepto`
  («Ana»), y las líneas de esa persona quedan enganchadas a ese pago, que es exactamente lo que ya
  hace el TPV al dividir. Lo compartido se reparte entre los que queden por pagar, o lo asume quien
  diga la mesa.
- **Dividir**: el total entre los comensales, a partes iguales. Es un solo importe repetido, no un
  reparto por líneas.

La mesa no se cierra hasta que el saldo es cero, y en todo momento se ve **cuánto falta**. Si uno
se va antes, paga lo suyo y la mesa sigue abierta con el resto: eso hoy no se puede contar bien y
con esto sí.

### Tickets

- **Uno por comensal** cuando cada uno paga lo suyo: el ticket lleva solo sus líneas y su importe.
- **Uno de la mesa entera** cuando se divide, con la nota de en cuántas partes se ha dividido.

La regla que no se puede romper: **la suma de los justificantes es la cuenta, ni un céntimo más**.
Un ticket por comensal más otro de la mesa entera sería cobrar dos veces lo mismo sobre el papel,
así que el sistema no deja emitir los dos: o uno por cabeza, o uno de todos.

---

## 3. Factura a petición

Hoy `facturas` distingue simplificada (el ticket de siempre) y completa (con NIF, nombre y
dirección). Lo que se añade es **quién la pide y cuándo**:

- **Desde la app, al pagar**: una casilla «quiero factura» que aparece en el momento del cobro y
  pide los datos fiscales.
- **Al camarero**, como siempre, desde el TPV o desde `facturas.html`.

### El plazo, y una corrección al encargo

La idea de «solo durante el día, y cuando el restaurante cierra ya no se emite» tiene todo el
sentido **como política de caja**: una factura emitida al día siguiente descuadra el arqueo y el
cierre Z de ayer, y eso es un lío que no compensa.

Pero como norma absoluta **no se sostiene legalmente**. El Reglamento de facturación (RD 1619/2012)
obliga a expedir factura cuando el cliente lo pide, y permite expedir una **factura completa a
partir de una simplificada ya emitida**; el plazo no termina al cerrar la persiana. Decirle a un
cliente «ya no se puede» porque pasaron las doce de la noche es una respuesta que puede acabar en
reclamación.

Así que la propuesta es:

- **Por defecto, durante el día**: mientras la caja del día esté abierta, la factura se emite sola
  desde la app o desde el TPV, sin que intervenga nadie.
- **Después, con el encargado**: la pantalla de facturas permite convertir un ticket en factura
  completa **en cualquier momento**, dejando constancia de que la fecha de expedición no es la de
  la operación. Es un botón detrás de un permiso, no un flujo abierto al público.
- Al cerrar el día, la app deja de ofrecerlo y explica **cómo pedirla** (teléfono o correo del
  local), en vez de decir que es imposible.

Esto además deja el sistema preparado para lo que viene: con Veri\*factu, cada factura se registra
con su encadenamiento y anularla o rectificarla deja rastro. Cuanto menos se improvise con las
fechas, mejor.

### Numeración

Las facturas siguen su serie, independientemente de cuántos tickets haya generado la mesa. Una
factura que nace de un ticket **referencia ese ticket** (ya hay `facturas.pedido_id`), y un ticket
solo puede dar lugar a una factura: la segunda petición devuelve la que ya existe, no una nueva.

---

## 4. El perfil del cliente y la factura automática

El cliente puede dejar configurado «factúrame siempre», con su NIF, nombre y dirección, y entonces
cada cobro suyo genera factura completa sin preguntar nada.

**Dónde viven esos datos** es la decisión importante, y la propuesta es la menos invasiva:

- **En su teléfono** (`localStorage`), y se mandan con cada cobro. El local no guarda una base de
  datos de clientes: guarda las facturas que ha emitido, que es lo que tiene que guardar de todas
  formas.
- Solo si algún día hay cuentas de cliente de verdad (con correo y contraseña) tendría sentido
  guardarlo en el servidor, y entonces hace falta lo de siempre: informar, poder borrarlo y no
  conservarlo más de lo necesario. Los datos fiscales de las facturas ya emitidas se conservan
  aparte y por obligación contable: eso no se borra a petición.

En el TPV, el camarero ve que esa persona pide factura automática **solo mientras dure la mesa**,
para no tener que preguntárselo.

---

## Por dónde se haría

1. `comensales` y `lineas_pedido.comensal_id`, y el popup **en modo consulta**: quién se sienta y
   qué ha pedido. Solo con esto la sala ya gana.
2. El reparto al cobrar: comensal a comensal, con lo compartido aparte.
3. Tickets individuales, con la regla de que los justificantes suman la cuenta y no más.
4. Factura desde la app y el plazo, con la salida del encargado para después del cierre.
5. El perfil con factura automática.

Los puntos 2 y 3 tocan dinero: no entran sin pruebas que comprueben que la suma cuadra, como las
que ya vigilan el arqueo.
