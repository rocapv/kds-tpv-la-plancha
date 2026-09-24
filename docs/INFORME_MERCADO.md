# Informe de mercado · Sistema KDS + TPV autoalojado para hostelería pequeña

**Proyecto Intermodular 1 · 1º CFGS Administración de Sistemas Informáticos en Red**
Autor: RocaPV · Septiembre de 2026 · Documento complementario a [MEMORIA.md](MEMORIA.md)

> **Pregunta que responde este informe:** ¿qué nos ha llevado a elegir un KDS + TPV como proyecto?

**Nota metodológica.** Todo dato numérico lleva fuente y año. Lo que no ha podido verificarse en una
fuente identificable se marca como «no se ha podido verificar», y las estimaciones propias se
señalan explicando el procedimiento. Las fuentes internas son los cuatro análisis de producto ya
realizados en este proyecto, citados por su ruta. Enlaces consultados el 21 de septiembre de 2026.

---

## 1. Resumen ejecutivo

La restauración española es un sector enorme y atomizado: 280.403 establecimientos de hostelería en
2024, de los cuales el 93 % son locales independientes (UVE Data Market Horeca, 2025). Pertenecen a
un tejido de microempresa: el 81,6 % de las empresas españolas tiene dos asalariados o menos (INE,
DIRCE 2025).

Ese sector factura más y gana menos. En 2025 la facturación creció entre un 2 % y un 4 % mientras la
rentabilidad de la restauración caía un 0,9 % (Anuario de Hostelería de España, enero de 2026). Con
el margen estrechándose, solo se compra tecnología que ahorre horas, evite errores o evite sanciones.

Tres normas obligan además a tocar el equipamiento: la Ley 11/2021 antifraude, el RD 1007/2023
(Verifactu), aplazado hasta enero y julio de 2027, y la factura electrónica entre empresas de la Ley
18/2022, desarrollada por el RD 238/2026.

El mercado está cubierto en funcionalidad pero cobra **por terminal**, y el KDS aparece casi siempre
como módulo o dispositivo facturable aparte: de trece productos revisados, solo Loyverse lo regala, y
a cambio los datos salen del local. Un local con cuatro estaciones de cocina paga cuatro veces.

Esa es la grieta que justifica el proyecto: un sistema web autoalojado en el que la pantalla número
cinco cuesta lo que cuesta la pantalla, no lo que cuesta la licencia.

---

## 2. El sector

### 2.1. Tamaño y estructura

**Tabla 1 · Magnitudes verificadas**

| Magnitud | Valor | Fuente y año |
|---|---|---|
| Establecimientos de hostelería en España | 280.403 (+1,6 %) | UVE Data Market Horeca 2025, vía *Profesional Horeca*, junio 2025 |
| Hostelería independiente / restauración organizada | 93 % (+1,3 %) frente a 7,5 % (+6,2 %) | Ídem |
| Empleo en hostelería | 1,89 millones de media en 2025 (+2 %); 8,6 % del empleo español | Anuario de Hostelería de España, enero 2026 |
| Facturación 2025 | +2 % a +4 % sobre 2024 | Ídem |
| **Rentabilidad de la restauración** (hasta septiembre 2025) | **−0,9 %** (alojamiento: +2,1 %) | Ídem |
| Empresas activas en España | 3,31 millones (+1,7 %) | INE, DIRCE a 1/1/2025 (publicado 11/12/2025) |
| Empresas sin asalariados / con dos o menos | 54,4 % / 81,6 % | Ídem |
| Bares y restaurantes en la Comunitat Valenciana | 31.186 (3.ª comunidad); un bar por cada 174 habitantes | Consejo General de Economistas sobre el Anuario 2024, prensa 27/05/2025 |
| Establecimientos Horeca en la provincia de València | 13.698 | Ídem |

Dos lecturas importan. **La atomización:** el DIRCE no desglosa asalariados para el epígrafe de
servicios de comidas y bebidas, así que el porcentaje exacto de locales de restauración con menos de
diez empleados **no se ha podido verificar**; sí está verificado el marco general y el 93 % de
independientes. El cliente típico de un TPV en España no es una cadena con departamento de sistemas:
es un local de cuatro personas sin nadie que sepa de informática. **La tijera entre ingresos y
margen:** un sector que factura más y gana menos juzga una herramienta por lo que ahorra, no por su
lista de funciones. Ese es el criterio con el que hay que evaluar un KDS.

### 2.2. Digitalización: mucho cobro, poca cocina

Conviene ser prudente, porque casi todas las cifras de «digitalización hostelera» que circulan
proceden de estudios encargados por fabricantes de TPV.

- **Estadística pública.** En la *Encuesta sobre el uso de TIC y comercio electrónico en las
  empresas* del INE (año 2024, datos definitivos de 2025), el 84,5 % de las empresas tiene sitio web
  y el 26,6 % vendió por comercio electrónico. El desglose de hostelería para empresas de menos de
  diez empleados existe en INEbase, pero **no se ha podido verificar** su valor exacto aquí.
- **Origen comercial, citado como tal.** Glop sitúa entre el 65 % y el 70 % los pagos en España por
  medios digitales, con datos de más de 8.000 clientes propios (*El Independiente*, 21/05/2026). Es
  una muestra de clientes de un fabricante: indicio, no estadística.
- **Descartado.** Circulan porcentajes de «establecimientos altamente digitalizados» (del 15 % al
  22 % según la fuente) sin informe original localizable; no se incorporan.

Lo que sí sostienen las fuentes y los cuatro análisis internos es una asimetría cualitativa: la
digitalización de la hostelería española se ha concentrado en **el cobro** (datáfono, TPV, carta por
QR) y apenas ha llegado a **la producción**. Entre la caja y el fogón siguen mandando el papel y la
voz.

---

## 3. La normativa que empuja la digitalización

Buena parte de la demanda de TPV en España no nace del deseo de modernizarse, sino de una obligación
legal. Los plazos que siguen están verificados a septiembre de 2026, porque el calendario fiscal se
ha modificado dos veces.

**Ley 11/2021, de 9 de julio, antifraude.** Introdujo el artículo 29.2.j) de la Ley General
Tributaria, que prohíbe producir, comercializar y usar programas de facturación capaces de llevar
contabilidades distintas, no registrar operaciones o alterar registros. Es la norma que ilegaliza el
«software de doble uso»: para un TPV, obliga a que el registro de ventas sea íntegro y trazable.

**RD 1007/2023, de 5 de diciembre (Verifactu).** Desarrolla ese artículo y fija los requisitos de
todo sistema de facturación: registro por cada factura, encadenamiento mediante huella, firma,
trazabilidad, conservación y, opcionalmente, remisión automática a la AEAT. Su calendario se ha
aplazado dos veces: de julio de 2025 pasó, por el RD 254/2025, a enero y julio de 2026, y por el
**Real Decreto-ley 15/2025** (BOE de 3/12/2025, convalidado el 16/12/2025) al **1 de enero de 2027**
para contribuyentes del Impuesto sobre Sociedades y al **1 de julio de 2027** para el resto
(Garrigues, diciembre de 2025).

La lectura es doble. Es la oportunidad de mercado más clara —cientos de miles de locales deberán
revisar su sistema antes de julio de 2027— y a la vez una limitación que este informe debe declarar:
el sistema desarrollado emite facturas con numeración correlativa y sin huecos garantizada dentro de
la transacción de base de datos, pero **no implementa** encadenamiento por huella, firma ni remisión
a la AEAT, y por tanto **hoy no es conforme al RD 1007/2023**. Es una línea de trabajo, no una
característica.

**Ley 18/2022 «Crea y Crece» y RD 238/2026.** El artículo 12 obliga a emitir y recibir factura
electrónica en las operaciones entre empresas y profesionales establecidos en España. Su desarrollo
reglamentario, el **RD 238/2026 (BOE de 31/03/2026)**, define plataformas privadas y una solución
pública de la AEAT, admite los formatos UBL, CII, EDIFACT y Facturae conformes al modelo europeo
**EN 16931**, y fija plazos de **12 meses** para empresas de más de ocho millones de euros de
facturación y **24 meses** para el resto, contados desde la orden ministerial de desarrollo. Excluye
expresamente las **facturas simplificadas**, y esa excepción es decisiva: lo que un bar entrega a un
cliente particular es un tique o una factura simplificada, de modo que la norma le afecta sobre todo
**como receptor** de las facturas de sus proveedores. Para el diseño del sistema, la prioridad
funcional está en el tique y la factura simplificada bien numerados.

**Alérgenos: Reglamento (UE) 1169/2011 y RD 126/2015.** El reglamento europeo obliga a informar de
las catorce sustancias de su anexo II; el RD 126/2015, de 27 de febrero, regula en España la
información de los alimentos sin envasar para el consumidor final —el caso exacto de un plato
servido en un bar—, que debe estar disponible antes de formalizar la compra y con soporte documental
verificable. La traducción al software es directa: el alérgeno es un dato obligatorio del producto
que debe verse a la vez en la carta del cliente, en la pantalla del camarero y en la línea que llega
a cocina, tal como lo modela el sistema desarrollado ([../README.md](../README.md)).

**RGPD y LOPDGDD.** El Reglamento (UE) 2016/679 y la Ley Orgánica 3/2018 alcanzan a los datos del
personal (usuarios, PIN, productividad) y del cliente (NIF en factura completa, reservas, reparto).
Dos principios importan aquí: la **minimización** (art. 5.1.c), que la pantalla pública de recogida
aplica literalmente al exponer solo números de pedido y tiempos; y la **protección desde el diseño**
(art. 25), pues autoalojar reduce el número de encargados del tratamiento y la carga documental del
artículo 28. Sin exagerar la diferencia: autoalojar no exime de cumplir el RGPD, solo simplifica la
cadena de responsabilidad y traslada al titular del local la obligación de seguridad y copias.

---

## 4. La competencia

El mercado español tiene tres capas: el **software español clásico de licencia** (Glop, Ágora,
Cuiner, Camarero10), heredero del TPV Windows instalado en el local; las **plataformas en la nube**
(Revo, Last.app, Lightspeed, Square, Epos Now), que cobran suscripción y venden la integración con
el reparto a domicilio; y el **modelo gratuito con monetización indirecta** (Loyverse, TMBill).

**Tabla 2 · Trece productos con KDS presentes en España**

| Producto | Modelo de precio (fuente y fecha) | ¿KDS aparte? | ¿Nube? | Punto débil para un local pequeño |
|---|---|---|---|---|
| **Oracle MICROS Simphony** (EE. UU.) | **Sin tarifa pública**: se cotiza. Comparadores: Essentials **desde 55 $/mes** y Plus **desde 75 $/mes** por estación; terminal 2.500–8.000 $; instalación 500–8.000 $; 2,4–2,9 % por pago (Loman y TrustRadius, 09/2026) | **Sí: módulo aparte**, importe no publicado | Sí, con controlador **Windows** en el local | Pensado para cadenas: cuota por estación, equipo Windows por cocina y respaldo en otra máquina. Ver [ANALISIS_KDS_ORACLE_SIMPHONY.md](ANALISIS_KDS_ORACLE_SIMPHONY.md) |
| **Revo XEF** (ES) | **Sin precio público**: remite al distribuidor (09/2026) | Módulo de la suite | Sí | Opacidad de precio y coste por terminal; depende del distribuidor |
| **Glop** (ES) | Desde **19,90 €/mes** o **~299 €** en pago único; Mini desde 199 € y Pro desde 399 € sin IVA (distribuidores, 09/2026) | Módulo de cocina | No: instalación local | Windows obligatorio; cada pantalla añade licencia |
| **Ágora / IGT** (ES) | **Desde 32 €/mes**; también licencia perpetua por terminal (agorapos.com, 09/2026) | Incluido como monitor de cocina | Opcional | Modelo por terminal: cada puesto suma |
| **Cuiner** (ES) | **Sin precio público**; se cotiza por local (el módulo de reservas, desde 22 €/mes) | Módulo de cocina | Mixto | Precio no transparente; funciones troceadas |
| **Camarero10** (ES) | **Sin precio oficial**; comparadores lo sitúan en **30–50 €/mes** (tpvhosteleria.org, 2026) | Módulo | Sí | Coste final dependiente de los módulos |
| **Lightspeed** (CA) | 69–399 $/mes según plan (tarifa de EE. UU., julio 2026). **Precio en euros: no verificado** | **Sí: ~30 $ por pantalla y mes** (UpMenu, 2026) | Sí | El coste por pantalla castiga la cocina por estaciones |
| **Square** (EE. UU.) | Plan gratuito o **59 €/mes + IVA por punto de venta**, licencias ilimitadas; **1,25 % + 0,05 €** por pago presencial UE (squareup.com/es, 09/2026) | Existe; **coste separado no publicado** en España | Sí | El coste real está en la comisión, no en la cuota |
| **Loyverse** (LV/EE. UU.) | TPV, panel, **KDS y pantalla de cliente gratuitos**; complementos: 5 €/mes por tienda (histórico), 5 €/mes por empleado, 25 €/mes por tienda (inventario) (loyverse.com/es/pricing, 09/2026) | **No: gratuito** | Sí: datos en su nube | Los datos salen del local y el histórico completo se paga |
| **TMBill** (IN) | **Sin precio público** en euros | Aplicación aparte (Windows y Android) | Sí | No orientado al mercado español: soporte, idioma, fiscalidad |
| **Epos Now** (RU/ES) | **Sin precio público en España**: cotización personalizada (en EE. UU., 39 $/mes o 449 $ por 12 meses) | Complemento de su tienda de *apps* | Sí | Paquete con hardware y permanencia; precio opaco |
| **Last.app** (ES) | Starter **50 €**, Growth **95 €**, Unlimited **175 €**/mes con pago anual + **500 € de alta** (last.app/precios, 21/09/2026) | **Sí: 35 €/mes por local**, en ningún plan | Sí | Alta de 500 € y KDS de pago antes de vender nada |
| **Ordatic** (ES) | **39 €/mes** (300 pedidos) a **149 €/mes** sin límite (comparadores, 2026) | No es TPV: integrador de reparto | Sí | Resuelve solo el reparto |

Dos advertencias: las cifras en dólares son del mercado estadounidense y no trasladables sin más a
España, y cuando la fuente es un comparador y no el fabricante se indica, porque los comparadores no
siempre actualizan tarifas.

**El líder marca el patrón.** Oracle compró MICROS en 2014 por **5.300 millones de dólares**; MICROS
tenía entonces **6.600 empleados** y **330.000 locales de clientes en 180 países** ([nota de prensa de
Oracle](https://www.oracle.com/corporate/pressrelease/oracle-buys-micros-systems-062314.html)), y hoy
Oracle declara **~141.000 empleados** y **67.357 M$** de ingresos (10-K FY2026). Su KDS no es una
pantalla: es un **servicio Windows** (*KDS Controller*) que hace de puente entre el TPV y los monitores,
con el respaldo obligatoriamente en otra máquina y un controlador por cada cocina independiente
([documentación de Oracle](https://docs.oracle.com/en/industries/food-beverage/simphony/simcm/t_shared_services_overview_kdsc.htm)).
Es una respuesta proporcionada a una cadena de mil locales y desproporcionada para un bar de barrio:
ahí está la grieta que este proyecto aprovecha. Análisis completo en
[ANALISIS_KDS_ORACLE_SIMPHONY.md](ANALISIS_KDS_ORACLE_SIMPHONY.md).

**Lo que se ve al mirar los productos por dentro.** Los cuatro análisis internos, hechos con
descarga, transcripción y fotogramas clave de demostraciones reales, dicen cosas que ninguna tabla
de precios recoge. En [ANALISIS_KDS_COMPETENCIA.md](ANALISIS_KDS_COMPETENCIA.md) (STARPOS), el KDS
vive dentro del TPV: ver comandas exige un equipo Windows con el punto de venta instalado, no un
cliente ligero. En [ANALISIS_KDS_TMBILL.md](ANALISIS_KDS_TMBILL.md), nueve de los quince minutos de
la demostración oficial son instalación y configuración de un ecosistema que se vende entero.
[ANALISIS_KDS_LOYVERSE.md](ANALISIS_KDS_LOYVERSE.md) documenta una decisión de diseño que el mercado
casi no usa: tratar el KDS **como una impresora más**, lo que simplifica el encaminamiento pero ata
la pantalla al modelo de «imprimir en destino» en vez de al estado de la línea. Y
[ANALISIS_KDS_EPOSNOW.md](ANALISIS_KDS_EPOSNOW.md) reduce el producto a lo esencial en 47 segundos:
qué ocurre en cocina en el instante en que el camarero envía la comanda, que es el núcleo funcional
de todo KDS.

**Tres patrones se repiten** con independencia del fabricante: la unidad de facturación es el
terminal o la pantalla; el KDS casi nunca está incluido (solo en Loyverse, a cambio de ceder los
datos); y el precio no es público en cinco de los doce casos, lo que obliga al local pequeño a
negociar sin referencia.

---

## 5. El cliente

No todos los locales pequeños tienen el mismo problema. La segmentación siguiente es **elaboración
propia** a partir de la observación del flujo de trabajo descrita en la memoria y del funcionamiento
de los productos analizados; no procede de un estudio con muestra estadística.

**Tabla 3 · Segmentos y necesidad dominante (elaboración propia, 2026)**

| Segmento | Servicio | Qué necesita | Valor del KDS |
|---|---|---|---|
| Bar de barrio | Barra, rotación alta, ticket bajo, cocina mínima | Cobrar rápido, dividir cuentas, cerrar caja sin descuadres | **Bajo-medio**: basta una pantalla de pase; el valor está en el TPV |
| Hamburguesería o comida rápida | Picos cortos y densos, cocina por estaciones, mucho «para llevar» | Que cada línea llegue a su estación y el retraso se vea | **Alto**: caso canónico, y el del proyecto |
| Arrocería o restaurante de mantel | Pocas comandas, cocciones largas y desiguales | Sincronizar el pase: que los platos salgan a la vez | **Alto, con otra lógica**: importa el pase, no la velocidad |
| Cafetería | Mostrador, producto preelaborado | Cobro ágil y control de caja | **Bajo**: una pantalla de recogida aporta más |
| Dark kitchen | Sin sala; pedidos de plataformas | Agregar varias plataformas en una cola de producción | **Muy alto**, pero la pieza crítica es la integración, que el proyecto no cubre |

El valor del KDS crece con **el número de estaciones y la densidad del pico de servicio**. Por eso
acierta el proyecto al elegir una hamburguesería de cuatro estaciones, donde la diferencia entre
papel y pantalla es máxima, y por eso debe reconocer que en una cafetería de mostrador aporta poco.

---

## 6. Los proveedores del sector

Un TPV se apoya en cuatro cadenas de suministro, y cada una condiciona alguna decisión técnica.

**Alimentación.** El canal mayorista del local independiente es el *cash & carry*: **Makro** opera
37 establecimientos en España y lidera por superficie comercial en la Comunitat Valenciana, Madrid y
País Vasco, y **GM Cash** (Transgourmet Ibérica) tiene 74 centros en doce comunidades y más de
200.000 clientes anuales (*Inforetail* y gmcash.es, 2026). **Bidfood** opera en España como
distribuidor de hostelería, aunque **no se ha podido verificar** el número de plataformas logísticas
que mantiene. Su papel aquí es indirecto pero real: el albarán del proveedor es la entrada natural
del escandallo y del control de existencias, línea de trabajo futura del sistema.

**Hardware.** **Epson** (serie TM) y **Star Micronics** dominan la impresión de tiques, **Elo** las
pantallas táctiles de punto de venta y **Sunmi** los terminales Android integrados de bajo coste.
Frente a este grupo, la decisión relevante del proyecto es **no depender de la impresora**: el tique
y la factura se dibujan en pantalla a cuarenta columnas y se descargan, lo que elimina el
controlador del sistema operativo como punto de fallo y como atadura de marca.

**Pagos.** **Redsys** es la plataforma participada por la banca que encamina la mayoría de las
operaciones con tarjeta de los comercios españoles; **SumUp** compite en el datáfono autónomo sin
cuota; **Stripe** y **Adyen** son los adquirentes habituales de las plataformas que integran el pago
en el propio TPV, como Square. La diferencia es estructural: cuando el TPV integra el pago, el
fabricante se vuelve intermediario financiero y su ingreso deja de estar en la cuota. Este proyecto
registra el método de pago pero no procesa el cobro: limitación deliberada y garantía de
independencia.

**Reparto.** Glovo, Uber Eats y Just Eat concentran el pedido a domicilio en España y generan la
complejidad de la que vive la categoría de los integradores. Para la *dark kitchen* es la
funcionalidad decisiva; para el bar de barrio, apenas cuenta. El sistema no la aborda, y ese es su
límite de mercado más claro.

---

## 7. DAFO del proyecto frente al mercado

Esta matriz no repite la de la memoria, que mira al local simulado; aquí se mira al **mercado**.

| | Favorable | Desfavorable |
|---|---|---|
| **Interno** | El número de pantallas no es variable de coste, que es justo donde el mercado cobra. Funciona en cualquier navegador: no impone sistema operativo ni marca. Los datos no salen del local, lo que simplifica la cadena del RGPD | No cumple aún el RD 1007/2023, el requisito que decidirá compras en 2027-2028. No integra pagos ni plataformas de reparto. No hay soporte ni red comercial, y el mercado compra soporte tanto como software |
| **Externo** | Dos oleadas normativas obligan a renovar antes de julio de 2027. El 93 % de establecimientos independientes es sensible al coste recurrente. El hardware táctil barato abarata la pantalla adicional | Competidores consolidados con distribución capilar. Modelos «freemium» como Loyverse neutralizan la ventaja de precio. Concentración en suites que incluyen pagos y reparto |

Conviene no maquillar la coincidencia entre una debilidad y una oportunidad: la misma normativa que
abre el mercado es la que el sistema todavía no cumple.

---

## 8. Conclusión: por qué un KDS + TPV

### 8.1. Dónde pierde dinero un local pequeño

Cuando el margen se estrecha —facturación al alza y rentabilidad al −0,9 %—, el coste que más duele
no es el que aparece en la factura, sino el que nadie mide: la comanda mal leída que obliga a
rehacer un plato, la mesa que espera porque nadie sabe qué falta, el turno en que una sola persona
sostiene en la cabeza el orden de toda la cocina.

Este informe **no dispone de un dato verificado** sobre el porcentaje de comandas erróneas en
hostelería española, y no lo va a inventar. Lo que sostienen las fuentes reunidas es un razonamiento
en tres pasos: el sector está formado casi por completo por locales independientes dentro de un
tejido de microempresa; esos locales ya han digitalizado el cobro pero no la producción; luego el
margen de mejora disponible no está en cobrar mejor, sino en **el tramo que va de la comanda al
plato**, que es exactamente el tramo que cubre un KDS.

### 8.2. Por qué el KDS es la pieza que el mercado cobra aparte

El patrón de la sección 4 no parece casual. Lightspeed factura el KDS por pantalla y mes; Last.app
lo vende como complemento de 35 €/mes que ningún plan incluye; Glop, Ágora y Cuiner lo tratan como
módulo; Epos Now lo coloca en su tienda de complementos; STARPOS lo empotra en el TPV, de modo que
ver comandas exige otro equipo Windows completo.

La razón es económica y transparente: el KDS es el único componente del sistema que **se multiplica
de forma natural**. Un local tiene una caja y quizá dos comanderos, pero puede tener cuatro, cinco o
seis pantallas si su cocina está bien dividida en estaciones. Cobrar por pantalla convierte una
buena práctica de organización —repartir la producción— en un coste creciente, y penaliza justo la
conducta que el propio producto dice fomentar.

El efecto es perverso y observable. Con una tarifa por pantalla, el sobrecoste crece linealmente con
cada estación, y el local acaba juntando dos estaciones en una sola pantalla: menos claridad, más
errores, peor servicio. La decisión técnica la toma la factura, no la cocina.

### 8.3. Por qué un sistema web autoalojado cambia la ecuación

Tres consecuencias se siguen de la arquitectura elegida —HTML servido sobre HTTPS desde un servidor
propio en la red del local, con WebSocket para el tiempo real—, y cada una ataca un punto de lo
anterior.

**La pantalla adicional deja de tener licencia.** Si la interfaz de cocina es una página web, añadir
una estación cuesta lo que cuesta la pantalla: un dispositivo con navegador y una dirección. El
presupuesto de la memoria cifra en 180 € la pantalla con soporte, pago único, frente a una cuota que
se repite cada mes mientras el local exista. La variable de coste desaparece y la decisión vuelve a
ser de organización de la cocina.

**Los datos se quedan dentro.** Ventas, tiempos de cocina y datos del personal residen en una base
de datos accesible solo por socket local. Esto no exime de cumplir el RGPD, y conviene decirlo sin
triunfalismo: traslada al titular del local la responsabilidad de la seguridad y de las copias. Pero
elimina un encargado del tratamiento de la cadena y, con él, el contrato del artículo 28, la
verificación de la ubicación del tratamiento y la dependencia de que un proveedor siga existiendo.

**El sistema operativo deja de importar.** Es el contraste más nítido con los análisis internos:
STARPOS exige Windows con el TPV instalado en cada puesto de cocina y TMBill distribuye aplicaciones
distintas para Windows y Android. Aquí sirve cualquier navegador reciente —una tableta vieja, un
portátil reutilizado, un mini-PC con una pantalla de segunda mano— y no hay nada que instalar ni
actualizar en las pantallas. El único equipo que mantener es el servidor, y es también el único que
necesita copia de seguridad.

### 8.4. Respuesta a la pregunta

Se eligió un KDS + TPV porque ahí coinciden tres cosas que rara vez coinciden: un mercado grande y
atomizado, una necesidad real que el sector dejó sin cubrir mientras digitalizaba el cobro, y un
modelo de precio de la competencia que penaliza justo la solución correcta.

Y se eligió construirlo **autoalojado y sobre web** porque esa decisión no es estética: es la que
hace el argumento demostrable. El proyecto no compite en funciones —el mercado está cubierto, como
reconoce la propia memoria— sino en una afirmación estructural: en un local pequeño, el número de
pantallas de cocina debería ser una decisión de cocina y no de tesorería.

Queda dicho con la misma franqueza lo que falta: conformidad con el RD 1007/2023, integración de
pagos y de plataformas de reparto, y alguien que dé soporte. Un informe de mercado honesto describe
la grieta que justifica el proyecto y también la distancia que lo separa de un producto.

---

## 9. Bibliografía

Formato APA 7.ª edición. Enlaces consultados el 21 de septiembre de 2026.

Ágora TPV. (2026). *Precios de software TPV y suscripciones*. https://www.agorapos.com/pricing/

El Independiente. (2026, 21 de mayo). *La digitalización silenciosa impulsa el uso del software TPV
en la hostelería española*. https://www.elindependiente.com/eli/2026/05/21/la-digitalizacion-silenciosa-impulsa-el-uso-del-software-tpv-en-la-hosteleria-espanola/

El Periòdic. (2025, 27 de mayo). *Un bar cada 174 valencianos: la Comunitat Valenciana, tercera con
más bares y restaurantes*. https://www.elperiodic.com/cada-valencianos-comunitat-valenciana-tercera-bares-restaurantes_1018629

España. (2015). *Real Decreto 126/2015, de 27 de febrero* (información alimentaria de alimentos sin
envasar). BOE, 54. https://www.boe.es/buscar/act.php?id=BOE-A-2015-2293

España. (2018). *Ley Orgánica 3/2018, de 5 de diciembre, de Protección de Datos Personales y
garantía de los derechos digitales*. BOE, 294. https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673

España. (2021). *Ley 11/2021, de 9 de julio, de medidas de prevención y lucha contra el fraude
fiscal*. BOE, 164. https://www.boe.es/buscar/act.php?id=BOE-A-2021-11473

España. (2022). *Ley 18/2022, de 28 de septiembre, de creación y crecimiento de empresas*. BOE, 234.
https://www.boe.es/buscar/act.php?id=BOE-A-2022-15818

España. (2023). *Real Decreto 1007/2023, de 5 de diciembre* (requisitos de los sistemas informáticos
de facturación). BOE, 291. https://www.boe.es/buscar/act.php?id=BOE-A-2023-24840

España. (2026, 31 de marzo). *Real Decreto 238/2026* (desarrollo reglamentario de la factura
electrónica entre empresarios y profesionales). BOE.

Garrido Abogados. (2026). *Real Decreto 238/2026: se aprueba el desarrollo reglamentario de la
factura electrónica*. https://garrido.es/real-decreto-238-2026-aprueba-el-desarrollo-reglamentario-de-la-factura-electronica/

Garrigues. (2025, diciembre). *Se retrasa la entrada en vigor de Veri\*factu*.
https://www.garrigues.com/es_ES/noticia/retrasa-entrada-vigor-verifactu

GM Cash / Transgourmet Ibérica. (2026). *Quiénes somos*. https://www.gmcash.es/quienes-somos/

Hosteltur. (2026, 5 de enero). *La hostelería alcanza los 1,89 millones de empleados en 2025 pero ve
amenazada su rentabilidad* [datos del Anuario de Hostelería de España]. https://www.hosteltur.com/173449_la-hosteleria-alcanza-los-189-millones-de-empleados-en-2025-pero-ve-amenazada-su-rentabilidad.html

Inforetail. (2025). *Makro y GM Cash lideran el cash&carry en tres comunidades autónomas*.
https://www.revistainforetail.com/

Instituto Nacional de Estadística. (2025, 11 de diciembre). *Directorio Central de Empresas (DIRCE).
Datos a 1 de enero de 2025* [Nota de prensa]. https://www.ine.es/dyngs/Prensa/DIRCE2025.htm

Instituto Nacional de Estadística. (2025). *Encuesta sobre el uso de TIC y del comercio electrónico
en las empresas. Año 2024 – 1.er trimestre de 2025* [Nota de prensa].
https://www.ine.es/dyngs/Prensa/ETICCE20241T2025.htm

Last.app. (2026). *Un precio para cada restaurante*. https://www.last.app/precios

Loyverse. (2026). *Precios*. https://loyverse.com/es/pricing

Makro España. (2026). *Cash and carry*. https://www.makro.es/compra-como-quieras/cash-and-carry

Profesional Horeca. (2025, junio). *La hostelería en España en 2025: 280.400 establecimientos,
transformación y consolidación* [datos de UVE Data Market Horeca 2025].
https://www.profesionalhoreca.com/la-hosteleria-en-espana-en-2025-280-400-establecimientos-transformacion-y-consolidacion/

Square. (2026). *Precios de Square en España*. https://squareup.com/es/es/pricing

TPV Hostelería. (2026). *Camarero10: reseñas y opiniones*. https://tpvhosteleria.org/camarero10/

Unión Europea. (2011). *Reglamento (UE) n.º 1169/2011 sobre la información alimentaria facilitada al
consumidor*. DOUE, L 304. https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX%3A32011R1169

Unión Europea. (2016). *Reglamento (UE) 2016/679 (RGPD)*. DOUE, L 119.
https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX%3A32016R0679

UpMenu. (2026). *Lightspeed POS pricing for restaurants: fees and hidden costs*.
https://www.upmenu.com/blog/lightspeed-pos-pricing/

VentaTPV. (2026). *Software Glop TPV: precios, versiones y características*.
https://ventatpv.com/content/34-tpv-glop

**Fuentes internas del proyecto.** RocaPV (2026): `docs/MEMORIA.md`;
`docs/ANALISIS_KDS_COMPETENCIA.md` (STARPOS); `docs/ANALISIS_KDS_TMBILL.md`;
`docs/ANALISIS_KDS_LOYVERSE.md`; `docs/ANALISIS_KDS_EPOSNOW.md`; y `README.md` del repositorio.

---

### Limitaciones de este informe

No se ha podido verificar, y por tanto no se afirma: el porcentaje de establecimientos de
restauración con menos de diez empleados en fuente primaria del INE; el desglose sectorial de la
encuesta TIC del INE para hostelería de menos de diez empleados; el precio en euros de Lightspeed
Restaurant y de Epos Now para España; el coste separado del KDS de Square; la tarifa oficial de Revo
XEF, Cuiner, Camarero10 y TMBill; el número de plataformas logísticas de Bidfood en España; y
cualquier cifra sobre porcentaje de comandas erróneas en hostelería.
