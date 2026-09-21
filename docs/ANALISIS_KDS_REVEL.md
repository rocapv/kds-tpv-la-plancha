# Análisis de un KDS comercial (Revel Systems) · la pantalla y su configuración

Cuarto estudio de competencia. Es un vídeo cortísimo —menos de un minuto— de marketing de **Revel
Systems**, un TPV estadounidense para iPad, subido por un revendedor. Por brevedad se podría
descartar, pero tiene dos fotogramas que valen más que muchos tutoriales largos: **la pantalla real
del KDS con tres comandas en tres estados distintos**, y **la ficha de producto del back office
donde se configura qué se imprime y a qué estación va cada plato**. Justo las dos piezas que este
proyecto está decidiendo ahora mismo.

## Ficha

| Dato | Valor |
|---|---|
| Vídeo | «Revel's Kitchen Display System (KDS)» |
| Canal | Mac4U IT Services (revendedor de Revel, no la propia Revel) |
| Publicado | 26 de septiembre de 2018 |
| Duración | 52 s |
| Resolución | 1280×720, 30 fps |
| Idioma | Inglés (locución sobre imágenes) |
| URL | https://www.youtube.com/watch?v=5vVwk86Gasg |

## Cómo se ha procesado

La misma cadena de los análisis anteriores, sin variaciones, que es precisamente la gracia de
tenerla escrita: `yt-dlp` desde **Raspa** (para no castigar la IP de Pecera, que hoy ya había
recibido un 429 de YouTube; se descargó **sin subtítulos**, que fue lo que disparó aquel aviso),
copia del `.mp4` a Pecera por `scp`, `ffmpeg` para audio y fotogramas, **faster-whisper** en la GPU
de Pecera y selección de fotogramas clave por diferencia entre imágenes consecutivas.

| Paso | Resultado |
|---|---|
| Descarga | 5,9 MB, vídeo 720p + audio, fusionados a mp4 |
| Audio | WAV mono a 16 kHz (lo que espera Whisper) |
| Fotogramas a 10 fps (escalados a 960 px) | **522 imágenes** |
| Transcripción | **20 segmentos**, idioma detectado **inglés** |
| Fotogramas clave | **10 momentos de cambio real** |

Dos decisiones técnicas que se repiten y conviene no olvidar: el modelo se carga con
`compute_type="int8_float32"` porque la GPU es una 1080 Ti (arquitectura Pascal, donde `float16` no
funciona), y se transcribe con `multilingual=True` porque sin esa opción el modelo **traduce** en
vez de transcribir. Aquí el original ya era inglés y no se habría notado, pero el hábito es el que
salva el análisis cuando el vídeo viene en otro idioma.

**Fotogramas prácticamente idénticos al anterior: 38 %** (cambio medio 4,73 sobre 255). Este número
es un diagnóstico, no una curiosidad. En los análisis anteriores quedó establecido que una captura
de pantalla por software da **más del 90 %** de fotogramas repetidos (la pantalla está quieta entre
acción y acción) y un vídeo grabado con cámara apuntando a un monitor da **cerca del 0 %** (el
sensor nunca produce dos imágenes iguales). Un 38 % no es ninguna de las dos cosas: delata un vídeo
**mixto**, montaje de metraje de cocina rodado con cámara intercalado con capturas limpias de la
aplicación. Y eso cambia cómo hay que leerlo: solo una parte pequeña de los 52 segundos contiene
interfaz aprovechable, así que el trabajo está en localizar esos fotogramas concretos y no en ver
el vídeo entero. Pedir 20 fotogramas clave devolvió solo 10 porque el script exige 4 segundos de
separación entre claves y el vídeo no da para más; con material tan corto ese mínimo es el que
manda, no la cifra pedida.

## Qué enseña, paso a paso

| Momento | Contenido |
|---|---|
| 0:00–0:07 | Rótulo sobre cocina real. El argumento de venta se abre por el dolor: tiques de papel e impresoras ocupando la cocina |
| 0:09–0:13 | El pedido viaja **del TPV a la cocina automáticamente**, sin papel de por medio. Plano de un iPad montado en brazo articulado sobre el pase, y una tableta suelta en mano de cocina |
| 0:14–0:17 | Dos beneficios explícitos: eliminar el tique y **aumentar la exactitud del pedido** |
| 0:18–0:22 | «El KDS muestra los pedidos en cola y los mantiene en pantalla hasta que se completan» — es decir, la comanda no desaparece hasta que alguien la cierra a mano |
| **0:23–0:27** | **Captura real del KDS.** Ver el desglose de abajo: es el fotograma más valioso del vídeo |
| 0:28–0:30 | Metraje de pase: plato emplatado, pilas de vajilla y una tableta KDS montada al fondo, a la altura de la vista del cocinero |
| 0:31–0:38 | Enrutado por estaciones: personal especializado puede **asignar ciertos productos y pedidos a estaciones concretas** para que la cocina fluya |
| **0:34** | **Captura del back office de Revel**: ficha de producto, pestaña *Display/Print Options* — donde se configura ese enrutado |
| 0:39–0:47 | Metraje de mostrador con dos iPads en soporte e impresora Epson al lado; cierre de marca «el TPV completo para tu negocio» |

### La pantalla del KDS (0:23) en detalle

Tres tarjetas en columna, cada una una comanda, y las tres en **estados distintos a propósito**:

- **Cabecera azul** con número de comanda (957, 960, 961), tipo de servicio (**To Go**), camarero
  que la tomó (*Server: Tessa S*) y un **cronómetro por comanda contando hacia arriba**
  (00:06:01, 00:01:48, 00:00:30). No es una hora de entrada: es tiempo transcurrido, que es lo que
  de verdad ordena la urgencia en un pase.
- **Un botón por comanda que cambia de texto y de estado según el contenido**: la comanda 957 tiene
  todas sus líneas en *Complete* y su botón está **activo** y dice **«Mark as Done»**; las comandas
  960 y 961 tienen líneas en *Waiting* y su botón está **gris** y dice **«Mark All Complete»**. O
  sea: el botón primero te obliga a completar las líneas, y solo cuando están todas te deja cerrar
  la comanda. El estado del botón es una consecuencia calculada, no algo que el usuario elija.
- **Estado por línea**, en pequeño encima del nombre del producto (*Waiting* / *Complete*). La
  unidad de trabajo es la línea, no la comanda.
- **Modificadores y notas debajo del producto**, indentados y en gris: «Lettuce, Tomatoes, Pickles,
  Onions» y, destacada con tres asteriscos, la nota `*** Extra cheese`. El marcado tipográfico
  distingue lo que el cliente **quitó o añadió** de lo que el plato lleva de serie.
- **Un icono circular «C»** a la derecha de algunas líneas (bebida y postre en la comanda 960),
  marca de agrupación —curso o estación— que no afecta a todas las líneas.
- **Fondo vacío a la derecha**: cabe mucha más comanda. La pantalla se llena por columnas.

### La ficha de producto (0:34) en detalle

Back office web de Revel (no la app de iPad), ruta `Products > Food Items > Curry > Curry Beef`. A
la izquierda un árbol de ajustes con casillas; a la derecha el formulario. La sección abierta es
**Display/Print Options**, y su contenido es exactamente la lista de cosas que un producto necesita
saber para aparecer bien en cocina:

`Main category` · `Additional categories` · `Image` · **`Color code`** (paleta de 12 colores con
nombre) · `Disable modifier popup` · **`Printers`** · **`Kitchen print name`** ·
**`Kitchen Description`** · `Print Tags` · `Shelf Edge Label Quantity`.

Lo importante: el producto tiene **un nombre para el cliente y otro distinto para cocina**
(*Kitchen print name*), más una descripción propia de cocina, un color y un destino
(*Printers* / *Print Tags*). El enrutado a estaciones del que habla la locución **no se decide en el
KDS: se decide en la ficha del producto**. Arriba se ve además un contador rojo de **«Offline
Stations»**, señal de que el propio sistema asume que las estaciones se caen y lo vigila.

## Qué aprendemos para nuestro KDS+TPV

1. **El cronómetro por comanda, contando hacia arriba, es la pieza de interfaz que ordena la
   cocina.** No la hora del pedido, sino cuánto lleva esperando. Es barato de implementar (un
   `timestamp` de creación y un contador en el cliente) y es lo que permite luego sacar el dato de
   tiempo medio de preparación sin instrumentar nada más. Debería estar en la tarjeta desde la
   primera versión.

2. **Dos niveles de cierre: línea y comanda, con el botón de comanda bloqueado hasta que las líneas
   estén hechas.** Es una regla de negocio sencilla que evita el error caro (dar por servida una
   comanda a la que le falta algo) sin añadir ninguna pantalla nueva. Nuestro modelo de datos debe
   tener estado en la línea, no solo en la comanda, o esto no se puede hacer después.

3. **El destino de cocina es un atributo del producto, no una decisión del KDS.** Revel lo resuelve
   con `Printers` / `Print Tags` / `Kitchen print name` en la ficha del artículo. Para nosotros
   significa: la tabla de productos necesita columnas de *estación destino* y *nombre corto para
   cocina* antes de plantearnos siquiera dividir la pantalla por estaciones. Si esto no está en el
   dato, el filtrado por estación acaba siendo una chapuza de cadenas de texto.

4. **Las notas y modificadores necesitan jerarquía visual explícita.** Revel indenta los
   modificadores y antepone `***` a las notas libres. Nuestra carta web ya deja al cliente pedir
   desde la mesa, y esos pedidos van a traer texto libre: si en la pantalla de cocina la nota se ve
   igual que el resto del plato, el cocinero la va a pasar por alto exactamente el día que importa.

5. **El sistema cuenta las estaciones caídas y lo enseña en la barra superior.** Con las tabletas de
   cocina por WiFi, la caída no es un caso raro sino el caso normal. Merece un indicador visible, no
   un log.

### Cruce con lo que ya tenemos

- **Versión móvil del camarero**: el vídeo confirma el patrón de que la comanda lleve siempre quién
  la tomó (*Server: Tessa S*). Nuestra app móvil ya identifica al camarero; hay que asegurarse de
  que ese identificador **llega hasta la tarjeta del KDS** y se muestra, porque es lo que permite
  preguntar sin buscar a nadie cuando algo no cuadra.
- **Carta web con pedido desde la mesa**: aquí todas las comandas son **To Go**, y el tipo de
  servicio ocupa un sitio fijo en la cabecera. Nosotros vamos a tener al menos tres orígenes (mesa
  por camarero, mesa por cliente desde la carta web, y recogida), y cocina necesita distinguirlos de
  un vistazo. Conviene reservar ya ese hueco en la cabecera de la tarjeta.
- **Lectura de albaranes por visión**: este vídeo **no toca nada de eso**. Revel enseña inventario y
  CRM en el menú del back office, pero no entra; no hay aquí ninguna referencia a captura
  automática de documentos de proveedor. Esa línea del proyecto sigue sin competencia observada en
  el material analizado hasta ahora.

## Conclusión

Un vídeo de 52 segundos de publicidad que, por ser publicidad, enseña solo lo que el fabricante
considera sus mejores argumentos: cero papel, exactitud, notas visibles y enrutado por estaciones.
Esa selección es en sí un dato útil, porque coincide con lo que estamos construyendo. El material
aprovechable son dos fotogramas, pero entre los dos cierran el circuito completo —cómo se configura
un producto en el back office y cómo acaba viéndose en la pantalla de cocina—, que es justo la
pregunta que teníamos abierta.

Lo accionable inmediato, por orden de coste: añadir el cronómetro a la tarjeta, mover el estado al
nivel de línea en el modelo de datos, y añadir a la tabla de productos el nombre corto de cocina y
la estación destino.

---

*Material de terceros: el vídeo, los fotogramas y la transcripción se han procesado en una carpeta
temporal fuera del repositorio y no se incluyen aquí. Este documento es análisis propio.*
