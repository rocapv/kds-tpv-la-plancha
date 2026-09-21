#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador del MAPA DE MERCADO SIMULADO — proyecto KDS+TPV
Proyecte Intermodular, 1r CFGS ASIR.

=========================== AVISO ===========================
TODOS LOS LOCALES DE ESTE FICHERO SON FICTICIOS.
Ni los nombres, ni las direcciones, ni las coordenadas exactas,
ni las cifras corresponden a ningún negocio real de València.
Se generan por sorteo con semilla fija para un trabajo académico.
Atribuir estos datos inventados a un negocio real seria una
difamación: por eso los nombres se construyen combinando piezas
que NO pueden coincidir con una marca existente y la página lo
advierte en cabecera y en pie.
=============================================================

Salida: locales.json, junto al HTML que lo carga.

Por qué semilla fija: el mapa se enseña en clase y se cita en la memoria.
Si cambiara en cada ejecución, las cifras del documento dejarían de cuadrar
con lo que se ve en pantalla.
"""

import json
import random
from pathlib import Path

random.seed(2026)  # resultado reproducible, ver docstring

# ---------------------------------------------------------------------------
# Barrios REALES de València con un rectángulo aproximado de coordenadas.
# El barrio es real (es geografía pública, no un negocio), pero el punto
# concreto se sortea dentro del rectángulo: así ningún marcador cae sobre
# un local existente de forma señalada.
# (lat_min, lat_max, lon_min, lon_max)
# ---------------------------------------------------------------------------
BARRIOS = {
    "Russafa":        (39.4570, 39.4640, -0.3810, -0.3710),
    "El Cabanyal":    (39.4620, 39.4720, -0.3300, -0.3210),
    "Benimaclet":     (39.4830, 39.4890, -0.3610, -0.3520),
    "Ciutat Vella":   (39.4700, 39.4790, -0.3830, -0.3720),
    "Campanar":       (39.4790, 39.4870, -0.4000, -0.3890),
    "Patraix":        (39.4590, 39.4660, -0.3990, -0.3890),
    "Algirós":        (39.4740, 39.4810, -0.3480, -0.3380),
    "Extramurs":      (39.4680, 39.4750, -0.3920, -0.3830),
    "L'Olivereta":    (39.4650, 39.4720, -0.4050, -0.3960),
    "Jesús":          (39.4530, 39.4600, -0.3900, -0.3800),
    "Quatre Carreres":(39.4440, 39.4560, -0.3720, -0.3580),
    "Poblats Marítims":(39.4530, 39.4620, -0.3330, -0.3230),
    "Camins al Grau": (39.4640, 39.4720, -0.3530, -0.3420),
    "La Saïdia":      (39.4830, 39.4890, -0.3800, -0.3700),
    "Rascanya":       (39.4900, 39.4970, -0.3700, -0.3600),
    "Benicalap":      (39.4900, 39.4970, -0.3900, -0.3800),
    "Pla del Real":   (39.4760, 39.4820, -0.3640, -0.3560),
    "L'Eixample":     (39.4640, 39.4700, -0.3700, -0.3620),
}

# Tipos de local y su perfil: cada uno arrastra un modo de cocinar distinto,
# y de ahí salen las estaciones y el volumen. El peso hace que el censo se
# parezca al reparto real de un barrio (muchos bares, pocas dark kitchen).
TIPOS = {
    "bar de barrio":  {"peso": 22, "color": "#c0844a"},
    "cafetería":      {"peso": 14, "color": "#d9b45b"},
    "hamburguesería": {"peso": 11, "color": "#cf5f3b"},
    "arrocería":      {"peso": 10, "color": "#e67e22"},
    "pizzería":       {"peso": 11, "color": "#b5533f"},
    "asiático":       {"peso":  9, "color": "#5aa0b8"},
    "dark kitchen":   {"peso":  7, "color": "#8e6fc0"},
    "gastrobar":      {"peso": 10, "color": "#4f9d69"},
    "taberna":        {"peso":  6, "color": "#a8703c"},
}

# --- Piezas para nombres claramente inventados -----------------------------
# Se combinan a propósito de forma un poco absurda (un sustantivo neutro +
# un complemento inventado) para que ningún nombre suene a marca registrada.
PREFIJOS = {
    "bar de barrio":  ["Bar", "Bar", "Cantina"],
    "cafetería":      ["Cafè", "Cafetería", "Cafè"],
    "hamburguesería": ["Burger", "Casa Burger", "Brasa"],
    "arrocería":      ["Arrosseria", "Casa", "Arrosseria"],
    "pizzería":       ["Pizzería", "Forn", "Pizzería"],
    "asiático":       ["Wok", "Sushi", "Fideus"],
    "dark kitchen":   ["Cuina", "Obrador", "Cuina"],
    "gastrobar":      ["Gastrobar", "Taula", "Gastrobar"],
    "taberna":        ["Taverna", "Bodega", "Taverna"],
}
NUCLEOS = [
    "Farolet", "Muntaner", "Tramuntana", "Aladroc", "Sorollet", "Boira",
    "Cudol", "Ventall", "Xaloc", "Pinyol", "Rajola", "Llebeig", "Garbí",
    "Tramús", "Cresol", "Espardenya", "Gavinot", "Timó", "Fusta", "Carnestoltes",
    "Rellotge", "Calaix", "Bufanda", "Cantonada", "Rodolí", "Escaleta",
    "Terrat", "Andana", "Clauer", "Pinzell", "Balancí", "Cresta", "Falzia",
    "Tabalet", "Pedrís", "Cistella", "Canut", "Bambú", "Regalèssia", "Tarongina",
    "Alfabeguera", "Sargantana", "Canyet", "Miraculós", "Perolet", "Llumeta",
    "Embut", "Manesa", "Rebost", "Voreta",
]
SUFIJOS = ["", "", "", " del Sud", " Vell", " Nou", " 21", " & Co.", " de Baix", " Petit"]


def nombre_ficticio(tipo, usados):
    """Combina prefijo + núcleo inventado + sufijo hasta dar con uno libre."""
    for _ in range(200):
        n = (random.choice(PREFIJOS[tipo]) + " " + random.choice(NUCLEOS)
             + random.choice(SUFIJOS))
        if n not in usados:
            usados.add(n)
            return n
    raise RuntimeError("sin nombres libres")


def entre(a, b):
    return random.randint(a, b)


# ===========================================================================
#  REGLAS DE CÁLCULO DEL HARDWARE
#  ---------------------------------------------------------------------
#  Ninguna cifra de hardware se sortea: todas se deducen del inmueble, de
#  la cocina y del servicio. El motivo es que el mapa se usa para estimar
#  un presupuesto comercial, y un presupuesto sorteado al azar no se puede
#  defender ante un cliente ni ante el tribunal del proyecto.
# ===========================================================================

def calcular_hardware(local):
    """Devuelve el equipamiento necesario y su coste estimado.

    Por qué cada regla:

    * PANTALLAS DE COCINA — una pantalla sirve para dos estaciones contiguas
      porque el cocinero levanta la vista, no camina. A partir de 60 comandas
      punta se añade una más: por encima de ese ritmo dos personas miran a la
      vez y una sola pantalla se convierte en cuello de botella. Si hay pase,
      el pase necesita la suya propia, porque quien monta los platos tiene que
      ver el pedido COMPLETO mientras las estaciones ven solo su parte.

    * PUESTOS DE TPV — uno por cada 18 mesas atendidas (interior + terraza):
      con más mesas por caja se forma cola en el cobro de la sobremesa. La
      barra suma uno propio, porque el cobro de barra es inmediato y no puede
      esperar a que el camarero de sala termine. El take-away también, ya que
      el mostrador de recogida cobra en paralelo al servicio de mesa.

    * TABLETAS DE CAMARERO — una por cada 12 mesas, que es aproximadamente el
      rango que cubre un camarero en un turno; por debajo de 8 mesas no
      compensa y se comanda desde el TPV fijo.

    * IMPRESORAS — una de tickets siempre (obligación de entregar justificante)
      más una de cocina SOLO si no hay pantalla que cubra todas las estaciones,
      o si trabaja con plataformas de reparto (la etiqueta del repartidor se
      imprime, no se lee en pantalla).

    * RED — cableada cuando hay tabletas y más de una planta o más de 160 m²:
      el wifi de un local grande con paredes de carga pierde comandas, y una
      comanda perdida es un plato que no sale. En el resto, wifi.
    """
    est = local["cocina"]["estaciones"]
    n_est = len(est)
    mesas = local["inmueble"]["mesas_interior"] + local["inmueble"]["mesas_terraza"]
    punta = local["servicio"]["comandas_punta"]

    # --- pantallas de cocina ---
    pantallas = max(1, (n_est + 1) // 2)          # una pantalla cada dos estaciones
    if punta >= 60:
        pantallas += 1                             # segundo par de ojos en punta
    if local["cocina"]["pase"]:
        pantallas += 1                             # el pase ve el pedido entero

    # --- puestos de TPV ---
    tpv = max(1, -(-mesas // 18))                  # división hacia arriba
    if "barra" in est:
        tpv += 1
    if local["servicio"]["para_llevar"]:
        tpv += 1

    # --- tabletas de camarero ---
    tabletas = mesas // 12 if mesas >= 8 else 0

    # --- impresoras ---
    impresoras = 1                                  # ticket al cliente
    if pantallas < n_est or local["servicio"]["plataformas"]:
        impresoras += 1                             # etiquetas / respaldo en cocina

    # --- red ---
    grande = local["inmueble"]["plantas"] > 1 or local["inmueble"]["m2_total"] > 160
    red = "cableada" if (tabletas > 0 and grande) else "wifi"

    # --- coste estimado de implantación (euros, PVP orientativo 2026) ---
    # Precios de catálogo genérico; el cableado se cobra por punto de red
    # porque es la partida que más se dispara y conviene verla aparte.
    coste = (pantallas * 420          # pantalla táctil 15" + soporte
             + tpv * 690              # terminal + cajón + periféricos
             + tabletas * 260         # tableta robusta + funda
             + impresoras * 180       # térmica de 80 mm
             + (140 * (pantallas + tpv) if red == "cableada" else 90))
    coste += 250                       # jornada de instalación y formación

    return {
        "pantallas_cocina": pantallas,
        "puestos_tpv": tpv,
        "tabletas_camarero": tabletas,
        "impresoras": impresoras,
        "red": red,
        "coste_implantacion": int(round(coste / 10) * 10),
    }


def calcular_encaje(local):
    """Puntúa de 0 a 100 lo bien que le encaja NUESTRO sistema, con su razón.

    La idea de fondo: nuestro producto se licencia por LOCAL, no por terminal.
    Por eso encaja mejor cuanto más equipo necesita el local, porque es ahí
    donde la competencia (licencia por pantalla o por TPV) se vuelve cara.
    Un local pequeño con una pantalla y un TPV no nota la diferencia, y
    ofrecérselo con insistencia es perder tiempo comercial.
    """
    hw = local["hardware"]
    p = 0
    razones = []

    # Terminales totales: el multiplicador del coste de la competencia.
    terminales = hw["pantallas_cocina"] + hw["puestos_tpv"]
    p += min(40, terminales * 7)
    if terminales >= 5:
        razones.append(f"{hw['pantallas_cocina']} pantallas y {hw['puestos_tpv']} TPV: "
                       f"con la competencia pagaría {terminales} licencias en vez de una")
    else:
        razones.append(f"solo {terminales} terminales, el ahorro por licencia es modesto")

    # Estaciones: cuantas más, más valor aporta el enrutado de comandas.
    n_est = len(local["cocina"]["estaciones"])
    p += n_est * 5
    if n_est >= 4:
        razones.append(f"{n_est} estaciones: el enrutado por estación evita que "
                       "cocina trabaje con una comanda en papel")

    # Volumen: por debajo de 30 comandas punta el KDS es un lujo.
    punta = local["servicio"]["comandas_punta"]
    if punta >= 70:
        p += 18
        razones.append(f"{punta} comandas en punta, volumen alto: el tiempo por plato se nota")
    elif punta >= 40:
        p += 11
    elif punta < 25:
        p -= 12
        razones.append(f"{punta} comandas en punta: volumen bajo, se apaña con comanda de voz")

    # Reparto: nuestro módulo de plataformas es diferencial.
    if local["servicio"]["plataformas"]:
        p += 12
        razones.append("trabaja con plataformas de reparto, donde nuestro agregador "
                       "de pedidos ahorra una tableta por plataforma")

    # Pase: el modo pase es nuestra pantalla más trabajada.
    if local["cocina"]["pase"]:
        p += 8
        razones.append("tiene pase, y la pantalla de pase es nuestra función más diferencial")

    # Dark kitchen: todo pedido entra por canal digital, encaje natural.
    if local["tipo"] == "dark kitchen":
        p += 10
        razones.append("dark kitchen: el 100 % de las comandas entran ya en digital")

    # Local muy pequeño: penaliza, no hay hueco físico ni presupuesto.
    if local["inmueble"]["m2_cocina"] < 18:
        p -= 8
        razones.append(f"cocina de {local['inmueble']['m2_cocina']} m²: poco sitio para "
                       "montar más de una pantalla")

    p = max(0, min(100, p))
    return p, "; ".join(razones) + "."


def generar_local(idx, usados):
    tipo = random.choices(list(TIPOS), weights=[t["peso"] for t in TIPOS.values()])[0]
    barrio = random.choice(list(BARRIOS))
    lat_a, lat_b, lon_a, lon_b = BARRIOS[barrio]
    lat = round(random.uniform(lat_a, lat_b), 5)
    lon = round(random.uniform(lon_a, lon_b), 5)

    # --- inmueble -----------------------------------------------------
    # La dark kitchen no tiene sala: solo cocina y mostrador de recogida.
    if tipo == "dark kitchen":
        m2_total = entre(45, 110)
        m2_cocina = int(m2_total * random.uniform(0.70, 0.85))
        m2_sala = m2_total - m2_cocina
        mesas_int = 0
        terraza = False
        mesas_ter = 0
        plantas = 1
    else:
        # La cafetería y el bar son locales estrechos; la arrocería y el
        # gastrobar necesitan sala porque el ticket se cobra sentado.
        if tipo in ("cafetería", "bar de barrio", "taberna"):
            m2_total = entre(55, 150)
        elif tipo in ("arrocería", "gastrobar"):
            m2_total = entre(120, 330)
        else:
            m2_total = entre(80, 220)
        m2_cocina = int(m2_total * random.uniform(0.18, 0.34))
        m2_sala = m2_total - m2_cocina
        # ~1,6 m² de sala por comensal y 4 comensales por mesa (norma de sala)
        mesas_int = max(2, int(m2_sala / 6.4))
        terraza = random.random() < (0.75 if tipo in ("bar de barrio", "cafetería") else 0.5)
        mesas_ter = entre(3, 16) if terraza else 0
        plantas = 2 if (m2_total > 180 and random.random() < 0.45) else 1

    aforo = mesas_int * 4 + mesas_ter * 4 + (entre(6, 14) if tipo != "dark kitchen" else 0)

    # --- cocina -------------------------------------------------------
    # Las estaciones no son libres: cada tipo tiene un núcleo obligatorio.
    base = {
        "bar de barrio":  ["plancha", "barra"],
        "cafetería":      ["barra", "fríos"],
        "hamburguesería": ["plancha", "freidora"],
        "arrocería":      ["fuegos", "fríos"],
        "pizzería":       ["horno", "fríos"],
        "asiático":       ["wok", "fríos"],
        "dark kitchen":   ["plancha", "freidora"],
        "gastrobar":      ["plancha", "fríos", "horno"],
        "taberna":        ["plancha", "barra"],
    }[tipo]
    estaciones = list(base)
    for extra in ("freidora", "horno", "fríos", "barra", "postres"):
        if extra not in estaciones and random.random() < 0.35:
            estaciones.append(extra)
    # El pase aparece cuando hay cocina suficiente para separar montaje:
    # con menos de tres estaciones nadie dedica una persona solo al pase.
    pase = len(estaciones) >= 3 and random.random() < 0.6
    # Potencia: ~1,6 kW por m² de cocina más 4 kW fijos de frío y luces.
    potencia = round(4 + m2_cocina * 1.6 * random.uniform(0.85, 1.2), 1)
    extraccion = random.choice(["campana mural", "campana central", "campana con "
                                "recuperador", "sin campana homologada"])
    camara = random.random() < (0.85 if m2_cocina >= 25 else 0.45)

    # --- servicio -----------------------------------------------------
    plazas = max(mesas_int * 4, 10)
    punta = int(plazas * random.uniform(0.7, 1.5)) + (entre(25, 70) if tipo == "dark kitchen" else 0)
    punta = max(8, punta)
    ticket = {
        "bar de barrio": (9, 18), "cafetería": (6, 14), "hamburguesería": (12, 22),
        "arrocería": (24, 45), "pizzería": (13, 24), "asiático": (14, 28),
        "dark kitchen": (11, 20), "gastrobar": (22, 48), "taberna": (12, 25),
    }[tipo]
    ticket_medio = round(random.uniform(*ticket), 2)
    para_llevar = True if tipo == "dark kitchen" else random.random() < 0.55
    plataformas = (["Glovo", "Uber Eats", "Just Eat"] if tipo == "dark kitchen"
                   else random.sample(["Glovo", "Uber Eats", "Just Eat"],
                                      k=random.choice([0, 0, 1, 1, 2, 3])))

    local = {
        "id": idx,
        "nombre": nombre_ficticio(tipo, usados),
        "tipo": tipo,
        "barrio": barrio,
        "lat": lat,
        "lon": lon,
        "inmueble": {
            "m2_total": m2_total, "m2_sala": m2_sala, "m2_cocina": m2_cocina,
            "plantas": plantas, "terraza": terraza, "mesas_terraza": mesas_ter,
            "mesas_interior": mesas_int, "aforo": aforo,
        },
        "cocina": {
            "estaciones": estaciones, "pase": pase, "potencia_kw": potencia,
            "extraccion": extraccion, "camara_frigorifica": camara,
        },
        "servicio": {
            "comandas_punta": punta, "ticket_medio": ticket_medio,
            "para_llevar": para_llevar, "plataformas": plataformas,
        },
    }
    local["hardware"] = calcular_hardware(local)
    p, razon = calcular_encaje(local)
    local["encaje"] = p
    local["encaje_razon"] = razon
    return local


def main():
    usados = set()
    locales = [generar_local(i + 1, usados) for i in range(100)]
    destino = Path(__file__).resolve().parent / "locales.json"
    datos = {
        "aviso": ("DATOS FICTICIOS. Locales, nombres, direcciones y cifras "
                  "generados por sorteo para un trabajo académico del CFGS ASIR. "
                  "No corresponden a ningún negocio real de València."),
        "semilla": 2026,
        "colores_tipo": {t: v["color"] for t, v in TIPOS.items()},
        "locales": locales,
    }
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")

    # Copia del MISMO contenido como script JavaScript. Motivo: el navegador
    # bloquea fetch() sobre file:// por política de mismo origen, y la página
    # tiene que poder abrirse con doble clic desde el disco de la VM, sin
    # servidor. El HTML intenta primero el .json (servidor) y, si falla,
    # carga este .js. Nunca se editan a mano: los escribe este script.
    (destino.parent / "locales.js").write_text(
        "window.DATOS_MERCADO = " + json.dumps(datos, ensure_ascii=False) + ";",
        encoding="utf-8")

    print(f"Escritos {len(locales)} locales ficticios en {destino}")
    print(f"  y su respaldo para file:// en {destino.parent / 'locales.js'}")
    print(f"  pantallas de cocina totales: {sum(l['hardware']['pantallas_cocina'] for l in locales)}")
    print(f"  puestos de TPV totales:      {sum(l['hardware']['puestos_tpv'] for l in locales)}")
    print(f"  encaje medio:                {sum(l['encaje'] for l in locales)/len(locales):.1f}")


if __name__ == "__main__":
    main()
