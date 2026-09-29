# Visión por cámara: dónde está cada cual y cuánto lleva ahí

Estado: **propuesta**, sin construir. La idea es aprovechar el CCTV que ya vigila el local para
saber **cuánta gente hay, en qué zona y desde cuándo**, y volcarlo sobre el plano de sala que ya
existe (`plano.html`, tabla `plano_elementos`).

Antes del diseño hay un asunto que manda sobre todo lo demás.

---

## 1. Lo primero: qué se puede hacer y qué no

Grabar la sala para seguridad es corriente y está resuelto con un cartel y un registro de
tratamiento. **Analizar ese vídeo para seguir a personas ya no es lo mismo**, y hay dos límites
que no se negocian:

- **Nada de identificar a nadie por la cara.** El reconocimiento facial es un dato biométrico, de
  categoría especial (art. 9 RGPD): fuera de la excepción del consentimiento explícito —que en un
  restaurante no se sostiene, porque nadie consiente libremente para poder sentarse a comer— es
  sencillamente ilegal. Aquí **no se construye**, ni con la excusa de «solo para empleados».
- **Nada de vigilar al trabajador individual.** El control laboral por cámara está acotado (art.
  20.3 del Estatuto de los Trabajadores y art. 89 LOPDGDD): hay que informar antes, de forma
  expresa y clara, no vale en zonas de descanso, y **medir el rendimiento persona a persona** con
  esto es justo lo que acaba en sanción. El sistema mide **puestos y zonas**, no nombres.

Lo que sí se puede, informando y con el cartel de zona videovigilada ampliado a «análisis de
aforo»:

- contar personas por zona y decir cuánto lleva ocupada una mesa;
- medir **tiempos de espera** (mesa sentada sin que se acerque nadie) y de servicio;
- ver si una mesa se quedó sin recoger;
- saber el aforo real por franjas para planificar turnos y compras.

Y hay dos cosas más que hay que dejar hechas desde el principio, no «para luego»:

- **La imagen no se guarda.** El detector trabaja en memoria, escribe posiciones y tira el
  fotograma. Lo que se conserva es una fila de números, no una cara.
- **Evaluación de impacto (DPIA)**: observación sistemática de una zona accesible al público la
  pide el art. 35 RGPD. Para un local pequeño es un documento corto, pero hay que escribirlo, y
  entra en la memoria del proyecto.

> Si algún día se quisiera identificar de verdad a los empleados, la vía legal es que **ellos
> lleven algo**: la sesión del TPV, un tag, el puesto asignado. Eso ya existe en el sistema
> (`puestos`, `sesiones`) y no necesita cámara.

---

## 2. Qué hace el sistema

Por cada cámara y cada fotograma que se procesa:

1. **Detectar** personas y unos pocos objetos útiles (bandeja, plato, vaso, silla, mesa) con un
   detector general (YOLO o RT-DETR, pesos COCO ya valen para empezar).
2. **Seguir** cada detección entre fotogramas (ByteTrack) para tener un `track_id` que dure lo que
   dura el paso de esa persona por el encuadre. **El `track_id` es efímero y no identifica a
   nadie**: si sale y vuelve, es otro número, y así debe ser.
3. **Proyectar** el punto de los pies al plano de la sala con la homografía de esa cámara
   (cuatro puntos marcados una vez sobre el plano que ya existe). Salen coordenadas en metros
   sobre el mismo plano donde están dibujadas las mesas.
4. **Escribir** una fila: cámara, instante, `track_id`, clase, x, y, confianza.
5. **Agregar**: quién está dentro del polígono de cada mesa, cuánto lleva, cuántas personas hay en
   cada zona, cuándo se acercó alguien del personal a una mesa.

De ahí salen los avisos que de verdad sirven en servicio: «mesa C4 sentada hace 6 minutos y nadie
ha ido», «la M2 lleva 20 minutos vacía y sin recoger», «hay cola en la puerta».

---

## 3. Dónde corre cada cosa

- **Raspa** es el servidor del KDS y **no da** para el detector. No se toca: recibe eventos.
- **Pecera** tiene la GPU (1080 Ti, Pascal: `int8_float32`, nunca `float16`) y es quien mira el
  RTSP de las cámaras y hace la inferencia. **El vídeo no sale de la red local.**
- El servicio de visión manda a la API del KDS lo ya agregado, no el chorro de posiciones: un
  `POST /api/vision/eventos` con token propio, cada pocos segundos.

Tablas nuevas, en la misma base:

| tabla | qué guarda |
|---|---|
| `camaras` | id, nombre, url RTSP (la contraseña fuera del repo), zona, homografía (4 pares de puntos), activa |
| `vision_presencia` | instante, cámara, `track_id`, clase, x, y — **se poda sola a los N días** (`ajustes.vision_retencion_dias`, 7 por defecto) |
| `vision_ocupacion` | por mesa y minuto: personas dentro, si hay personal cerca, estado derivado |

Los avisos reutilizan lo que ya hay: el mismo canal de `avisos_empleado` y las alertas de sala que
hoy miran el reloj del cliente.

---

## 4. Lo que va a fallar (y conviene saberlo antes)

- **Una cámara de techo de gran angular deforma**: la homografía de cuatro puntos se queda corta en
  los bordes. Se corrige por cámara, o se acepta un error de medio metro, que para «quién está en
  la mesa 4» es suficiente.
- **Oclusiones**: en hora punta las personas se tapan y el contador se queda corto. Para aforo da
  igual; para «cuántos comensales hay en esta mesa», no: ese dato lo sigue poniendo el camarero.
- **El detector confunde objetos**: una bandeja y un plato grande son lo mismo a cinco metros. Los
  objetos son un extra, no la base de ninguna decisión.
- **Coste**: cada cámara a 5 fps ocupa GPU de forma continua. Con dos o tres cámaras y la 1080 Ti
  va sobrado; con ocho, no.
- **Si Pecera se apaga, el local sigue funcionando.** Esto es un accesorio: el KDS, el TPV y la
  cuenta del cliente no pueden depender de que haya visión.

---

## 5. Por dónde empezaría

1. Una cámara, una zona, **solo contar personas** y pintarlas en el plano en tiempo real. Sin
   objetos, sin tiempos.
2. Polígonos de mesa y el aviso de «sentados y sin atender», que es el que paga el trabajo.
3. Tiempos por zona e informe de aforo por franjas.
4. Objetos, si es que hacen falta.

Y antes del paso 1: el cartel, el registro de tratamiento y la DPIA. Es media tarde de escribir y
es lo que convierte esto en un proyecto presentable en vez de en un problema.
