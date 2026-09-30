"""Dos personas se sientan a una mesa y sala las atiende. Diez segundos.

Es el hermano corto de `video_servicio.py`: mismo local, mismo reparto y mismas
reglas de plano, pero sin una sola pantalla. Aquí no se explica el KDS ni el TPV;
se enseña el momento de antes, el que da pie a todo lo demás —la mesa se ocupa y
alguien de sala se acerca—. Sirve de cabecera para los otros vídeos y de plano de
apoyo cuando hace falta enseñar la sala sin datos por medio.

Diez segundos dan para tres planos, y tres es también el mínimo que pide el
encargo: **dos** personas sentándose es dos planos, porque un plano generado
lleva UN nombre como máximo. `referencia_para` (IP-Adapter) ancla la cara de la
primera persona de la lista y a las demás les copia ese mismo rostro, así que
«Teo y Suri sentados» en un solo encuadre sale como Teo dos veces. Lo comprueba
`main()` y aborta. Se intentó meter al acompañante «de espaldas» para tener dos
cuerpos: no funcionó nunca, el segundo cuerpo no aparecía.

Por eso los dos comensales van en planos consecutivos de la MISMA cámara
(`mesa`): el corte entre ellos se lee como un contraplano —la cámara pasa de uno
al otro en la misma mesa—, que es la forma barata de decir «están juntos» sin
meter dos caras en el encuadre. La narración lo remata; el plano solo no lo dice.

Y no se rueda en `entrada` ni en `mirador`, por si la tentación vuelve: la
primera tiene el mapa de profundidad vacío (56% de píxeles negros, contra un 16%
del resto) y ControlNet no tiene ahí nada que sujetar; la segunda es un ventanal,
y un ventanal le pide al modelo lo que hay al otro lado —salió un rascacielos con
sol contra un negativo que decía «daylight, outdoors, sky» tres veces—.

    python video_mesa.py --guion     lo enseña sin gastar GPU
    python video_mesa.py             el vídeo entero (~2 min de GPU)
"""
import argparse
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from estudio import elenco as E          # noqa: E402
from estudio import guion as Gu          # noqa: E402
from estudio import produccion as Pr     # noqa: E402

CAMARERO = "oliver"
COMENSALES = ["teo", "suri"]

PROMPT = ("Dos personas se sientan a una mesa de la Cantina Vesta-9 y un camarero "
          "las atiende.")

ESCENAS = [
    # El único plano de los tres sin molde previo: en el vídeo largo Teo llega
    # de pie al atraque y se sienta ya con el móvil, y aquí hace falta el gesto
    # de sentarse a secas. Sin molde hay que rodar tomas y mirar, que es para lo
    # que está `toma` — y `toma=2` sale de mirar las cuatro con
    # `probar_tomas.py --guion video_mesa 1 0 1 2 3`:
    #   · toma 0 lo pone lejos y pequeño, y la sala se lee como oficina;
    #   · toma 1 encuadra bien pero la sala es un cuartito con una puerta;
    #   · toma 2 lo sienta a una mesa redonda con más mesas detrás → comedor;
    #   · toma 3 sale oscuro y de cabeza gacha.
    # «seen from the waist up» tampoco es adorno: ControlNet fija la sala, pero el
    # TAMAÑO de quien la ocupa lo decide el texto, y sin pedirlo el modelo pone a
    # la persona a quince metros y del tamaño de un pulgar (toma 0 lo enseña).
    dict(camara="mesa", segundos=3, personajes=["teo"], toma=2,
         accion="a young man sits down on a chair at the table, one hand on the "
                "table top, seen from the waist up",
         evitar="standing, walking, lying down, fashion pose",
         narracion="Teo se sienta a una mesa de la Cantina Vesta-9.",
         rotulo=""),

    # Misma cámara que el plano anterior a propósito: el corte es un contraplano
    # y con eso se entiende que comparten mesa.
    #
    # La acción está copiada LETRA POR LETRA de `video_servicio.py`, y su posición
    # en la lista también. No es pereza: la semilla es
    # `f(cámara, acción, índice, toma)` (`guion.py`), así que misma cámara, mismo
    # texto, mismo índice y misma toma devuelven EL MISMO fotograma —y el de allí
    # ya está mirado y aprobado, Suri con su abrigo verde sentada a la mesa—.
    # Cambiar una coma es volver a jugar a la lotería. Se aprendió caro: la
    # primera versión de este guion decía «looking across the table, seen from
    # the waist up» en vez de «looking towards the door», y esa coma de más sacó
    # a una mujer distinta en una cocina doméstica con sillas verdes que no es la
    # cantina. Lo mismo el plano 3: con «seen from the waist up» de más, el
    # camarero salió siendo una azafata de vuelo, con «woman, female» en el
    # negativo y las seis fotos de referencia de Óliver puestas.
    dict(camara="mesa", segundos=3, personajes=["suri"],
         accion="a woman sits at the table, hands resting on it, looking towards "
                "the door",
         evitar="lying down, reclining, fashion pose, legs stretched out",
         narracion="Suri se sienta enfrente: cenan juntos.",
         rotulo=""),

    # Índice 2 y texto exacto del plano 3 del vídeo largo, por lo mismo de arriba.
    dict(camara="comedor", segundos=4, personajes=["oliver"],
         accion="a waiter stands at a table holding a tablet in one hand, taking an order",
         narracion="Sala se acerca a atenderles y abre la mesa.",
         rotulo="Sala atiende la mesa"),
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
            tutorial=False,
        ))
    return Gu.Guion(titulo="Una mesa se ocupa en la Cantina Vesta-9",
                    tipo="escena", escenas=escenas, prompt=PROMPT)


def main() -> int:
    p = argparse.ArgumentParser(description="El vídeo corto de la mesa")
    p.add_argument("--guion", action="store_true", help="enseña el guion y no gasta GPU")
    p.add_argument("--sin-voz", action="store_true")
    p.add_argument("--sin-publicar", action="store_true",
                   help="lo deja en salidas/ para mirarlo antes de subirlo")
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

    print(f"\n{len(generados)} planos de GPU, unos {len(generados) * 40 // 60 or 1} minutos.\n")
    t = Pr.Trabajo(Pr._nuevo_id())
    try:
        estado = Pr.producir(g.prompt, t, con_voz=not args.sin_voz, guion_hecho=g,
                             publicar=not args.sin_publicar)
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
