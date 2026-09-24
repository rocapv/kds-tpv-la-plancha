# Análisis de la competencia · Oracle MICROS Simphony

El líder mundial del punto de venta en hostelería, y el que faltaba en la tabla de doce productos
de [INFORME_MERCADO.md](INFORME_MERCADO.md). Se estudia aparte porque no juega en la misma liga:
no es un competidor más, es **la referencia del sector**, y sirve para medir lo que este proyecto
hace igual, lo que hace distinto y —sobre todo— lo que no hace.

Consultado el 24 de septiembre de 2026. Cada cifra lleva su fuente; lo que no se ha podido
verificar se dice.

---

## 1. Quién hay detrás

Simphony no nació en Oracle. Es el producto de **MICROS Systems**, una empresa de terminales para
hostelería que Oracle compró en 2014.

| Dato | Valor | Fuente |
|---|---|---|
| Anuncio de la compra | 23 de junio de 2014 | [Oracle Buys MICROS Systems](https://www.oracle.com/corporate/pressrelease/oracle-buys-micros-systems-062314.html) |
| Precio | **68,00 $ por acción · ~5.300 millones de dólares** (4.600 M$ netos de caja) | Ídem |
| Empleados de MICROS entonces | **más de 6.600** | Ídem |
| Implantación entonces | **330.000 sitios de clientes en 180 países** | Ídem |
| Empleados de Oracle hoy | **~141.000 a jornada completa** (49.000 en EE. UU. y 92.000 fuera), frente a 162.000 un año antes | [Oracle, formulario 10-K FY2026](https://www.sec.gov/Archives/edgar/data/0001341439/000119312526277521/orcl-20260531.htm) (ejercicio cerrado el 31/05/2026) |
| Ingresos de Oracle FY2026 | **67.357 millones de dólares** (+17,35 % sobre FY2025) | [Macrotrends sobre los estados financieros de ORCL](https://www.macrotrends.net/stocks/charts/ORCL/oracle/revenue) |
| Reparto por área | ~43.000 en I+D · 34.000 en servicios · 26.000 en nube y software · 25.000 en ventas y marketing | Oracle 10-K FY2026 |

**La comparación que interesa para la memoria**: la plantilla de I+D de Oracle (~43.000 personas)
es, ella sola, mayor que la población de muchos municipios; el equipo de MICROS en el momento de
la compra (6.600) era mayor que toda la plantilla de la mayoría de empresas españolas de TPV. Este
proyecto lo ha hecho **una persona**, y son 8.928 líneas de código.

Eso no significa que el producto grande sea mejor para el caso de uso de este proyecto. Significa
que compiten en cosas distintas, y conviene decir en cuáles.

---

## 2. Cómo funciona su KDS

La documentación oficial de Oracle describe una arquitectura de **tres piezas** para la cocina
([Kitchen Display System Controller](https://docs.oracle.com/en/industries/food-beverage/simphony/simcm/t_shared_services_overview_kdsc.htm)):

```
POS clients ──► KDS shared service ──► KDS Controller (servicio Windows) ──► KDS Displays
                (en el «service host»)
```

Textualmente: *«When an order is sent to the kitchen, POS clients send data to the KDS shared
service running on the designated service host. The KDS shared service forwards the information to
the KDS Windows service, which then manages the communication to and from the KDS clients.»*

Cuatro detalles de esa arquitectura, todos de la misma fuente:

- El **KDS Controller** es *«the bridge between the POS and KDS clients»*: es quien lleva la lógica
  de negocio de la cocina, no las pantallas.
- Relación **uno a uno** entre el *shared service* de Simphony y el servicio Windows del controlador.
- Un local puede tener **más de un controlador**, útil *«when there are revenue centers with
  independent kitchens»* (varias cocinas independientes).
- El controlador principal y el de respaldo **no pueden vivir en el mismo hardware**.

Además, Oracle vende el KDS como pieza que ordena el trabajo por estaciones, con pantallas táctiles,
*bump bars* (barras de botones físicas) y vistas remotas, y que recoge pedidos de varios canales a
la vez: sala, quiosco de autoservicio, *drive-thru*, web, aplicación móvil y plataformas de reparto
de terceros ([Oracle · KDS](https://www.oracle.com/food-beverage/restaurant-pos-systems/kds-kitchen-display-systems/)).

### Lo que esa arquitectura implica

| Decisión de Oracle | Consecuencia práctica |
|---|---|
| El controlador es un **servicio Windows** | Hace falta al menos un equipo Windows encendido en el local, con su licencia y su mantenimiento |
| La lógica vive en el controlador, no en la pantalla | Las pantallas son clientes: si cae el controlador, la cocina se queda a oscuras |
| Redundancia = **otro hardware** | La alta disponibilidad se compra con una segunda máquina |
| Varias cocinas = varios controladores | El coste crece con la complejidad del local, no solo con el número de pantallas |

---

## 3. Cuánto cuesta

Oracle **no publica tarifa completa**: el precio se cotiza. Lo que se ha podido encontrar con fuente
identificable, en dólares y para el mercado estadounidense (no trasladable a España sin más):

| Concepto | Importe | Fuente |
|---|---|---|
| Simphony Essentials | **desde 55 $/mes** (locales pequeños) | [Loman · Micros Pricing](https://loman.ai/blog/micros-pricing) |
| Simphony Plus | **desde 75 $/mes** (multi-local) | Ídem |
| Terminal completo | **2.500 – 8.000 $** | Ídem |
| Instalación y puesta en marcha | **500 – 8.000 $** | Ídem |
| Comisión de pagos | **2,4 % – 2,9 % por transacción** | Ídem |
| KDS | **módulo aparte, con coste adicional**; importe no publicado | [TrustRadius · Oracle Simphony pricing](https://www.trustradius.com/products/oracle-simphony/pricing) |

La cuota es **por estación**. Es exactamente el patrón que el informe de mercado señala como la
grieta del sector: *un local con cuatro estaciones de cocina paga cuatro veces*.

---

## 4. Frente a este proyecto

| Asunto | Oracle MICROS Simphony | Este proyecto |
|---|---|---|
| Pantalla de cocina nueva | Módulo facturable + hardware | **Una pestaña más del navegador**: coste 0 |
| Dónde corre la lógica de cocina | Servicio **Windows** en un equipo del local | El mismo servicio que ya sirve el TPV (una Raspberry Pi) |
| Alta disponibilidad | Segundo controlador en **otro hardware** | No la hay: es un local, no un aeropuerto |
| Canales de entrada | Sala, quiosco, *drive-thru*, web, móvil y plataformas de reparto | Sala y móvil del cliente por QR |
| Sin conexión | El TPV aguanta sin red (capacidad *offline* del cliente) | El TPV aguanta **y además** lo reenvía sin duplicar (clave de idempotencia) |
| Datos | En la nube de Oracle | En el local, en su MariaDB |
| Precio | Cotización; cuota por estación y comisión por pago | El coste del Pi y la luz |
| Soporte | 24/7 mundial, 180 países | El autor del proyecto |
| Fiscalidad | Multipaís | Solo España (IVA, RD 1619/2012) |

### Lo honesto: lo que Oracle hace y aquí no está

No reconocerlo sería vender humo delante del tribunal.

1. **Multi-local de verdad**: carta centralizada, precios por zona, consolidación de ventas de
   cientos de establecimientos.
2. **Integración con plataformas de reparto**, que hoy es por donde entra buena parte de la
   facturación de muchos locales.
3. **Soporte 24/7 y responsabilidad contractual**: si a las tres de la mañana falla el TPV, hay un
   teléfono. Aquí no.
4. **Fiscalidad de 180 países** y certificaciones que este proyecto no tiene ni pretende.
5. **Cuarenta años de casos límite** ya resueltos: propinas repartidas, turnos partidos, *drive-thru*
   con dos ventanillas, pantallas de 42 pulgadas con *bump bar* físico…

### Lo que este proyecto hace y ahí cuesta dinero

1. La **pantalla número cinco** no cuesta licencia: cuesta lo que cuesta la pantalla.
2. **Sin Windows**: el navegador de cualquier tableta vale, incluso una de 60 €.
3. **Los datos no salen del local**: ni nube, ni cuota, ni dependencia de que el proveedor siga
   existiendo dentro de cinco años.
4. **El código es auditable** por quien lo compra, que es justo lo que un instituto necesita para
   enseñarlo.

---

## 5. Qué se ha copiado (y qué no)

Del estudio de Simphony se ha adoptado **una idea**: que la lógica de la cocina viva en el servidor
y las pantallas sean clientes tontos. Es lo que permite que una tableta de 60 € haga de KDS y que
apagarla no pierda nada.

No se ha copiado el **modelo de despliegue**: un servicio Windows por cocina, con su equipo, su
respaldo en otra máquina y su licencia, es una respuesta para una cadena con mil locales; para una
cantina de trece mesas es el problema, no la solución.
