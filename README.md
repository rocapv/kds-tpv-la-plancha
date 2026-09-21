# KDS + TPV · Hamburguesería «La Plancha»

Proyecto Intermodular 1 · 1º ASIR. Sistema de punto de venta (TPV) para sala y de pantallas de cocina (KDS) que se comunican en tiempo real.

## Arquitectura

```
 Tablet/PC sala ──┐                     ┌── Pantalla Plancha
 (tpv.html)       │  HTTP REST + WS     │── Pantalla Freidora
                  ├──────► FastAPI ◄────┤── Pantalla Fríos
 Encargado ───────┘   (uvicorn :8090)   │── Pantalla Barra
 (informe.html)             │           └── Pase (todas)
                        MariaDB
                    (kds_tpv, socket)
```

- **Backend:** Python 3.12, FastAPI y PyMySQL. Expone una API REST y un WebSocket `/ws` que avisa a todas las pantallas cuando hay cambios.
- **Base de datos:** MariaDB. Los importes se guardan en céntimos (enteros) y el precio se congela en cada línea en el momento de la venta. El IVA es el 10 % de hostelería, incluido en el precio.
- **Frontend:** HTML, CSS y JavaScript sin frameworks, pensado para pantallas táctiles. El ticket y la factura se ven en la propia pantalla.
- **Sistema:** servicio `systemd --user` con reinicio automático, en Linux Mint 22.3.

## Aplicaciones

La portada es el **menú principal**, con el trabajo pendiente de cada estación en vivo:

| App | Para qué sirve |
|---|---|
| TPV | Mesas, comandas, cobro y documento del pedido |
| Facturación | Cobros del día, emisión de facturas y consulta de las emitidas |
| KDS (×4 + pase) | Pantallas de cocina por estación |
| Informe | Cierre de caja del día |
| Carta | Productos, precios, categorías, alérgenos y agotados |
| Usuarios | Altas, bajas, cambio de rol y de PIN |
| Ajustes | Datos fiscales del local, IVA y minutos de aviso del KDS |
| API | Documentación OpenAPI generada sola |

## Ticket y factura: sin impresora

El sistema **nunca llama a la impresora del sistema operativo**. El documento se dibuja en pantalla
tal y como saldría en papel (40 columnas) y se puede descargar como `.txt`. Imprimirlo, si hace
falta, es una decisión de la persona desde su navegador.

- **Ticket:** resumen del pedido, sin validez fiscal.
- **Factura simplificada:** numerada, sin datos del cliente.
- **Factura completa:** exige NIF y nombre; añade también la dirección.

La numeración es `A<año>/<5 dígitos>`, correlativa y sin huecos: se calcula dentro de la transacción
con `SELECT MAX(numero)+1 … FOR UPDATE`, y cada pedido solo puede tener una factura (`UNIQUE`), así
que repetir la petición devuelve la misma factura en lugar de duplicarla.

## Flujo de una comanda

1. El camarero entra con su PIN, elige una mesa (o «para llevar») y añade productos. Un clic derecho o una pulsación larga permite añadir notas.
2. Con **Enviar a cocina**, cada línea pasa a `enviada` y va a la pantalla de su estación.
3. En cocina, **Empezar** la pasa a `preparando`, **Listo** a `lista` (el TPV recibe el aviso) y **Servido** a `servida`. Si se toca una línea, avanza solo esa.
4. Se cobra entero, **dividido en partes iguales** o **por líneas**, y con varios métodos en el mismo pedido (mitad tarjeta, mitad efectivo). El pedido se cierra solo cuando lo pagado alcanza el total; mientras siga abierto, un pago se puede deshacer. Al cerrarse aparece el ticket en pantalla, desde el que se emite la factura.
5. El **informe** muestra la facturación, la base imponible y el IVA, los productos más vendidos, las ventas por hora y el tiempo medio de cocina de cada estación.

Las comandas se ponen en amarillo a los 8 minutos y en rojo, parpadeando, a los 15.

## Instalación (Mint)

```bash
sudo mariadb < deploy/00_crear_bd.sql   # una vez: crea la BD y da permisos
sudo loginctl enable-linger roca        # una vez: el servicio sigue vivo sin sesión abierta
bash deploy/instalar.sh                 # venv, esquema, datos de ejemplo y servicio
bash deploy/instalar.sh --reset-bd      # vuelve a los datos de ejemplo
```

## Demo

- Portada: `http://<ip-mint>:8090/`
- PIN de prueba: Laura `1111`, Marc `2222` (camareros), Pau `9999` (encargado).
- Servicio simulado:

```bash
backend/.venv/bin/python backend/simulador.py --rapido
```

  Con `--sin-cocina`, una persona lleva la cocina desde el KDS.
- API documentada automáticamente en `/docs` (OpenAPI).

## Estructura

```
backend/app/main.py      API REST + WebSocket
backend/app/db.py        conexión MariaDB
backend/sql/             esquema y datos de ejemplo
backend/simulador.py     generador de servicio para la demo
frontend/                tpv, kds, informe (estáticos)
deploy/                  SQL de alta, unit systemd, instalador
```

## Cuentas divididas

`pagos` admite varias filas por pedido y cada línea puede quedar enganchada al pago que la liquidó
(`lineas_pedido.pago_id`), así que una línea no se cobra dos veces. El servidor rechaza pagar más de
lo que queda pendiente y solo marca el pedido como cobrado cuando la suma de los pagos alcanza el
total.

## Carta editable

La carta se mantiene desde la propia aplicación: crear y editar productos y categorías, cambiar
precios, apuntar alérgenos y marcar **agotado** (sigue en la carta, pero el TPV no lo deja pedir) o
dar de **baja** (desaparece de la carta; los pedidos antiguos lo conservan). Los cambios llegan a
los TPV abiertos por WebSocket, sin recargar.

## Mejoras pendientes

En [docs/PENDIENTES.md](docs/PENDIENTES.md).

## Límites conocidos (mejoras futuras)

- El PIN identifica al empleado, pero la API no exige token. Es aceptable en una LAN cerrada, no en Internet.
- No hay HTTPS. En producción iría detrás de nginx con TLS.
- No hay control de stock ni facturación Verifactu.
