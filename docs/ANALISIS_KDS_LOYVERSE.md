# Análisis de un KDS comercial (Loyverse) · el KDS como impresora

Tercer estudio de competencia. Después del KDS casero del primer vídeo y de la suite completa de
TMBill, este es el caso intermedio y el más parecido al nuestro: **Loyverse**, un TPV gratuito muy
extendido en hostelería pequeña, cuyo KDS es una aplicación Android aparte que corre en una tableta
de la misma red. El vídeo es la quinta parte de un curso en español y enseña dos cosas en siete
minutos: la pantalla para el cliente y la pantalla de cocina.

Interesa por una decisión de diseño que no habíamos visto en los otros dos: **Loyverse no trata el
KDS como un módulo del TPV, sino como una impresora más**. Eso cambia por completo cómo se conecta
y cómo se decide qué comanda va a qué pantalla.

## Ficha

| Dato | Valor |
|---|---|
| Vídeo | «Curso Loyverse TPV GRATIS parte 5 — Configurando el visor y la impresora de cocina digital» |
| Canal | Bytechip Soluciones Tecnológicas (el presentador se presenta como David, de *reiniciaypunto*) |
| Publicado | 21 de mayo de 2023 · 4.993 visitas |
| Duración | 7 min 27 s |
| Resolución | 1280×720, 60 fps |
| Idioma | Español |

## Cómo se ha procesado

La misma cadena que los dos análisis anteriores, sin cambiar nada: descarga con `yt-dlp` desde
Raspa, `ffmpeg` en Pecera para el audio y los fotogramas, faster-whisper en la GPU para la
transcripción y selección de fotogramas clave por diferencia media entre imágenes consecutivas.

| Paso | Resultado |
|---|---|
| Fotogramas a 10 fps (escalados a 960 px) | 4.470 imágenes, 207 MB |
| Transcripción | 59 segmentos, idioma detectado **español** |
| Fotogramas clave | 20 momentos de cambio real |

**El dato de método, otra vez:** el **90 %** de los fotogramas es prácticamente idéntico al anterior
(cambio medio 0,96 sobre 255). Es una captura de pantalla por software, como el vídeo de TMBill
(95 %) y al contrario que el primero, grabado con una cámara apuntando al monitor, donde ese
porcentaje era del **0 %**. La medida sigue funcionando como criba previa: por encima del 90 % sabes
antes de mirar nada que basta con extraer veinte fotogramas clave, porque el resto es pantalla
quieta.

Aquí el vídeo ya venía en español, así que `multilingual=True` no cambiaba el idioma de salida, pero
se ha mantenido igualmente: la regla es no tocar los parámetros entre análisis para que los tres
sean comparables.

Conviene anotar cómo está grabado, porque explica la mitad de lo que se ve en pantalla: el
presentador no graba los dispositivos, sino **dos sesiones de AnyDesk** abiertas en su PC, una
contra el móvil que hace de TPV y otra contra la tableta que hace de KDS. Gracias a eso las dos
pantallas se ven a la vez y se puede seguir el recorrido de una comanda de un lado al otro.

## Qué enseña

| Momento | Contenido |
|---|---|
| 0:14 | Menú de tres rayas del TPV → Configuración → **Pantalla para clientes**. Está vacía: «Todavía no tienes pantallas» |
| 0:45–1:35 | Crear la pantalla: solo pide **nombre del dispositivo** e **dirección IP** (la tableta, 192.168.1.204), con un botón *Buscar* que la localiza en la red. Se equivoca al teclear la IP y no conecta: el emparejamiento es literalmente por IP, sin descubrimiento automático fiable |
| 1:37–2:05 | *Vincular*: la tableta pide confirmación y queda emparejada con el TPV |
| 2:06–2:35 | Prueba real: abre turno con 250 € de fondo de caja, añade croquetas y una cola, y **los productos van apareciendo en la pantalla del cliente a la vez que se teclean** |
| 2:23–2:40 | La pantalla del cliente no es solo un espejo del ticket: tiene un campo donde **el cliente escribe su propio correo** y pulsa «Enviar recibo». Cuando el camarero cobra, el recibo ya sale al correo sin que nadie lo haya tecleado |
| 2:46–3:10 | Segunda parte: el KDS. Y aquí está la sorpresa, porque no se configura en un apartado «cocina» sino en **Configuración → Impresoras → Añadir**, eligiendo el tipo **«Pantalla de cocina»** |
| 3:12–3:40 | Otra vez se pide la IP de la tableta y se pulsa *Buscar*; la tableta muestra su propia IP en sus ajustes por si no aparece sola |
| 3:58–4:15 | La impresora queda listada como **«IMPRESORA VISUAL · Pantalla de cocina · Pedidos»**, y se elige **qué categorías de productos se imprimen en ella** («solamente los de cocina»). Ese es el mecanismo de enrutado: cocina ve la comida, barra vería las bebidas |
| 4:15–4:35 | Cierra la app del visor de cliente en la tableta para que no estorbe y abre la de cocina; esta sí encuentra el dispositivo solo (`SMT-510`) |
| 4:42–5:10 | Manda el pedido desde el TPV. Detalle importante: **no basta con guardar el ticket**, hay que usar «Imprimir pedido»; y tarda unos segundos en llegar |
| 5:10–5:25 | El KDS con la comanda dentro: cabecera **«1 pedido»**, tarjeta verde con **«mesa 1»**, un **cronómetro que cuenta hacia arriba** (00:09, 00:17…), el nombre del camarero («David»), el tipo de servicio («Comer dentro») y las líneas de producto. Al tocar una línea **se tacha**; al tocar la cabecera de la tarjeta, la comanda desaparece de la pantalla |
| 5:28–7:07 | Cierre del curso y anuncio de la continuación: reutilizar **un ordenador viejo instalándole Android** para que haga de KDS, en vez de comprar hardware |

## Lo que se aprende para este proyecto

**1. Tratar el KDS como un destino de impresión, no como una pantalla más.** Es la idea más
aprovechable del vídeo. Si la pantalla de cocina es «una impresora», entonces toda la lógica de
enrutado que ya existe para las impresoras de tíquets vale tal cual: por cada destino se marca qué
categorías de producto le corresponden, y el TPV reparte las líneas de una misma comanda entre
varios destinos sin código nuevo. Nuestro sistema hoy manda todo a una única pantalla; con este
modelo, «cocina», «barra» y «postres» son solo tres destinos con distintos filtros de categoría, y
añadir uno no toca el TPV.

**2. Enviar la comanda es un acto explícito, y eso es correcto.** En Loyverse guardar el ticket no
lo manda a cocina: hay que pulsar «Imprimir pedido». Parece un engorro (el propio presentador se
queda esperando) pero protege de lo peor que puede pasar en un servicio: que la cocina empiece a
cocinar un ticket que el camarero todavía está montando. Merece la pena revisar que en nuestro TPV
la frontera entre «estoy tomando nota» y «esto ya va a fuego» esté igual de marcada.

**3. La pantalla del cliente puede pedir datos, no solo enseñar el ticket.** El truco del correo es
pequeño y muy bueno: el cliente teclea su dirección en su lado mientras el camarero sigue a lo suyo,
y el recibo sale solo al cobrar. Nadie dicta un correo en voz alta ni el camarero lo transcribe mal.
En nuestra versión web para el cliente esto encaja directamente, y sin coste: ya tenemos un canal
abierto hacia el teléfono del cliente.

**4. El emparejamiento por IP fija es el punto débil, y lo demuestra el propio vídeo.** El
presentador teclea mal la IP y se queda un minuto largo sin entender por qué no conecta. Cualquier
sistema montado así se rompe el día que el router cambie las direcciones. Nuestro planteamiento —el
KDS es una dirección web que se abre en el navegador de cualquier tableta— evita el problema de
raíz, pero conviene que el servidor tenga nombre e IP reservada en la red del local y no dependa de
que a alguien le toque teclearla.

**5. La tarjeta de comanda confirma nuestro diseño, con dos matices.** Muestra mesa, camarero, tipo
de servicio, productos y un cronómetro que cuenta desde que entró, igual que la nuestra. Los dos
matices: el suyo **cuenta hacia arriba en segundos** desde el primer momento (00:09), lo que da
sensación inmediata de reloj corriendo, y el tachado línea a línea permite **ir marcando productos
sueltos** antes de cerrar la comanda entera, que es como se cocina de verdad cuando una mesa pide
cosas de distinto tiempo.

**6. El hardware puede ser lo que haya.** El curso termina anunciando que instalará Android en un
ordenador viejo para que haga de KDS. Es el mismo argumento que sostiene nuestra decisión de hacerlo
web: cualquier trasto con un navegador sirve, y no hay que instalar ni actualizar una aplicación en
cada pantalla del local.

## Conclusión

De los tres productos analizados, Loyverse es el que está más cerca de nuestro tamaño y el que más
nos deja copiar sin complicarnos. TMBill enseñaba un ecosistema que no vamos a construir; este
enseña dos decisiones concretas y baratas: **el KDS como destino de impresión con filtro por
categorías** y **la pantalla del cliente como sitio donde el cliente también escribe**. Las dos se
pueden llevar a nuestro proyecto sin reescribir nada.

Y deja también una confirmación por contraste: sus dos problemas —una aplicación que instalar en
cada dispositivo y un emparejamiento a mano por dirección IP— son exactamente los dos que nuestro
enfoque web no tiene. Eso no es mérito nuestro, es que la restricción de hacerlo todo sobre
navegador nos ahorró el problema antes de que existiera.

---

Material de trabajo (vídeo, 4.470 fotogramas, transcripción y fotogramas clave) en el directorio
temporal de la sesión; no se guarda en el repositorio porque es contenido de terceros.
