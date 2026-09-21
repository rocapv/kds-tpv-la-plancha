# Análisis de un KDS comercial (STARPOS) · competencia directa

Estudio de un vídeo de demostración de un KDS integrado en un TPV Windows, hecho para el
apartado de competencia de la memoria. El objetivo no es copiar, sino ver **qué resuelve su
producto, cómo lo enseña y dónde se queda corto** frente al sistema de este proyecto.

## Ficha

| Dato | Valor |
|---|---|
| Vídeo | «KDS desde punto de venta Windows» |
| Canal | Capacitación y asesorías Mys inventarios |
| Publicado | 3 de septiembre de 2026 |
| Duración | 2 min 51 s |
| Resolución | 638×360, 30 fps |
| Producto | STARPOS (marca visible en la tableta y en el TPV) |

## Cómo se ha procesado

| Paso | Herramienta | Dónde |
|---|---|---|
| Descarga | `yt-dlp` | Raspa (es quien habla con YouTube) |
| Fotogramas a 10 fps | `ffmpeg -vf fps=10` | Pecera · 1.708 imágenes, 51 MB |
| Audio | `ffmpeg` a WAV 16 kHz mono | Pecera |
| Transcripción | faster-whisper `medium`, `int8_float32`, `multilingual=True` | GPU de Pecera · 30 segmentos |
| Fotogramas clave | diferencia media entre imágenes consecutivas | 18 momentos de cambio real |

Dos detalles del procesado que conviene recordar: en la 1080 Ti hay que usar `int8_float32`
—`float16` no va en Pascal— y sin `multilingual=True` el modelo traduce en lugar de transcribir.

El vídeo está **grabado con una cámara apuntando a la pantalla**, no capturado por software: hay
reflejos, desenfoque y una mano tapando la interfaz a cada paso. Por eso el «cambio medio entre
fotogramas» es alto en todo el vídeo (10,6 sobre 255) y prácticamente ningún fotograma es idéntico
al anterior, aunque la pantalla no cambie: se mueve la cámara, no la aplicación.

## Qué enseña, paso a paso

| Momento | Qué ocurre |
|---|---|
| 0:00–1:05 | Cómo actualizar el TPV: Configuración → Actualizar, confirmar, esperar la sincronización y reiniciar. Al volver, la aplicación muestra el número de versión |
| 1:13 | Inicio de sesión con el usuario **cajero** |
| 1:20–1:40 | Desde la tableta del **mesero**: se eligen productos y se pulsa **Enviar orden**; suena una notificación |
| 1:45–1:52 | En el TPV Windows: menú de la esquina superior derecha → opción **KDS** |
| 1:57–2:10 | El KDS muestra las comandas en tres columnas: **GENERADAS**, **EN PREPARACIÓN** y **DESPACHADAS**. Cada tarjeta lleva mesa, número de orden, usuario, hora de creación y minutos transcurridos |
| 2:10–2:31 | Botón **Iniciar preparación**; luego **Despachar 1** por producto o **Despachar todo** para la comanda entera |
| 2:36–2:46 | Filtro de **fecha inicial y final** para consultar comandas de días anteriores |

## Lo que hacen igual y lo que hacen distinto

| Asunto | STARPOS | Este proyecto |
|---|---|---|
| Estructura del KDS | Tres columnas por estado, en una sola pantalla | Una pantalla por estación (placa, fritura, fríos, barra) más el pase |
| Reparto del trabajo | Todas las comandas juntas: cada cocinero busca lo suyo | Cada línea va a la estación que la cocina; nadie ve lo que no es suyo |
| Avance | Botón «Iniciar preparación» y «Despachar» | Igual, y además el estado se puede **deshacer** |
| Granularidad | Por producto («Despachar 1») o toda la comanda | Por línea o toda la comanda |
| Tiempo en pantalla | Minutos transcurridos, sin aviso visual | Minutos + amarillo a los 8 y rojo a los 15 |
| Dónde vive el KDS | Dentro del TPV, como una opción de menú | Pantalla propia con su dirección; se cuelga un monitor y ya está |
| Actualizaciones | Manuales, con parada del TPV y reinicio | `desplegar.sh`: copia, pruebas y reinicio del servicio |
| Histórico | Filtro por fechas dentro del KDS | Informe de cierre y facturación por día |

## Observaciones útiles

**Un acierto que merece la pena copiar:** el filtro por fechas dentro del propio KDS. Permite mirar
comandas de días anteriores sin salir de la pantalla de cocina, algo que en nuestro sistema hoy
obliga a ir al informe.

**Un problema visible en su propia demostración:** una de las comandas marca **360 min** en la
tarjeta. El contador sigue subiendo sin más, sin ningún aviso de color. En un servicio real, un
número así ya no informa de nada: si algo lleva seis horas sin despacharse, lo que hace falta es que
la pantalla grite, no que cuente. Nuestro umbral de 8 y 15 minutos nace justo de esto.

**Una diferencia de diseño, no de calidad:** su KDS es una ventana más del TPV, lo que obliga a
tener un equipo Windows con el punto de venta instalado para ver las comandas. El nuestro es una
página: cualquier pantalla con navegador vale, y por eso poner una en cada estación no cuesta una
licencia más. Es exactamente el argumento del apartado de competencia de la memoria.

**Lo que su vídeo deja sin enseñar** y nosotros sí tenemos documentado: qué pasa si se cae la red,
cómo se hacen las copias de seguridad, quién puede ver qué y si el tráfico va cifrado.

## Para la memoria

Este análisis refuerza el apartado 2.2 (competencia): el mercado cubre la funcionalidad básica
—comanda, estados y despacho— pero la reparte por licencias de terminal y la deja atada a un equipo
Windows. La diferencia de este proyecto no está en hacer algo que no exista, sino en que poner una
pantalla más en la cocina no cueste dinero ni dependa del sistema operativo.

---

Material de trabajo (transcripción completa, 1.708 fotogramas y los 18 fotogramas clave) en el
directorio temporal de la sesión; no se guarda en el repositorio porque es contenido de terceros.
