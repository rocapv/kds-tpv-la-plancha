# El reconocimiento de imágenes del Cargo Router (StarCitizen.es / el Director)

Documento de investigación, escrito el 2026-09-21 leyendo el código real y la máquina de
producción. Objetivo: entender **cómo** está hecho el reconocimiento de imágenes de la
herramienta de carga («barra de cargo») del Director, para poder reutilizar la técnica en el
proyecto de restaurante (kds_tpv).

Todo lo marcado **[verificado]** lo he leído en el código o lo he consultado en la máquina.
Lo marcado **[conjetura]** no lo he podido comprobar, y lo digo explícitamente.
No se ha modificado nada de los proyectos investigados. No hay credenciales en este documento.

---

## 1. Qué es el sistema

El **Cargo Router (PYRO-HAUL)** es el optimizador de rutas de carga de Star Citizen que vive
dentro del Director (starcitizen.es/director, sección Transporte) y también como sitio público
(starcitizen.es/cargo).

El flujo de cara al usuario es: **pegas, arrastras o subes una captura de pantalla** del gestor
de contratos del juego, un **modelo de visión** la lee y devuelve los contratos en JSON, la web
los pinta como tarjetas editables, y un solver calcula la ruta óptima de recogidas y entregas y
la dibuja en un mapa. **[verificado]**

La parte que nos interesa aquí es solo la primera: **imagen a JSON estructurado**.

### La conclusión más útil, de entrada

**No hay OCR clásico ni detección de objetos.** No hay Tesseract, ni EasyOCR, ni PaddleOCR, ni
OpenCV, ni YOLO, ni comparación de plantillas, ni hashes perceptuales en ninguna parte del Cargo
Router. **[verificado: grep sobre todo el repo del Director y sobre cargo_router, y el
package.json del backend solo declara express, better-sqlite3 y dotenv]**

Todo el «reconocimiento» es **un VLM (modelo de lenguaje con visión) al que se le manda la imagen
en base64 por una API compatible con OpenAI Chat Completions, con un prompt muy disciplinado y un
JSON Schema de salida**. El código propio es la fontanería alrededor: prompt, esquema, validación,
cola, caché, cuotas y saneado de la salida.

---

## 2. Arquitectura

```
Navegador (Director o sitio público)
  |  el usuario pega, arrastra o sube de 1 a 8 capturas PNG o JPG
  |  PREPROCESO EN EL CLIENTE (JS, canvas):
  |     reescalado a 1080 px de ALTO conservando proporción -> JPEG calidad 0.9 -> base64
  v
proxy.php  (PHP en el hosting de starcitizen.es)
  |  exige sesión SSO de Discord e inyecta la cabecera X-User-Discord-Id (identidad autoritativa)
  |  consulta la cuota (/v2/cargo/cuota/comprobar) antes de crear el trabajo
  |  CURLOPT_TIMEOUT 300 s SOLO para las rutas de cargo (el resto se queda en 30 s)
  v
Node/Express :3000   (en Baguette, escuchando en 172.17.0.1, nunca público)
  |-- jobs.js            cola de trabajos y 3 capas de filtro: PRECHECK -> CACHE -> MODELO
  |-- lmstudio.js        cadena de proveedores de visión y saneado de la salida
  |-- vision-prompt.js   los tres prompts (sistema, visión, fusión multi-imagen)
  |-- solver.js          optimizador de ruta (nada que ver con la visión)
  |-- db.js              SQLite (preferencias por usuario)
        |
        |-- PRIMARIO: OpenRouter (nube)   -> modelo qwen/qwen3-vl-8b-instruct
        |-- RESPALDO: LM Studio en :1234  -> Qwen3-VL-8B-Instruct-MLX-8bit en un Mac mini M4
                                             (alcanzado por LM Link, sin puertos abiertos)
  v
Respuesta: JSON {screen, reason, contracts[{reward, legs[{to, scu, com, pickups[]}]}]}
  -> saneado en el servidor -> solo {contracts} al navegador
  -> el libro de uso (coste USD real, veredicto) se escribe en MariaDB: dir_cargo_extracciones
```

Modelo de entrega asíncrono **[verificado]**:

```
POST /api/extract-jobs      -> 202 {job_id, status: queued, position}
GET  /api/extract-jobs/:id  -> queued | running | done | error  (el cliente pregunta cada 2 s)
POST /api/extract-contracts -> ruta síncrona antigua, pasa por los mismos carriles
```

---

## 3. Qué reconoce exactamente

De una captura del **gestor de contratos** (mobiGlas) el sistema saca **[verificado, leyendo
vision-prompt.js]**:

1. **Un veredicto sobre la imagen** (campo `screen`), antes de extraer nada:
   - `contract_fullscreen`: captura de pantalla completa de la página del contrato. Se extrae.
   - `sc_wrong_format`: sí es Star Citizen, pero no vale (foto del monitor hecha con el móvil, con
     marco, reflejos, moiré o perspectiva; recorte fuerte; otra pantalla del juego). No se extrae,
     se le explica al usuario, sin sanción.
   - `not_sc`: cualquier otra cosa (otro juego, escritorio, webs, fotos, memes). Cuenta como
     strike, y dos strikes son bloqueo automático en el sitio público.
   - Y un campo `reason` de máximo 12 palabras que se le muestra al usuario.
2. **Los datos del contrato**: `reward` (entero) y una lista de **objetivos de entrega**: destino
   (`to`), cantidad total en SCU (`scu`), mercancía (`com`) y la lista de puntos de recogida
   (`pickups[]`).

Reglas del prompt que valen su peso en oro, porque son las que hacen fiable el resultado:

- Mira **solo** el panel PRIMARY OBJECTIVES y el valor Reward. **Ignora** el título, la
  descripción, el lore, el mapa de ruta, los temporizadores y los botones.
- **Transcribe exactamente** lo que ves: no abrevies, no traduzcas, no autocompletes; si algo no
  se lee, devuelve null.
- **Nunca hagas aritmética**: reporta el número impreso, que el reparto lo hace el código. Esta
  regla nació de un fallo real: al pedirle un tramo por recogida, el modelo estampaba el total en
  cada recogida (total por N) o se dejaba recogidas. Hoy el modelo reporta el total y
  `sanitizeContracts()` reparte en enteros entre las recogidas, con el resto a la primera.
- Multi-imagen: si el contrato no cabe en una captura se mandan hasta 8 vistas de scroll, y un
  `MERGE_PREAMBLE` le dice que son **el mismo** contrato, que fusione y deduplique el solape. El
  veredicto del conjunto es el peor de los individuales.
- El idioma de la interfaz puede variar, pero los nombres de sitios y mercancías salen siempre en
  inglés en el juego. Por eso los prompts están escritos en inglés y no se traducen nunca.

---

## 4. Bibliotecas, modelos y versiones concretas

| Pieza | Qué es | Versión y procedencia |
|---|---|---|
| Modelo de visión primario | `qwen/qwen3-vl-8b-instruct` servido por **OpenRouter** (nube, API compatible con OpenAI) | cuenta propia con saldo prepagado; la clave vive solo en el .env del servidor. **[verificado en el .env de producción: VISION_PRIMARY=openrouter, OPENROUTER_MODEL=qwen/qwen3-vl-8b-instruct, OPENROUTER_TIMEOUT_MS=120000]** |
| Modelo de visión de respaldo | **Qwen3-VL-8B-Instruct-MLX-8bit** (unos 9 GB) servido por **LM Studio** | se descarga de Hugging Face (lmstudio-community/Qwen3-VL-8B-Instruct-MLX-8bit) con `lms get`; el id del modelo es `qwen3-vl-8b-instruct-mlx`; se carga con `--gpu max --context-length 32768`, porque los 32 k de contexto hacen falta para el modo multi-imagen. **[verificado en el README y en el .env]** |
| Backend | Node >= 20 con **Express**, **better-sqlite3** y **dotenv** | `cargo_router/server/package.json`. **Ninguna dependencia de visión ni de imagen.** **[verificado]** |
| Preproceso de imagen | **API Canvas del navegador** (`drawImage` y `toDataURL` en JPEG 0.9) | cero librerías. **[verificado]** |
| Medida del tamaño de imagen en el servidor | parser propio de cabeceras **PNG, WebP y JPEG** escrito a mano (unas 35 líneas, `imageDims()` en jobs.js) | evita instalar un decodificador de imágenes. **[verificado]** |
| Almacén | SQLite (`prefs.sqlite`) para las preferencias, y **MariaDB** (`dir_cargo_extracciones`, `dir_cargo_config`) para el libro de uso y las cuotas | **[verificado]** |
| Salida estructurada | `response_format` de tipo json_schema con un esquema propio (`CONTRACTS_SCHEMA`) y `temperature: 0` | con reintento **una sola vez sin esquema** si el proveedor lo rechaza con 400 o 422. **[verificado]** |

Hay otro uso de visión en el ecosistema, no relacionado con el cargo: el proyecto
`M:\CLAUDE\StarCitizenAI\` identifica naves y escenarios en keyframes de vídeo con
`qwen/qwen3-vl-8b` Q4 en LM Studio **local sobre la GTX 1080 Ti**, también forzando json_schema
(`identify.py`), más un corrector de fabricante que hace de filtro anti-alucinación. Y existe un
plan, no ejecutado que yo haya visto, de una «Capa 2» de OCR sobre esos keyframes con **PaddleOCR
en CPU**: es la única mención de OCR clásico en todo el proyecto, y es un plan, no código.
**[verificado en la memoria sc_vision_keyframes.md]**

---

## 5. Dónde y cómo corre, y cuánto tarda

**[verificado por SSH de solo lectura a Baguette el 2026-09-21]**

- El Node de producción vive en **Baguette** (VPS Debian, carpeta `~/sc-cargo-router/`), **no** en
  la Raspberry Pi. La documentación del repo (`docs/CARGO_ROUTER.md`) sigue diciendo «Raspa
  (prod)» y **es falsa**: es una trampa documental conocida y ya casi tumbó producción una vez.
- No hay systemd: lo mantiene vivo **cron** (cada minuto, más un arranque al reiniciar, vía
  `vigilante.sh`), porque systemctl de usuario exigiría linger y eso exige root.
- Escucha en **172.17.0.1:3000** (la puerta del puente docker0), no en 127.0.0.1: el php-fpm corre
  dentro de un contenedor Docker y su loopback no es el del anfitrión.
- Estado real consultado hoy: `primary: openrouter` alcanzable, y **lmstudio: false**, o sea que el
  respaldo local (Mac mini) está caído y el sistema funciona solo con la nube. Carriles de
  concurrencia: OpenRouter 4, LM Studio 1. Caché con 151 entradas vivas.

**Dónde corre el cómputo de visión: en la nube (OpenRouter), en GPU ajena.** El respaldo corre en
la GPU de un Mac mini M4 de 24 GB (Apple Silicon, runtime MLX). La Pecera (GTX 1080 Ti, Pascal)
**no** participa en el cargo: su GPU se usa para Whisper y FAISS de otros proyectos.

**Tiempos y coste medidos** (del node.log de producción, una imagen por petición) **[verificado]**:

- OpenRouter: **1,7 a 4,2 s por imagen**, unos 3.200 tokens, **0,0004 a 0,0008 USD por imagen**.
- LM Studio en el Mac mini: **8 a 25 s** por captura (una prueba con 1440p dio 8 s directa y 20 s a
  través del Node). El modo scroll con varias imágenes **tarda minutos**: de ahí los timeouts de
  300 s en PHP y en el proxy.
- Techo de gasto diario del sitio público: 3 USD, configurable en base de datos.

---

## 6. Preproceso, y por qué

1. **Reescalado en el cliente a 1080 px de alto**, conservando la proporción, y recompresión a
   **JPEG de calidad 0.9** (constante `TARGET_H = 1080` en `_cargo_shared.php`). Por qué: una
   captura 4K en base64 no cabe razonablemente en el cuerpo de la petición (Express limita a 20 MB,
   y hay un tope de unos 8 MB por imagen, además del `post_max_size` de PHP) y el modelo no gana
   nada con más píxeles. Si la imagen ya mide 1080 o menos, se manda tal cual sin recomprimir.
2. **Precheck barato en el servidor, sin llamar al modelo** (`precheck()` en jobs.js): se leen el
   ancho y el alto **de la cabecera del fichero** (PNG, WebP o JPEG) y se rechaza lo que no puede
   ser una captura de pantalla. Umbrales actuales: ancho mínimo 1000, alto mínimo 560, y relación
   de aspecto entre **1,45 y 3,7** (una foto de móvil en 4:3 da 1,33 y cae fuera; 16:9 es 1,78 y
   32:9 es 3,56). Cuesta cero y filtra fotos verticales y recortes antes de gastar un solo token.
3. **Caché por sha256 del contenido de las imágenes** (TTL de 24 h, máximo 500 entradas): subir dos
   veces la misma captura no cuesta nada.
4. **No hay** umbralizado, binarizado, corrección de perspectiva, recorte automático ni deskew. Es
   coherente con el enfoque: un VLM lee bien la interfaz de un juego sin limpiar la imagen, y esos
   pasos son justo los que necesitaría un pipeline de OCR clásico.
5. **Saneado de la salida** (`sanitizeContracts()`), tratando al modelo como si fuera un cliente
   hostil: coerción a entero no negativo, SCU recortado a 100.000, deduplicación de objetivos y de
   recogidas repetidas (el solape del scroll), descarte de tramos malformados y de contratos sin
   tramos válidos. **El JSON crudo del modelo no sale nunca hacia el navegador.**
6. **Resolución de nombres en el cliente** (`canon()`): el modelo transcribe el nombre del sitio tal
   cual lo ve, con erratas incluidas, y el front lo casa contra la base de datos de ubicaciones por
   coincidencia exacta, luego por nombre inicial, luego por nombre poético de los puntos de
   Lagrange, y por último **por distancia de edición**. Los nombres repetidos se desambiguan usando
   el sistema estelar del otro extremo del mismo tramo. Lo que no se resuelve se deja literal y se
   marca en la interfaz con un aviso.

---

## 7. Qué falla: trampas documentadas

**Del modelo y de la visión** **[verificado en código y diarios]**

- **Aritmética**: el modelo no sabe repartir cantidades. Se le prohíbe calcular y el reparto lo
  hace el servidor. Fue un fallo real con los contratos de la versión 4.8 del juego, donde un
  destino puede tener varias recogidas.
- **Números pequeños y códigos cortos** (las cantidades en SCU, los L1/L2 de los puntos de
  Lagrange) son lo que peor lee; el prompt lo avisa explícitamente.
- **Erratas en los nombres de sitio**: se arreglan aguas abajo con la comparación difusa, no
  pidiéndole al modelo que corrija. De hecho se le prohíbe autocompletar para que no invente.
- **Las fotos de un monitor se detectan bien.** Hay un rechazo real en el log con el motivo
  «Visible monitor bezel and room lighting present». Y el precheck caza los recortes: «image too
  small for a full-screen screenshot (725x376)».
- **Un proveedor puede rechazar el json_schema**: se reintenta una vez sin esquema, confiando en el
  prompt y en el saneado posterior.

**De la infraestructura** **[verificado]**

- **LM Studio no autocarga el modelo (JIT) de forma fiable por API.** Una petición de visión tumbó
  el modelo («The model has crashed without additional information») y el autoload lo recargó con
  **4096 de contexto en vez de 32768**, con lo que el modo multi-imagen dejó de funcionar. Y desde
  la máquina remota no se puede arreglar: `lms load` solo conoce el catálogo **local** de modelos y
  responde «Model not found»; a través de LM Link solo se ve si está cargado o no.
- **LM Studio sirve una generación a la vez.** Sin serializar, dos usuarios simultáneos significan
  que el segundo falla. De ahí la cola con un carril por proveedor (LM Studio = 1).
- **El eslabón corto de los timeouts era PHP** (30 s), mientras Node y Apache ya tenían 300.
  `curl_exec` devolvía false y el usuario veía un 502 confuso.
- **Escuchar en 127.0.0.1 con php-fpm dentro de Docker** deja a todo el mundo fuera; pasó, y fueron
  diez minutos de caída.
- **Los trabajos viven en memoria**: un reinicio del Node los pierde, y el cliente reintenta.
- **Documentación desfasada** como causa raíz de un casi-incidente: fiarse del docs/ en vez de
  comprobar la máquina.
- Hueco conocido: el aviso de saldo bajo (`aviso_saldo_usd`) está en la configuración y en la
  interfaz, pero **nada lo consume**. Lo que protege el gasto es el techo diario y el límite de
  crédito de la clave.

---

## 8. Ficheros clave (rutas completas)

Código del backend de visión (repo del Director, en la Pecera):

- `M:\CLAUDE\director\cargo_router\server\lmstudio.js` — cadena de proveedores, esquema JSON de
  salida, lectura del veredicto y `sanitizeContracts()`. **Es el fichero central.**
- `M:\CLAUDE\director\cargo_router\server\vision-prompt.js` — `SYSTEM_PROMPT`, `VISION_PROMPT` y
  `MERGE_PREAMBLE`.
- `M:\CLAUDE\director\cargo_router\server\jobs.js` — cola con carriles, precheck por cabecera de
  fichero, caché sha256 y topes por usuario.
- `M:\CLAUDE\director\cargo_router\server\index.js` — rutas HTTP: `/api/extract-jobs`,
  `/api/extract-contracts`, `/api/health`, `/api/prompt`, `/api/plan`, `/api/preferences`.
- `M:\CLAUDE\director\cargo_router\server\solver.js` — optimizador de ruta (no es visión).
- `M:\CLAUDE\director\cargo_router\README.md` — arquitectura original y notas de producción.

Cliente y puerta de entrada:

- `M:\CLAUDE\director\web\menus\_cargo_shared.php` — **el preproceso de imagen** (`TARGET_H`,
  `toB64()`), la cola con polling, los mensajes de veredicto y `canon()`. Es compartido por el
  Director y el sitio público.
- `M:\CLAUDE\director\web\menus\transport.php` — envoltura de la página dentro del Director.
- `M:\CLAUDE\director\web_cargo\` — sitio público (`index.php` y un `proxy.php` con lista blanca).
- `M:\CLAUDE\director\web\proxy.php` — puerta autenticada, inyecta `X-User-Discord-Id`.

Cuotas, libro de uso y documentación:

- `M:\CLAUDE\director\cargo_cuotas.py` — cuotas, strikes, bans y verificación de pertenencia.
- `M:\CLAUDE\director\docs\CARGO_ROUTER.md` — documento de referencia (ojo: dice «Raspa» donde hoy
  es Baguette).
- `M:\CLAUDE\director\docs\CARGO_PUBLICO_PLAN.md` — decisiones del sitio público: veredictos,
  strikes, techo de gasto.
- `M:\CLAUDE\director\diario\2026\diario_220.md`, `diario_232.md` y `diario_236.md` — el porqué de
  las decisiones y los fallos reales (el contexto de 4096, la llegada de OpenRouter, el coste real).

En producción (Baguette, leído en solo lectura):

- `~/sc-cargo-router/server/` — copia desplegada del Node.
- `~/sc-cargo-router/.env` — la configuración real (las claves viven ahí, no en el repo).
- `~/sc-cargo-router/node.log` — el log con tiempos y coste por petición.
- `~/sc-cargo-router/arrancar.sh` y `~/sc-cargo-router/vigilante.sh` — arranque por cron.

Memorias del usuario relevantes, en `C:\Users\Roca\.claude\projects\M--CLAUDE\memory\`:
`director_cargo_router.md` (estado real de producción), `sc_vision_keyframes.md` (el otro camino de
visión), `starcitizen_screenshots_folder.md`, `gpu_pascal.md` y `cuda_in_venv.md`.

---

## 9. Qué se puede reutilizar en el sistema del restaurante

El proyecto quiere tres cosas: **(A)** subir fotos de albaranes, **(B)** fotografiar un palet desde
varios ángulos para estimar su volumen, y **(C)** analizar frames de cámaras cenitales para contar
cajas que se sacan del palet.

### Reutilizable casi tal cual (el patrón, no el código de Star Citizen)

1. **La arquitectura entera de imagen -> VLM -> JSON validado.** Es agnóstica del dominio:
   navegador que reescala y manda base64, proxy autenticado que inyecta la identidad, servicio
   pequeño con cola, proveedor de visión, saneado y base de datos. Vale igual para un albarán que
   para un contrato de un juego.
2. **lmstudio.js como plantilla de cadena de proveedores**: primario en la nube, respaldo local,
   el mismo cuerpo de petición para los dos (ambos hablan OpenAI Chat Completions), fallo del
   primario que cae al respaldo de forma transparente, y un `/health` que reporta los dos. Muy útil
   para un restaurante: la nube es rápida y barata, pero si se cae internet el local sigue leyendo
   albaranes.
3. **La disciplina de prompt**, que es lo más valioso del sistema: (a) clasificar antes de extraer
   y devolver un veredicto con motivo corto; (b) decir qué zona mirar y qué ignorar; (c)
   transcribir exacto, null si no se lee, prohibido inventar; (d) **prohibido calcular**, que las
   sumas, el IVA, los totales y las conversiones de unidad las haga el código. En un albarán esto
   es exactamente lo que hace falta.
4. **Salida estructurada con JSON Schema y temperature 0**, con reintento sin esquema.
5. **El saneado de salida como patrón**: tratar la respuesta del modelo como entrada hostil, con
   coerción de tipos, recorte de valores absurdos, deduplicación, descarte de filas malformadas y
   la regla de **no devolver nunca el JSON crudo del modelo**.
6. **El precheck por cabecera de fichero** (`imageDims()`, unas 35 líneas y cero dependencias) para
   rechazar barato lo que no puede servir. Para el restaurante los umbrales cambian de sentido: un
   albarán fotografiado con el móvil es **vertical**, así que el filtro correcto sería resolución
   mínima y quizá nitidez, nunca exigir que sea apaisado.
7. **La caché por sha256**: en un restaurante la misma foto se sube dos veces a diario.
8. **La cola con carriles por proveedor y el patrón 202 más polling**, con tope de trabajos por
   usuario. Evita que un proveedor que solo sirve una generación a la vez se atragante, y que un
   worker de PHP se quede pinzado cinco minutos.
9. **El libro de uso con el coste real por petición**: se pide el bloque de uso con include activo y
   el proveedor devuelve el USD cobrado por esa petición. Para un negocio, saber lo que cuesta cada
   albarán leído es un requisito, no un lujo.
10. **La resolución difusa de nombres** (`canon()`): el modelo transcribe y el código casa contra el
    catálogo propio por exacto, por prefijo y por distancia de edición, marcando lo no resuelto para
    revisión humana. Trasladado al restaurante: casar la descripción del albarán contra el catálogo
    de artículos y proveedores. Es de las piezas más valiosas, y hay que reescribirla con el
    catálogo propio.
11. **La revisión humana como parte del diseño.** En el Cargo Router lo extraído sale en tarjetas
    editables y lo dudoso viene marcado. Copiar eso en el flujo de albaranes.

### Atado a Star Citizen (hay que tirarlo o reescribirlo)

- `vision-prompt.js` entero: los tres prompts hablan de PRIMARY OBJECTIVES, SCU, aUEC y mobiGlas.
  Se reescribe el contenido y **se copia la estructura**.
- El esquema `CONTRACTS_SCHEMA` y los valores de veredicto: la idea del veredicto se queda, los
  valores cambian (por ejemplo albaran_legible, foto_inservible, no_es_albaran).
- `solver.js`, el mapa, la base de datos de ubicaciones, los pesos de coste de viaje y el apaño del
  bug de la version 4.8: nada que ver con un restaurante.
- Las cuotas por pertenencia a la organización y los strikes por imagen ajena: la mecánica de cuota
  y coste es reutilizable, el criterio concreto no.
- El reescalado a **1080 px de alto** está calibrado para capturas de pantalla de un juego. Un
  albarán con letra pequeña probablemente necesite **más** resolución, del orden de 1600 a 2000 px
  en el lado largo. Hay que medirlo, no copiarlo. **[conjetura razonada]**

### Lo que este sistema NO te da para los tres casos

Conviene ser honesto: el Cargo Router resuelve **un** problema, que es leer texto y estructura de
una interfaz digital.

- **(A) Albaranes: encaje directo.** Es el mismo problema. Se copia la arquitectura, se cambian el
  prompt y el esquema, y se añaden el casado contra el catálogo y una pantalla de revisión. Es lo
  primero que haría, y con muy poco trabajo.
- **(B) Volumen de un palet desde varios ángulos: no hay nada reutilizable de la parte de visión.**
  Estimar volumen es geometría: fotogrametría o multi-view stereo, o un sensor de profundidad, o un
  marcador de escala conocido dentro de la foto. Un VLM no mide; como mucho dirá que parece un
  palet europeo con unas cinco capas, que es una estimación gruesa, no una medida. Lo único
  reutilizable es el andamiaje: mandar N imágenes en una sola petición (aquí se hace con hasta 8 y
  un preámbulo que dice que son la misma cosa desde vistas distintas), la cola, la caché y el
  saneado. **El algoritmo de volumen hay que traerlo de fuera**, con OpenCV y calibración o con una
  librería de fotogrametría. **[verificado que no existe nada de esto en el proyecto]**
- **(C) Contar cajas en frames de cámara cenital: tampoco hay nada reutilizable de visión, y el
  enfoque VLM es el equivocado.** Contar objetos por frame y seguirlos entre frames es detección
  más tracking (YOLO o RT-DETR con ByteTrack, o diferencia de fondo si la cámara es fija):
  determinista, en GPU local, decenas de frames por segundo y coste cero por imagen. Un VLM a 2-4 s
  y 0,0005 USD por imagen no sirve para vídeo continuo, y además cuenta mal los objetos repetidos.
  Lo aprovechable aquí es la lección de reparto de carga: filtro barato antes del modelo caro,
  caché, cola con carriles y registro del coste. Curiosamente, en el proyecto hermano
  StarCitizenAI se descartó entrenar YOLO **porque bastaba el VLM zero-shot**; para contar cajas la
  decisión debería ir justo al revés.

### Plan de reutilización que propondría

1. Copiar de `cargo_router/server/` la forma de `lmstudio.js`, `jobs.js` e `index.js` como
   microservicio propio de visión, y reescribir `vision-prompt.js` para albaranes.
2. Añadir la pantalla de revisión humana, con lo dudoso marcado, antes de tocar el stock.
3. Para el palet y el conteo de cajas, **proyectos aparte** con visión clásica y detección,
   reutilizando del cargo solo la cola, el precheck, la caché y la contabilidad del coste.

---

## 10. Qué falta por averiguar

- La **versión exacta de Node** en Baguette: el binario está en `~/node/bin/node` y `node` no está
  en el PATH de una sesión no interactiva, así que no la he leído. El package.json exige >= 20.
- El **estado actual del Mac mini** (LM Studio y LM Link). Hoy el health lo da inalcanzable, pero no
  he entrado en esa máquina para saber si está apagado o solo sin modelo cargado.
- Las **métricas de exactitud**: no he encontrado ningún conjunto de pruebas ni medición formal de
  aciertos y fallos de extracción, solo validaciones manuales sueltas en los diarios (cuatro
  capturas reales extraídas correctas). Si el restaurante necesita una cifra de precisión, hay que
  construir el conjunto de evaluación desde cero.
- La **comparación de calidad entre OpenRouter y el modelo local** quedó anotada como pendiente en
  el diario del 20 de agosto; no he encontrado el resultado.
- El detalle del **registro de minerales** del Director, que es otra lectura de imágenes: según la
  memoria se hace anclando el tooltip por la etiqueta morada del nombre y recortando y ampliando
  con PIL, pero **no he encontrado ese script en el repo**. Todo apunta a que fue un proceso manual
  asistido y no código desplegado, pero lo marco como **no verificado**.
