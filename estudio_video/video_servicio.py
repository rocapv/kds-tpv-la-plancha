"""Un servicio completo: dos comensales y un camarero, de la puerta a la factura.

Este vídeo tiene un encargo concreto: servir de **ejemplo visual de cómo funciona
el KDS+TPV**. Por eso el guion no lo escribe el modelo de lenguaje, se escribe
aquí. Un guionista automático ordena las escenas por lo que suena bien; este
orden lo manda el sistema, y es el que hay que respetar:

    sala abre la mesa ─► el cliente pide ─► la comanda entra en cocina
    ─► cocina la marca lista ─► SALA la recoge del pase y la lleva
    ─► el cliente paga desde la app ─► el TPV cierra el cobro

La regla que más se equivoca al contarla es la del pase: cocina termina en
«lista», pero **quien la lleva a la mesa es sala**. Si el vídeo enseña a un
cocinero sirviendo, enseña algo que el sistema no hace. Aquí se dice en voz alta
en el plano 10, porque es el que se malinterpreta.

Cuatro decisiones, y las cuatro salen de mirar las tiradas plano a plano:

  · **Un solo personaje con nombre por plano generado.** `referencia_para` ancla
    la cara de la PRIMERA persona de la lista y nada más; las demás caras del
    encuadre las pinta el modelo copiando el único rostro que tiene delante. Lo
    comprueba `main()` y aborta si hay dos. (Se intentó meter al acompañante «de
    espaldas» para tener dos cuerpos en cuadro: no funcionó nunca, el segundo
    cuerpo sencillamente no aparecía, y se quitó.)
  · **Las pantallas van SIN las burbujas del tutorial.** Las burbujas explican la
    interfaz iluminando un elemento y apagando el resto; aquí lo que hay que ver
    es el dato —la mesa abierta, la comanda entrando, el aviso de la cuenta— y
    quien explica es la narración.
  · **El reparto lo eligen las fichas, no el azar.** El elenco tiene
    `personalidad` escrita justo para esto. Nadia «no se fía de las pantallas:
    prefiere pedirle al camarero», así que ponerla a pagar desde la app —como
    hacía la primera versión de este guion— es enseñar a un personaje haciendo
    lo contrario de lo que dice su ficha. Los que sí encajan: **Teo**, que «come
    con el móvil en la mano», pide por QR; **Suri**, que «paga desde la app sin
    levantar la vista», paga; y **Óliver** es sala.
  · **Un plano que sale mal se vuelve a rodar, no se arregla con una constante.**
    Para eso está `toma`: reorienta la semilla de ESE plano y deja los demás
    intactos. Antes, la única palanca era global, y subir la fuerza de ControlNet
    para salvar un plano estropeaba los otros seis. Las tomas se miran con
    `probar_tomas.py` y la elegida se escribe aquí.

Dos detalles de redacción que costaron un plano cada uno:

  · Al móvil se le dice **dónde está y hacia dónde se mira**, nunca «holds up a
    phone»: con «up» el modelo entiende llamada y lo coloca en la oreja. Y aun
    diciéndolo bien seguía haciéndolo, porque en las fotos de las que aprendió un
    móvil junto a una cara casi siempre es una llamada; lo que lo arregló fue
    decirlo en NEGATIVO, en el campo `evitar`.
  · Hay que pedir el **tamaño de la persona en el encuadre** («seen from the
    waist up»). ControlNet fija la sala, pero no dice a qué distancia está quien
    la ocupa, y por defecto el modelo la pone lejos y pequeña.

    python video_servicio.py --guion     lo enseña sin gastar GPU
    python video_servicio.py             el vídeo entero (~5 min de GPU)
"""
import argparse
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from estudio import biblia as B          # noqa: E402
from estudio import elenco as E          # noqa: E402
from estudio import guion as Gu          # noqa: E402
from estudio import produccion as Pr     # noqa: E402

CAMARERO = "oliver"
COMENSALES = ["teo", "suri"]

PROMPT = ("Dos comensales y un camarero: piden, son servidos y pagan. Un ejemplo "
          "visual de cómo funciona el servicio con el KDS y el TPV.")

# Cada escena es un paso del servicio. `personajes` lleva UN nombre como máximo:
# es el único al que IP-Adapter le ancla la cara, y lo que haya de más sale
# clonado de él. El acompañante, cuando hace falta, va «seen from behind».
ESCENAS = [
    # NO se rueda en `entrada`, que es la cámara que pide el sentido común para
    # una llegada. Su mapa de profundidad está VACÍO —56% de píxeles negros, y
    # ninguna otra cámara de interior pasa del 16%—, así que allí ControlNet no
    # tiene nada que sujetar y el modelo devuelve a la persona posando en un
    # cuarto que no es la cantina, a cualquier fuerza. Se arregla en el plano,
    # no aquí. Mientras tanto, la llegada se cuenta desde el mirador, que además
    # es el sitio bonito del local.
    # Tercera cámara para esta llegada, y por fin una que aguanta. `entrada` está
    # descartada arriba. `mirador` tampoco vale, y no por el mapa —tiene un 94% de
    # cobertura, de las mejores— sino por lo que hay en él: es un ventanal, y un
    # ventanal le pide al modelo lo que hay AL OTRO LADO. Salió un rascacielos con
    # sol, contra un negativo que dice «daylight, outdoors, sky» tres veces. La
    # geometría manda dentro del encuadre, no fuera de él, y por un agujero en la
    # pared se cuela todo. `atraque` es pared, barra y caja: no hay por dónde.
    #
    # «seen from the waist up» tampoco es un capricho: sin eso el modelo pone a la
    # persona a quince metros y del tamaño de un pulgar. ControlNet fija la sala;
    # el TAMAÑO de quien la ocupa lo decide el texto, y hay que pedirlo.
    dict(camara="atraque", segundos=4, personajes=["teo"], toma=2,
         accion="a young man arrives at the counter and looks across the dining "
                "room, seen from the waist up",
         narracion="Teo llega a cenar a la Cantina Vesta-9.",
         rotulo=""),

    dict(camara="mesa", segundos=4, personajes=["suri"],
         accion="a woman sits at the table, hands resting on it, looking towards "
                "the door",
         evitar="lying down, reclining, fashion pose, legs stretched out",
         narracion="Suri ya tiene mesa: cenan juntos.",
         rotulo=""),

    dict(camara="comedor", segundos=5, personajes=["oliver"],
         accion="a waiter stands at a table holding a tablet in one hand, taking an order",
         narracion="Sala les atiende y abre la mesa en el TPV.",
         rotulo="Sala abre la mesa"),

    dict(camara="atraque", segundos=6, pantalla="tpv",
         narracion="Cada mesa dice qué está esperando: sin pedir, en cocina, "
                   "lista en el pase o esperando la cuenta.",
         rotulo="TPV · el estado de cada mesa"),

    # El `evitar` de este plano es el que justifica que exista el campo. En las
    # fotos con las que se entrenó el modelo, un móvil cerca de una cara es casi
    # siempre una llamada, así que por mucho que el positivo diga «mira la
    # pantalla», el teléfono se le iba a la oreja toma tras toma. No hay manera de
    # escribir «no estás llamando» en positivo; en negativo sí.
    dict(camara="mesa", segundos=4, personajes=["teo"],
         accion="a seated young man looks down at a phone held in both hands over "
                "the table",
         evitar="phone to ear, phone call, talking on the phone, hand raised to head",
         narracion="Teo lee el código de su mesa con el móvil.",
         rotulo="El cliente pide desde su móvil"),

    dict(camara="mesa", segundos=6, pantalla="cliente",
         narracion="La carta se abre en su teléfono, con los alérgenos de cada plato.",
         rotulo="Carta del cliente · alérgenos"),

    dict(camara="cocina", segundos=6, pantalla="kds",
         narracion="Al confirmar, la comanda entra en cocina repartida por estaciones.",
         rotulo="KDS · la comanda entra en cocina"),

    # Sin nombre a propósito: cocina no está en el elenco, y de espaldas no hay
    # cara que anclar ni que clonar.
    dict(camara="cocina", segundos=4, personajes=[],
         accion="a cook at a hot plate, steam and flame rising, seen from behind",
         narracion="Cada tarjeta cambia de color con el tiempo: nadie mira el reloj.",
         rotulo=""),

    dict(camara="pase", segundos=5, pantalla="sala",
         narracion="Cuando cocina la marca lista, sala la ve en el pase.",
         rotulo="Sala · listo en el pase"),

    dict(camara="comedor", segundos=5, personajes=["oliver"],
         accion="a bearded waiter sets a plate down on a table between the tables "
                "of the dining room",
         evitar="floating object, transparent body, double exposure, ghost",
         narracion="Y es sala quien recoge del pase y lleva el plato a la mesa, "
                   "no cocina.",
         rotulo="Sala entrega en mesa"),

    # `toma=3` no es superstición: las tomas 1 y 2 de este plano le quitaron el
    # abrigo verde y la dejaron en top, que es dejar de ser el personaje. Se
    # eligió mirando las cuatro con `probar_tomas.py`.
    dict(camara="mesa", segundos=4, personajes=["suri"], toma=3,
         accion="a seated woman looks down at a small phone flat on the table and "
                "taps it with one finger",
         evitar="camera, video camera, binoculars, phone to ear, phone call",
         narracion="Suri pide la cuenta desde la app y paga con ella.",
         rotulo="Pago desde la app"),

    # `gesto="cobrar"` porque este plano y el 4 son la MISMA pantalla, y sin gesto
    # salían el mismo fotograma: el mapa de mesas, quieto, dos veces. El segundo
    # promete un paso —«cierra el cobro y emite el ticket»— que no se veía, y en un
    # vídeo que existe para enseñar cómo funciona el servicio eso se lee como que
    # ese paso no existe. El gesto abre la mesa que espera la cuenta, saca el panel
    # de cobro y elige tarjeta: se ve el total, lo pendiente y el ticket.
    dict(camara="atraque", segundos=5, pantalla="tpv", gesto="cobrar",
         narracion="El TPV cierra el cobro y emite el ticket o la factura.",
         rotulo="TPV · cobro y factura"),
]


def guion() -> Gu.Guion:
    escenas = []
    for e in ESCENAS:
        escenas.append(Gu.Escena(
            camara=e["camara"],
            accion=e.get("accion", ""),
            narracion=e["narracion"],
            personajes=e.get("personajes", []),
            segundos=e["segundos"],
            rotulo=e.get("rotulo", ""),
            evitar=e.get("evitar", ""),
            toma=e.get("toma", 0),
            pantalla=e.get("pantalla"),
            gesto=e.get("gesto", ""),
            pantalla_como="completa" if e.get("pantalla") else "inserto",
            tutorial=False,          # se enseña el dato, no la explicación de la interfaz
        ))
    return Gu.Guion(titulo="Un servicio completo en la Cantina Vesta-9",
                    tipo="escena", escenas=escenas, prompt=PROMPT)


def main() -> int:
    p = argparse.ArgumentParser(description="El vídeo del servicio completo")
    p.add_argument("--guion", action="store_true", help="enseña el guion y no gasta GPU")
    p.add_argument("--sin-voz", action="store_true")
    args = p.parse_args()

    g = guion()
    generados = [e for e in g.escenas if not e.pantalla]
    pantallas = [e for e in g.escenas if e.pantalla]

    print(f"{g.titulo}")
    print(f"{len(g.escenas)} planos, {g.segundos} s: {len(generados)} generados, "
          f"{len(pantallas)} pantallas grabadas")
    for i, e in enumerate(g.escenas, start=1):
        que = (f"pantalla {e.pantalla}" + (f":{e.gesto}" if e.gesto else "")
               if e.pantalla else "+".join(e.personajes) or "sin gente")
        print(f"  {i:2d}. {e.camara:8s} {e.segundos}s  {que:24s} {e.narracion}")

    # La regla del plano: más de un nombre y las caras de sobra salen clonadas de
    # la primera. Se comprueba aquí y no se confía en la revisión a ojo.
    multiples = [i for i, e in enumerate(g.escenas, start=1) if len(e.personajes) > 1]
    if multiples:
        print(f"\nplanos con más de un personaje anclado: {multiples}. "
              "IP-Adapter solo ancla al primero y clona su cara en los demás.")
        return 1

    if args.guion:
        return 0

    faltan = [c for c in [CAMARERO] + COMENSALES if not E.vistas_de(c)]
    if faltan:
        print(f"\nsin hoja de personaje: {', '.join(faltan)}. "
              "Lanza `python estudio_cli.py hojas`.")
        return 1

    print(f"\n{len(generados)} planos de GPU, unos {len(generados) * 40 // 60} minutos.\n")
    t = Pr.Trabajo(Pr._nuevo_id())
    try:
        estado = Pr.producir(g.prompt, t, con_voz=not args.sin_voz, guion_hecho=g)
    except Exception as e:
        print(f"FALLÓ: {e}")
        return 1
    print(f"\nlisto: {Pr.DIR_SALIDAS / estado['salida']}")
    if estado.get("url"):
        print(f"publicado: {estado['url']}")
    for a in estado["avisos"]:
        print(f"  aviso: {a}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
