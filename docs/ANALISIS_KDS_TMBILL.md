# Análisis de un KDS comercial (TMBill) · el ecosistema completo

Segundo estudio de competencia, esta vez de un producto mucho más grande: TMBill, una suite india
de TPV para restauración. El vídeo es un tutorial de 15 minutos sobre cómo conectar su KDS al TPV.
Interesa porque enseña **el ecosistema entero**, no solo la pantalla de cocina: aplicación de
camarero en el móvil, pedido del propio cliente, pedidos digitales y KDS en Windows y en Android.

## Ficha

| Dato | Valor |
|---|---|
| Vídeo | «Kitchen Display System — KDS & Token Management System for Restaurants, Café & QSR» |
| Canal | TMBill |
| Publicado | 3 de marzo de 2023 · 8.533 visitas |
| Duración | 15 min 18 s |
| Resolución | 1920×1080, 30 fps |
| Idioma | Hindi (el título está en inglés) |

## Cómo se ha procesado

Misma cadena que el análisis anterior: `yt-dlp` desde Raspa, `ffmpeg` para el audio y los
fotogramas, faster-whisper en la GPU de Pecera y selección de fotogramas clave por diferencia.

| Paso | Resultado |
|---|---|
| Fotogramas a 10 fps (escalados a 960 px) | 9.175 imágenes, 533 MB |
| Transcripción | 128 segmentos, idioma detectado **hindi** |
| Fotogramas clave | 24 momentos de cambio real |

**Un dato que sirve de método:** aquí el **95 %** de los fotogramas es prácticamente idéntico al
anterior (cambio medio 0,86 sobre 255), porque es una captura de pantalla por software. En el vídeo
anterior, grabado con una cámara apuntando al monitor, ese porcentaje era del **0 %**. La misma
medida distingue un tutorial capturado de uno filmado, y dice de antemano cuántos fotogramas clave
tiene sentido extraer.

La transcripción salió en hindi, como debe ser: con `multilingual=True` el modelo transcribe lo que
oye. Sin esa opción habría devuelto una traducción al inglés y el análisis habría partido de un
texto que nadie dijo.

## Qué enseña

| Momento | Contenido |
|---|---|
| 0:05–1:10 | El KDS funciona en dos plataformas: **tableta Android** y **Windows**. En el back office, la aplicación Android se llama **CS**: *Captain, Self ordering and Kitchen Display System*, las tres cosas en una |
| 1:13 | El KDS de Windows en marcha: tarjetas por comanda (KOT) con mesa, número de KOT, usuario, productos y «5 min ago» |
| 2:00–4:10 | Configuración: conectar el KDS al TPV, elegir qué sale en cada pantalla |
| 8:15–9:20 | Instalación y arranque de la aplicación |
| 10:05–11:00 | El TPV: carta con **fotos y tiempo de preparación por producto** («30 minutes»), pestañas **Dine In / PickUp-Delivery / Quick Bill**, cuenta dividida, asignar camarero y cobro |
| 13:20–14:00 | El KDS con carga real: comandas de mesa, de camarero, de **Quick Bill** y de **Digital Order** (pedido online), con el encabezado en **rojo a los 19-28 minutos** frente al verde de las recientes |
| 14:50–15:18 | Cierre: «Settle All», contador de KOT pendientes y cierre de sesión |

## Lo que se aprende para este proyecto

**1. El KDS es la punta del iceberg.** Su valor no está en la pantalla de cocina, sino en que la
comanda puede entrar por cuatro caminos —camarero en el móvil, cliente desde su propio teléfono,
mostrador y pedido online— y todos acaban en la misma cocina. Nuestro sistema hoy solo tiene un
camino: el TPV de sala.

**2. La aplicación de camarero es un móvil, no una tableta de barra.** Su «Captain» es exactamente
eso: tomar la comanda de pie, junto a la mesa. Nuestro TPV funciona en cualquier navegador, pero la
interfaz está pensada para una pantalla grande; en un móvil se queda corta.

**3. El cliente pide desde su teléfono.** Su «Self ordering» es la carta en el móvil del cliente,
normalmente tras un QR en la mesa. Para un local pequeño esto quita trabajo de sala en las horas
punta, que es justo cuando falta gente.

**4. El tiempo de preparación por producto** aparece en la carta («30 minutes»). Nosotros medimos el
tiempo real en cocina, pero no declaramos el previsto: teniéndolo se puede avisar al cliente de
cuánto va a tardar su pedido.

**5. Confirmación de lo que ya hacemos bien:** su KDS también colorea por retraso (verde → rojo) y
avanza por estados, lo que respalda nuestra decisión de los umbrales de 8 y 15 minutos. Y su KDS de
Windows es una aplicación que hay que instalar y conectar —el vídeo dedica nueve de sus quince
minutos a instalarlo y configurarlo—, mientras que el nuestro es una dirección que se abre en
cualquier navegador.

## Consecuencia directa

De este análisis salen las dos piezas que faltan y que se abordan a continuación:

- **Versión móvil para el personal**: el TPV en el bolsillo del camarero.
- **Versión web para el cliente**: la carta y el estado del pedido en el teléfono del cliente, sin
  instalar nada y sin PIN.

---

Material de trabajo (vídeo, 9.175 fotogramas, transcripción y fotogramas clave) en el directorio
temporal de la sesión; no se guarda en el repositorio porque es contenido de terceros.
