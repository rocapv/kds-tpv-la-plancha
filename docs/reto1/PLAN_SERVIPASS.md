# Reto 1 · Cambio de enfoque: la empresa es ServiPass

Plan del 30/10/2026, borrador. Todavía no se ha tocado `contenido.js`.

**Enfoque nuevo.** El informe deja de analizar una hamburguesería y pasa a analizar **ServiPass**, la
empresa del equipo: **soluciones de IT para hostelería** (definición del 30/10). El KDS + TPV es su
producto estrella, pero no el único: red, wifi de clientes, puesto de caja, Verifactu, copias,
videovigilancia, ciberseguridad y soporte. **Burglar King, Hundred
Burgers y Goiko se mantienen**: Burglar King como cliente piloto y caso práctico; Hundred y Goiko como
empresas de referencia del apartado 2, como ahora.

**Idea de fondo.** Casi todo lo del informe actual sirve, pero leído desde el otro lado:
- lo que para Burglar King era un **coste** (5.000-8.000 € de proyecto, Verifactu, fin de Windows 10)
  es ahora el **ingreso** y la **demanda** de ServiPass;
- el diagnóstico de la infraestructura de Burglar King (1.4) es la **auditoría inicial** de un cliente;
- el análisis de los trece productos con KDS (`docs/INFORME_MERCADO.md`, `docs/competencia/`) pasa a
  ser la **competencia** de ServiPass;
- el censo simulado de cien locales (`docs/mercado/locales.json`) es la **cartera de clientes potenciales**.

## Apartado por apartado

| Apartado | Qué dice ahora | Qué dirá |
|---|---|---|
| Portada, cabecera y pie | «Burglar King: contextualización de la empresa y análisis de su entorno económico»; logo de Burglar King | «ServiPass: contextualización…»; empresa, cabecera y pie con ServiPass; **logo de ServiPass generado en Pecera con la GPU** |
| 1. Contextualización | Hamburguesería de Burjassot junto al campus; CNAE 56.10; 13 mesas | Empresa de soluciones de IT para hostelería: diseña, instala y mantiene la tecnología de bares y restaurantes pequeños, con el KDS + TPV autoalojado como producto propio; CNAE 62.02 (consultoría informática) y 62.09 (otros servicios TIC); origen: el proyecto KDS + TPV del ciclo |
| 1.1. Ficha | Razón social, local de 120 m², 6 personas, horario de comidas, ticket, canales | ServiPass, sin forma jurídica; socios: Riches Manuel y Roca; sede en Burjassot; fundada en 2026; ámbito (área metropolitana de València); catálogo de servicios; horario de soporte |
| 1.2. Estructura organizativa | Organigrama plano: encargado, sala, cocina, externos | Organigrama de ServiPass: dirección y comercial, implantación (red y hardware), desarrollo del software, soporte; externos: gestoría, mayorista de hardware, hosting/GitHub. **Figura nueva** |
| 1.3. Flujos de trabajo | Procesos del restaurante (comanda en papel, cobro, cierre de caja…) y sus problemas | Ciclo de un cliente: captación → visita y auditoría → presupuesto → instalación (red, equipos, software, Verifactu) → formación → puesta en marcha en un servicio real → soporte. Con herramienta y riesgo de cada paso |
| 1.4. Infraestructura | Inventario de Burglar King (PC de 2015, red plana, grabador expuesto) y esquema de red | **Infraestructura propia** de ServiPass (portátiles, repositorio, maqueta de laboratorio, kit de instalación, copias). El inventario de Burglar King **no se pierde**: pasa al apartado 5 como auditoría del cliente piloto, con su esquema de red |
| 2. Empresa de referencia | Hundred Burgers (referencia) y Goiko (contrapunto) frente a Burglar King | **Se mantienen Hundred (referencia) y Goiko (contrapunto)** (decidido el 30/10), pero se leen como modelos de empresa para ServiPass. **2.1 Hundred:** especializarse en pocas cosas bien hechas y crecer despacio → ServiPass solo trabaja para hostelería, con un catálogo corto, en vez de hacer «informática para todos»; empieza por hamburguesería y comida rápida, donde el KDS rinde más. **2.2 Goiko:** crecer deprisa con costes fijos altos lleva a pérdidas → ServiPass no puede firmar más instalaciones de las que puede mantener; el soporte limita el crecimiento. **2.3 tabla:** la columna Burglar King pasa a ser **ServiPass** (origen, plantilla, ingresos, ingresos por persona, precio medio = precio por instalación, peso del mantenimiento frente a la instalación, catálogo, propiedad). Además, las dos cadenas son el segmento de cliente al que ServiPass **no** se dirige (tienen departamento de sistemas propio) |
| 3.1. PESTEL | Factores vistos desde un restaurante: Verifactu como obligación, IPC que encarece la materia prima, APPCC, alérgenos, bisfenol en tickets | Factores vistos desde un integrador. **Político/legal:** Verifactu y fin de Windows 10 como **motor de demanda**; fin del Kit Digital; ServiPass es **encargado del tratamiento** de sus clientes (art. 28 RGPD); responsabilidad por software de facturación (art. 201 bis LGT, también para quien lo produce); garantía de los equipos. **Económico:** IPC 4,9 % y su efecto en los salarios y en los presupuestos de los clientes; sector TIC. **Social:** escasez de técnicos; cliente poco digital. **Tecnológico:** web autoalojada, tabletas baratas, wifi 6. **Ambiental:** RAEE de los equipos sustituidos (RD 110/2015), facturación sin papel |
| 3.2. Microentorno | Clientes del restaurante (estudiantes 45 %…), proveedores del restaurante, competencia de barrio | **Clientes:** segmentos de hostelería (tabla de `INFORME_MERCADO.md`) y Burglar King como early adopter. **Proveedores:** mayoristas de hardware, operadoras, gestoría. **Competencia:** en el producto, las tres capas del mercado y los trece productos con KDS (Revo, Glop, Ágora, Last.app, Loyverse…); en el servicio, los distribuidores de TPV y las tiendas de informática del barrio, que hacen la instalación pero no conocen la cocina |
| 4. Modelo de negocio | Ventas de 45.000 €/mes por canales; cuenta de resultados del restaurante (EBITDA 8.190 €); punto muerto 32.400 € | Ingresos de ServiPass por línea de negocio: **proyectos KDS + TPV** (precio por proyecto, el rango de 5.000-8.000 € que antes era coste de Burglar King), **trabajos de infraestructura** sueltos (red, wifi, cámaras), **reventa de equipos** con margen y **ampliaciones** (lo que la licencia no cubre). **Modelo de precio (decidido el 30/10): pago único por la implantación + licencia del software por diez años**, que se paga una vez por década. En las cuentas, la licencia cobrada por adelantado se reparte como ingreso a lo largo de los diez años (periodificación) y deja tesorería al principio. El argumento comercial es que se paga una vez por década, frente a la cuota mensual por terminal de la competencia (Last.app, Lightspeed, Revo); número de instalaciones al año; cuenta de resultados, punto muerto en instalaciones al mes y sensibilidad. **Todo nuevo** |
| 4.1. Financiación | 60.000 € de Burglar King en 2022; tabla de fuentes para pagar el proyecto | Capital de los socios, capitalización del paro, ENISA Jóvenes Emprendedores, microcrédito MicroBank, ayudas de LABORA al emprendimiento. La tabla de fuentes **se reutiliza en parte** (MicroBank e ICO siguen; Digitaliza-CV y Kit Digital se releen desde el proveedor) |
| 4.2. Salarios | Convenio de hostelería de Valencia; camareros, cocinero, ayudante | Los dos socios trabajadores (Riches Manuel y Roca), con una retribución fijada y sin detallar el régimen. Si se contrata a un técnico de sistemas, el convenio estatal de **consultoría, tecnologías de la información y estudios de mercado** y la cotización empresarial de 2026 |
| 4.3. Gastos materiales | Escandallo de la hamburguesa; electricidad, gas, envases | Equipos que se compran para revender o instalar (miniPC, tabletas, switch, AP, SAI, impresora), herramientas y material de cableado, vehículo o desplazamientos, licencias, hosting, seguro de responsabilidad civil profesional |
| 4.4. Locales | Alquileres de Burjassot y el local de 120 m² con salida de humos | **Misma tabla de anuncios de Burjassot**, leída para una oficina o almacén pequeño (el de 40 m² junto al campus por 550 € encaja), o un coworking. La parte de obras en el local alquilado pasa a «qué hay que pedir al propietario del cliente» |
| 5. Servicios prestados | Servicios del restaurante (sala, barra, para llevar, reparto, reservas…) y flujo de la comanda en papel | Catálogo de ServiPass en tres bloques. **Producto:** KDS + TPV con Verifactu y carta digital. **Infraestructura:** auditoría, red segmentada (negocio, clientes, cámaras), wifi en sala y terraza, puesto de caja, SAI, copias de seguridad, videovigilancia conforme a la LOPDGDD. **Servicio:** migración de la carta, formación, soporte y mantenimiento, ciberseguridad básica. **Caso Burglar King:** su inventario, la red actual y el flujo de comanda en papel (las figuras que ya existen) como antes, y lo que ServiPass instala como después |
| 6. Publicidad | Marketing de la hamburguesería (Google, Instagram, menú universitario, fidelización) | Marketing **entre empresas**: visita en persona con el mapa de cien locales, Burglar King como caso de éxito con demostración en vivo, asociaciones de hostelería, ferias del sector, Google y LinkedIn, gestorías como canal de recomendación |
| 7. Conclusiones | Burglar King es viable pero optimista; Verifactu y Windows 10 obligan a renovar | ServiPass es viable si consigue N instalaciones al mes; Verifactu y el fin de Windows 10 abren una ventana hasta el 1/1/2027 (sociedades) y el 1/7/2027 (resto) |
| Referencias | APA 7 de hostelería, convenio, Hundred, Goiko | Se mantienen las que sigan citadas; se añaden competencia, convenio TIC y ayudas al emprendimiento |

## Lo que arrastra el cambio fuera del informe

- `generar_html.py`, `guion.json` y la presentación HTML: hay que rehacerlos con el nuevo enfoque.
- `laboratorios/` (hora punta, red, Verifactu): siguen valiendo como demostraciones de ServiPass sobre
  el caso Burglar King; solo cambian los textos de presentación.
- Figuras: `organigrama` y `costes` se rehacen; `red_actual` y `flujo_comanda` se quedan (caso
  Burglar King).
- La revisión del tribunal (`revision_reto1/`) era sobre la hamburguesería: la mayoría de sus
  observaciones de Economía y Empresariales caducan. Lo legal (RGPD, videovigilancia, factura
  simplificada) se conserva como auditoría que ServiPass hace al cliente.

## Decisiones abiertas

1. ~~Hundred y Goiko~~ → **decidido el 30/10: siguen como empresa de referencia** (apartado 2).
2. ~~Datos de ServiPass~~ → **decidido el 30/10: socios Riches Manuel y Roca; no se pone forma
   jurídica.** Consecuencias: la ficha no lleva razón social (solo «ServiPass»); la cuenta de
   resultados llega hasta el resultado antes de impuestos, sin elegir entre impuesto sobre sociedades e
   IRPF; los socios aparecen como socios trabajadores, sin detallar su régimen de cotización.
   Pendientes, con valor por defecto si no se dice otra cosa: **sede en Burjassot** (se reutiliza la
   tabla de alquileres) y **fundación en 2026**, con el proyecto del ciclo.
3. ~~Modelo de precio~~ → **decidido el 30/10: pago único por la implantación + licencia por década.**
   **La licencia incluye actualizaciones (Verifactu y cambios legales) y soporte; no incluye
   ampliaciones** (decidido el 30/10): módulos o funciones nuevas, más pantallas o terminales y
   trabajos a medida se presupuestan aparte. Los equipos duran menos que la licencia (unos 5 años una
   tableta), así que su sustitución también se cobra aparte. En las cuentas, el soporte incluido es un
   coste fijo durante diez años: el precio de la licencia tiene que cubrirlo.
4. ~~Logo de ServiPass~~ → **decidido el 30/10: lo genera Pecera con la GPU** (imagen fija; en la
   1080 Ti caben Flux-schnell GGUF y SDXL). Se usa en portada, cabecera y pie. Los de `docs/logos/`
   son de Burglar King y se quedan para el caso del cliente.
