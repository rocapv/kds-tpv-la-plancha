# Análisis de un KDS comercial (Epos Now) · el envío de la comanda, paso a paso

Tercer estudio de competencia. Epos Now es un TPV británico con delegación en España, y este vídeo
es lo contrario de los dos anteriores: 47 segundos, sin narración y con **la pantalla partida en
dos**, TPV a la derecha y KDS a la izquierda. No enseña a instalar nada ni vende el ecosistema;
enseña una sola cosa, que es justo la que nos interesa: **qué pasa en la cocina en el instante en
que el camarero envía la comanda**.

Vale la pena precisamente por eso. TMBill dedicaba nueve de sus quince minutos a instalar y
configurar; aquí el 100 % del metraje es el flujo en funcionamiento.

## Ficha

| Dato | Valor |
|---|---|
| Vídeo | «Comandas en KDS (Kitchen Display System)» |
| Canal | Epos Now ES |
| Publicado | 10 de octubre de 2025 · 906 visitas |
| Duración | 47 s |
| Resolución | 1920×1080, 30 fps |
| Idioma | **Ninguno**: no hay voz, solo música de fondo |

## Cómo se ha procesado

La misma cadena de los dos análisis anteriores: `yt-dlp` desde Raspa, `ffmpeg` para el audio y los
fotogramas, faster-whisper en la GPU de Pecera y selección de fotogramas clave por diferencia.

| Paso | Resultado |
|---|---|
| Fotogramas a 10 fps (escalados a 960 px) | 472 imágenes, 15 MB |
| Transcripción | **0 segmentos** · sin habla |
| Fotogramas clave | 20 momentos de cambio real |

**Fotogramas prácticamente idénticos al anterior: 86 %** (cambio medio 0,86 sobre 255). Confirma lo
que ya sabíamos por TMBill: esto es una **captura de pantalla por software**, no un vídeo grabado
con una cámara. El listón que veníamos usando (>90 % captura, ~0 % cámara) se sostiene, aunque aquí
el porcentaje baja algo porque el vídeo es corto y arranca con una animación de logotipo y una
transición a pantalla completa, segundos en los que *todo* cambia y que tiran la media hacia abajo.
La lectura correcta no es «no es captura», sino «es captura con cabecera animada».

**La transcripción salió vacía, y es el resultado correcto.** El audio tiene nivel (media −27 dB,
pico −2,2 dB) pero el detector de voz no encontró habla; repetido sin el filtro de voz, el
resultado fue el mismo. Es un vídeo mudo con música. Se deja constancia porque «0 segmentos» podría
confundirse con un fallo de la cadena, y no lo es: aquí toda la información está en la imagen. Se
comprobó antes de darlo por bueno, midiendo el volumen y reintentando sin filtro.

## Qué enseña, paso a paso

| Momento | Contenido |
|---|---|
| 0:00–0:08 | Animación del logotipo y transición a la pantalla partida |
| 0:09–0:13 | **Estado de reposo del KDS** (izquierda): fondo azul, un tic grande y «No orders to show», contador **«0 ORDERS IN QUEUE»** y dos botones fijos abajo, **RECALL ORDER** (recuperar una comanda ya cerrada) y **MOVE TICKET** (pasarla a otra pantalla). A la derecha, el TPV: usuario «Manuel Gerente», caja TILL10, fecha, y las pestañas PRODUCTOS · CLIENTES · PEDIDOS · CUENTAS Y MESAS |
| 0:13–0:19 | **Se compone la comanda** en el TPV: categorías en cuadrícula de colores (CAFE, CAVA, CERVEZAS, COCKTAILS, CRUJIENTE…) paginadas, y dentro de cada una los productos con precio. El ticket de la derecha lleva **MESA 5 y COMENSALES 4**, y columnas Producto / Cant. / Cada uno / Total |
| 0:19 | Detalle importante: bajo tres líneas de «Bravas» aparece **«Promoción 3 Bravas por 15 €»** con su descuento en negativo línea a línea. Abajo, **DESCUENTO TOTAL 2,10 €**, un interruptor de **SERVICIO**, y TOTAL / POR PAGAR / IMPUESTO separados |
| 0:21–0:24 | Se pulsa **PEDIR/APARTAR** —no PAGAR— y la comanda **aparece al instante en el KDS**: tarjeta con etiqueta **NEW**, cabecera verde, **ORDER A-15**, **TABLE 5**, **STARTED AT 04:49 PM**, la fila **EAT-IN | MANUEL GERE…** y las cinco líneas, cada una con **su propia casilla** a la derecha. El contador pasa a «1 ORDERS IN QUEUE» |
| 0:24–0:30 | El **cronómetro** de la esquina de la tarjeta corre solo: 0:00 → 0:02 → 0:04. Mientras tanto el TPV ya ha vuelto a estar libre |
| 0:27 | **Plano de mesas**: pestañas CUENTAS / SALÓN PRINCIPAL / **TERRAZA** / BARRA, mesas numeradas con su número de comensales entre paréntesis, y una leyenda de estados por color —SENTADOS, MAIN, BEBIDAS, POSTRES, **WAITING TO PAY**— más DISPONIBLE / SELECCIONADO / ACTIVO / MOVER |
| 0:35–0:45 | Se monta y envía una **segunda comanda**. El KDS las coloca **lado a lado**, A-15 con 0:17 y A-16 recién llegada con 0:00, y el contador marca «2 ORDERS IN QUEUE» |

## Lo que se aprende para este proyecto

**1. La comanda se envía sin cobrar, y ese botón es el corazón del sistema.** El botón que dispara
la cocina es PEDIR/APARTAR, y está separado de PAGAR. Parece obvio, pero es la decisión de diseño
que sostiene todo lo demás: la mesa puede pedir tres veces a lo largo de la cena y pagar una sola
al final. Nuestro TPV ya funciona así; esto lo confirma como el camino correcto y no como un atajo.

**2. Una casilla por línea, no un botón por comanda.** Su tarjeta tiene una casilla junto a *cada*
producto. Eso permite que el cocinero marque las bravas cuando salen sin esperar a los buñuelos, y
que de un vistazo se vea qué falta de cada mesa. Nosotros hoy movemos la comanda entera de estado.
Es la mejora más barata y más útil de las tres.

**3. El cronómetro empieza en la tarjeta, no en un informe.** Cada comanda muestra el tiempo que
lleva esperando, en grande y arriba, y además la hora exacta de entrada («STARTED AT»). Las dos
cosas juntas son las que hacen que el color por retraso signifique algo. Ya tenemos el cronómetro;
nos falta mostrar la hora de entrada, que es la que sirve para reclamar cuando alguien discute.

**4. El estado de reposo también comunica.** Cuando no hay nada, la pantalla no se queda en blanco:
dice «no hay comandas» con un tic. En una cocina eso distingue «está todo servido» de «la pantalla
se ha colgado», que es una duda real a las tres de la tarde.

**5. RECALL ORDER: deshacer un cierre por error.** Un botón permanente para recuperar una comanda
ya marcada como servida. En cocina se pulsa mal constantemente; sin esa salida, el error obliga a
salir a preguntar a sala. Nuestro KDS tiene un deshacer, pero conviene que sea igual de visible.

**6. El plano de mesas con estado de servicio.** Sus mesas no solo están libres u ocupadas: llevan
por dónde va la comida (bebidas, principal, postres, esperando pagar). Es información que el TPV ya
tiene y que sale gratis, y le dice al camarero a qué mesa acercarse sin recorrer la sala.

**7. Un aviso sobre idiomas.** Su TPV está en español pero el KDS sigue en inglés: «No orders to
show», «ORDERS IN QUEUE», «EAT-IN». Un producto grande con una traducción a medias. Como el nuestro
va a ser bilingüe, conviene que las dos pantallas se traduzcan a la vez y desde el mismo sitio, no
cada una por su cuenta.

## Conclusión

Es el vídeo más corto de los tres y el que más aprovechamos, porque la pantalla partida enseña el
único momento que de verdad importa: la comanda sale del TPV y está en cocina antes de que el
camarero levante el dedo. No hay retardo visible, no hay confirmación, no hay impresora.

De aquí salen tres tareas concretas y acotadas, por orden de valor: **casilla por línea de
producto** en la tarjeta del KDS, **hora de entrada** junto al cronómetro, y **estado de servicio
en el plano de mesas** del TPV. Las tres son añadidos sobre lo que ya funciona; ninguna obliga a
rehacer nada.

---

Material de trabajo (vídeo, 472 fotogramas y 20 fotogramas clave) en el directorio temporal de la
sesión; no se guarda en el repositorio porque es contenido de terceros.
