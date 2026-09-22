# KDS + TPV · Cantina «Vesta-9»

Proyecto Intermodular 1 · 1º ASIR. Sistema de punto de venta (TPV) para sala y de pantallas de cocina (KDS) que se comunican en tiempo real.

El local es una cantina de la estación minera **Vesta-9**, excavada dentro de un asteroide: el
decorado (nombre, carta, rótulos de las zonas y paleta de color) vive en `sql/06_tema_asteroide.sql`
y en el bloque final de `frontend/css/estilo.css`, separado de la lógica.

## Arquitectura

```
 Tablet/PC sala ──┐                     ┌── Pantalla Placa térmica
 (tpv.html)       │  HTTP REST + WS     │── Pantalla Fritura
                  ├──────► FastAPI ◄────┤── Pantalla Cámara fría
 Encargado ───────┘   (uvicorn :8090)   │── Pantalla Barra
 (informe.html)             │           └── Pase (todas)
                        MariaDB
                    (kds_tpv, socket)
```

- **Backend:** Python 3.12, FastAPI y PyMySQL. Expone una API REST y un WebSocket `/ws` que avisa a todas las pantallas cuando hay cambios.
- **Base de datos:** MariaDB. Los importes se guardan en céntimos (enteros) y el precio se congela en cada línea en el momento de la venta. El IVA es el 10 % de hostelería, incluido en el precio.
- **Frontend:** HTML, CSS y JavaScript sin frameworks, pensado para pantallas táctiles. El ticket y la factura se ven en la propia pantalla.
- **Seguridad:** sesiones con token (el PIN solo viaja al entrar), roles comprobados en el servidor y **HTTPS** en todo el tráfico, incluido el WebSocket.
- **Sistema:** tres servicios `systemd --user` con reinicio automático, en Linux Mint 22.3.

## Aplicaciones

La portada es el **menú principal**, con el trabajo pendiente de cada estación en vivo:

| App | Para qué sirve |
|---|---|
| TPV | Mesas, comandas, cobro y documento del pedido |
| Facturación | Cobros del día, emisión de facturas y consulta de las emitidas |
| KDS (×4 + pase) | Pantallas de cocina por estación |
| Informe | Ventas del día: facturación, más vendidos y tiempos de cocina |
| Arqueo | Fondo, movimientos de efectivo, descuadre y cierre Z |
| Carta | Productos, precios, categorías, alérgenos y agotados |
| Usuarios | Altas, bajas, cambio de rol y de PIN |
| Recogida | Pantalla de sala con los números «para llevar» listos (pública, sin PIN) |
| Ajustes | Datos fiscales del local, IVA y minutos de aviso del KDS |
| API | Documentación OpenAPI generada sola |
| **Carta del cliente** | `cliente.html` · pública, en el móvil del cliente tras el QR de la mesa |

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
5. Al terminar el servicio, el **arqueo** cuenta el cajón y firma el cierre Z.
6. El **informe** muestra la facturación, la base imponible y el IVA, los productos más vendidos, las ventas por hora y el tiempo medio de cocina de cada estación.

Las comandas se ponen en amarillo a los 8 minutos y en rojo, parpadeando, a los 15.

## Pantalla de recogida

`recogida.html` se cuelga en la sala para los pedidos **para llevar**: dos columnas, «Listos» y «En
preparación», con el número del pedido en grande y el tiempo de espera. Un número pasa a «Listos»
en cuanto cocina marca la comanda como lista, y desaparece al marcarla como servida (entregada).

Es la única pantalla sin PIN, porque la ve el cliente. Para que no filtre nada usa una API y un
WebSocket propios (`GET /api/recogida` y `/ws/publico`) que solo devuelven números y tiempos: ni
nombres, ni productos, ni importes. El aviso del WebSocket público no lleva datos, solo dice
«vuelve a mirar», y cada 30 segundos se refresca igualmente por si se perdió algún aviso.

## Seguridad

**Sesiones.** `POST /api/login` es el único sitio por donde pasa el PIN: devuelve un token que se
guarda en la tabla `sesiones` (así un reinicio del servicio no echa a nadie a media comanda) y que
viaja en `Authorization: Bearer …` en cada petición. El WebSocket también lo exige y cierra con el
código 4401 si no vale. Las sesiones caducan a las 12 h (ajustable en Ajustes) y el encargado puede
ver y cerrar las sesiones abiertas.

**Roles, comprobados en el servidor** (no en el navegador):

| Rol | Puede |
|---|---|
| camarero | mesas, pedidos, cobros, facturas y documentos |
| cocina | pantallas KDS y avance de comandas |
| encargado | todo lo anterior + usuarios, carta, ajustes e informes |

Cada pantalla pide el PIN si no hay sesión, y avisa si el rol no es el que toca.

**Solo red local.** El servidor no atiende a nadie de fuera del local, en dos capas:
el servicio escucha **solo en la IP de la LAN** (`KDS_BIND` en la unit, ni siquiera abre el
puerto en otras interfaces) y, dentro, una guarda rechaza con 403 cualquier cliente que no esté
en las redes de `KDS_REDES`. La guarda mira la IP real de la conexión, nunca `X-Forwarded-For`,
que la escribe quien llama. El WebSocket cierra con el código 4403.
Cuando se dispone de root, `sudo bash deploy/cortafuegos.sh` añade la capa que de verdad importa:
ufw con todo denegado salvo 22, 8443 y 8090 desde la red del local, y MariaDB cerrada a cal y canto.

**HTTPS.** El tráfico va cifrado en el puerto **8443**; el 8090 solo devuelve un 301 hacia él, para
que ninguna pantalla vieja siga tecleando PIN sobre HTTP. En el aula el TLS lo termina el propio
uvicorn, porque no hay root para instalar nginx; `deploy/nginx-kds-tpv.conf` deja la configuración
de nginx lista (con las cabeceras del WebSocket y HSTS) para la máquina donde sí se tenga.
El certificado es autofirmado (`deploy/certificado.sh`, con la IP en `subjectAltName`), así que la
primera vez el navegador avisa: es lo esperado en una demo de aula.

## Instalación (Mint)

```bash
sudo mariadb < deploy/00_crear_bd.sql   # una vez: crea la BD y da permisos
sudo loginctl enable-linger roca        # una vez: los servicios siguen vivos sin sesión abierta
bash deploy/instalar.sh                 # venv, BD, certificado y servicios
bash deploy/instalar.sh --reset-bd      # vuelve a los datos de ejemplo
```

Servicios que quedan instalados:

| Unidad | Qué hace |
|---|---|
| `kds-tpv.service` | la aplicación, HTTPS en el 8443 |
| `kds-tpv-http.service` | 301 del 8090 al 8443 |
| `kds-mariadb.service` | solo si no hay root: MariaDB del usuario |

## Demo

- Portada: `https://<ip-mint>:8443/` (el 8090 redirige)
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
backend/sql/             esquema, datos de ejemplo y ampliaciones (01…16)
backend/pruebas/         pytest (API, arqueo y modo sin red)
backend/simulador.py     generador de servicio para la demo
frontend/                tpv, kds, informe (estáticos)
frontend/js/sinred.js    modo sin red del TPV: cola en IndexedDB y reenvío
frontend/sw.js           copia del TPV para poder abrirlo sin servidor
deploy/                  SQL de alta, unit systemd, instalador, QA
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

## Alérgenos

Lo que el encargado apunta en la carta viaja con el producto hasta donde hace falta: el botón del
TPV lo lleva debajo del nombre, el diálogo de la nota lo repite antes de confirmar la comanda, cada
línea del ticket lo arrastra y la pantalla de cocina lo enseña en rojo junto al plato. Vaciar el
campo en la carta lo borra de verdad (un `null` explícito), para que nadie sirva con un dato viejo.

## La sala mientras ocurre

El KDS mide la cocina y el arqueo mide el dinero al cerrar. Faltaba lo que vive el cliente, y
resulta que casi todo estaba ya fechado en la base de datos: solo hacía falta un dato que nadie
apuntaba, **cuántos se sientan en la mesa**, que ahora se marca en el TPV con un toque.

**Sala en vivo** (`sala.html`) enseña ocupación —mesas, comensales y media por mesa— y, sobre todo,
**quién está esperando**. Las alertas no miran el reloj del plato sino el del cliente:

| Aviso | Salta cuando |
|---|---|
| Sin tomar nota | la mesa lleva sentada más de 6 min y nadie le ha pedido la comanda |
| Listo en el pase | hay platos listos que nadie recoge desde hace 5 min |
| Cuenta sin cobrar | todo está servido y la cuenta sigue abierta desde hace 8 min |

Los tres umbrales se ajustan en Ajustes, porque una cantina de menú y un local de sobremesa larga
no esperan lo mismo. Un plato puede salir en seis minutos y el cliente llevar veinte esperando: eso
es justo lo que esta pantalla saca a la luz.

**Tiempos de la visita** (en el informe): sentarse → tomar nota → cocina → comer y pagar, más las
cinco visitas más lentas del día con su camarero. Sale de marcas de tiempo que ya existían; no hubo
que registrar nada nuevo.

## En el móvil

Dos pantallas están pensadas para el teléfono, no adaptadas a él:

- **El TPV del camarero.** En pantallas de menos de 800 px el ticket deja de ser una columna y pasa a
  ser una hoja que sube desde abajo: plegada enseña el total y los botones, y se despliega tocando el
  tirador. Los botones pasan a 46 px de alto para que se acierte con el dedo mientras se anda.
- **La carta del cliente** (`/cliente.html?mesa=3`). Sin instalar nada y sin PIN: la abre el cliente
  al leer el QR de su mesa.

## El cliente pide desde su mesa

El cliente ve la carta, añade a su cesta y envía la comanda. **Lo que envía no llega a cocina**: entra
en una bandeja del TPV, y un camarero la acepta o la rechaza. Esa frontera es deliberada: el QR de una
mesa no puede ser una puerta abierta a la cocina. Al aceptarla se convierte en un pedido normal, y si
la mesa ya tenía uno abierto se le suma.

El cliente sigue su propia comanda desde el teléfono —pendiente, aceptada, y qué lleva cocina— y no ve
nada más: la carta pública no expone estaciones, ni empleados, ni pedidos ajenos. Hay un freno de tres
solicitudes sin resolver por mesa, para el niño que se aburre pulsando.

Se puede apagar entero desde Ajustes (`cliente_pedidos`), dejando la carta como simple consulta.

## Copias de seguridad

Completa semanal + **incremental por binlogs** cada hora de servicio, con poda automática a
cuatro semanas. El incremental no repite la base entera: guarda solo el registro binario de lo
que ha cambiado, así que un día de servicio ocupa kilobytes y permite recuperar hasta el último
minuto antes del fallo.

```bash
deploy/copia.sh completa       # volcado íntegro y punto de partida
deploy/copia.sh incremental    # binlogs nuevos desde la última completa
deploy/copia.sh estado         # qué hay guardado y cuándo se probó por última vez
deploy/restaurar.sh probar     # restaura en kds_tpv_prueba y compara filas e importes
```

`restaurar.sh probar` corre solo cada semana con un temporizador: compara tabla por tabla y, además,
el total cobrado. Una copia que nunca se ha restaurado no es una copia, es un fichero.

| Temporizador | Cuándo |
|---|---|
| `kds-copia-completa.timer` | lunes 05:30 |
| `kds-copia-incremental.timer` | cada hora, de 09:00 a 23:55 |
| `kds-copia-prueba.timer` | lunes 06:15 |

## Pruebas y despliegue

62 pruebas con `pytest` sobre una base de datos de pruebas que se crea y se destruye sola, nunca
contra la real. Cubren lo que debe funcionar y, sobre todo, lo que debe fallar: cobros, cuentas
divididas, numeración de facturas, estados de cocina, permisos por rol, congelación de precios,
el arqueo de caja con su cierre Z y el reenvío de lo apuntado sin red (que no duplique nada).

```bash
cd backend && .venv/bin/python -m pytest      # las pruebas
bash deploy/desplegar.sh                      # copia → pruebas → reinicio → comprobación
```

Si una prueba falla, el despliegue se aborta y el servicio sigue con la versión anterior.

## Arqueo de caja y cierre Z

El informe dice lo que se ha vendido; el arqueo dice si el dinero está. El día empieza abriendo la
caja con su **fondo de cambio** y termina contando el cajón:

```
esperado   = fondo + ventas en efectivo + entradas - salidas
descuadre  = contado - esperado          (negativo = falta dinero)
```

Las **entradas y salidas** son el efectivo que se mueve sin ser una venta (pagar al del pan, reponer
cambio, retirar al banco); sin ellas el descuadre mentiría. El recuento se teclea por billetes y
monedas y el servidor rechaza el cierre si el desglose no cuadra con el efectivo declarado.

El **cierre Z** es correlativo (`Z<año>/<5 dígitos>`, con el mismo `FOR UPDATE` que las facturas),
congela las cifras del día, guarda el descuadre y queda firmado con el nombre del encargado y la
hora. No se puede repetir ni deshacer, y no se cierra con pedidos sin cobrar salvo que el encargado
lo fuerce a conciencia. Como el ticket y la factura, el documento se ve en pantalla y se descarga
como `.txt`: **nunca** se llama a la impresora del sistema.

El histórico de cierres enseña de un vistazo si el descuadre es un día suelto o una costumbre.

## Simulación de actividad (demo)

Al lado de **Salir**, el encargado tiene tres mandos: **▶** pone en marcha un servicio simulado
(clientes que entran, cocina que avanza, caja que cobra), **⏸** lo congela donde esté y **⟲** lo
para y borra lo que la simulación creó. Es el `simulador.py` de siempre, pero dentro del servicio y
llamando a las mismas funciones de la API que usan las pantallas, así que también ejerce el backend.

Dos cautelas para que la demo no se coma datos de verdad: la simulación **solo avanza en cocina sus
propias comandas**, y el **reset borra únicamente los pedidos anotados en su rastro**
(`~/.local/share/kds-tpv/simulacion.json`, que sobrevive a un reinicio del servicio). Los mandos
son de rol `encargado`; a un camarero la API le responde 403.

## Quién está dónde: el plano de la cantina

En **Usuarios → Mapa de la cantina** el encargado arrastra la ficha de cada persona al puesto
donde trabaja ese turno. El puesto no es decorado: decide **a qué pantalla entra** al teclear el
PIN y **qué le deja hacer el servidor**.

| Puesto | Pantalla | Trabaja como |
|---|---|---|
| Comedor presurizado · Mirador · Atraque | `tpv.html` | camarero |
| Caja | `facturas.html` | camarero |
| Placa térmica · Fritura · Cámara fría · Barra de oxígeno · Pase | `kds.html` (su estación) | cocina |
| Recogida | `recogida.html` | cocina |
| Oficina | menú | — (gestión, por rol) |
| Fuera de servicio (o ficha fuera de las cajas) | menú | nadie: la API contesta 403 |

Encima del plano hay un botón **«Repartir automáticamente»** (`POST /api/plantilla/reparto`):
coloca a cada persona en un puesto de su rol, por turnos, para que no se amontonen todos en la
misma caja — camareros al comedor, mirador, atraque y caja; cocina repartida entre las estaciones,
el pase y la recogida; el encargado a la oficina. Es el punto de partida para abrir el servicio;
después se arrastra lo que haga falta.

Así, un camarero puesto en la placa térmica trabaja de cocina sin tocarle el rol, y al volver al
comedor vuelve a cobrar. La comprobación es del servidor (`exige()` en `auth.py`), no del
navegador: mover la ficha de alguien con la sesión abierta le cambia la pantalla al vuelo por el
WebSocket. Dos cautelas: **la gestión** (carta, usuarios, ajustes, informes, arqueo) sigue pidiendo
**rol encargado de verdad**, para que nadie se deje a sí mismo fuera moviendo su ficha; y el puesto
gobierna lo que se **hace**, no lo que se **mira** (los contadores del menú siguen siendo de lectura
para cualquier sesión válida).

## Plano del local en 2D

`plano.html` dibuja el local visto desde arriba: muros, puertas, zonas (comedor, mirador,
atraque, cocina, oficina, recogida), las mesas —enlazadas a la tabla `mesas`, así que una mesa
ocupada se ve en rojo— y los equipos de cocina, cada uno atado a su sección. Encima se pintan las
fichas del personal que esté colocado en el plano de puestos.

De encargado para arriba hay modo edición: se arrastra cada pieza, se estira por la esquina y se
quita con **Supr**; «Regenerar» vuelve a dibujar un local de partida y reparte las mesas por su
zona. **La regla del muro la aplica el servidor**: lo que ocupa sitio —mesas, barra y equipos— no
se puede guardar dentro de una pared, y si se intenta, la pieza vuelve a su sitio.

## Escalafones y contraseñas

La posición en la empresa (`escalafones`) es distinta del puesto de cocina y del rol del turno:
`1 Administrador · 2 Gerente · 3 Encargado · 4 Empleado base · 5 Empleado base junior`. **A menor
número, más mando**, para que la plantilla pueda crecer por abajo (6, 7, 8…) sin renumerar nada.
El junior es el primer año; el base cobra un 5 % más.

Quien entra en la gestión lo decide la bandera `gestion` del escalafón, no el rol. La nómina y el
reparto de escalafones son de gerencia. Cada empleado tiene número (la PK), nombre y apellidos,
PIN de cuatro cifras para las pantallas y **contraseña** para entrar por número de empleado; la
contraseña se guarda con pbkdf2-sha256 y sal, y solo se enseña en claro al generarla.

## Simulación con bots por área

Los mandos **▶ ⏸ ⟲** de la barra levantan **un bot por área**: uno en cada puesto de sala, que
solo sienta gente en su zona, y uno en cada sección de cocina, que solo avanza sus líneas — con la
persona que el encargado haya puesto en el plano. Además, la caja cobra un ticket cada diez
segundos pase lo que pase, para que el informe y el arqueo se muevan durante la demo. El **reset**
borra solo lo que la simulación creó.

## Sin red: se sigue tomando nota

Si se cae el wifi, el TPV no se para. **Sin red se toma nota; con red se cobra.**

- Se puede: abrir mesa, añadir y quitar líneas, comensales y mandar la comanda a cocina (saldrá
  al volver la red). Una barra amarilla lo dice mientras dure el corte.
- No se puede: cobrar, facturar ni arquear. La numeración de tickets y facturas es del servidor;
  dos tabletas desconectadas emitirían el mismo número.
- La pantalla se abre aunque no haya servidor (`frontend/sw.js` guarda HTML, CSS y JS del TPV) y
  lo apuntado aguanta recargas y cierres del navegador (IndexedDB).
- Al volver la red se reenvía solo, en orden. **Nada se duplica**: cada acción lleva una clave de
  idempotencia (`Idempotency-Key`) y el servidor, si la ve repetida, devuelve la respuesta que ya
  dio en vez de volver a ejecutarla (`backend/sql/16_idempotencia.sql`).
- Lo que el servidor rechace al reenviar (mesa ya cobrada, producto agotado) se descarta y se
  **dice en pantalla**, con su motivo.

```bash
python deploy/qa_sinred.py --url https://192.168.1.105:8443   # corta la red de verdad y comprueba
```

Dos condiciones: **el certificado tiene que estar confiado en la tableta** (si no, el navegador no
registra el trabajador de servicio y el TPV solo aguanta el corte con la pantalla ya abierta) y
**empezar el turno exige red**, porque el PIN lo valida el servidor.

## Despliegue en RASPA (home.pr1.es) — 22/09/2026

El sistema **vive ahora en Raspa** (Raspberry Pi, Debian 13). Piezas:

| Pieza | Dónde |
|---|---|
| Código | `/home/roca/kds_tpv` |
| Base de datos | MariaDB **del sistema**, base `kds_tpv`, usuario `roca` por socket (sin contraseña escrita) |
| API | `kds-tpv.service` → uvicorn en **127.0.0.1:8092**, sin puerto abierto a la red |
| Pantallas | **document root de Apache** (`/var/www/html`), publicadas con `deploy/raspa/publicar.sh` |
| Nombres | `http://192.168.1.100/` (solo LAN) y **`https://home.pr1.es`** (abierto a internet) |

```bash
# publicar cambios del frontal (pone el sello de versión en las páginas)
bash deploy/raspa/publicar.sh
# recargar la API
sudo systemctl restart kds-tpv
```

Tres cosas que cuestan una tarde si no se saben:

1. **`/api` ya tenía dueño en Raspa.** `sites-enabled/director-ocr.conf` declara un `<Location /api/>`
   FUERA de todo vhost, así que se lleva el `/api` de *todos* los sitios a la API OCR del Director.
   Se le gana con otro `<Location /api/>` dentro del vhost del KDS; un `ProxyPass` suelto no basta.
2. **uvicorn trae `--proxy-headers` activado.** Detrás de Apache, la aplicación ve la IP REAL del
   navegante (no la del proxy), así que la lista `KDS_REDES` decide quién entra de verdad.
3. **El frontal lo sirve Apache, que no sustituye `__V__`.** El sello de versión lo pone
   `publicar.sh` al copiar; si se copia a mano, el navegador se queda con el JavaScript viejo.

### Abierto a internet

Por decisión expresa (22/09/2026), `home.pr1.es` atiende a cualquiera: `KDS_REDES=0.0.0.0/0,::/0`.
HTTPS con certificado de Let's Encrypt (renovación automática por webroot) y el `:80` redirige.
**El PIN de 4 cifras no tiene límite de intentos**: expuesto a internet, eso son 10.000
combinaciones al alcance de un robot. Para volver a cerrarlo basta con poner
`KDS_REDES=127.0.0.0/8,192.168.1.0/24` en `deploy/raspa/kds-tpv.service`.

### Raspa se actualiza sola

No se despliega a mano: **se commitea y se sube**. Un temporizador de systemd mira la rama
`ASIR-KDS-TPV` cada 5 minutos y, si hay algo nuevo, lo pone en marcha.

```
git push            →   kds-actualiza.timer (cada 5 min)
                         └─ git merge --ff-only
                            ├─ dependencias      (si cambió requirements)
                            ├─ pruebas           (si cambió backend/) ─── fallan → vuelve atrás
                            ├─ esquema           (ampliaciones que falten, migrar.sh)
                            ├─ pantallas         (publicar.sh, con su sello de versión)
                            └─ reinicio de la API (si cambió backend/app)
```

```bash
sudo systemctl start kds-actualiza.service     # traerlo ya, sin esperar
journalctl -u kds-actualiza -n 40 --no-pager   # qué hizo la última vez
systemctl list-timers kds-actualiza            # cuándo vuelve a mirar
```

Lo que **no** hace solo, y por qué:

- **No pisa trabajo sin commitear.** Si en Raspa hay cambios a medias, se para y lo dice: quien
  esté editando ahí no se encuentra el fichero reescrito a mitad de frase.
- **No fuerza la rama.** Solo avanza en línea recta; un historial divergido lo mira una persona.
- **No instala los vhosts de Apache.** Esa máquina también sirve Jellyfin, el Director y demás:
  cambiar su configuración no puede ser un efecto secundario de un `git push`. Avisa y ya.
- **No ejecuta `01_schema.sql` ni `02_seed.sql` jamás.** El primero empieza con `DROP TABLE` y el
  segundo son datos de ejemplo. Las demás ampliaciones se aplican una vez y quedan apuntadas en
  la tabla `migraciones`.

Si algo falla —pruebas, esquema o la API que no responde— vuelve al commit anterior, republica y
reinicia: el local se queda con la versión que se sabe que funcionaba.

La credencial es una **clave de despliegue de solo lectura** (`~/.ssh/kds_deploy_ed25519`,
registrada en GitHub como `raspa-autodespliegue`): Raspa puede leer el repo, no escribirlo.

## Mejoras pendientes

En [docs/PENDIENTES.md](docs/PENDIENTES.md).

## Límites conocidos (mejoras futuras)

- El certificado es autofirmado: vale para la LAN del aula, no para Internet.
- El PIN de 4 cifras es cómodo en barra pero débil; no hay límite de intentos ni segundo factor.
- No hay control de stock ni facturación Verifactu.
- Sin red la carta que se ve es la de la última conexión; el precio definitivo lo pone el
  servidor al reenviar la comanda.
