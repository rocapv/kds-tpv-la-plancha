# Informe de mercado · Sistema KDS + TPV autoalojado para hostelería pequeña

**Proyecto Intermodular 1 · 1º CFGS Administración de Sistemas Informáticos en Red**
Autor: RocaPV · Septiembre de 2026
Documento complementario a [MEMORIA.md](MEMORIA.md)

> **Pregunta que responde este informe:** ¿qué nos ha llevado a elegir un KDS + TPV como proyecto?

**Nota metodológica.** Todos los datos numéricos de este informe llevan fuente y año. Cuando un dato
no ha podido verificarse en una fuente primaria o secundaria fiable, se indica expresamente con la
fórmula «no se ha podido verificar». Las estimaciones propias se señalan como tales y se explica el
procedimiento con el que se han obtenido. Las fuentes internas son los cuatro análisis de producto
ya realizados en este mismo proyecto, citados por su ruta.

---

## 1. Resumen ejecutivo

La restauración española es un sector enorme y extraordinariamente atomizado: 280.403
establecimientos de hostelería en 2024 (UVE Data Market Horeca, junio de 2025), de los cuales el
93 % son locales independientes, no cadenas. El tejido empresarial español al que pertenecen es de
microempresa: el 54,4 % de las empresas activas no tiene ningún asalariado y el 81,6 % tiene dos o
menos (INE, DIRCE a 1 de enero de 2025, publicado en diciembre de 2025).

Ese sector factura más cada año pero gana menos: en 2025 la facturación creció entre un 2 % y un
4 %, mientras la rentabilidad de la restauración cayó un 0,9 % (Anuario de Hostelería de España,
enero de 2026). Es decir, el margen se estrecha, y con él aumenta el valor de cualquier herramienta
que reduzca error y tiempo muerto en el servicio.

Al mismo tiempo, tres normas empujan a renovar el equipamiento: la Ley 11/2021 antifraude, el
Real Decreto 1007/2023 (reglamento de sistemas informáticos de facturación, conocido como
Verifactu) y la factura electrónica entre empresas de la Ley 18/2022. El local pequeño va a tener
que tocar su sistema de cobro sí o sí en los próximos ejercicios.

El mercado de TPV está cubierto en funcionalidad, pero cobra casi siempre **por terminal**, y el
KDS —la pantalla de cocina— aparece de forma sistemática como módulo aparte o como dispositivo
adicional facturable. Un local que quiere cuatro pantallas de cocina paga cuatro veces. Esa es la
grieta concreta que justifica este proyecto: un sistema web autoalojado en el que la pantalla
número cinco cuesta lo que cuesta la pantalla, no lo que cuesta la licencia.

---

## 2. El sector: la restauración en España y en la Comunitat Valenciana

### 2.1. Tamaño y estructura

**Tabla 1 · Magnitudes del sector (datos verificados)**

| Magnitud | Valor | Fuente y año |
|---|---|---|
| Establecimientos de hostelería en España | 280.403 (+1,6 % interanual) | UVE Data Market Horeca 2025, difundido por *Profesional Horeca*, junio de 2025 |
| Cuota de hostelería independiente (no cadena) | 93 % de los establecimientos (+1,3 %) | UVE Data Market Horeca 2025 |
| Cuota de restauración organizada (cadenas y franquicias) | 7,5 % de los establecimientos, creciendo al +6,2 % | UVE Data Market Horeca 2025 |
| Empleo medio en hostelería | 1,89 millones de personas en 2025 (+2 %), con picos de 2 millones en verano | Anuario de Hostelería de España, enero de 2026 |
| Peso de la hostelería en el empleo total | 8,6 % del empleo en España; 65,9 % del empleo turístico | Anuario de Hostelería de España, enero de 2026 |
| Crecimiento de la facturación en 2025 | entre +2 % y +4 % sobre 2024 | Anuario de Hostelería de España, enero de 2026 |
| Rentabilidad de la restauración (hasta septiembre de 2025) | **−0,9 %** (el alojamiento, en cambio, +2,1 %) | Anuario de Hostelería de España, enero de 2026 |
| Empresas activas en España | 3,31 millones (+1,7 %) | INE, DIRCE a 1 de enero de 2025 (publicado 11/12/2025) |
| Empresas sin asalariados | 54,4 % del total | INE, DIRCE 2025 |
| Empresas con dos asalariados o menos | 81,6 % del total | INE, DIRCE 2025 |

Dos lecturas importan para este proyecto.

**La primera es la atomización.** El DIRCE no publica en su nota de prensa el desglose de
asalariados restringido al epígrafe de servicios de comidas y bebidas, de modo que el porcentaje
exacto de locales de restauración con menos de diez empleados **no se ha podido verificar** en
fuente primaria. Lo que sí está verificado es el marco general —más de ocho de cada diez empresas
españolas tienen dos asalariados o menos— y el dato sectorial de que el 93 % de los
establecimientos de hostelería son independientes. Ambos apuntan en la misma dirección: el cliente
típico de un TPV en España no es una cadena con departamento de sistemas, es un local con cuatro
personas y sin nadie que sepa de informática.

**La segunda es la tijera entre ingresos y margen.** La restauración factura más y gana menos. Un
sector cuyo margen se estrecha no compra tecnología por moda: la compra si ahorra horas de trabajo,
si evita platos devueltos o si evita una sanción. Ese es el criterio con el que hay que juzgar un
KDS, y no por la lista de funciones.

### 2.2. Comunitat Valenciana

**Tabla 2 · La hostelería valenciana**

| Magnitud | Valor | Fuente y año |
|---|---|---|
| Bares y restaurantes en la Comunitat Valenciana | 31.186 establecimientos (tercera comunidad de España) | Consejo General de Economistas sobre el Anuario de la Hostelería de España 2024, recogido en prensa el 27/05/2025 |
| Densidad | aproximadamente **un bar por cada 174 habitantes** (media española: uno por cada 175) | Misma fuente, 2025 |
| Establecimientos del canal Horeca en la provincia de València | 13.698 | Misma fuente, 2024 |

La Comunitat Valenciana es, por tanto, el tercer mercado español por número de locales y tiene una
densidad de establecimientos por habitante ligeramente superior a la media nacional. Para un
proyecto que nace en Burjassot (València), el mercado potencial inmediato es de decenas de miles de
locales, la inmensa mayoría independientes.

### 2.3. Digitalización: mucho cobro, poca cocina

Aquí conviene ser prudente, porque la mayoría de las cifras de «digitalización hostelera» que
circulan proceden de estudios encargados por fabricantes de TPV y no de estadística pública.

- **Dato verificado (estadística pública, pero no sectorial).** El INE publica anualmente la
  *Encuesta sobre el uso de TIC y del comercio electrónico en las empresas*, armonizada con
  Eurostat; en la edición de 2024 (datos definitivos publicados en 2025) el 84,5 % de las empresas
  dispone de sitio web y el 26,6 % vendió por comercio electrónico. El desglose específico del
  epígrafe de hostelería para empresas de menos de diez empleados existe en INEbase pero **no se ha
  podido verificar** su valor exacto en esta investigación.
- **Dato de origen comercial, citado como tal.** Glop, empresa española de software TPV, sitúa
  entre el 65 % y el 70 % los pagos realizados en España por medios digitales, a partir de datos de
  más de 8.000 clientes propios (*El Independiente*, 21/05/2026). Es una muestra de clientes de un
  fabricante, no representativa del sector, y debe leerse como indicio, no como estadística.
- **Cifras no verificadas.** Circulan porcentajes concretos de «establecimientos altamente
  digitalizados» (entre el 15 % y el 22 % según la fuente) atribuidos a informes sectoriales; no ha
  sido posible localizar el informe original ni su año de publicación, de modo que **no se
  incorporan** a este informe.

Lo que sí puede afirmarse con las fuentes disponibles y con las observaciones de los cuatro
análisis de producto internos es una asimetría cualitativa: la digitalización de la hostelería
española se ha concentrado en **el cobro** (terminal de pago, TPV, carta con código QR) y apenas ha
llegado a **la producción**, es decir, a la cocina. El comandero de papel y la voz siguen siendo el
protocolo entre sala y fogón en una parte muy grande del sector.

---

## 3. La normativa que empuja la digitalización

Una parte relevante de la demanda de TPV en España no nace del deseo de modernizarse, sino de una
obligación legal. Conviene distinguir cuatro bloques, con sus plazos **verificados a fecha de
septiembre de 2026**, porque el calendario de facturación se ha modificado dos veces.

### 3.1. Ley 11/2021 antifraude: el fin del software de doble uso

La Ley 11/2021, de 9 de julio, de medidas de prevención y lucha contra el fraude fiscal, añadió a
la Ley General Tributaria el artículo 29.2.j), que prohíbe producir, comercializar y usar programas
de facturación que permitan llevar contabilidades distintas, no registrar operaciones o alterar
registros. Es la norma que hace ilegal el «software de doble uso» y la que abre la puerta al
desarrollo reglamentario posterior. Para un TPV de hostelería, su efecto práctico es que el
registro de las ventas debe ser íntegro, trazable e inalterable.

### 3.2. Real Decreto 1007/2023 (Verifactu): requisitos de los sistemas de facturación

El Real Decreto 1007/2023, de 5 de diciembre, aprueba el reglamento que desarrolla ese artículo y
fija los requisitos que debe cumplir todo sistema informático de facturación: registro de
facturación por cada factura emitida, encadenamiento mediante huella o *hash*, firma, trazabilidad,
conservación, accesibilidad y, opcionalmente, remisión automática de los registros a la Agencia
Tributaria (modalidad **Verifactu** propiamente dicha).

**Plazos vigentes.** El calendario se ha aplazado dos veces:

| Hito | Plazo |
|---|---|
| Redacción original del RD 1007/2023 | julio de 2025 |
| Tras el Real Decreto 254/2025 | 1 de enero de 2026 (sociedades) y 1 de julio de 2026 (resto) |
| **Tras el Real Decreto-ley 15/2025** (BOE de 3/12/2025, en vigor el 4/12/2025, convalidado el 16/12/2025) | **1 de enero de 2027** para contribuyentes del Impuesto sobre Sociedades y **1 de julio de 2027** para el resto (autónomos en IRPF, no residentes con establecimiento permanente y entidades en atribución de rentas) |

*Fuente: Garrigues, «Se retrasa la entrada en vigor de Veri\*factu», diciembre de 2025; y
Real Decreto-ley 15/2025.*

La lectura para este proyecto es doble. Por un lado, es la **oportunidad de mercado** más clara:
cientos de miles de locales tendrán que revisar o cambiar su sistema de facturación antes de julio
de 2027. Por otro, es una **limitación honesta** que este informe debe declarar: el sistema
desarrollado emite facturas con numeración correlativa y sin huecos, garantizada dentro de la
transacción de base de datos, pero **no implementa todavía** el encadenamiento por huella, la firma
ni la remisión a la AEAT, y por tanto **no es hoy un sistema conforme al RD 1007/2023**. Es una
línea de trabajo, no una característica actual.

### 3.3. Ley 18/2022 «Crea y Crece» y la factura electrónica entre empresas

El artículo 12 de la Ley 18/2022, de 28 de septiembre, de creación y crecimiento de empresas,
obliga a emitir y recibir factura electrónica en todas las operaciones entre empresas y
profesionales establecidos en España. Su desarrollo reglamentario es el **Real Decreto 238/2026,
publicado en el BOE el 31 de marzo de 2026**, que define los requisitos técnicos, las plataformas
privadas de intercambio y una solución pública de facturación gestionada por la AEAT.

- Formatos admitidos: UBL, CII, EDIFACT y Facturae, todos conformes al modelo semántico europeo
  **EN 16931**.
- Calendario: **12 meses** para empresas con facturación superior a 8 millones de euros y
  **24 meses** para el resto, contados desde la fecha que fije la orden ministerial de desarrollo.
- Quedan expresamente **exceptuadas las facturas simplificadas**.

Esa última excepción es decisiva para entender el caso de un bar. El documento que un local entrega
a un cliente particular es un ticket o una factura simplificada, no una factura electrónica B2B: la
obligación de «Crea y Crece» le afecta sobre todo **como receptor** de las facturas de sus
proveedores, y solo como emisor cuando factura a empresas (comidas de empresa, *catering*). Para el
diseño del sistema, esto significa que la prioridad funcional está en el ticket y la factura
simplificada bien numerados —que es lo que el proyecto implementa— y que la factura electrónica
estructurada es un requisito de segundo orden para este segmento.

### 3.4. Alérgenos: Reglamento (UE) 1169/2011 y Real Decreto 126/2015

El **Reglamento (UE) n.º 1169/2011** del Parlamento Europeo y del Consejo, de 25 de octubre de 2011,
sobre la información alimentaria facilitada al consumidor, obliga a informar de la presencia de las
catorce sustancias o productos que causan alergias e intolerancias recogidos en su anexo II. El
**Real Decreto 126/2015, de 27 de febrero**, regula en España la información obligatoria de los
alimentos que se presentan sin envasar para la venta al consumidor final, que es exactamente el
caso de un plato servido en un bar: la información debe estar disponible antes de que se formalice
la compra y puede facilitarse por escrito o de forma verbal siempre que exista un soporte
documental accesible y verificable.

Este requisito tiene una traducción directa en el software: el alérgeno no es un adorno de la carta
digital, es un dato obligatorio asociado al producto, que debe verse a la vez en la carta del
cliente, en la pantalla del camarero y en la línea de comanda que llega a cocina. El sistema
desarrollado lo modela así (véase [../README.md](../README.md), aplicaciones «Carta» y «Carta del
cliente»).

### 3.5. Protección de datos: RGPD y LOPDGDD

El **Reglamento (UE) 2016/679** (RGPD) y la **Ley Orgánica 3/2018, de 5 de diciembre**, de
Protección de Datos Personales y garantía de los derechos digitales (LOPDGDD) se aplican a los
datos personales que maneja un TPV: los del personal (usuarios, PIN, jornada, productividad) y los
del cliente cuando se emite factura completa con NIF, se gestiona una reserva o se opera con una
plataforma de reparto.

Dos principios del RGPD son especialmente pertinentes en el diseño de un sistema de sala y cocina:

- **Minimización (art. 5.1.c).** Solo deben tratarse los datos necesarios. La pantalla pública de
  recogida del sistema desarrollado aplica este principio de forma literal: expone únicamente
  números de pedido y tiempos de espera, sin nombres, productos ni importes.
- **Protección de datos desde el diseño y por defecto (art. 25).** Un sistema autoalojado en el que
  los datos no salen de la red del local reduce el número de encargados del tratamiento y, con él,
  la superficie de riesgo y la carga documental. Un TPV en la nube exige, como mínimo, identificar
  al proveedor como encargado del tratamiento, firmar el contrato del artículo 28 del RGPD y
  verificar la ubicación del tratamiento. Conviene no exagerar la diferencia: autoalojar no exime
  de cumplir el RGPD, solo simplifica la cadena de responsabilidad y traslada al titular del local
  la obligación de la seguridad y de las copias.

---

## 4. La competencia

### 4.1. Panorama

El mercado español de TPV de hostelería tiene tres capas. La primera es la del **software español
clásico de licencia** (Glop, Ágora, Cuiner, Camarero10), heredero del TPV Windows instalado en el
local. La segunda es la de las **plataformas en la nube** (Revo, Last.app, Lightspeed, Square, Epos
Now), que cobran suscripción y venden la integración con reparto a domicilio como argumento
principal. La tercera es la del **software gratuito o muy barato con monetización indirecta**
(Loyverse, TMBill), que regala el TPV y cobra los complementos o los pagos.

**Tabla 3 · Competencia en TPV con KDS presente en España**

| Producto | Origen | Modelo de precio (fuente y fecha) | ¿KDS aparte? | ¿Depende de la nube? | Punto débil para un local pequeño |
|---|---|---|---|---|---|
| **Revo XEF** | España | **Sin precio público**: la web y la documentación remiten al distribuidor (consultado 21/09/2026) | Módulo diferenciado dentro de la suite | Sí, arquitectura en la nube | Opacidad de precio y coste por terminal; el local depende del distribuidor para cualquier cambio |
| **Glop Hostelería** | España | Desde **19,90 €/mes** o **~299 € en pago único**; versiones Mini desde 199 € y Pro desde 399 € sin IVA (red de distribuidores, consultado 09/2026) | Módulo de cocina adicional | No: instalación local | Windows obligatorio; escalar a varias pantallas implica licencias adicionales |
| **Ágora (IGT / Iberical)** | España | **Desde 32 €/mes** en suscripción; también licencia perpetua por terminal (agorapos.com, consultado 09/2026) | KDS incluido como módulo de monitor de cocina | Opcional | Modelo por terminal: cada puesto suma |
| **Cuiner** | España | **Sin precio público** para el TPV: se cotiza por local. El módulo de reservas se anuncia desde 22 €/mes (cuiner.com y comparadores, 09/2026) | Módulo de cocina adicional | Mixto | Precio no transparente; funciones troceadas en módulos |
| **Camarero10** | España | **Sin precio público oficial**; los comparadores sitúan la base en **30–50 €/mes** (tpvhosteleria.org, 2026). Cifra de comparador, no del fabricante | KDS como módulo | Sí | Coste final dependiente de los módulos contratados |
| **Lightspeed Restaurant** | Canadá | Planes desde **69 $/mes** (Starter) hasta 399 $/mes (Premium), tarifa de EE. UU., julio de 2026. **Precio en euros para España: no se ha podido verificar** | **Sí: en torno a 30 $ por pantalla y mes** (análisis de UpMenu y Merchant Maverick, 2026) | Sí | El KDS por pantalla multiplica el coste justo en el local con cocina por estaciones |
| **Square for Restaurants** | EE. UU. | Plan gratuito, o **59 €/mes + IVA por punto de venta** con licencias de TPV ilimitadas; comisión **1,25 % + 0,05 €** en pagos presenciales en la UE (squareup.com/es, consultado 09/2026) | Square KDS existe; **su coste separado no está publicado** en la web española | Sí | El coste real está en la comisión por transacción, no en la cuota |
| **Loyverse** | Letonia / EE. UU. | TPV, panel, **KDS y pantalla de cliente gratuitos**. Complementos: historial de ventas ilimitado 5 €/mes por tienda, gestión del personal 5 €/mes por empleado, inventario avanzado 25 €/mes por tienda (loyverse.com/es/pricing, consultado 09/2026) | **No: el KDS es gratuito** | Sí: los datos residen en su nube | Es la excepción del mercado, pero a cambio los datos salen del local y el histórico de ventas se paga |
| **TMBill** | India | **Sin precio público** en euros | KDS como aplicación aparte (Windows y Android) | Sí | Producto no orientado al mercado español: soporte, idioma y fiscalidad |
| **Epos Now** | Reino Unido, con delegación en España | **Sin precio público en España**: cotización personalizada. En EE. UU. se anuncian 39 $/mes o 449 $ por doce meses (comparadores, 2026) | KDS como aplicación de su tienda de complementos | Sí | Venta por paquete con hardware y permanencia; precio no transparente |
| **Last.app** | España | Starter **50 €/mes**, Growth **95 €/mes**, Unlimited **175 €/mes** con facturación anual, más **500 € + IVA de alta** (last.app/precios, consultado 21/09/2026) | **Sí: 35 €/mes por local**, complemento no incluido en ningún plan | Sí | El alta de 500 € y el KDS de pago se abonan antes de vender nada |
| **Ordatic** | España | De **39 €/mes** (hasta 300 pedidos) a **149 €/mes** sin límite (comparadores, 2026) | No es un TPV: es integrador de reparto | Sí | Resuelve solo el reparto; no sustituye a un TPV ni a un KDS |

Dos advertencias metodológicas sobre esta tabla. La primera: las cifras en dólares corresponden al
mercado estadounidense y no son trasladables sin más a España; se incluyen porque son el único dato
público del fabricante. La segunda: cuando la fuente es un comparador y no el fabricante, se dice
expresamente, porque los comparadores no siempre actualizan las tarifas.

### 4.2. Lo que se ve al mirar los productos por dentro

Los cuatro análisis de producto realizados en este proyecto —con descarga, transcripción y
selección de fotogramas clave de demostraciones reales— permiten afirmar cosas que ninguna tabla de
precios dice:

- **El KDS suele vivir dentro del TPV.** En [ANALISIS_KDS_COMPETENCIA.md](ANALISIS_KDS_COMPETENCIA.md)
  (STARPOS) se documenta que para ver las comandas hace falta un equipo Windows con el punto de
  venta instalado. La pantalla de cocina no es un cliente ligero: es otra instalación completa.
- **El ecosistema se vende entero o no se vende.** En [ANALISIS_KDS_TMBILL.md](ANALISIS_KDS_TMBILL.md)
  nueve de los quince minutos de la demostración oficial son instalación y configuración: aplicación
  de camarero, pedido del cliente, canales digitales y KDS en dos sistemas operativos distintos.
- **Hay una alternativa de diseño que el mercado casi no usa.**
  [ANALISIS_KDS_LOYVERSE.md](ANALISIS_KDS_LOYVERSE.md) muestra que Loyverse trata el KDS como si
  fuera **una impresora más**: eso simplifica el encaminamiento de comandas, pero ata la pantalla al
  modelo de «imprimir en destino» en lugar de al estado de la línea.
- **Lo que de verdad importa dura menos de un minuto.**
  [ANALISIS_KDS_EPOSNOW.md](ANALISIS_KDS_EPOSNOW.md) reduce el producto a lo esencial: 47 segundos
  de pantalla partida que enseñan qué ocurre en cocina en el instante en que el camarero envía la
  comanda. Ese instante es el núcleo funcional de todo KDS.

### 4.3. Conclusión del análisis competitivo

Tres patrones se repiten con independencia del fabricante:

1. **La unidad de facturación es el terminal o la pantalla.** Lightspeed lo cobra explícitamente por
   pantalla; Last.app lo cobra como complemento por local; Glop y Ágora lo cobran como licencia de
   puesto.
2. **El KDS casi nunca está incluido.** De los doce productos de la tabla, solo en Loyverse el KDS
   es gratuito sin condiciones, y a cambio los datos del local residen en la nube del fabricante y
   el histórico de ventas completo es de pago.
3. **El precio no es público.** En cinco de los doce casos no existe tarifa publicada. Para un local
   de cuatro personas, eso significa negociar sin referencia y, a menudo, con permanencia.

---

## 5. El cliente: a quién sirve un KDS y a quién no

No todos los locales pequeños tienen el mismo problema. La segmentación siguiente es **elaboración
propia**, a partir de la observación del flujo de trabajo descrita en la memoria y del
funcionamiento de los productos analizados; no procede de un estudio de mercado con muestra
estadística, y debe leerse como hipótesis de trabajo, no como dato.

**Tabla 4 · Segmentos de cliente y necesidad dominante (elaboración propia, 2026)**

| Segmento | Cómo es el servicio | Qué necesita de verdad | Valor del KDS |
|---|---|---|---|
| **Bar de barrio** | Barra, rotación alta, ticket bajo, cocina pequeña o inexistente | Cobrar rápido, dividir cuentas, cerrar la caja sin descuadres | **Bajo-medio**: una sola pantalla de pase basta; el valor está en el TPV |
| **Hamburguesería o comida rápida** | Picos cortos y muy densos, cocina dividida en estaciones (plancha, fritura, fríos), mucho «para llevar» | Que cada línea llegue a la estación correcta y que el retraso se vea | **Alto**: es el caso canónico, y es el del proyecto |
| **Arrocería o restaurante de mantel** | Menos comandas, tiempos de cocción largos y muy desiguales, coordinación de pases | Sincronizar el pase de mesa: que todos los platos salgan a la vez | **Alto, pero con otra lógica**: importa el pase, no la velocidad |
| **Cafetería o panadería-cafetería** | Mostrador, producto mayormente preelaborado | Cobro ágil y control de caja | **Bajo**: una pantalla de recogida aporta más que un KDS por estaciones |
| **Dark kitchen** | Sin sala; casi todos los pedidos entran por plataformas de reparto | Agregar pedidos de varias plataformas en una sola cola de producción | **Muy alto**, pero la pieza crítica es la integración con las plataformas, que este proyecto no cubre |

La conclusión operativa es que el KDS no es un producto universal: su valor crece con **el número de
estaciones de cocina y la densidad del pico de servicio**. El proyecto acierta al elegir una
hamburguesería con cuatro estaciones y servicio concentrado, porque es el escenario donde la
diferencia entre papel y pantalla es máxima; y debe reconocer que para una cafetería de mostrador la
misma herramienta aporta poco.

---
