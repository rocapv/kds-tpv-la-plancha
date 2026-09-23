"""El cronómetro de los bots de la demo: rachas, pero nunca todos a la vez.

Lo que se protege aquí no es el aspecto de la demo, es que no se forme un cuello de botella
delante del tribunal: si todos los camareros apretaran a la vez mientras toda la cocina va
floja, la pantalla del pase se llena de tarjetas que nadie saca.
"""
from app.simulacion import (CICLO_MARCHA, COLA_APURO, COLA_ATASCO, FACTORES,
                            PLATOS_EN_APURO, marcha_en, repartir_desfases)


def test_cada_marcha_dura_tres_minutos():
    assert CICLO_MARCHA == 180.0
    assert marcha_en(0, 0) == "fuerte"
    assert marcha_en(0, 179) == "fuerte"
    assert marcha_en(0, 181) == "flojo"
    assert marcha_en(0, 361) == "fuerte"          # y vuelve a empezar


def test_ir_fuerte_es_mas_del_doble_de_rapido_que_ir_flojo():
    assert FACTORES["fuerte"] < 0.5 < 1 < FACTORES["flojo"]


def test_los_desfases_reparten_el_ciclo_entero():
    d = repartir_desfases(4)
    assert d == [0.0, 90.0, 180.0, 270.0]
    assert repartir_desfases(1) == [0.0]
    assert repartir_desfases(0) == []


def test_nunca_van_todos_a_la_misma_marcha():
    """Con dos bots o más, en NINGÚN instante del ciclo coinciden todos."""
    for cuantos in (2, 3, 4, 5, 6, 8):
        desfases = repartir_desfases(cuantos)
        for t in range(0, int(CICLO_MARCHA * 2), 5):
            marchas = {marcha_en(d, t) for d in desfases}
            assert len(marchas) == 2, f"con {cuantos} bots, en t={t} todos van «{marchas}»"


def test_la_capacidad_total_no_se_mueve():
    """Siempre hay aproximadamente la mitad del equipo apretando.

    Esta es la propiedad que evita el cuello de botella, y no «que no cambien dos a la vez»:
    en los desfases opuestos el relevo es simultáneo (uno baja justo cuando el otro sube), y
    eso está bien, porque la capacidad del equipo se queda igual. Lo que no puede pasar nunca
    es que el equipo entero se ponga flojo mientras el otro lado sigue produciendo.
    """
    for cuantos in (2, 3, 4, 5, 6, 8):
        desfases = repartir_desfases(cuantos)
        for t in range(0, int(CICLO_MARCHA * 2), 5):
            fuertes = sum(1 for d in desfases if marcha_en(d, t) == "fuerte")
            assert abs(fuertes - cuantos / 2) <= 1, (
                f"con {cuantos} bots, en t={t} van fuerte {fuertes}")


def test_las_valvulas_van_en_el_sentido_correcto():
    """Apretar tiene que ser más rápido que ir fuerte, y esperar más lento que ir flojo."""
    assert FACTORES["apuro"] <= FACTORES["fuerte"] < 1 < FACTORES["espera"] <= FACTORES["flojo"]
    # El cocinero apurado saca varias de una tacada, o no recupera nunca el terreno perdido.
    assert PLATOS_EN_APURO >= 2
    # La sección se da por apurada ANTES de que la cocina entera se dé por atascada.
    assert COLA_APURO < COLA_ATASCO
