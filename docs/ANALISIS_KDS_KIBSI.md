# Análisis de visión por computador aplicada a sala (Kibsi) · la mesa como fuente de datos

Este estudio se sale de la serie anterior a propósito. Los análisis previos (TMBill, Revel, Loyverse,
Epos Now) miraban productos que compiten con el nuestro: TPV y KDS. Kibsi **no vende un TPV**: vende
una plataforma de visión por computador sin código, y este vídeo es su demostración aplicada a un
restaurante. Interesa porque ataca el mismo problema que nuestro KDS —saber qué está pasando y
cuánto lleva pasando— pero desde el lado contrario: en vez de que el dato lo teclee el camarero,
lo deduce una cámara del techo.

Es además el vídeo más corto que hemos analizado (36 segundos) y el único **sin una sola palabra
hablada**. Eso obliga a que todo el análisis salga de la imagen, y de paso sirve para probar que la
cadena aguanta un vídeo mudo.

## Ficha

| Dato | Valor |
|---|---|
| Vídeo | «Restaurant Computer Vision AI» |
| Canal | Kibsi — The No-Code Computer Vision Platform |
| Publicado | 28 de octubre de 2022 |
| Duración | 36 s |
| Resolución | 1920×1080, 24 fps |
| Audio | Solo música, **sin voz** |
| Enlace | `youtube.com/watch?v=i_mL3LT0lDg` (no se guarda el vídeo en el repositorio) |

## Cómo se ha procesado

La misma cadena de siempre, sin cambios: `yt-dlp` desde Raspa (nunca desde Pecera, para no gastar
ahí la cuota de YouTube), copia del `.mp4` por `scp`, `ffmpeg` para separar audio y fotogramas,
faster-whisper en la GPU de Pecera y selección de fotogramas clave por diferencia.

| Paso | Resultado |
|---|---|
| Descarga | 4,4 MB, sin error 429 |
| Fotogramas a 10 fps (escalados a 960 px) | 360 imágenes, 14 MB |
| Transcripción | **0 segmentos de voz** |
| Fotogramas clave | 20 momentos de cambio |
| Fotogramas mirados de verdad | 10 |

### El vídeo es mudo, y eso no es un fallo

La primera pasada de transcripción con filtro de voz (VAD) devolvió **cero segmentos**. Antes de
darlo por bueno hay que descartar la avería, porque «cero segmentos» es también lo que sale cuando
el audio se ha extraído mal. Dos comprobaciones:

- Nivel de audio medido con `ffmpeg -af volumedetect`: media **−12,1 dB**, pico **−1,0 dB**. Hay
  señal de sobra; el archivo no está vacío ni mudo.
- Segunda pasada **sin** el filtro de voz: el modelo devuelve tres segmentos y los tres son el
  símbolo de nota musical, su forma de decir «esto es música, no habla».

Conclusión: el vídeo lleva banda sonora y ningún narrador. El filtro de voz funcionó exactamente
como debía. Es un vídeo promocional de 36 segundos que se explica solo con rótulos en pantalla.

Se mantuvo `multilingual=True` aunque no hubiera voz, por la razón de siempre: sin esa opción el
modelo traduce en vez de transcribir, y aquí habría podido inventar texto en inglés sobre una pista
de música. Y `compute_type="int8_float32"` porque la GPU es una 1080 Ti (Pascal) y `float16` no
funciona en esa arquitectura.

### El porcentaje de fotogramas repetidos: 31,8 %

La medida que venimos usando para caracterizar un vídeo antes de mirarlo: qué proporción de
fotogramas es prácticamente idéntica al anterior (diferencia media por debajo de 1 sobre 255).

| Vídeo | Repetidos | Qué es |
|---|---|---|
| Captura de pantalla por software (TMBill) | 95 % | Un puntero que se mueve sobre una interfaz quieta |
| Grabado con cámara apuntando al monitor | 0 % | Todo el encuadre tiembla, nada se repite |
| **Kibsi** | **31,8 %** | **Mixto** |

El 31,8 % encaja con lo que el vídeo resultó ser: **metraje real de un restaurante con gráficos
superpuestos encima**. Los tramos en los que la cámara está quieta y solo se mueven los rótulos
suben el porcentaje; los tramos de comedor lleno, con gente andando, lo bajan. La diferencia media
por fotograma es de 5,46, diez veces la de una captura de pantalla.

Esto tiene una consecuencia práctica, y es la razón de medirlo: en un vídeo así **no se puede
confiar en los picos de diferencia para encontrar los momentos interesantes**. Los picos más altos
aquí fueron transiciones desenfocadas y fundidos a negro, no pantallas nuevas. De los 20 fotogramas
clave seleccionados, tres resultaron ser borrones de transición. En una captura de pantalla eso no
pasa. Con vídeo mixto hay que mirar más fotogramas de los que el algoritmo propone y completar a
mano los huecos.

## Qué enseña, paso a paso

| Momento | Contenido |
|---|---|
| 0:00–0:03 | Marca Kibsi sobre negro |
| 0:08–0:12 | **Capa 1 — detección cruda.** Vista cenital de un comedor lleno. La cámara dibuja recuadros sobre cada objeto que reconoce, con su etiqueta y su confianza: `person 0.84`, `chair 0.76`, `dining table 0.39`, `bottle`, `potted plant`. Son decenas de recuadros solapados, ilegibles a propósito: es el dato en bruto, antes de significar nada |
| 0:16–0:18 | Transición desenfocada: los recuadros se funden y reaparecen como otra cosa |
| 0:18–0:23 | **Capa 2 — el dato convertido en mesa.** Cada mesa aparece resaltada con una rejilla morada y una etiqueta numerada (`TABLE 11` a `TABLE 24`). Al lado, una ficha por mesa con seis campos: `STATE`, `SEATED`, `ORDERED`, `FOOD`, `DINERS`, `SERVER`, más `TYPE` (`Walk-in`) o `RESERVATION` |
| 0:18 | La ficha ampliada de la mesa 15 es el corazón del vídeo: estado **«Waiting for check»**, sentados hace 72 min, pidieron hace 60, la comida salió hace 42, **5 adultos y 1 niño**, camarero **Larry, hace 9 minutos**. Y un **triángulo rojo de alerta**: esa mesa lleva demasiado esperando la cuenta |
| 0:24–0:33 | **Capa 3 — el panel.** Las fichas de mesa se apilan a la izquierda y aparece el `PERFORMANCE DASHBOARD`. «Average dining experience: **1.25 HR**», desglosada en una barra apilada de seis fases con su leyenda de colores: *wait for table*, *time to greet*, *time to order*, *time for food*, *time to eat*, *time to pay*. Debajo, **ocupación**: 4,7 comensales por mesa, 132 comensales en total, 12 mesas libres y 28 ocupadas |
| 0:33–0:36 | Fundido a negro y cierre con la marca y la dirección web |

Los estados de mesa que se leen en las fichas son cinco: `Available`, `Ready to order`,
`Ready to pay`, `Waiting for check` y las mesas con `Reservation: in 5 mins`. Cada ficha lleva
además un punto verde o una alerta roja, exactamente la misma señal de semáforo que usa nuestro KDS.

## Qué aprendemos para nuestro KDS+TPV

Conviene decir primero, con claridad, **qué parte de esto ya tenemos y cuál no**, porque el vídeo
toca de lleno cosas del proyecto.

**Lo que ya está hecho y este vídeo confirma:**

- **El semáforo por tiempo de espera.** Sus fichas de mesa van de verde a alerta roja según lo que
  lleva esperando la mesa. Es la misma idea que nuestros umbrales de 8 y 15 minutos en el KDS por
  estaciones. Tercer producto seguido que lo hace igual: la decisión está respaldada.
- **El estado como máquina de estados explícita.** Sus cinco estados de mesa son el equivalente en
  sala de nuestros estados de comanda. Misma forma de pensar.
- **La visión por computador ya está en marcha aquí**, pero aplicada a otra cosa: nuestro trabajo en
  curso es la **lectura de albaranes con un modelo de visión**, es decir, visión sobre un papel para
  ahorrar tecleo en el almacén. Kibsi aplica visión sobre la sala para ahorrar tecleo en el
  servicio. Mismo instrumento, problema distinto.

**Lo que no tenemos y el vídeo deja ver:**

**1. Del tiempo de la comanda al tiempo de la mesa.** Es el hallazgo principal. Nuestro KDS cronometra
la comanda: desde que entra hasta que sale de cocina. Kibsi cronometra **la visita entera**, y la
parte de cocina es solo uno de sus seis tramos. Un plato que sale en 6 minutos es un éxito para
nuestro KDS aunque la mesa lleve 20 minutos esperando a que alguien la salude. Lo importante es que
**los cuatro tramos que tocan al TPV ya los tenemos fechados**: sentar, pedir, salida de cocina y
cobro son cuatro marcas de tiempo que nuestra base de datos ya guarda. Falta el primer tramo
(*wait for table*), que nadie teclea. Con lo que ya hay se puede pintar hoy una barra de cinco de
las seis fases, sin cámara y sin hardware nuevo: es un informe, no un desarrollo.

**2. El panel de ocupación como pantalla de encargado.** «12 libres / 28 ocupadas», «4,7 comensales
por mesa», «132 comensales». Nuestro arqueo dice cuánto se ha facturado **al cerrar**; esto dice
cómo va el servicio **mientras ocurre**. Es una vista que no existe en nuestro sistema y que no
necesita cámara: el TPV sabe qué mesas están abiertas y con cuántos comensales, si se registra ese
dato al abrir la mesa. El número de comensales es hoy el eslabón que falta.

**3. La alerta por espera del cliente, no del plato.** La mesa 15 salta en rojo porque lleva 12
minutos pidiendo la cuenta. Nuestro sistema avisa cuando un plato tarda; no avisa cuando un cliente
espera. Y para el cliente, esperar la cuenta con el abrigo puesto pesa más que dos minutos de más en
la cocina. Es un aviso barato de implementar: una consulta sobre comandas con todo servido y sin
cobrar, con un umbral de minutos, reutilizando el mismo mecanismo de semáforo del KDS.

**Lo que no debemos copiar:** la visión por computador en sí. Montar cámaras cenitales en un local
pequeño supone hardware, calibración por local y datos personales de clientes filmados, con todo lo
que eso arrastra. El valor de Kibsi está en que **deduce sin teclear**, y ese problema nosotros no
lo tenemos: nuestro camarero ya teclea. Lo aprovechable son las **preguntas** que se hace su panel,
no el instrumento con el que las responde.

## Conclusión

Un vídeo de 36 segundos, sin voz, del que salen tres cosas concretas para el proyecto: cronometrar
la visita completa y no solo la comanda, un panel de ocupación en vivo para el encargado, y una
alerta por cliente que espera y no solo por plato que tarda. Las tres son aprovechables **con los
datos que el TPV ya guarda**, salvo el número de comensales por mesa, que habría que empezar a
registrar al abrir la mesa. Ninguna necesita una cámara.

Y una lección de método: el 31,8 % de fotogramas repetidos avisó de que era un vídeo mixto, y en un
vídeo mixto los picos de diferencia apuntan a las transiciones, no al contenido. Conviene mirar más
fotogramas de los que el algoritmo propone.

---

*Material de terceros: el vídeo, los fotogramas y el audio se han procesado en una carpeta temporal
fuera del repositorio y no se incluyen aquí.*
