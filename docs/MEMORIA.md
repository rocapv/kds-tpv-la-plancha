# Sistema KDS + TPV para hostelería «La Plancha»

**Proyecto Intermodular 1 · 1º CFGS Administración de Sistemas Informáticos en Red**
Autor: RocaPV · Septiembre de 2026

---

## Abstract

**English.** This project builds and deploys a complete point-of-sale (POS) and kitchen display
system (KDS) for a small burger restaurant. Waiting staff take orders on a touch screen, each line
is routed in real time to the kitchen station that cooks it, and payment supports split bills and
mixed payment methods. The system issues tickets and sequentially numbered invoices on screen,
without depending on a printer. It runs as three systemd services on a Linux server over HTTPS,
with token-based sessions and server-side role checks.

**Valencià.** Aquest projecte construeix i desplega un sistema complet de punt de venda (TPV) i de
pantalles de cuina (KDS) per a una hamburgueseria xicoteta. El personal de sala pren la comanda en
una pantalla tàctil, cada línia arriba en temps real a l'estació que la cuina, i el cobrament admet
comptes dividits i pagaments mixtos. El sistema emet tiquets i factures numerades en pantalla, sense
dependre d'una impressora. Funciona com tres serveis de systemd en un servidor Linux sobre HTTPS,
amb sessions per testimoni i comprovació de rols al servidor.

**Castellano.** Este proyecto construye y despliega un sistema completo de punto de venta (TPV) y de
pantallas de cocina (KDS) para una hamburguesería pequeña. La sala toma la comanda en una pantalla
táctil, cada línea llega en tiempo real a la estación que la cocina, y el cobro admite cuentas
divididas y pagos mixtos. El sistema emite tickets y facturas numeradas en pantalla, sin depender de
una impresora. Funciona como tres servicios de systemd en un servidor Linux sobre HTTPS, con
sesiones por token y comprobación de roles en el servidor.

**Keywords / Paraules clau / Palabras clave:** POS · KDS · WebSocket · MariaDB · HTTPS · systemd

---

## Índice

1. [Introducción y justificación](#1-introducción-y-justificación)
2. [Estudio del entorno de la empresa](#2-estudio-del-entorno-de-la-empresa)
3. [Diseño y elaboración del proyecto](#3-diseño-y-elaboración-del-proyecto)
4. [Desarrollo técnico](#4-desarrollo-técnico)
5. [Evaluación del proyecto](#5-evaluación-del-proyecto)
6. [Viabilidad económica](#6-viabilidad-económica)
7. [Conclusiones y líneas futuras](#7-conclusiones-y-líneas-futuras)
8. [Bibliografía y normativa](#8-bibliografía-y-normativa)
9. [Anexos](#9-anexos)

**Índice de tablas**

| Nº | Tabla |
|---|---|
| 1 | Competencia directa en TPV de hostelería |
| 2 | Matriz DAFO |
| 3 | Estrategia CAME |
| 4 | Objetivos SMART y sus KPI |
| 5 | Roles y permisos del sistema |
| 6 | Resultados medidos frente a los KPI |
| 7 | Presupuesto de implantación |
| 8 | Coste comparado a cinco años |
| 9 | La interfaz antes y después del rediseño |

**Índice de figuras**

| Nº | Figura |
|---|---|
| 1 | Arquitectura del sistema |
| 2 | Ciclo de vida de una línea de comanda |
| 3 | Modelo entidad-relación de la base de datos |
| 4 | Flujo de cobro dividido |

---

## 1. Introducción y justificación

Un restaurante pequeño pierde dinero en dos sitios que casi nunca mide: en la comanda que llega mal
a la cocina y en la mesa que espera de más porque nadie sabe qué plato falta. La solución habitual
—comandero de papel y voz— funciona con poca gente y se rompe en cuanto hay servicio.

Este proyecto nace de ahí: construir el sistema que conecta la sala con la cocina y con la caja, y
hacerlo de principio a fin, no como maqueta. Se ha elegido esta temática porque cruza los tres
módulos del primer curso de ASIR:

- **Implantación de Sistemas Operativos:** el servicio corre sobre Linux, con arranque automático,
  supervisión y recuperación tras un corte.
- **Gestión de Bases de Datos:** el modelo relacional es el corazón del negocio, y un error de
  diseño ahí se paga en euros mal cobrados.
- **Planificación y Administración de Redes:** varias pantallas simultáneas, tiempo real, y tráfico
  cifrado en una red local.

La hostelería es, además, el sector donde un alumno de ASIR tiene más probabilidades de encontrar su
primer cliente: en la Comunitat Valenciana hay decenas de miles de establecimientos de restauración,
la mayoría con menos de diez empleados, y muchos siguen trabajando con papel o con un TPV antiguo
que solo sirve para cobrar.

La empresa simulada es ficticia, pero el sistema no: está desplegado, funcionando y probado.

---

## 2. Estudio del entorno de la empresa

### 2.1. Actividad y ubicación

**La Plancha** es una hamburguesería de barrio situada en Burjassot (València), con 13 mesas
repartidas en sala, terraza y barra, y servicio de comida para llevar. Plantilla de cuatro personas:
dos camareros, una cocinera y un encargado. Ticket medio previsto: entre 15 y 25 €.

La ubicación no es casual: Burjassot tiene una población universitaria alta y una densidad notable
de locales de restauración rápida, lo que significa servicio concentrado en franjas cortas —el peor
escenario para el papel y el mejor para un KDS.

### 2.2. Entorno específico: la competencia

**Tabla 1 · Competencia directa en TPV de hostelería**

| Producto | Modelo de negocio | Coste orientativo | Punto débil para un local pequeño |
|---|---|---|---|
| Revo XEF | Cuota mensual por terminal | ~60 €/mes y terminal | El KDS se paga aparte; depende de la nube |
| Glop Hostelería | Licencia perpetua + mantenimiento | ~600 € + cuota | Windows obligatorio; KDS como extra |
| Ágora (Iberical) | Licencia por terminal | ~500 € y terminal | Licencia por puesto: escalar sale caro |
| Cuiner / TPV genérico Android | Cuota baja o gratuito con publicidad | 0–20 €/mes | Datos fuera del local; funciones limitadas |
| **La Plancha (este proyecto)** | Software propio | Coste de implantación | Requiere quien lo mantenga |

Se ha estudiado además una demostración real de un KDS comercial (STARPOS) integrado en un TPV
Windows: tres columnas por estado, despacho por producto o por comanda y filtro por fechas. El
análisis completo, con el método de captura y las diferencias encontradas, está en
[docs/ANALISIS_KDS_COMPETENCIA.md](ANALISIS_KDS_COMPETENCIA.md). Dos conclusiones de ahí: su KDS
vive dentro del TPV —hace falta un equipo Windows con el punto de venta para ver las comandas— y
su contador de tiempo sube sin avisar (en su propia demostración se ve una comanda con 360 min).

La conclusión del análisis es clara: el mercado está cubierto en funcionalidad, pero cobra **por
terminal**. Un local que quiere cuatro pantallas de cocina paga cuatro veces. La propuesta de valor
de este proyecto no es hacer algo que no exista, sino que el número de pantallas deje de ser una
variable de coste.

### 2.3. Público objetivo (target y early adopter)

- **Target:** locales de restauración de 1 a 3 establecimientos, con 10-40 mesas y cocina dividida
  en estaciones, que ya usan un TPV para cobrar pero llevan la cocina a voces.
- **Early adopter:** el local con dueño joven y perfil técnico, que ya usa tabletas para otras cosas
  y acepta un sistema autoalojado a cambio de no pagar cuota por pantalla.

### 2.4. DAFO y CAME

**Tabla 2 · Matriz DAFO**

| | Favorable | Desfavorable |
|---|---|---|
| **Interno** | **Fortalezas**: sin cuotas por terminal; funciona en LAN sin internet; código propio adaptable; datos dentro del local | **Debilidades**: sin soporte 24/7; depende de una persona que lo mantenga; sin certificación fiscal |
| **Externo** | **Oportunidades**: obligación legal de facturación verificable (Verifactu) que empuja renovaciones; hardware táctil barato; hostelería que no quiere depender de la nube | **Amenazas**: competidores consolidados con soporte; exigencias fiscales crecientes; un fallo en hora punta cuesta clientes |

**Tabla 3 · Estrategia CAME**

| Estrategia | Acción concreta en el proyecto |
|---|---|
| **Corregir** (debilidades) | Documentación e instalador reproducible (`deploy/instalar.sh`); copias de seguridad automáticas previstas |
| **Afrontar** (amenazas) | Cada servicio con `Restart=always`; el sistema entero se levanta solo tras un corte, ya verificado |
| **Mantener** (fortalezas) | Todo el dato dentro del local; la aplicación funciona sin salida a internet |
| **Explotar** (oportunidades) | Facturación con numeración correlativa ya implementada, como base para la adaptación a Verifactu |

### 2.5. Cultura de empresa

- **Nombre e imagen:** La Plancha. Identidad sobria en fondo oscuro, naranja como color de acción
  (`#e67e22`), pensada para verse en pantalla a dos metros y en cocina con las manos ocupadas.
- **Misión:** que el cliente reciba lo que pidió, caliente y a tiempo.
- **Visión:** ser el local de barrio donde el servicio no se cae los viernes por la noche.
- **Valores:** honestidad en la cuenta, respeto al tiempo del cliente y cuidado del equipo de cocina.

### 2.6. ODS y responsabilidad social

| ODS | Acción concreta |
|---|---|
| **12. Producción y consumo responsables** | El sistema no imprime: ticket y factura se ven en pantalla y solo se imprimen si el cliente lo pide |
| **8. Trabajo decente** | El KDS reparte la carga por estaciones y hace visible el retraso, en lugar de acumular presión sobre una persona |
| **9. Industria e innovación** | Software propio y auditable, sin dependencia de un proveedor externo |

Acciones de RSE: carta con alérgenos señalados en cada producto, para que la información obligatoria
llegue igual al cliente y al personal.

---

## 3. Diseño y elaboración del proyecto

### 3.1. Fuentes de información

- **Primarias:** observación del flujo de trabajo en hostelería (comanda, pase, cobro) y la propia
  guía del módulo.
- **Secundarias:** documentación oficial de FastAPI, MariaDB, nginx y systemd; normativa española y
  europea de facturación y alérgenos (apartado 8).

### 3.2. Viabilidad técnica

El sistema debe funcionar en el hardware que ya tiene un local pequeño: un equipo modesto como
servidor y pantallas táctiles o tabletas como clientes. La decisión de no usar frameworks de
JavaScript en el cliente y de servir HTML estático responde a eso: cualquier navegador reciente vale
y no hace falta instalar nada en las pantallas.

Se ha verificado en la práctica: el servidor es una máquina virtual con **1 CPU y 4 GB de RAM**, y
con ella sostiene la base de datos, la API, el WebSocket y las pantallas sin degradación apreciable.

### 3.3. Objetivos SMART y sus KPI

**Tabla 4 · Objetivos SMART y sus KPI**

| # | Objetivo | KPI | Meta |
|---|---|---|---|
| O1 | La comanda llega a cocina sin pasar por papel | Tiempo entre «enviar» y aparecer en el KDS | < 1 s |
| O2 | Cocina sabe siempre qué lleva retraso | Comandas marcadas en amarillo/rojo por tiempo | Aviso a 8 min, crítico a 15 |
| O3 | Ningún importe mal cobrado por redondeo | Descuadre entre suma de líneas y total cobrado | 0 € |
| O4 | El local no depende de una impresora | Documentos emitidos sin hardware de impresión | 100 % |
| O5 | El servicio se recupera solo tras un corte | Intervención manual tras reiniciar el servidor | 0 acciones |
| O6 | Ningún dato de sesión viaja en claro | Peticiones servidas sobre HTTP | 0 |
| O7 | Una copia sirve de verdad | Restauración probada automáticamente | Semanal, sin fallos |
| O8 | Ningún cambio rompe lo que funcionaba | Pruebas automáticas antes de desplegar | 100 % en verde |

### 3.4. Tareas y metodología

Se ha trabajado con un tablero Kanban simple —*Backlog, En curso, Revisión, Hecho*— con la columna
de revisión explícita que recomienda la guía ampliada: nada pasa a «Hecho» sin una prueba que lo
demuestre. Cada bloque de trabajo termina en un *commit* y una entrada de diario fechada, lo que
deja una traza completa de qué se construyó y cuándo.

Fases:

1. Modelo de datos y API (núcleo del negocio).
2. Pantallas de sala y cocina.
3. Facturación y cierre de caja.
4. Gestión (usuarios, carta, ajustes).
5. Seguridad (sesiones, roles, HTTPS).
6. Explotación: copias de seguridad y pruebas automáticas.

### 3.5. Relación funcional y flujos de comunicación

| Puesto | Herramienta | Recibe | Envía |
|---|---|---|---|
| Camarero | TPV | Aviso de plato listo | Comanda, cobro |
| Cocina | KDS de su estación | Líneas de su estación | Cambios de estado |
| Encargado | Informe, Usuarios, Carta, Ajustes | Ventas y tiempos | Precios, altas, ajustes |

La comunicación interna es el propio sistema: un cambio en cualquier pantalla se propaga al resto
por WebSocket sin que nadie tenga que avisar a voces.

---

## 4. Desarrollo técnico

### 4.1. Arquitectura

**Figura 1 · Arquitectura del sistema**

```
  Tableta sala ─────┐                              ┌───── Pantalla plancha
  (TPV)             │                              │
  Encargado ────────┤  HTTPS + WSS (8443)          ├───── Pantalla freidora
  (informe)         ├──────►  FastAPI  ◄───────────┤
  Caja ─────────────┘        (uvicorn)             ├───── Pantalla fríos
  (facturación)                  │                 │
                                 │                 └───── Pase
                              MariaDB
                        (socket local, sin red)

  Puerto 8090 ──► 301 ──► https://servidor:8443
```

Decisiones y su porqué:

- **Importes en céntimos enteros.** Nunca coma flotante: `0,1 + 0,2` no es `0,3` y en una caja eso
  es un descuadre. El KPI O3 depende de esta decisión.
- **Precio congelado en la línea.** Cada línea guarda el precio que tenía el producto al venderse,
  así cambiar la carta no reescribe el pasado.
- **Bajas lógicas.** Ni empleados ni productos se borran: un pedido de hace un mes debe seguir
  diciendo quién lo atendió y qué se vendió.
- **WebSocket para los avisos, REST para los datos.** El WebSocket solo dice «algo ha cambiado»; la
  pantalla vuelve a pedir el dato por la API. Así un mensaje perdido no deja una pantalla mintiendo.

### 4.2. Ciclo de vida de una línea de comanda

**Figura 2 · Ciclo de vida de una línea**

```
 pendiente ──enviar a cocina──► enviada ──empezar──► preparando ──listo──► lista ──servir──► servida
     │                              │                                                          │
     └──── el camarero la quita ────┴──────────────── anulada ◄────────────────────────────────┘
```

La línea, no el pedido, es la unidad que viaja: en una mesa de cuatro, las bebidas pueden estar
servidas mientras la plancha sigue trabajando. Por eso cada estación ve solo lo suyo y el pase lo ve
todo.

### 4.3. Base de datos

**Figura 3 · Modelo entidad-relación (resumen)**

```
 empleados ──< pedidos >── mesas          categorias ──< productos
     │            │                                        │
     │            └──< lineas_pedido >─────────────────────┘
     │                      │
  sesiones              (pago_id)
                            │
                         pagos ──┐
                                 ├── facturas ──(1:1)── pedidos
                       ajustes ──┘

  arqueos ──< movimientos_caja
```

Trece tablas y una vista (`v_totales_pedido`). Puntos de diseño destacables:

- `UNIQUE (serie, ejercicio, numero)` en facturas: la numeración no puede repetirse.
- `UNIQUE (pedido_id)` en facturas: un pedido, una factura. Pedirla dos veces devuelve la misma.
- `lineas_pedido.pago_id`: liga cada línea al pago que la liquidó, de modo que en una cuenta
  dividida ninguna línea se cobra dos veces.
- `UNIQUE (fecha)` en arqueos: un solo arqueo por día de servicio; y `UNIQUE (z_ejercicio,
  z_numero)`, que impide repetir un número de cierre Z.
- Claves foráneas en todas las relaciones, con `ON DELETE CASCADE` solo donde tiene sentido
  (las líneas mueren con su pedido; los pagos y las facturas, nunca).

### 4.4. Cobro: cuenta dividida y pago mixto

**Figura 4 · Flujo de cobro dividido**

```
 total 45,00 €
   ├── pago 1: líneas 1,2 con tarjeta ....... 19,10 €   (líneas marcadas como pagadas)
   ├── pago 2: parte en efectivo ............ 15,00 €   (entrega 20 €, cambio 5 €)
   └── pago 3: resto con bizum .............. 10,90 €   → pendiente 0 → pedido cobrado
```

El servidor rechaza cobrar más de lo pendiente, rechaza líneas ya pagadas y solo cierra el pedido
cuando la suma alcanza el total. Mientras siga abierto, un pago se puede deshacer: el error de caja
se corrige en el momento, no al día siguiente.

### 4.5. Facturación sin impresora

Ticket y factura se dibujan en pantalla con el mismo aspecto que tendrían en papel de 72 mm, y se
pueden descargar como fichero de texto. Es una decisión consciente, no una limitación: evita
depender del hardware de impresión, permite trabajar con el ticket digital y ahorra papel (ODS 12).
La numeración de facturas se calcula dentro de la transacción con `SELECT MAX(numero)+1 … FOR
UPDATE`, de modo que dos cajas simultáneas no pueden generar el mismo número.

### 4.6. Arqueo de caja y cierre Z

La facturación dice lo que se ha vendido; el arqueo dice si el dinero está. El servicio empieza
declarando el **fondo de cambio** y termina contando el cajón, con el efectivo que se mueve durante
el día sin ser una venta (pagar a un proveedor, reponer cambio, retirar al banco) anotado como
entradas y salidas:

```
esperado   = fondo + ventas en efectivo + entradas − salidas
descuadre  = contado − esperado          (negativo = falta dinero)
```

El recuento se teclea por billetes y monedas y el servidor rechaza el cierre si el desglose no suma
el efectivo declarado. El **cierre Z** recibe numeración correlativa propia (`Z<año>/<5 dígitos>`,
con el mismo `SELECT MAX(…) … FOR UPDATE` que las facturas), congela las cifras del día en la tabla
`arqueos`, guarda el descuadre y queda firmado con el nombre del encargado y la hora; no se puede
repetir ni deshacer, y no se cierra con pedidos sin cobrar salvo decisión expresa del encargado. El
documento se ve en pantalla y se descarga como texto, igual que el ticket y la factura.

El histórico de cierres permite distinguir un descuadre puntual de uno sistemático, que es lo que
convierte el arqueo en una herramienta de control y no en un trámite.

### 4.7. Seguridad

**Tabla 5 · Roles y permisos**

| Rol | Sala | Cocina | Facturación | Usuarios / Carta / Ajustes / Informes |
|---|---|---|---|---|
| Camarero | Sí | No | Sí | No |
| Cocina | No | Sí | No | No |
| Encargado | Sí | Sí | Sí | Sí |

- **Sesiones con token.** El PIN solo viaja al entrar. A partir de ahí, un token aleatorio de 256
  bits (`secrets.token_urlsafe(32)`) guardado en la tabla `sesiones`, con caducidad configurable
  (12 h por defecto). Reiniciar el servicio no cierra la sesión de nadie.
- **Roles comprobados en el servidor.** Las dependencias de FastAPI cortan la petición antes de
  tocar la base de datos. Ocultar un botón en el navegador no es seguridad.
- **El servidor no se fía del cliente.** El pedido guarda el camarero que hay en la sesión, no el
  identificador que mande el navegador.
- **Solo la red local.** El servicio escucha únicamente en la IP de la LAN y, además, rechaza
  con 403 a cualquier cliente de fuera de las redes autorizadas, mirando la IP real de la conexión
  y no una cabecera que el cliente pueda inventarse. Con permisos de administrador se añade `ufw`,
  que deniega todo salvo SSH y los dos puertos del sistema desde la red del local, y deja MariaDB
  accesible solo por socket Unix. Es defensa en capas: lo que no llega al proceso no puede fallar
  en el proceso.
- **HTTPS en todo.** TLS en el 8443, incluido el WebSocket; el 8090 solo devuelve un 301, para que
  ninguna pantalla con la dirección antigua guardada siga tecleando su PIN en claro.

### 4.8. Despliegue y explotación

Tres unidades de `systemd` de usuario, todas con `Restart=always`:

| Unidad | Función |
|---|---|
| `kds-tpv.service` | La aplicación, HTTPS en el 8443 |
| `kds-tpv-http.service` | Redirección 301 del 8090 al 8443 |
| `kds-mariadb.service` | Base de datos (solo cuando no se dispone de root) |

**Copias de seguridad.** Completa semanal más incremental por registro binario (*binlog*) cada hora
de servicio, con poda a cuatro semanas. El incremental guarda solo lo que ha cambiado, de modo que
un día entero ocupa kilobytes y se puede recuperar hasta el último minuto antes del fallo. Cada
semana, un temporizador restaura la copia en una base de pruebas y compara tabla por tabla y el
total cobrado: si algo no cuadra, queda registrado como fallo.

**Pruebas y despliegue.** 65 pruebas automáticas con `pytest` sobre una base de datos que se crea y
se destruye sola. El despliegue las ejecuta antes de reiniciar: si fallan, el servicio se queda con
la versión anterior. La secuencia es copia → pruebas → reinicio → comprobación de salud.

La instalación completa en una máquina nueva es un script: entorno virtual, esquema, datos de
ejemplo, certificado y servicios. Para la máquina donde se disponga de root, queda preparada la
configuración de nginx como frontal TLS, con HSTS y las cabeceras que el WebSocket necesita.

---

## 4.8. Medir al cliente, no solo al plato

Los seis análisis de competencia (apartado 2.2 y anexo) coinciden en medir el tiempo de cocina. Uno
de ellos, Kibsi, lo hace de otra forma: cronometra la visita entera con cámaras. La idea es buena y
la implementación, innecesaria para nosotros: **cuatro de los tramos que ellos deducen por vídeo
están ya fechados en nuestra base de datos** —abrir la mesa, enviar a cocina, el último plato listo
y el cobro—. Lo único que faltaba era el número de comensales, que ahora se marca en el TPV.

De ahí salen dos piezas que no costaron desarrollo, sino consulta:

- **Sala en vivo**: ocupación y avisos por espera del cliente (sin tomar nota, plato listo sin
  recoger, cuenta sin cobrar), con umbrales configurables.
- **Tiempos de la visita** en el informe: cuánto tarda cada tramo y cuáles fueron las visitas más
  lentas del día.

Es un ejemplo de lo que este proyecto ha buscado desde el principio: antes de añadir tecnología,
mirar si el dato ya estaba.

## 4.9. Modo sin red: el servicio no se para porque se caiga el wifi

En un local el wifi se cae, y se cae en hora punta. Hasta ahora eso dejaba al camarero sin poder
ni tomar nota. El TPV pasa a funcionar sin servidor con una regla clara:

> **Sin red se toma nota; con red se cobra.**

Lo que se puede hacer a ciegas es abrir mesa, añadir y quitar líneas, apuntar comensales y mandar
la comanda a cocina (que saldrá cuando vuelva la red). Lo que **no**: cobrar, facturar ni arquear.
No es una limitación técnica sino legal y contable: la numeración de tickets y facturas es
correlativa y la asigna el servidor (RD 1619/2012 y Ley 11/2021); dos tabletas desconectadas
emitirían el mismo número.

**Cómo funciona** (`frontend/js/sinred.js`, `frontend/sw.js`):

1. Mientras hay servidor, la tableta guarda en IndexedDB copia de lo que necesita para trabajar a
   ciegas: carta, mesas, empleado de la sesión y los pedidos abiertos.
2. Al caer la red, cada acción del camarero se aplica sobre esa copia —con identificadores
   **negativos**, que no pueden confundirse con los del servidor— y se encola.
3. Un trabajador de servicio (*service worker*) guarda el HTML, el CSS y el JS del TPV, para que la
   pantalla se pueda **abrir** aunque no haya servidor. Estrategia *primero la red*: la copia solo
   sale cuando la red falla. Nada de `/api` se guarda nunca: una respuesta vieja de la API sería un
   precio o una mesa mintiendo.
4. Al volver la red, la cola se reenvía en orden traduciendo los identificadores locales por los de
   verdad. Lo que el servidor rechace (mesa ya cobrada, producto agotado) no se reintenta sin fin:
   se descarta y **se dice en pantalla**, que es lo que permite arreglarlo a mano.

**El problema de verdad no es perder la comanda, es duplicarla.** Si la petición llegó al servidor
y lo que se perdió fue la respuesta, el reenvío crearía un pedido gemelo: dos platos en cocina y
dos cobros en la caja. Se resuelve con **idempotencia** (`backend/sql/16_idempotencia.sql`): cada
acción lleva una clave que el cliente inventa **una vez** —no por intento— y el servidor guarda la
respuesta que dio la primera vez. Repetir devuelve esa misma respuesta sin ejecutar nada. Es el
mecanismo de las pasarelas de pago (`Idempotency-Key`). Solo se guardan las respuestas buenas: un
«esa mesa ya está cobrada» no se congela, porque si la situación cambia merece respuesta nueva.

**Verificación** (`deploy/qa_sinred.py`, navegador real contra el servidor): con la red cortada se
abre mesa, se apuntan dos productos y se mandan a cocina; el botón de cobrar queda bloqueado; se
**recarga la tableta sin red** y la pantalla vuelve a abrirse con lo apuntado intacto; al restaurar
la red la cola se vacía sola y la comprobación contra la API encuentra **un** pedido con dos líneas
en cocina, no dos. Ocho pruebas automáticas más (`backend/pruebas/test_sinred.py`) cubren la
idempotencia: reenviar no duplica, sin clave sí duplica, la respuesta repetida es idéntica a la
primera, un rechazo no se guarda y la clave no salta los permisos.

**Límites conocidos y asumidos**: empezar el turno exige red (el PIN lo valida el servidor); la
carta que se ve sin red es la de la última conexión, aunque el precio final siempre lo pone el
servidor al reenviar; y el certificado debe estar confiado en la tableta, porque si no el navegador
no registra el trabajador de servicio y se pierde el aguante a la recarga.

## 4.10. La interfaz: medida, no opinada

Una interfaz de hostelería no se juzga por si «queda bonita» en la pantalla de quien la programa,
sino por si se puede usar de pie, con prisa, con las manos ocupadas y con la luz que haya. Por eso
el rediseño del 23/09/2026 se hizo con un medidor delante, no a ojo.

**El sistema de diseño** (`frontend/css/estilo.css`) se apoya en cinco reglas:

1. **44 px de objetivo táctil** en todo lo que se toca (recomendación de las WCAG 2.1 y de las
   guías de Apple y Google). Un botón de 24 px es un botón que se falla con el dedo mojado.
2. **Contraste AA**: 4,5:1 para el texto normal y 3:1 para el grande. Cada color de fondo del
   sistema lleva emparejado su color de texto (`--ok` / `--ok-texto`), de modo que no se puede
   poner un verde de fondo y olvidar que encima iba texto blanco ilegible.
3. **Fondos sólidos** bajo el texto: los degradados engañan al ojo y al medidor.
4. **Un solo acento**. El ámbar significa «la acción principal de esta pantalla»; el verde,
   dinero o plato listo; el rojo, destruir; el amarillo, esperar. Nada más compite.
5. **Sin imágenes ni fuentes externas**: el local (y el aula) trabajan sin salida a internet.

**El medidor** (`deploy/qa_gui.py`) recorre cada pantalla con cada rol, en tableta (1280×800) y en
móvil (390×844), y mide lo que un revisor miraría a mano pero sin cansarse: desbordes horizontales,
contraste real de cada texto —calculado componiendo los fondos transparentes hasta el primero
opaco—, objetivos táctiles por debajo de 40 px, textos que se cortan sin avisar y errores de
consola. Deja captura de cada pantalla y un informe en Markdown.

**Tabla 9 · La interfaz antes y después del rediseño**

| Medida | Antes | Después |
|---|---|---|
| Pantallas medidas | 48 | 72 |
| Desbordes horizontales | 4 | **0** |
| Textos por debajo del contraste AA | 72 | **0** |
| Objetivos táctiles < 40 px | 57 | **0** |
| Textos cortados | 2 | **0** |
| Errores de consola | 8 | **0** |

Dos matices honestos sobre esas cifras. La primera columna mide menos pantallas porque el propio
recorrido tenía un fallo: las tarjetas de cocina llegan por AJAX y el medidor no las esperaba, así
que las seis pantallas de KDS no se estaban midiendo. Y de los 57 objetivos pequeños, parte eran
del medidor y no de la interfaz: una casilla de 24 px dentro de su etiqueta de 44 se toca igual, y
ahora se mide el área que de verdad recibe el dedo.

### 4.11. Que la cocina atascada no tumbe la pantalla

Durante las pruebas apareció un fallo que no se ve con datos de juguete: con la cocina atascada
—5.736 comandas pendientes, dejadas por la simulación— la pantalla del pase dejaba de responder.
No era un error de lógica: el repintado incremental es correcto, pero recorrer 5.736 tarjetas en
cada aviso del WebSocket es más trabajo del que una Raspberry Pi hace entre dos toques.

La solución no es pintar más rápido, es **no pintar lo que nadie va a cocinar ahora**: `/api/kds`
manda como mucho 60 comandas, **las más antiguas** (que es el orden en el que se despacha), y dice
cuántas quedan detrás; la pantalla lo enseña («… y 37 comandas más esperando turno») en vez de
callarlo. El tablón de recogida de la sala hace lo mismo con 24 números. Tres pruebas automáticas
lo fijan: que el tope se respete, que las que se manden sean las más viejas y que un `limite`
absurdo (0, negativo, 99.999) no tumbe la consulta.

## 5. Evaluación del proyecto

Los KPI del apartado 3.3 se han medido sobre el sistema desplegado, con un simulador que reproduce
un servicio completo usando únicamente la API pública —es decir, probando el backend de verdad.

**Tabla 6 · Resultados medidos**

| KPI | Meta | Resultado |
|---|---|---|
| O1 · Comanda en el KDS | < 1 s | Inmediato (aviso por WebSocket) |
| O2 · Aviso de retraso | 8 / 15 min | Correcto; umbrales configurables |
| O3 · Descuadre de caja | 0 € | 0 €; cobro dividido y mixto cuadran con el total |
| O4 · Documentos sin impresora | 100 % | 100 %; ticket y factura en pantalla |
| O5 · Recuperación tras corte | 0 acciones | Verificado: tras reiniciar el servidor, los tres servicios levantaron solos; y con el wifi cortado el TPV sigue tomando nota y reenvía al volver (apartado 4.9) |
| O6 · Tráfico en claro | 0 | 0; el 8090 redirige y el WebSocket exige token |
| O7 · Copia restaurable | Restauración probada | Verificada: 8 tablas y el total cobrado coinciden |
| O8 · Regresiones en producción | 0 | 65 pruebas automáticas bloquean el despliegue si fallan, y dos recorridos de interfaz (`qa_gui.py`, `qa_cliente.py`) se pasan antes de publicar |

Pruebas de comportamiento ante el error, todas comprobadas contra la API:

| Situación | Respuesta del sistema |
|---|---|
| Cobrar sin enviar a cocina | 409 |
| Efectivo entregado insuficiente | 422 |
| Cobrar dos veces el mismo pedido | 409 |
| Pagar líneas ya pagadas | 409 |
| Pagar más de lo pendiente | 422 |
| Pedir un producto agotado | 409 |
| Dar de baja al último encargado | 409 |
| Petición sin token, con token falso o tras cerrar sesión | 401 |
| Camarero en usuarios, informes o carta | 403 |
| Cocina abriendo un pedido | 403 |
| WebSocket sin token | Cierre 4401 |

**Incidencias durante el desarrollo y qué se aprendió:**

- La caché del navegador ocultó tres veces cambios ya desplegados. Se resolvió sirviendo los
  recursos con un sello de versión calculado por el servidor. *Lección: antes de depurar un
  comportamiento, comprobar qué fichero está sirviendo realmente el servidor.*
- La máquina virtual se apagó dos veces porque el proceso quedaba colgando de la sesión que la
  lanzaba. *Lección: los servicios se lanzan desacoplados, y por eso existe systemd.*
- El disco externo de entrega se corrompió a mitad del trabajo. El script de entrega detecta ahora
  que el destino no admite escritura y usa uno alternativo. *Lección: un procedimiento de entrega
  que solo funciona con el disco bueno no es un procedimiento.*

---

## 6. Viabilidad económica

**Tabla 7 · Presupuesto de implantación (local de 13 mesas, 4 pantallas de cocina)**

| Concepto | Unidades | Precio unitario | Total |
|---|---|---|---|
| Servidor (mini PC, 8 GB RAM, SSD) | 1 | 250 € | 250 € |
| Tableta de sala 10" | 2 | 150 € | 300 € |
| Pantalla de cocina + soporte | 4 | 180 € | 720 € |
| Punto de acceso wifi de local | 1 | 120 € | 120 € |
| SAI para servidor y red | 1 | 90 € | 90 € |
| Software (sistema operativo, MariaDB, Python) | — | 0 € | 0 € |
| Desarrollo e implantación (80 h × 25 €/h) | 80 | 25 € | 2.000 € |
| **Total de implantación** | | | **3.480 €** |
| Mantenimiento anual estimado | 1 | 400 € | 400 €/año |

**Tabla 8 · Coste comparado a cinco años**

| Solución | Año 1 | Años 2-5 | Total 5 años |
|---|---|---|---|
| Este proyecto | 3.480 € | 400 €/año | **5.080 €** |
| TPV por suscripción (2 terminales + 4 KDS) | ~1.500 € hardware + 2.880 €/año | 2.880 €/año | **~15.900 €** |
| TPV con licencia perpetua (6 puestos) | ~3.000 € + hardware | ~600 €/año | **~7.000 €** |

El ahorro no está en el software, que en todos los casos acaba siendo barato, sino en **no pagar por
pantalla**: el modelo por suscripción penaliza justo lo que este sistema quiere fomentar, que es
poner una pantalla en cada estación.

---

## 7. Conclusiones y líneas futuras

El objetivo era un sistema que funcionara de verdad, no una maqueta de presentación, y eso se ha
cumplido: el sistema está desplegado, tiene datos reales de un servicio simulado, se recupera solo
de un reinicio y su seguridad no depende de ocultar botones.

Lo que más ha enseñado este proyecto no ha sido escribir código, sino tres cosas de administración
de sistemas: que un servicio que no arranca solo no está terminado, que un despliegue que no se
puede repetir no es un despliegue, y que casi todo fallo raro tiene una explicación aburrida —una
caché, un proceso colgando de la sesión equivocada, un disco que se cae— antes que una compleja.

**Viabilidad futura e incorporación al mercado.** El producto es viable para locales pequeños que no
quieran pagar por terminal, pero para venderlo faltan dos piezas: soporte con un tiempo de respuesta
comprometido y adaptación a la normativa de sistemas de facturación verificables. Ninguna de las dos
es un obstáculo técnico; son trabajo.

**Líneas de trabajo futuras** (documentadas y priorizadas en el repositorio):

1. Modo sin red en el TPV, para que una caída de wifi no pare el servicio: es la única de las diez
   mejoras propuestas que queda por hacer.

---

## 8. Bibliografía y normativa

### Referencias bibliográficas

Ramírez, S. (2026). *FastAPI documentation*. https://fastapi.tiangolo.com/

MariaDB Foundation. (2026). *MariaDB server documentation*. https://mariadb.com/kb/en/documentation/

freedesktop.org. (2026). *systemd.service — service unit configuration*.
   https://www.freedesktop.org/software/systemd/man/systemd.service.html

nginx. (2026). *NGINX documentation: WebSocket proxying*.
   https://nginx.org/en/docs/http/websocket.html

Mozilla. (2026). *MDN Web Docs: WebSocket API*.
   https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API

### Normativa consultada

Reglamento (UE) 2016/679 del Parlamento Europeo y del Consejo, de 27 de abril de 2016, relativo a la
   protección de las personas físicas en lo que respecta al tratamiento de datos personales (RGPD).

Ley Orgánica 3/2018, de 5 de diciembre, de Protección de Datos Personales y garantía de los derechos
   digitales.

Real Decreto 1619/2012, de 30 de noviembre, por el que se aprueba el Reglamento por el que se
   regulan las obligaciones de facturación.

Ley 11/2021, de 9 de julio, de medidas de prevención y lucha contra el fraude fiscal (requisitos de
   los sistemas informáticos de facturación).

Real Decreto 1007/2023, de 5 de diciembre, por el que se aprueba el Reglamento de requisitos de los
   sistemas informáticos de facturación (Verifactu).

Ley 37/1992, de 28 de diciembre, del Impuesto sobre el Valor Añadido (tipo reducido aplicable a
   servicios de hostelería).

Reglamento (UE) 1169/2011 sobre la información alimentaria facilitada al consumidor, y Real Decreto
   126/2015 (información de alérgenos en alimentos sin envasar).

Real Decreto 499/2024, de 21 de mayo, por el que se establecen los títulos de formación profesional
   (resultados de aprendizaje del módulo de proyecto).

---

## 9. Anexos

### Anexo I · Endpoints principales de la API

| Método | Ruta | Rol | Función |
|---|---|---|---|
| POST | `/api/login` | — | Abre sesión con PIN y devuelve token |
| GET | `/api/catalogo` | cualquiera | Carta vigente |
| POST | `/api/pedidos` | camarero | Abre pedido en mesa o para llevar |
| POST | `/api/pedidos/{id}/lineas` | camarero | Añade línea con notas |
| POST | `/api/pedidos/{id}/enviar` | camarero | Manda las líneas a cocina |
| GET | `/api/kds` | cocina | Comandas activas de una estación |
| POST | `/api/kds/pedido/{id}/avanzar` | cocina | Avanza la comanda un paso |
| POST | `/api/pedidos/{id}/pagos` | camarero | Pago total, por líneas o por partes |
| POST | `/api/pedidos/{id}/factura` | camarero | Emite factura numerada |
| GET | `/api/informe` | encargado | Ventas del día |
| POST | `/api/arqueo/apertura` | encargado | Abre la caja con su fondo de cambio |
| POST | `/api/arqueo/movimientos` | camarero | Entrada o salida de efectivo |
| POST | `/api/arqueo/cierre` | encargado | Cierre Z: descuadre y firma |
| WS | `/ws?token=…` | cualquiera | Avisos de cambio en tiempo real |

### Anexo II · Estructura del repositorio

```
backend/app/      main.py (API), auth.py (sesiones y roles), db.py, redirector.py
backend/sql/      01_schema · 02_seed · 03_facturacion · 04_carta_y_pagos · 05_sesiones · 06_arqueo
                  · 07…15 (tema, puestos, estaciones, escalafones, carta, plano, sala)
                  · 16_idempotencia (modo sin red)
backend/pruebas/  test_api.py · test_arqueo.py · test_sinred.py · test_tope_pantallas.py (65)
backend/          simulador.py (servicio simulado para la demo)
frontend/         menú, tpv, kds, facturas, carta, usuarios, ajustes, informe, arqueo, recogida
                  js/sinred.js y sw.js (modo sin red del TPV)
deploy/           instalar.sh, certificado.sh, entregar.sh, units de systemd, nginx.conf
                  qa.py (roles), qa_sinred.py (modo sin red), qa_gui.py (interfaz medida)
                  y qa_cliente.py (el cliente pide y sigue su comanda)
docs/             esta memoria y PENDIENTES.md
```

### Anexo III · Datos de la demostración

Acceso: `https://<servidor>:8443/` · PIN de prueba: Laura `1111` (camarera), Aitana `3333` (cocina),
Pau `9999` (encargado). Carta de 21 productos en 5 categorías, 13 mesas y 4 estaciones de cocina.
