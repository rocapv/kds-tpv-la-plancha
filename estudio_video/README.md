# Estudio de vídeo del KDS+TPV — Cantina Vesta-9

Una caja de texto, un botón, y sale un vídeo. Tutoriales de cómo se usa el sistema
y escenas de clientes llegando, siendo servidos, pidiendo desde el móvil y pagando
con la app.

Lo que lo diferencia de escribirle un prompt a un generador de vídeo cualquiera es
que **aquí la cantina no se inventa en cada toma**. El encargo era que el resultado
saliera «siempre en la misma línea»: mismas medidas, mismos clientes, mismo menú y
la misma carta. Con difusión pura eso no se consigue —dos tomas del mismo prompt
son dos restaurantes distintos—, así que la consistencia no se le pide al modelo:
se le impone desde fuera, con cuatro anclas.

```
    plano.html del KDS  ─────►  geometria.py  ─────►  mapa de profundidad
    (mesas, muros, barra)       (3D a escala)         por cada cámara fija
                                                              │
                                                              ▼
    retratos del elenco ─────►  IP-Adapter  ────►  ┌──────────────────┐
    (congelados)                                   │  AnimateDiff v3  │ ──► clip
                                                   │     SD 1.5       │
    semilla del guion   ─────────────────────────► └──────────────────┘
                                                              │
    /api/publico/carta  ─────►  pantallas.py  ────────────────┤
    (platos y precios)          (el KDS de verdad,            │
                                 grabado con Playwright)      ▼
                                                          montaje.py
                                      Piper (Raspa) ────►  ffmpeg  ───► MP4 1080p
```

1. **La sala sale del plano de la base de datos.** `13_plano.sql` guarda muros,
   zonas, mesas y barra en milésimas. El estudio los levanta en 3D a escala (16 m
   de lado), mira la sala desde nueve cámaras fijas y saca un mapa de profundidad
   por cada una. ControlNet obliga al modelo a respetar esa geometría. Si el
   encargado mueve una mesa en `plano.html`, los vídeos siguientes tienen esa mesa
   movida; hasta entonces, no cambia nada.
2. **El elenco son cinco moldes con hoja de personaje.** El camarero, dos
   clientes y dos clientas. Cuantas menos caras haya, más veces sale cada una, y
   antes se nota que siempre es la misma persona. Cada molde tiene **siete
   vistas** —frontal, tres cuartos, perfil, tres primeros planos de cara
   (neutra, hablando y mirando hacia abajo, que es como se mira un móvil) y un
   plano medio—, todas generadas a partir del retrato base, y en cada escena se
   le pasan **todas a la vez** a IP-Adapter, que promedia sus embeddings. Con un
   solo retrato frontal, en cuanto la persona gira la cabeza deja de
   reconocerla y sale «alguien parecido».

   El casting se hace una vez y no se vuelve a tocar: es lo único del estudio
   que no se puede volver a deducir de la base de datos. Mirar la hoja antes de
   rodar no es opcional —de las tres tandas que hicieron falta, las tres se
   corrigieron mirando lo que salía: vistas partidas en dos, primeros planos que
   eran un cuello, y un personaje con los labios pintados de rosa.

   ```powershell
   python estudio_cli.py casting      # los cinco retratos base
   python estudio_cli.py hojas        # las siete vistas de cada uno
   python hoja_elenco.py --hojas      # la hoja entera, para mirarla
   python prueba_moldes.py            # las mismas 4 acciones para cada molde
   ```
3. **La carta y las pantallas no se generan: se graban.** SD 1.5 no sabe escribir
   «Brasa de Perihelio · 11,90 €»; saca garabatos. Cuando una escena tiene que
   enseñar interfaz, se abre el KDS de verdad en un navegador y se graba.

   Con burbujas o sin ellas, y **no es lo mismo**. Las de `tutorial.js` explican
   la interfaz iluminando un elemento y apagando el resto: perfectas para un
   tutorial, y justo lo que estorba en una escena de servicio, donde lo que hay
   que ver es el dato —la mesa abierta, la comanda entrando, el aviso de la
   cuenta— y quien explica es la narración. Lo decide `tutorial` en cada escena,
   que por defecto vale lo que valga el `tipo` del guion.
4. **La semilla sale del guion.** El mismo guion da el mismo vídeo. Si algo sale
   mal, se repite exacto y se compara.

## Dónde está cada cosa

El estudio vive **en este repo** (`estudio_video/`), junto al sistema que graba. El
motor de imagen vive **aparte**, en `M:\CLAUDE\Kinemato`: ComfyUI con su propio
venv, su CUDA y sus 8 GB de pesos, que no tienen nada que hacer en el repositorio
de un TPV. Se hablan por HTTP (`127.0.0.1:8188`), y la ruta del motor se dice en
`DIR_KINEMATO` (variable de entorno `KINEMATO` para cambiarla).

El estudio corre con el intérprete de `M:\CLAUDE\.venv`, que ya tiene Playwright,
numpy y Pillow. No necesita CUDA: quien genera es ComfyUI, al otro lado del HTTP.

Nada de esto lo toca el despliegue automático del KDS, que solo instala
`backend/requirements*` y ejecuta `backend/pruebas`.

## Uso

```powershell
.\arrancar.ps1          # ComfyUI + la web, y abre Firefox en http://127.0.0.1:8099
```

Y desde la línea de órdenes, para todo lo demás:

```powershell
python estudio_cli.py salud                   # qué hay encendido y qué falta
python estudio_cli.py biblia                  # releer el plano y la carta del KDS
python estudio_cli.py casting                 # retratar al elenco (gasta GPU, una vez)
python estudio_cli.py guion "un prompt"       # ver el guion sin gastar nada
python estudio_cli.py producir "un prompt"    # el vídeo entero
```

Y para el vídeo de referencia —el servicio completo, de la puerta a la factura—,
que lleva el guion escrito a mano porque el orden lo manda el sistema y no el
guionista:

```powershell
python video_servicio.py --guion              # los 12 planos, sin gastar GPU
python video_servicio.py                      # el vídeo (~5 min de GPU)
```

Cada trabajo deja **todo** en `trabajos/<id>/`: el guion, los clips, la voz, los
subtítulos y el estado paso a paso. El MP4 terminado va a `salidas/`, con su `.srt`
y su portada.

## Lo que hay que saber antes de usarlo

- **La GPU se comparte y suele estar ocupada.** En Pecera la usan los relatos de la
  bitácora, los cursos de la academia y el pipeline de Star Citizen, y LM Studio
  carga modelos de 7 GB en ella. Antes de generar, el estudio mira cuánta VRAM hay
  **preguntándole al driver**, no a ComfyUI (ComfyUI informa de lo suyo, no de la
  tarjeta: con 10 GB ocupados por LM Studio seguía diciendo «9.489 MiB libres»). Si
  no cabe, el trabajo **no se tira**: se monta con las pantallas grabadas y avisa de
  qué falta, para relanzarlo cuando se libere.
- **No se toca la base de datos del restaurante.** Las pantallas se graban del sitio
  de pruebas (`:8093`) y en modo lectura. Las comandas que se ven en los vídeos son
  un escaparate servido por el propio navegador (`page.route`): platos y mesas de
  verdad, pedidos que no existen. La demo que sí escribía llegó a crear 6.736
  pedidos y a tumbar la API.
- **Ningún dato personal en los vídeos.** La primera grabación del TPV salió con
  nombres de clientes de pedidos para llevar y sus importes. El escaparate sustituye
  ahora todo lo que lleve nombres o dinero, y lo que no sabe falsear lo **corta** en
  vez de dejarlo pasar: un hueco en la pantalla se ve, un dato real no.
- **Hardware.** GTX 1080 Ti (Pascal, sm_61). Por eso SD 1.5 y AnimateDiff v3 y no
  algo de este año: lo demás pide BF16/FP8. Y por eso torch **2.9.1+cu126**: cu128 ya
  no trae kernels de Pascal, y con torch 2.6 el ComfyUI actual ni arranca.
- **Coste.** Unos 36 minutos de cómputo por minuto de vídeo generado, a 640×360 y
  20 pasos. Un tutorial hecho solo de pantallas grabadas sale en menos de un minuto
  porque no toca la GPU.

## Grabar pantallas: cinco trampas, todas silenciosas

Las cinco pantallas de un vídeo de servicio son la mitad del metraje y **son el
producto**: si salen mal, da igual lo bien que salga la gente generada. Lo que las
hace difíciles es que ninguna de estas cinco cosas da un error. El clip se graba,
dura lo que tiene que durar y enseña otra cosa.

- **La cámara arranca al crear el contexto, no al pedirlo.** `record_video_dir` es
  un argumento de `new_context`, así que abrir la página, esperar la red y teclear
  el PIN —dos o tres segundos— van dentro del clip, y el montaje corta por el
  principio. Tres de cada cinco planos enseñaban el teclado numérico. Se arregla
  tecleando el PIN en un contexto **que no se graba** y pasando su `storage_state()`
  al que sí (`_sesion_previa`); el token vive en `localStorage`, así que el contexto
  que graba nace ya identificado. No hay forma de retrasar el comienzo.
- **Un error de JavaScript no rompe la grabación: rompe la pantalla.** El vídeo sale
  igual, con el hueco donde iba el contenido. Así se perdió el plano del pase, en
  negro con el titular puesto, y nadie se enteró hasta mirar el montaje fotograma a
  fotograma. Ahora `grabar()` escucha `pageerror` y `console.error` y avisa al
  terminar. **Si una pantalla sale vacía, mirar ese aviso antes que nada.**
- **El escaparate tiene que devolver la forma EXACTA de la API.** El pase
  contestaba con la lista pelada y la API la envuelve en `{"comandas": [...]}`; en
  `sala.html` el `try` protege la llamada pero no lo de después, así que el
  TypeError se llevó por delante a `cargar()` entera —indicadores, avisos y zonas
  incluidos—. Cuando se añada un endpoint nuevo al escaparate, copiar la forma del
  backend, no la de memoria.
- **Dos planos de la misma pantalla salen iguales si no se toca nada.** Para eso
  están los **gestos** (`GESTOS` en `pantallas.py`, campo `gesto` de la escena):
  `cobrar` abre la mesa que espera la cuenta y saca el panel de cobro. Los clics se
  graban —no hay forma de pausar— pero quedan al principio, y el montaje los salta
  leyendo un `.json` que se escribe junto al clip. El corte se ancla al **final**
  del clip, que siempre termina con la pantalla ya quieta durante `segundos`;
  cronometrar desde Python da un número parecido y equivocado, porque el vídeo
  empieza a contar en el primer fotograma pintado.
- **Media pantalla no está en la API: la calcula el backend.** El estado de una mesa
  no se guarda en ninguna columna; `/api/sala` lo deduce de las líneas del pedido
  —sin líneas, «sentados, sin pedir»; una sola línea en «lista», «listo en el pase»;
  todas «servida», «esperando la cuenta»—. Inventar las líneas al azar deja el mapa a
  lo que salga: faltaba «sin pedir» porque toda línea nacía enviada a cocina. Ahora
  el estado se decide primero (`_guion_de_sala`) y las líneas se eligen para que el
  backend deduzca ESE estado; lo que se sortea es el relleno. Y lo deducido tiene que
  cuadrar **entre planos**: el pase sale de las mesas que de verdad tienen algo en
  «lista», no de las tres primeras comandas, porque son dos planos casi seguidos y se
  desmentían entre ellos.

Y una regla que no es de Playwright sino del encargo: **lo que se lee en pantalla es
lo que el espectador entiende del sistema**. Por eso las notas de comanda van por
categoría (un «poco hecho» en un batido parece que el sistema mezcla las notas); por
eso el escaparate también sirve `/api/catalogo` y `/api/publico/carta`, filtrados
—el «Pato · 999,00 €» de la carta de desarrollo, en un TPV, se lee como un TPV con la
carta mal—; y por eso la estación de cocina de cada plato se baja de la base de datos
en vez de sortearse: una cerveza en la freidora desmiente la propia narración del
plano, que dice «repartida por estaciones».

## Qué se cambia para cambiar el resultado

| Quiero cambiar | Dónde |
|---|---|
| El aspecto de todos los vídeos | `ESTILO` en `biblia.py` |
| Resolución, fps, pasos, semilla base | `FORMATO` en `biblia.py` |
| Los encuadres | `CAMARAS` en `biblia.py` (y `python estudio_cli.py camaras`) |
| Quién sale | `ELENCO` en `biblia.py` + `casting --rehacer`, o las caras de la web |
| Qué lleva puesto cada uno | `vestuario` en `ELENCO` (+ `probar_vestuario.py` para comprobarlo) |
| Las vistas de la hoja de personaje | `VISTAS` en `elenco.py` + `hojas --rehacer` |
| Cuánto manda la sala sobre el modelo | `FUERZA_PROFUNDIDAD` y `HASTA_PROFUNDIDAD` en `comfy.py` |
| Qué se ve en las pantallas grabadas | `Servicio` en `pantallas.py` |
| Qué se HACE en una pantalla mientras se graba | `GESTOS` en `pantallas.py` + `gesto` en la escena |
| La voz | `VOZ_POR_DEFECTO` en `voz.py` (`sharvard` o `davefx`) |

## La ropa es parte del personaje

Un molde no es solo una cara: es una cara **y** una ropa. Al principio el
vestuario iba dentro de la misma frase que describía a la persona, y ahí competía
con la acción: el mismo hombre salía con chaleco reflectante en un plano y con
chaleco y pajarita en el siguiente.

Ahora se sujeta por dos sitios a la vez:

- **En el prompt**, el campo `vestuario` va aparte y con su propio peso
  (`(ropa:1.2)`), delante de la acción.
- **En la imagen**, un segundo IP-Adapter encadenado mira la vista de plano medio
  de la hoja —la que enseña la ropa entera— con peso bajo (0,30) y entrando
  tarde. Flojo a propósito: si aprieta más, se lleva el color de la ropa a las
  paredes.

Comprobado con `probar_vestuario.py`, que pone al mismo molde en las cuatro
cámaras para poder mirar la fila entera. Aguanta en los planos medios y cortos;
**en el plano general muy lejano se pierde**, porque la persona ocupa poca imagen
y ni el prompt ni la referencia llegan. Si la ropa tiene que leerse, el plano
tiene que ser corto.

Y una regla que cuesta aceptar: si el modelo interpreta una prenda de una forma
distinta a la pedida pero lo hace SIEMPRE IGUAL, gana el modelo y se cambia la
ficha. Lo que importa es que se repita; pelearse por cuál prenda es naranja solo
consigue que deje de repetirse.

## Pendiente

- **Probar la generación de imagen de punta a punta.** El día que se montó, la GPU
  estuvo ocupada por Graphify de otra sesión todo el rato. El motor está escrito y
  el grafo validado contra los nodos reales de ComfyUI 0.37, pero falta la primera
  tirada: casting + un clip. Hasta entonces, las cifras de calidad y de tiempo son
  estimaciones.
- **La zona de recogida no tiene mostrador en el plano**, así que en esa cámara el
  mueble lo pone el modelo y puede variar. Se arregla dibujándolo en `plano.html`,
  no aquí.
- **`reservas.html` y `pantalla.html` dan 404 en el sitio de pruebas** (:8093) aunque
  existen en producción: la copia de pruebas se quedó atrás. Se arregla con
  `publicar.sh <frontend> /var/www/kds_pruebas`.
- Publicar los vídeos terminados en Raspa para verlos desde `home.pr1.es`.
