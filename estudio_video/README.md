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
2. **El elenco son retratos congelados.** Nueve personas con su ficha y su
   semilla. IP-Adapter las mantiene reconocibles entre tomas. El casting se hace
   una vez y no se vuelve a tocar: es lo único del estudio que no se puede volver
   a deducir de la base de datos.
3. **La carta y las pantallas no se generan: se graban.** SD 1.5 no sabe escribir
   «Brasa de Perihelio · 11,90 €»; saca garabatos. Cuando una escena tiene que
   enseñar interfaz, se abre el KDS de verdad en un navegador y se graba, con las
   burbujas del tutorial que ya venían escritas en `tutorial.js`.
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

## Qué se cambia para cambiar el resultado

| Quiero cambiar | Dónde |
|---|---|
| El aspecto de todos los vídeos | `ESTILO` en `biblia.py` |
| Resolución, fps, pasos, semilla base | `FORMATO` en `biblia.py` |
| Los encuadres | `CAMARAS` en `biblia.py` (y `python estudio_cli.py camaras`) |
| Quién sale | `ELENCO` en `biblia.py` + `casting --rehacer` |
| Cuánto manda la sala sobre el modelo | `FUERZA_PROFUNDIDAD` en `comfy.py` |
| Qué se ve en las pantallas grabadas | `Servicio` en `pantallas.py` |
| La voz | `VOZ_POR_DEFECTO` en `voz.py` (`sharvard` o `davefx`) |

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
